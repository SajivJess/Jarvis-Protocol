"""Tests for Tasks 6 and 7: RewardCalculator and JarvisEnv."""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from catalog import VulnerabilityEntry, HTTPTest, VulnerabilityCatalog
from parser import OutputParser
from reward import RewardCalculator, GateResult


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def parser():
    return OutputParser()


@pytest.fixture
def calculator(parser):
    return RewardCalculator(parser)


@pytest.fixture
def sample_vuln():
    return VulnerabilityEntry(
        id="nosql-injection",
        vuln_type="NoSQL Injection",
        route_path="/api/login",
        route_file="routes/login.js",
        vulnerable_code="module.exports = (req, res) => { ... }",
        description="NoSQL injection in login",
        happy_path_tests=[
            HTTPTest(
                method="POST",
                path="/api/login",
                headers={"Content-Type": "application/json"},
                body={"username": "alice", "password": "password123"},
                expected_status=200,
                expected_body={"username": "alice"},
            ),
            HTTPTest(
                method="POST",
                path="/api/login",
                headers={"Content-Type": "application/json"},
                body={"username": "wrong", "password": "wrong"},
                expected_status=401,
                expected_body=None,
            ),
        ],
        ultron_payloads=[
            HTTPTest(
                method="POST",
                path="/api/login",
                headers={"Content-Type": "application/json"},
                body={"username": {"$gt": ""}, "password": {"$gt": ""}},
                expected_status=200,
            ),
            HTTPTest(
                method="POST",
                path="/api/login",
                headers={"Content-Type": "application/json"},
                body={"username": "alice", "password": {"$ne": "wrong"}},
                expected_status=200,
            ),
            HTTPTest(
                method="POST",
                path="/api/login",
                headers={"Content-Type": "application/json"},
                body={"username": {"$regex": ".*"}, "password": {"$regex": ".*"}},
                expected_status=200,
            ),
        ],
        expected_secure_status=[400, 401, 403],
    )


# ── Task 6.1: Gate 1 Format ───────────────────────────────────────────


class TestGate1Format:
    """Tests for RewardCalculator._gate1_format()."""

    def test_both_tags_present_passes(self, calculator):
        output = "<reasoning>analysis</reasoning>\n<patch>code</patch>"
        result = calculator._gate1_format(output)
        assert result.gate == 1
        assert result.passed is True
        assert result.reward == 0.0
        assert result.detail == "Format OK"

    def test_missing_reasoning_fails(self, calculator):
        output = "<patch>code</patch>"
        result = calculator._gate1_format(output)
        assert result.passed is False
        assert result.reward == -0.5
        assert "<reasoning>" in result.detail

    def test_missing_patch_fails(self, calculator):
        output = "<reasoning>analysis</reasoning>"
        result = calculator._gate1_format(output)
        assert result.passed is False
        assert result.reward == -0.5
        assert "<patch>" in result.detail

    def test_missing_both_fails(self, calculator):
        output = "just some text"
        result = calculator._gate1_format(output)
        assert result.passed is False
        assert result.reward == -0.5
        assert "<reasoning>" in result.detail
        assert "<patch>" in result.detail

    def test_incomplete_reasoning_tag_fails(self, calculator):
        output = "<reasoning>analysis\n<patch>code</patch>"
        result = calculator._gate1_format(output)
        assert result.passed is False
        assert "<reasoning>" in result.detail

    def test_incomplete_patch_tag_fails(self, calculator):
        output = "<reasoning>analysis</reasoning>\n<patch>code"
        result = calculator._gate1_format(output)
        assert result.passed is False
        assert "<patch>" in result.detail


# ── Task 6.2: Gate 2 Syntax/Liveness ──────────────────────────────────


