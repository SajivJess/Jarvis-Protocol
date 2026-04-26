"""Vulnerability catalog data structures for Jarvis Protocol.

Defines the core dataclasses used to represent vulnerabilities,
HTTP test cases, and the catalog that holds all entries.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class HTTPTest:
    """A single HTTP request used for happy-path or exploit testing.

    Attributes:
        method: HTTP method — ``"GET"`` or ``"POST"``.
        path: Request path (may include URL parameters).
        headers: Request headers (e.g. auth tokens).
        body: Request body for POST requests; None for GET.
        expected_status: Expected HTTP status code.
        expected_body: Expected response body (partial match), or None.
    """

    method: str
    path: str
    headers: dict
    body: dict | None
    expected_status: int
    expected_body: dict | str | None = None


@dataclass
class VulnerabilityEntry:
    """A single vulnerability in the catalog.

    Attributes:
        id: Unique identifier, e.g. ``"nosql-injection"``.
        vuln_type: Human-readable type, e.g. ``"NoSQL Injection"``.
        route_path: Express route path, e.g. ``"/api/login"``.
        route_file: Relative path to the route handler file.
        vulnerable_code: Full source of the vulnerable handler.
        description: Human-readable description for the agent.
        happy_path_tests: At least 2 legitimate HTTP requests.
        ultron_payloads: Exactly 3 exploit payloads.
        expected_secure_status: Status codes indicating a blocked exploit.
    """

    id: str
    vuln_type: str
    route_path: str
    route_file: str
    vulnerable_code: str
    description: str
    happy_path_tests: list[HTTPTest]
    ultron_payloads: list[HTTPTest]
    expected_secure_status: list[int]


@dataclass
class VulnerabilityCatalog:
    """Collection of vulnerability entries.

    Provides random sampling for training variety and deterministic
    lookup for debugging.

    Attributes:
        entries: List of all vulnerability entries in the catalog.
    """

    entries: list[VulnerabilityEntry]

    def sample(self) -> VulnerabilityEntry:
        """Return a randomly selected vulnerability entry.

        Used during training to provide varied scenarios across episodes.

        Returns:
            A randomly chosen VulnerabilityEntry from the catalog.

        Raises:
            ValueError: If the catalog is empty.
        """
        if not self.entries:
            raise ValueError("Cannot sample from an empty catalog")
        return random.choice(self.entries)

    def get_by_id(self, vuln_id: str) -> VulnerabilityEntry:
        """Return the vulnerability entry with the given ID.

        Used for deterministic selection during debugging and testing.

        Args:
            vuln_id: The unique identifier of the vulnerability.

        Returns:
            The matching VulnerabilityEntry.

        Raises:
            KeyError: If no entry with the given ID exists.
        """
        for entry in self.entries:
            if entry.id == vuln_id:
                return entry
        raise KeyError(f"No vulnerability entry with id '{vuln_id}'")
