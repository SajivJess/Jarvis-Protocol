"""Tests for Tasks 3, 4, and 5: Vulnerability Catalog, Output Parser, Ultron Engine."""

import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from catalog import VulnerabilityCatalog, VulnerabilityEntry, HTTPTest
from parser import OutputParser, ParseResult
from ultron import UltronEngine, ExploitResult


# ── Task 3: Vulnerability Catalog ──────────────────────────────────────


class TestVulnerabilityCatalog:
    """Tests for catalog loading, sample(), and get_by_id()."""

    def test_load_catalog(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        assert isinstance(catalog, VulnerabilityCatalog)
        assert len(catalog.entries) == 3

    def test_catalog_entry_ids(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        ids = {e.id for e in catalog.entries}
        assert ids == {"nosql-injection", "path-traversal", "bola"}

    def test_each_entry_has_3_ultron_payloads(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        for entry in catalog.entries:
            assert len(entry.ultron_payloads) == 3, f"{entry.id} has {len(entry.ultron_payloads)} payloads"

    def test_each_entry_has_at_least_2_happy_path_tests(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        for entry in catalog.entries:
            assert len(entry.happy_path_tests) >= 2, f"{entry.id} has {len(entry.happy_path_tests)} happy paths"

    def test_nosql_injection_entry(self):
        from vulnerabilities.nosql_injection import ENTRY

        assert ENTRY.id == "nosql-injection"
        assert ENTRY.route_path == "/api/login"
        assert ENTRY.route_file == "routes/login.js"
        assert "matchesQuery" in ENTRY.vulnerable_code
        assert len(ENTRY.ultron_payloads) == 3
        assert all(p.method == "POST" for p in ENTRY.ultron_payloads)

    def test_path_traversal_entry(self):
        from vulnerabilities.path_traversal import ENTRY

        assert ENTRY.id == "path-traversal"
        assert ENTRY.route_path == "/api/files/:filename"
        assert ENTRY.route_file == "routes/files.js"
        assert "ALLOWED_DIR" in ENTRY.vulnerable_code
        assert len(ENTRY.ultron_payloads) == 3
        assert all(p.method == "GET" for p in ENTRY.ultron_payloads)

    def test_bola_entry(self):
        from vulnerabilities.bola import ENTRY

        assert ENTRY.id == "bola"
        assert ENTRY.route_path == "/api/notes/:id"
        assert ENTRY.route_file == "routes/notes.js"
        assert "x-user" in ENTRY.vulnerable_code
        assert len(ENTRY.ultron_payloads) == 3
        assert all(p.method == "GET" for p in ENTRY.ultron_payloads)

    def test_sample_returns_entry(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        entry = catalog.sample()
        assert isinstance(entry, VulnerabilityEntry)
        assert entry.id in {"nosql-injection", "path-traversal", "bola"}

    def test_sample_empty_catalog_raises(self):
        catalog = VulnerabilityCatalog(entries=[])
        with pytest.raises(ValueError):
            catalog.sample()

    def test_get_by_id_found(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        entry = catalog.get_by_id("nosql-injection")
        assert entry.id == "nosql-injection"

    def test_get_by_id_not_found(self):
        from vulnerabilities import load_catalog

        catalog = load_catalog()
        with pytest.raises(KeyError):
            catalog.get_by_id("nonexistent")


# ── Task 4: Output Parser ──────────────────────────────────────────────


class TestOutputParser:
    """Tests for OutputParser.parse()."""

    def setup_method(self):
        self.parser = OutputParser()

    def test_patch_tags_extraction(self):
        output = "<reasoning>Fix the bug</reasoning>\n<patch>const x = 1;</patch>"
        result = self.parser.parse(output)
        assert result.reasoning == "Fix the bug"
        assert result.patch == "const x = 1;"
        assert result.parse_method == "patch_tags"

    def test_markdown_fallback(self):
        output = "Here is the fix:\n```javascript\nconst x = 1;\n```"
        result = self.parser.parse(output)
        assert result.patch == "const x = 1;"
        assert result.parse_method == "markdown_fallback"

    def test_patch_tags_preferred_over_markdown(self):
        output = "<patch>from tags</patch>\n```\nfrom markdown\n```"
        result = self.parser.parse(output)
        assert result.patch == "from tags"
        assert result.parse_method == "patch_tags"

    def test_reasoning_extraction(self):
        output = "<reasoning>Step 1: analyze\nStep 2: fix</reasoning>\n<patch>code</patch>"
        result = self.parser.parse(output)
        assert result.reasoning == "Step 1: analyze\nStep 2: fix"

    def test_no_reasoning(self):
        output = "<patch>code</patch>"
        result = self.parser.parse(output)
        assert result.reasoning is None
        assert result.patch == "code"

    def test_empty_patch_content(self):
        output = "<patch>   \n  </patch>"
        result = self.parser.parse(output)
        assert result.parse_method == "failed"
        assert result.patch is None

    def test_no_extractable_content(self):
        output = "Just some text without any tags or code blocks"
        result = self.parser.parse(output)
        assert result.parse_method == "failed"
        assert result.patch is None

    def test_nested_tags_takes_first(self):
        output = "<patch>first</patch> some text <patch>second</patch>"
        result = self.parser.parse(output)
        assert result.patch == "first"

    def test_multiple_code_blocks_takes_first(self):
        output = "```\nfirst block\n```\n```\nsecond block\n```"
        result = self.parser.parse(output)
        assert result.patch == "first block"
        assert result.parse_method == "markdown_fallback"

    def test_empty_markdown_block_falls_through(self):
        output = "```\n   \n```"
        result = self.parser.parse(output)
        assert result.parse_method == "failed"


# ── Task 5: Ultron Engine ──────────────────────────────────────────────


class TestUltronEngine:
    """Tests for UltronEngine.execute()."""

    def test_execute_returns_results(self, monkeypatch):
        """Test that execute returns ExploitResult list with correct structure."""

        class MockResponse:
            status_code = 200
            text = '{"message": "ok"}'

        def mock_request(**kwargs):
            return MockResponse()

        import requests as http_requests

        monkeypatch.setattr(http_requests, "request", mock_request)

        engine = UltronEngine()
        payloads = [
            HTTPTest(method="POST", path="/api/login", headers={}, body={"a": "b"}, expected_status=200),
        ]
        results = engine.execute(payloads, "http://localhost:3000")
        assert len(results) == 1
        assert isinstance(results[0], ExploitResult)
        assert results[0].status_code == 200
        assert results[0].blocked is False

    def test_blocked_detection(self, monkeypatch):
        """Test that 400/401/403 are detected as blocked."""

        class MockResponse:
            status_code = 403
            text = '{"error": "forbidden"}'

        def mock_request(**kwargs):
            return MockResponse()

        import requests as http_requests

        monkeypatch.setattr(http_requests, "request", mock_request)

        engine = UltronEngine()
        payloads = [
            HTTPTest(method="GET", path="/api/notes/1", headers={}, body=None, expected_status=200),
        ]
        results = engine.execute(payloads, "http://localhost:3000")
        assert results[0].blocked is True

    def test_timeout_propagates(self, monkeypatch):
        """Test that requests.Timeout is NOT caught internally."""
        import requests as http_requests

        def mock_request(**kwargs):
            raise http_requests.Timeout("Connection timed out")

        monkeypatch.setattr(http_requests, "request", mock_request)

        engine = UltronEngine()
        payloads = [
            HTTPTest(method="GET", path="/test", headers={}, body=None, expected_status=200),
        ]
        with pytest.raises(http_requests.Timeout):
            engine.execute(payloads, "http://localhost:3000")

    def test_deterministic_order(self, monkeypatch):
        """Test that payloads are executed in the same order they are provided."""
        call_order = []

        class MockResponse:
            status_code = 200
            text = ""

        def mock_request(**kwargs):
            call_order.append(kwargs["url"])
            return MockResponse()

        import requests as http_requests

        monkeypatch.setattr(http_requests, "request", mock_request)

        engine = UltronEngine()
        payloads = [
            HTTPTest(method="GET", path="/a", headers={}, body=None, expected_status=200),
            HTTPTest(method="GET", path="/b", headers={}, body=None, expected_status=200),
            HTTPTest(method="GET", path="/c", headers={}, body=None, expected_status=200),
        ]
        engine.execute(payloads, "http://localhost:3000")
        assert call_order == [
            "http://localhost:3000/a",
            "http://localhost:3000/b",
            "http://localhost:3000/c",
        ]
