"""Arize Phoenix observability and tracing integration for NexaAssist."""

from __future__ import annotations

import os
import socket
from typing import Any
import structlog

logger = structlog.get_logger()

_phoenix_session: Any = None
_instrumented: bool = False


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def init_phoenix(port: int = 6006) -> Any:
    """Connect OpenTelemetry LangChain tracer to Phoenix.

    If Phoenix is not already running on `port`, launches it in-process.
    """
    global _phoenix_session, _instrumented

    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor

        # 1. Register OpenTelemetry OTLP tracer provider pointing to Phoenix collector
        if not _instrumented:
            tracer_provider = register(endpoint=f"http://localhost:{port}/v1/traces")
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            _instrumented = True
            logger.info("langchain_openinference_instrumented", endpoint=f"http://localhost:{port}/v1/traces")

        # 2. Launch in-process Phoenix only if port is not already occupied
        import phoenix as px
        if not _is_port_in_use(port) and px.active_session() is None:
            os.environ["PHOENIX_PORT"] = str(port)
            _phoenix_session = px.launch_app()
            logger.info("phoenix_launched", url=str(_phoenix_session.url))
        else:
            _phoenix_session = px.active_session()

        return _phoenix_session
    except Exception as exc:
        logger.warning("phoenix_initialization_failed", error=str(exc))
        return None


def get_phoenix_session() -> Any:
    """Return the currently running Phoenix session if active."""
    return _phoenix_session


def stop_phoenix() -> None:
    """Stop the Phoenix application if running."""
    global _phoenix_session
    if _phoenix_session is not None:
        try:
            import phoenix as px
            px.close_app()
        except Exception:
            pass
        _phoenix_session = None
