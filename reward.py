"""Reward calculator implementing the 4-gate fail-fast waterfall pipeline.

Gates are evaluated in strict order:
  1. Format Compliance — checks for ``<reasoning>`` and ``<patch>`` tags
  2. Syntax / Liveness — applies patch, verifies server health
  3. Happy-Path — runs legitimate user requests
  4. Security (Ultron) — runs exploit payloads, scores proportionally
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests as http_requests

if TYPE_CHECKING:
    from catalog import HTTPTest, VulnerabilityEntry
    from parser import OutputParser


@dataclass
class GateResult:
    """Result of evaluating a single gate in the reward waterfall.

    Attributes:
        gate: Gate number (1–4).
        passed: Whether the gate was passed.
        reward: Reward value assigned by this gate.
        detail: Human-readable description of the outcome.
    """

    gate: int
    passed: bool
    reward: float
    detail: str


class RewardCalculator:
    """Computes episode reward via a 4-gate fail-fast waterfall.

    Reward range: [-1.0, +1.0].
    """

    def __init__(self, parser: OutputParser) -> None:
        """Initialize with an OutputParser instance.

        Args:
            parser: The parser used to extract patches from agent output.
        """
        self.parser = parser

    def evaluate(
        self,
        agent_output: str,
        vuln_entry: VulnerabilityEntry,
        app_url: str,
        env: object,
    ) -> tuple[float, dict]:
        """Run the full 4-gate waterfall and return (total_reward, info_dict).

        Args:
            agent_output: Raw LLM output string.
            vuln_entry: The current vulnerability being evaluated.
            app_url: Base URL of the running Express app.
            env: The JarvisEnv instance (used for timeout-triggered restarts).

        Returns:
            A tuple of (total_reward, info) where info contains keys
            ``"gates"``, ``"gate_reached"``, and ``"total_reward"``.
        """
        info: dict = {"gates": [], "gate_reached": 0, "total_reward": 0.0}

        # Gate 1: Format Compliance
        gate1 = self._gate1_format(agent_output)
        info["gates"].append(gate1.__dict__)
        info["gate_reached"] = 1
        if not gate1.passed:
            info["total_reward"] = gate1.reward
            return gate1.reward, info

        # Gate 2: Syntax / Liveness
        parse_result = self.parser.parse(agent_output)
        gate2 = self._gate2_syntax_liveness(parse_result.patch, vuln_entry, app_url, env)
        info["gates"].append(gate2.__dict__)
        info["gate_reached"] = 2
        if not gate2.passed:
            info["total_reward"] = gate2.reward
            return gate2.reward, info

        # Gate 3: Happy-Path
        gate3 = self._gate3_happy_path(vuln_entry.happy_path_tests, app_url, env)
        info["gates"].append(gate3.__dict__)
        info["gate_reached"] = 3
        if not gate3.passed:
            info["total_reward"] = gate3.reward
            return gate3.reward, info

        # Gate 4: Security (Ultron)
        gate4 = self._gate4_security(vuln_entry.ultron_payloads, app_url, env)
        info["gates"].append(gate4.__dict__)
        info["gate_reached"] = 4
        info["total_reward"] = gate4.reward
        return gate4.reward, info

    def _gate1_format(self, agent_output: str) -> GateResult:
        """Gate 1: Check for both ``<reasoning>`` and ``<patch>`` tag pairs.

        Returns:
            GateResult with reward 0.0 on pass, -0.5 on failure.
        """
        has_reasoning = "<reasoning>" in agent_output and "</reasoning>" in agent_output
        has_patch = "<patch>" in agent_output and "</patch>" in agent_output
        if has_reasoning and has_patch:
            return GateResult(1, True, 0.0, "Format OK")
        missing = []
        if not has_reasoning:
            missing.append("<reasoning>")
        if not has_patch:
            missing.append("<patch>")
        return GateResult(1, False, -0.5, f"Missing required tags: {', '.join(missing)}")

    def _gate2_syntax_liveness(
        self,
        patch_code: str,
        vuln_entry: VulnerabilityEntry,
        app_url: str,
        env: object,
    ) -> GateResult:
        """Gate 2: Write patch to disk, reload, and verify server health.

        On any ``requests.Timeout``, triggers ``env._restart_server()``
        and returns a failure result.

        Returns:
            GateResult with reward 0.0 on pass, -1.0 on failure.
        """
        # 1. Write patch to disk
        route_file_path = os.path.join(env.app_dir, vuln_entry.route_file)
        with open(route_file_path, "w") as f:
            f.write(patch_code)

        # Derive route_key from route_file: "routes/login.js" → "login"
        route_key = os.path.splitext(os.path.basename(vuln_entry.route_file))[0]

        # 2. POST /_control/reload
        try:
            resp = http_requests.post(
                f"{app_url}/_control/reload",
                json={"routeFile": vuln_entry.route_file, "routeKey": route_key},
                timeout=env.HTTP_TIMEOUT,
            )
        except http_requests.Timeout:
            env._restart_server()
            return GateResult(2, False, -1.0, "Timeout during reload")

        if resp.status_code == 500:
            return GateResult(2, False, -1.0, f"SyntaxError: {resp.text}")

        # 3. GET /health
        try:
            health_resp = http_requests.get(
                f"{app_url}/health",
                timeout=env.HTTP_TIMEOUT,
            )
        except http_requests.Timeout:
            env._restart_server()
            return GateResult(2, False, -1.0, "Timeout during health check")

        if health_resp.status_code != 200:
            return GateResult(2, False, -1.0, "Health check failed")

        return GateResult(2, True, 0.0, "Syntax OK, server alive")

    def _gate3_happy_path(
        self,
        tests: list[HTTPTest],
        app_url: str,
        env: object,
    ) -> GateResult:
        """Gate 3: Execute all happy-path tests.

        On any ``requests.Timeout``, triggers ``env._restart_server()``
        and returns a failure result.

        Returns:
            GateResult with reward 0.0 on pass, -1.0 on failure.
        """
        for test in tests:
            try:
                resp = http_requests.request(
                    method=test.method,
                    url=f"{app_url}{test.path}",
                    headers=test.headers,
                    json=test.body,
                    timeout=env.HTTP_TIMEOUT,
                )
            except http_requests.Timeout:
                env._restart_server()
                return GateResult(3, False, -1.0, "Timeout during happy path")

            if resp.status_code != test.expected_status:
                return GateResult(
                    3,
                    False,
                    -1.0,
                    f"Happy path failed: expected {test.expected_status} got {resp.status_code}",
                )

            if test.expected_body is not None and not self._body_matches(resp.text, test.expected_body):
                return GateResult(
                    3,
                    False,
                    -1.0,
                    f"Happy path body mismatch",
                )

        return GateResult(3, True, 0.0, "All happy paths passed")

    def _gate4_security(
        self,
        payloads: list[HTTPTest],
        app_url: str,
        env: object,
    ) -> GateResult:
        """Gate 4: Execute Ultron exploit payloads and score proportionally.

        Reward is ``K/3`` where K is the number of blocked payloads.
        On any ``requests.Timeout``, triggers ``env._restart_server()``
        and returns a failure result.

        Returns:
            GateResult with proportional reward on pass, -1.0 on timeout.
        """
        blocked = 0
        for payload in payloads:
            try:
                resp = http_requests.request(
                    method=payload.method,
                    url=f"{app_url}{payload.path}",
                    headers=payload.headers,
                    json=payload.body,
                    timeout=env.HTTP_TIMEOUT,
                )
            except http_requests.Timeout:
                env._restart_server()
                return GateResult(4, False, -1.0, "Timeout during Ultron")

            if resp.status_code in (400, 401, 403):
                blocked += 1

        reward = round(blocked / len(payloads), 2)
        return GateResult(4, blocked > 0, reward, f"{blocked}/{len(payloads)} exploits blocked")

    def _body_matches(self, response_text: str, expected_body) -> bool:
        """Check if the response body matches the expected body.

        Supports string partial matching and dict key-value matching.
        """
        if isinstance(expected_body, str):
            return expected_body in response_text
        if isinstance(expected_body, dict):
            try:
                body = json.loads(response_text)
                return all(body.get(k) == v for k, v in expected_body.items())
            except json.JSONDecodeError:
                return False
        return True