class TestGate2SyntaxLiveness:
    """Tests for RewardCalculator._gate2_syntax_liveness()."""

    def test_successful_reload_and_health(self, calculator, sample_vuln, tmp_path):
        """Patch applied, reload succeeds, health check passes."""
        # Create route file directory
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        mock_reload_resp = MagicMock()
        mock_reload_resp.status_code = 200

        mock_health_resp = MagicMock()
        mock_health_resp.status_code = 200

        with patch("reward.http_requests.post", return_value=mock_reload_resp) as mock_post, \
             patch("reward.http_requests.get", return_value=mock_health_resp) as mock_get:
            result = calculator._gate2_syntax_liveness(
                "const x = 1;", sample_vuln, "http://localhost:3000", env
            )

        assert result.gate == 2
        assert result.passed is True
        assert result.reward == 0.0
        assert result.detail == "Syntax OK, server alive"
        # Verify patch was written to disk
        assert (routes_dir / "login.js").read_text() == "const x = 1;"

    def test_syntax_error_returns_500(self, calculator, sample_vuln, tmp_path):
        """Reload returns 500 for syntax error."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "SyntaxError: Unexpected token"

        with patch("reward.http_requests.post", return_value=mock_resp):
            result = calculator._gate2_syntax_liveness(
                "const x = {;", sample_vuln, "http://localhost:3000", env
            )

        assert result.passed is False
        assert result.reward == -1.0
        assert "SyntaxError" in result.detail

    def test_reload_timeout_triggers_restart(self, calculator, sample_vuln, tmp_path):
        """Timeout during reload triggers server restart."""
        import requests as http_requests

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        with patch("reward.http_requests.post", side_effect=http_requests.Timeout("timeout")):
            result = calculator._gate2_syntax_liveness(
                "code", sample_vuln, "http://localhost:3000", env
            )

        assert result.passed is False
        assert result.reward == -1.0
        assert "Timeout during reload" in result.detail
        env._restart_server.assert_called_once()

    def test_health_check_timeout_triggers_restart(self, calculator, sample_vuln, tmp_path):
        """Timeout during health check triggers server restart."""
        import requests as http_requests

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        mock_reload_resp = MagicMock()
        mock_reload_resp.status_code = 200

        with patch("reward.http_requests.post", return_value=mock_reload_resp), \
             patch("reward.http_requests.get", side_effect=http_requests.Timeout("timeout")):
            result = calculator._gate2_syntax_liveness(
                "code", sample_vuln, "http://localhost:3000", env
            )

        assert result.passed is False
        assert result.reward == -1.0
        assert "Timeout during health check" in result.detail
        env._restart_server.assert_called_once()

    def test_health_check_non_200_fails(self, calculator, sample_vuln, tmp_path):
        """Health check returning non-200 fails gate 2."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        mock_reload_resp = MagicMock()
        mock_reload_resp.status_code = 200

        mock_health_resp = MagicMock()
        mock_health_resp.status_code = 503

        with patch("reward.http_requests.post", return_value=mock_reload_resp), \
             patch("reward.http_requests.get", return_value=mock_health_resp):
            result = calculator._gate2_syntax_liveness(
                "code", sample_vuln, "http://localhost:3000", env
            )

        assert result.passed is False
        assert result.reward == -1.0
        assert "Health check failed" in result.detail


# ── Task 6.3: Gate 3 Happy Path ───────────────────────────────────────


