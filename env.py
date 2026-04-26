"""JarvisEnv — OpenEnv-compliant RL environment for training security patching agents."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field


@dataclass
class Observation:
    """Data returned to the agent at the start of an episode.

    Contains the vulnerable code snippet, vulnerability metadata,
    and episode status information.
    """

    vuln_id: str | None = None
    vuln_type: str | None = None
    route_path: str | None = None
    vulnerable_code: str | None = None
    description: str | None = None
    episode_active: bool = False


class JarvisEnv:
    """OpenEnv-compliant RL environment for training security patching agents.

    Manages a long-lived Node.js Express app, applying agent-generated patches
    via hot-reload, then evaluating them through a 4-gate fail-fast waterfall
    reward pipeline.
    """

    HTTP_TIMEOUT: float = 10.0  # seconds; any request exceeding this is treated as a hang

    def __init__(
        self,
        catalog_path: str = "./vulnerabilities",
        app_dir: str = "./express_app",
    ) -> None:
        """Initialize the environment.

        Loads the VulnerabilityCatalog, assigns a dynamic port,
        and starts the Express app subprocess.

        Args:
            catalog_path: Path to the vulnerability catalog directory.
            app_dir: Path to the express_app directory.
        """
        import sys

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        self.app_dir = os.path.abspath(app_dir)
        self.app_process = None
        self.app_port = self._find_free_port()
        self.current_vuln = None
        self.current_observation = None
        self.episode_active = False

        from vulnerabilities import load_catalog

        self.catalog = load_catalog()

        from parser import OutputParser
        from reward import RewardCalculator

        self.parser = OutputParser()
        self.reward_calculator = RewardCalculator(self.parser)

        self._start_server()

    @staticmethod
    def _find_free_port() -> int:
        """Find and return a free port on localhost."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def reset(self) -> Observation:
        """Select a vulnerability, restore original code, return observation.

        Samples a vulnerability from the catalog, copies the original
        vulnerable file from ``_originals/`` back to the active route path,
        calls ``/_control/reload`` to hot-swap the handler, and returns
        an Observation with the vulnerability metadata.
        """
        import shutil

        import requests as http_requests

        self.current_vuln = self.catalog.sample()

        # Restore original vulnerable file
        original_path = os.path.join(
            self.app_dir, "_originals", os.path.basename(self.current_vuln.route_file)
        )
        active_path = os.path.join(self.app_dir, self.current_vuln.route_file)
        shutil.copy2(original_path, active_path)

        # Hot-reload the original code
        route_key = os.path.splitext(os.path.basename(self.current_vuln.route_file))[0]
        try:
            http_requests.post(
                f"http://localhost:{self.app_port}/_control/reload",
                json={"routeFile": self.current_vuln.route_file, "routeKey": route_key},
                timeout=self.HTTP_TIMEOUT,
            )
        except http_requests.Timeout:
            self._restart_server()

        self.current_observation = Observation(
            vuln_id=self.current_vuln.id,
            vuln_type=self.current_vuln.vuln_type,
            route_path=self.current_vuln.route_path,
            vulnerable_code=self.current_vuln.vulnerable_code,
            description=self.current_vuln.description,
            episode_active=True,
        )
        self.episode_active = True
        return self.current_observation

    def step(self, agent_output: str) -> tuple[float, bool, dict]:
        """Run 4-gate waterfall: parse → apply → test → attack → reward.

        CRITICAL: Every HTTP request inside step() uses self.HTTP_TIMEOUT.
        If ANY request (reload, health, happy-path, Ultron) raises a
        requests.Timeout, step() immediately:
          1. Returns reward = -1.0
          2. Calls self._restart_server() to kill and respawn Node

        Args:
            agent_output: The raw string output from the LLM agent containing
                ``<reasoning>`` and ``<patch>`` tags.

        Returns:
            A tuple of (reward, done, info) where reward is in [-1.0, +1.0],
            done is always True (single-step episodes), and info contains
            per-gate evaluation details.
        """
        app_url = f"http://localhost:{self.app_port}"
        reward, info = self.reward_calculator.evaluate(
            agent_output, self.current_vuln, app_url, self
        )
        self.episode_active = False
        return reward, True, info

    def state(self) -> Observation:
        """Return current observation and episode status.

        If no ``reset()`` has been called yet, returns an Observation
        with ``episode_active=False`` and all other fields set to None.
        """
        if self.current_observation:
            return self.current_observation
        return Observation()

    # ── Server Lifecycle Methods ──────────────────────────────────────

    def _start_server(self) -> None:
        """Spawn a new Node.js subprocess for the Express app.

        Sets ``self.app_process`` to the new Popen handle.
        Waits up to 5 seconds for ``/health`` to return 200.
        Raises RuntimeError if the server fails to start.
        """
        import time

        import requests as http_requests

        env = os.environ.copy()
        env["PORT"] = str(self.app_port)
        self.app_process = subprocess.Popen(
            ["node", "server.js"],
            cwd=self.app_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for health check
        url = f"http://localhost:{self.app_port}/health"
        for _ in range(50):  # 5 seconds total
            time.sleep(0.1)
            try:
                resp = http_requests.get(url, timeout=1)
                if resp.status_code == 200:
                    return
            except Exception:
                pass
        raise RuntimeError(f"Express app failed to start on port {self.app_port}")

    def _stop_server(self) -> None:
        """Kill the current Node.js subprocess unconditionally.

        Uses ``process.kill()`` (SIGKILL) to guarantee termination even if
        the event loop is blocked by an infinite loop. Sets
        ``self.app_process`` to None after cleanup.
        """
        if self.app_process:
            self.app_process.kill()
            self.app_process.wait()
            self.app_process = None

    def _restart_server(self) -> None:
        """Stop then start the server. Used after any HTTP timeout.

        Calls ``self._stop_server()`` then ``self._start_server()``.
        This is the ONLY safe recovery path when the Node event loop
        is unresponsive.
        """
        print("[JarvisEnv] Restarting Express server after timeout...")
        self._stop_server()
        self.app_port = self._find_free_port()
        self._start_server()
