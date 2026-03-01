"""
Railway deployment test suite.

Validates the three layers that must work for a healthy Railway deploy:
  1. Config files — railway.json, Procfile, requirements.txt are correct
  2. Environment defaults — config.py has safe fallbacks; no key = no crash
  3. API contract — /health exists, route table is complete, CORS is wired up

No external HTTP calls, no OpenRouter, no Ollama. Uses the real DB only
where unavoidable (TestClient hitting /health which has zero DB dependency).
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.railway

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Config file validation
# ---------------------------------------------------------------------------


class TestRailwayConfigFiles:
    """Railway JSON, Procfile, and requirements.txt must be correctly formed."""

    def test_api_railway_json_exists(self):
        assert (ROOT / "api" / "railway.json").exists()

    def test_frontend_railway_json_exists(self):
        assert (ROOT / "frontend" / "railway.json").exists()

    def test_api_healthcheck_path_is_slash_health(self):
        data = json.loads((ROOT / "api" / "railway.json").read_text())
        assert data["deploy"]["healthcheckPath"] == "/health"

    def test_api_start_command_uses_port_env_var(self):
        data = json.loads((ROOT / "api" / "railway.json").read_text())
        cmd = data["deploy"]["startCommand"]
        assert "uvicorn" in cmd
        assert "api.main:app" in cmd
        assert "$PORT" in cmd

    def test_api_healthcheck_timeout_sufficient_for_cold_start(self):
        """Cold start includes DB init + optional seeding — needs ≥60 s."""
        data = json.loads((ROOT / "api" / "railway.json").read_text())
        assert data["deploy"]["healthcheckTimeout"] >= 60

    def test_api_restart_policy_on_failure(self):
        data = json.loads((ROOT / "api" / "railway.json").read_text())
        assert data["deploy"]["restartPolicyType"] == "ON_FAILURE"
        assert data["deploy"]["restartPolicyMaxRetries"] >= 1

    def test_frontend_healthcheck_configured(self):
        data = json.loads((ROOT / "frontend" / "railway.json").read_text())
        assert "healthcheckPath" in data["deploy"]
        assert data["deploy"]["healthcheckTimeout"] >= 30

    def test_procfile_declares_web_process(self):
        text = (ROOT / "Procfile").read_text()
        assert text.startswith("web:")

    def test_procfile_uses_port_env_var(self):
        text = (ROOT / "Procfile").read_text()
        assert "$PORT" in text or "${PORT" in text

    def test_procfile_and_railway_json_both_use_uvicorn(self):
        procfile_cmd = (ROOT / "Procfile").read_text().strip().split("web: ", 1)[1]
        data = json.loads((ROOT / "api" / "railway.json").read_text())
        railway_cmd = data["deploy"]["startCommand"]
        for cmd in (procfile_cmd, railway_cmd):
            assert "uvicorn" in cmd, f"uvicorn missing from command: {cmd!r}"
            assert "api.main:app" in cmd, f"entrypoint missing from command: {cmd!r}"

    def test_requirements_has_uvicorn(self):
        assert "uvicorn" in (ROOT / "requirements.txt").read_text()

    def test_requirements_has_fastapi(self):
        assert "fastapi" in (ROOT / "requirements.txt").read_text()

    def test_requirements_has_sqlalchemy(self):
        assert "sqlalchemy" in (ROOT / "requirements.txt").read_text().lower()


# ---------------------------------------------------------------------------
# Environment / config defaults
# ---------------------------------------------------------------------------


class TestEnvironmentDefaults:
    """config.py must have safe defaults so Railway deploy works without .env."""

    def test_database_url_defaults_to_sqlite(self):
        from config import DATABASE_URL
        # Either the default SQLite path or an explicit override is fine
        assert "sqlite" in DATABASE_URL or os.getenv("DATABASE_URL", "")

    def test_collect_schedule_hour_is_valid_utc_hour(self):
        from config import COLLECT_SCHEDULE_HOUR
        assert 0 <= COLLECT_SCHEDULE_HOUR <= 23

    def test_cors_origins_is_non_empty_list(self):
        from config import CORS_ORIGINS
        assert isinstance(CORS_ORIGINS, list)
        assert len(CORS_ORIGINS) >= 1

    def test_log_level_is_valid(self):
        from config import LOG_LEVEL
        assert LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

    def test_ollama_url_has_default(self):
        from config import OLLAMA_BASE_URL
        assert OLLAMA_BASE_URL  # non-empty string

    def test_missing_openrouter_key_returns_none_client(self):
        """No API key → get_ai_client() returns None, not an exception.

        Patches the module-level constants in ai.client directly because the
        values are captured from config at import time, not read from os.environ
        at call time.
        """
        with patch("ai.client.OPENROUTER_API_KEY", ""), \
             patch("ai.client.OPENAI_API_KEY", ""):
            from ai.client import get_ai_client
            client = get_ai_client()
            assert client is None

    def test_sec_edgar_user_agent_has_default(self):
        from config import SEC_EDGAR_USER_AGENT
        assert SEC_EDGAR_USER_AGENT

    @pytest.mark.parametrize("model_var", ["AI_MODEL_BULK", "AI_MODEL_PREMIUM"])
    def test_ai_model_vars_have_defaults(self, model_var):
        import config
        assert getattr(config, model_var), f"{model_var} must have a default value"


# ---------------------------------------------------------------------------
# API route table and startup contract
# ---------------------------------------------------------------------------


class TestApiRoutes:
    """The FastAPI app must register all routes that the frontend and Railway need."""

    @pytest.fixture(scope="class")
    def app(self):
        from api.main import app as _app
        return _app

    def test_health_route_registered(self, app):
        paths = {r.path for r in app.routes}
        assert "/health" in paths

    @pytest.mark.parametrize("path", [
        "/api/prospects",
        "/api/signals",
        "/api/signals/stats",
        "/api/competitors",
        "/api/dashboard",
        "/api/dashboard/digest",
        "/api/admin/stats",
    ])
    def test_api_route_registered(self, app, path):
        paths = {r.path for r in app.routes}
        assert path in paths, f"Route {path!r} not registered in app"

    def test_cors_middleware_configured(self, app):
        from starlette.middleware.cors import CORSMiddleware
        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert CORSMiddleware in middleware_classes, "CORSMiddleware not added to app"

    def test_app_has_title(self, app):
        assert app.title
        assert "Iren" in app.title

    def test_app_has_version(self, app):
        assert app.version


# ---------------------------------------------------------------------------
# /health endpoint — the Railway healthcheck target
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """/health must always return 200 {"status": "ok"} with no DB dependency."""

    def test_health_function_returns_ok(self):
        """Call the handler directly — zero infrastructure required."""
        from api.main import health
        assert health() == {"status": "ok"}

    def test_health_via_test_client(self):
        """TestClient must get 200 on /health so Railway considers the deploy live."""
        from fastapi.testclient import TestClient
        from api.main import app

        with patch("api.main._scheduled_collect"), \
             patch("api.main._startup_collect_if_empty"):
            with TestClient(app, raise_server_exceptions=True) as client:
                resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_has_no_auth_requirement(self):
        """Health endpoint must be reachable without any auth headers."""
        from fastapi.testclient import TestClient
        from api.main import app

        with patch("api.main._scheduled_collect"), \
             patch("api.main._startup_collect_if_empty"):
            with TestClient(app) as client:
                resp = client.get("/health", headers={})
        assert resp.status_code == 200
