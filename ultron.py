"""Ultron Exploit Engine — deterministic exploit executor for Jarvis Protocol.

Runs exactly 3 payloads per vulnerability type in deterministic order
and reports per-payload results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from catalog import HTTPTest


@dataclass
class ExploitResult:
    """Result of executing a single exploit payload.

    Attributes:
        payload: The HTTPTest payload that was executed.
        status_code: HTTP status code returned by the server.
        blocked: True if the status code indicates the exploit was blocked
            (400, 401, or 403).
        response_body: Raw response body text.
    """

    payload: HTTPTest
    status_code: int
    blocked: bool
    response_body: str


class UltronEngine:
    """Deterministic exploit executor.

    Runs exactly 3 payloads per vulnerability type against the
    patched Express app and reports whether each was blocked.
    """

    def execute(
        self,
        payloads: list[HTTPTest],
        app_url: str,
        timeout: float = 10.0,
    ) -> list[ExploitResult]:
        """Execute payloads in deterministic order.

        Args:
            payloads: List of HTTPTest exploit payloads to execute.
            app_url: Base URL of the running Express app.
            timeout: Per-request timeout in seconds.

        Returns:
            A list of ExploitResult, one per payload, in the same order.

        Raises:
            requests.Timeout: If any single payload exceeds the timeout.
                The caller (RewardCalculator) is responsible for catching
                the timeout and triggering a server restart.
        """
        import requests as http_requests

        results = []
        for payload in payloads:
            response = http_requests.request(
                method=payload.method,
                url=f"{app_url}{payload.path}",
                headers=payload.headers,
                json=payload.body,
                timeout=timeout,
            )
            blocked = response.status_code in (400, 401, 403)
            results.append(
                ExploitResult(
                    payload=payload,
                    status_code=response.status_code,
                    blocked=blocked,
                    response_body=response.text,
                )
            )
        return results
