from __future__ import annotations


def init_telemetry(enabled: bool) -> None:
    """Patch supported integrations for CLI startup.

    Serve FastAPI with ddtrace-run so instrumentation starts before app creation.
    Load .env into the process first; the SDK reads its own DD_* configuration.
    """
    if not enabled:
        return
    from ddtrace import patch_all

    patch_all()