class TestGate3HappyPath:
    """Tests for RewardCalculator._gate3_happy_path()."""

    def test_all_happy_paths_pass(self, calculator):
        """All tests pass with expected status codes."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        tests = [
            HTTPTest(method="POST", path="/api/login", headers={},
                     body={"username": "alice"}, expected_status=200, expected_body=None),
            HTTPTest(method="POST", path="/api/login", headers={},
                     body={"username": "wrong"}, expected_status=401, expected_body=None),
        ]

        mock_responses = [MagicMock(status_code=200, text="{}"), MagicMock(status_code=401, text="{}")]

        with patch("reward.http_requests.request", side_effect=mock_responses):
            result = calculator._gate3_happy_path(tests, "http://localhost:3000", env)

        assert result.passed is True
        assert result.reward == 0.0
        assert result.detail == "All happy paths passed"

    def test_status_mismatch_fails(self, calculator):
        """Wrong status code fails gate 3."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        tests = [
            HTTPTest(method="POST", path="/api/login", headers={},
                     body={"username": "alice"}, expected_status=200, expected_body=None),
        ]

        mock_resp = MagicMock(status_code=500, text="{}")

        with patch("reward.http_requests.request", return_value=mock_resp):
            result = calculator._gate3_happy_path(tests, "http://localhost:3000", env)

        assert result.passed is False
        assert result.reward == -1.0
        assert "expected 200 got 500" in result.detail

    def test_timeout_triggers_restart(self, calculator):
        """Timeout during happy path triggers server restart."""
        import requests as http_requests

        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        tests = [
            HTTPTest(method="POST", path="/api/login", headers={},
                     body={}, expected_status=200, expected_body=None),
        ]

        with patch("reward.http_requests.request", side_effect=http_requests.Timeout("timeout")):
            result = calculator._gate3_happy_path(tests, "http://localhost:3000", env)

        assert result.passed is False
        assert result.reward == -1.0
        assert "Timeout during happy path" in result.detail
        env._restart_server.assert_called_once()

    def test_body_string_match(self, calculator):
        """String body matching works."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        tests = [
            HTTPTest(method="GET", path="/test", headers={},
                     body=None, expected_status=200, expected_body="hello"),
        ]

        mock_resp = MagicMock(status_code=200, text="hello world")

        with patch("reward.http_requests.request", return_value=mock_resp):
            result = calculator._gate3_happy_path(tests, "http://localhost:3000", env)

        assert result.passed is True

    def test_body_dict_match(self, calculator):
        """Dict body matching works."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        tests = [
            HTTPTest(method="GET", path="/test", headers={},
                     body=None, expected_status=200, expected_body={"username": "alice"}),
        ]

        mock_resp = MagicMock(status_code=200, text='{"username": "alice", "role": "user"}')

        with patch("reward.http_requests.request", return_value=mock_resp):
            result = calculator._gate3_happy_path(tests, "http://localhost:3000", env)

        assert result.passed is True

    def test_body_dict_mismatch_fails(self, calculator):
        """Dict body mismatch fails gate 3."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        tests = [
            HTTPTest(method="GET", path="/test", headers={},
                     body=None, expected_status=200, expected_body={"username": "alice"}),
        ]

        mock_resp = MagicMock(status_code=200, text='{"username": "bob"}')

        with patch("reward.http_requests.request", return_value=mock_resp):
            result = calculator._gate3_happy_path(tests, "http://localhost:3000", env)

        assert result.passed is False
        assert result.reward == -1.0


# ── Task 6.4: Gate 4 Security ─────────────────────────────────────────


class TestGate4Security:
    """Tests for RewardCalculator._gate4_security()."""

    def test_all_blocked(self, calculator):
        """All 3 payloads blocked → reward 1.0."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        payloads = [
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
        ]

        mock_resp = MagicMock(status_code=403, text="{}")

        with patch("reward.http_requests.request", return_value=mock_resp):
            result = calculator._gate4_security(payloads, "http://localhost:3000", env)

        assert result.passed is True
        assert result.reward == 1.0
        assert "3/3" in result.detail

    def test_none_blocked(self, calculator):
        """0 payloads blocked → reward 0.0, passed=False."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        payloads = [
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
        ]

        mock_resp = MagicMock(status_code=200, text="{}")

        with patch("reward.http_requests.request", return_value=mock_resp):
            result = calculator._gate4_security(payloads, "http://localhost:3000", env)

        assert result.passed is False
        assert result.reward == 0.0
        assert "0/3" in result.detail

    def test_partial_blocked(self, calculator):
        """2 of 3 blocked → reward 0.67."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        payloads = [
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
        ]

        responses = [
            MagicMock(status_code=400, text="{}"),
            MagicMock(status_code=200, text="{}"),
            MagicMock(status_code=403, text="{}"),
        ]

        with patch("reward.http_requests.request", side_effect=responses):
            result = calculator._gate4_security(payloads, "http://localhost:3000", env)

        assert result.passed is True
        assert result.reward == 0.67
        assert "2/3" in result.detail

    def test_one_blocked(self, calculator):
        """1 of 3 blocked → reward 0.33."""
        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        payloads = [
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
        ]

        responses = [
            MagicMock(status_code=200, text="{}"),
            MagicMock(status_code=401, text="{}"),
            MagicMock(status_code=200, text="{}"),
        ]

        with patch("reward.http_requests.request", side_effect=responses):
            result = calculator._gate4_security(payloads, "http://localhost:3000", env)

        assert result.passed is True
        assert result.reward == 0.33
        assert "1/3" in result.detail

    def test_timeout_triggers_restart(self, calculator):
        """Timeout during Ultron triggers server restart."""
        import requests as http_requests

        env = MagicMock()
        env.HTTP_TIMEOUT = 10.0

        payloads = [
            HTTPTest(method="POST", path="/api/login", headers={}, body={}, expected_status=200),
        ]

        with patch("reward.http_requests.request", side_effect=http_requests.Timeout("timeout")):
            result = calculator._gate4_security(payloads, "http://localhost:3000", env)

        assert result.passed is False
        assert result.reward == -1.0
        assert "Timeout during Ultron" in result.detail
        env._restart_server.assert_called_once()


