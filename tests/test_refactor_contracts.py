"""Compatibility checks for shared startup and FastAPI dependency extraction."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from unittest.mock import Mock

import pytest
from fastapi import FastAPI

from app import agent_main, main
from app.api import agent, agent_runs, dependencies
from app.core import lifespan as startup
from app.core.config import Settings


def test_existing_dependency_exports_keep_override_identity() -> None:
    """Keep legacy and durable routes on the same overridable dependencies."""
    assert agent.rag_client is dependencies.rag_client is agent_runs.rag_client
    assert agent.banking_client is dependencies.banking_client is agent_runs.banking_client
    assert main.lifespan is startup.lifespan is agent_main.lifespan


def test_agent_import_does_not_construct_the_rag_application() -> None:
    """Import the Agent entry point without importing the RAG app factory."""
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import app.agent_main; assert 'app.main' not in sys.modules",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def test_shared_startup_preserves_initialization_order(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """Initialize telemetry, logging, and the tokenizer before yielding control.

    Args:
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
        settings: Validated application configuration for this operation.
    """
    events: list[str] = []
    monkeypatch.setattr(startup, "get_settings", lambda: settings)
    telemetry = Mock(side_effect=lambda _: events.append("telemetry"))
    logging = Mock(side_effect=lambda _: events.append("logging"))
    encoder = Mock(side_effect=lambda _: events.append("tokenizer"))
    monkeypatch.setattr(startup, "init_telemetry", telemetry)
    monkeypatch.setattr(startup, "configure_logging", logging)
    monkeypatch.setattr(startup, "token_encoder", encoder)

    async def run() -> None:
        async with startup.lifespan(FastAPI()):
            assert events == ["telemetry", "logging", "tokenizer"]

    asyncio.run(run())
    telemetry.assert_called_once_with(settings.dd_trace_enabled)
    logging.assert_called_once_with(settings.log_level)
    encoder.assert_called_once_with(settings.token_encoding)