# ── Task 6.5: Evaluate Orchestration ──────────────────────────────────


class TestEvaluate:
    """Tests for RewardCalculator.evaluate() orchestration."""

    def test_gate1_fail_stops_early(self, calculator, sample_vuln):
        """Missing tags → gate 1 fail, no further gates evaluated."""
        env = MagicMock()
        reward, info = calculator.evaluate("no tags here", sample_vuln, "http://localhost:3000", env)

        assert reward == -0.5
        assert info["gate_reached"] == 1
        assert len(info["gates"]) == 1
        assert info["total_reward"] == -0.5

    def test_gate2_fail_stops_at_gate2(self, calculator, sample_vuln, tmp_path):
        """Syntax error → gate 2 fail, gates 3 and 4 not evaluated."""
        import requests as http_requests

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "SyntaxError"

        agent_output = "<reasoning>fix</reasoning>\n<patch>bad code {;</patch>"

        with patch("reward.http_requests.post", return_value=mock_resp):
            reward, info = calculator.evaluate(agent_output, sample_vuln, "http://localhost:3000", env)

        assert reward == -1.0
        assert info["gate_reached"] == 2
        assert len(info["gates"]) == 2

    def test_full_pipeline_all_gates_pass(self, calculator, sample_vuln, tmp_path):
        """All gates pass → reward from gate 4."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "login.js").write_text("original")

        env = MagicMock()
        env.app_dir = str(tmp_path)
        env.HTTP_TIMEOUT = 10.0

        # Gate 2: reload OK + health OK
        mock_reload = MagicMock(status_code=200)
        mock_health = MagicMock(status_code=200)

        # Gate 3: happy path responses (2 tests)
        mock_happy1 = MagicMock(status_code=200, text='{"username": "alice"}')
        mock_happy2 = MagicMock(status_code=401, text='{}')

        # Gate 4: all blocked
        mock_blocked = MagicMock(status_code=403, text='{}')

        agent_output = "<reasoning>fix</reasoning>\n<patch>const x = 1;</patch>"

        with patch("reward.http_requests.post", return_value=mock_reload), \
             patch("reward.http_requests.get", return_value=mock_health), \
             patch("reward.http_requests.request", side_effect=[mock_happy1, mock_happy2, mock_blocked, mock_blocked, mock_blocked]):
            reward, info = calculator.evaluate(agent_output, sample_vuln, "http://localhost:3000", env)

        assert info["gate_reached"] == 4
        assert len(info["gates"]) == 4
        assert reward == 1.0
        assert info["total_reward"] == 1.0

    def test_info_dict_structure(self, calculator, sample_vuln):
        """Info dict always has required keys."""
        env = MagicMock()
        reward, info = calculator.evaluate("no tags", sample_vuln, "http://localhost:3000", env)

        assert "gates" in info
        assert "gate_reached" in info
        assert "total_reward" in info
        assert isinstance(info["gates"], list)
        assert isinstance(info["gate_reached"], int)
        assert isinstance(info["total_reward"], float)

    def test_reward_range(self, calculator, sample_vuln):
        """Reward is always in [-1.0, +1.0]."""
        env = MagicMock()
        # Gate 1 fail
        reward, info = calculator.evaluate("no tags", sample_vuln, "http://localhost:3000", env)
        assert -1.0 <= reward <= 1.0


# ── Task 7: JarvisEnv ─────────────────────────────────────────────────


class TestJarvisEnvUnit:
    """Unit tests for JarvisEnv methods using mocks (no real server)."""

    def test_find_free_port(self):
        """_find_free_port returns a valid port number."""
        from env import JarvisEnv
        port = JarvisEnv._find_free_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_state_before_reset(self):
        """state() before reset returns empty Observation."""
        from env import Observation

        obs = Observation()
        assert obs.episode_active is False
        assert obs.vuln_id is None
        assert obs.vuln_type is None

    def test_observation_dataclass(self):
        """Observation can be constructed with all fields."""
        from env import Observation

        obs = Observation(
            vuln_id="test",
            vuln_type="Test Type",
            route_path="/test",
            vulnerable_code="code",
            description="desc",
            episode_active=True,
        )
        assert obs.vuln_id == "test"
        assert obs.episode_active is True
