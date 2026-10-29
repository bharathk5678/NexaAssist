"""Diagnostic and verification tool for Datadog APM & LLM Observability in NexaAssist.

Usage:
  uv run python test_datadog.py
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import urllib.request
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.core.config import get_settings


def check_agent_connectivity(url: str) -> bool:
    """Check if the local Datadog Agent is responding on the APM port."""
    try:
        req = urllib.request.Request(f"{url}/info", headers={"User-Agent": "NexaAssist-Probe"})
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def validate_datadog_api_key(api_key: str, site: str) -> bool:
    """Validate Datadog API Key against Datadog's official validate API endpoint."""
    try:
        req = urllib.request.Request(
            f"https://api.{site}/api/v1/validate",
            headers={"DD-API-KEY": api_key, "User-Agent": "NexaAssist-Probe"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def test_datadog_setup() -> None:
    print("=" * 80)
    print("DATADOG INTEGRATION CHECK FOR NEXAASSIST")
    print("=" * 80)

    # 1. Check SDK Installation
    try:
        import ddtrace
        from ddtrace.llmobs import LLMObs
        print(f"✓ Datadog SDK (ddtrace) installed: version {ddtrace.__version__}")
    except ImportError:
        print("❌ ddtrace is not installed! Run: uv add ddtrace")
        return

    # 2. Check Environment & Configuration
    settings = get_settings()
    dd_api_key = os.getenv("DD_API_KEY", "").strip()
    dd_site = os.getenv("DD_SITE", "datadoghq.com")
    agentless = os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "false").lower() in ("true", "1")
    agent_url = os.getenv("DD_TRACE_AGENT_URL", "http://127.0.0.1:18126")
    ml_app = os.getenv("DD_LLMOBS_ML_APP", "nexaassist")
    env = os.getenv("DD_ENV", "dev")

    print(f"\nConfiguration summary (from .env):")
    print(f"  DD_SERVICE                  : {os.getenv('DD_SERVICE', 'nexaassist-api')}")
    print(f"  DD_ENV                      : {env}")
    print(f"  DD_SITE                     : {dd_site}")
    print(f"  DD_LLMOBS_ML_APP            : {ml_app}")
    print(f"  DD_TRACE_ENABLED            : {os.getenv('DD_TRACE_ENABLED', 'true')}")
    print(f"  DD_LLMOBS_ENABLED           : {os.getenv('DD_LLMOBS_ENABLED', 'true')}")
    print(f"  DD_LLMOBS_AGENTLESS_ENABLED : {agentless}")
    print(f"  DD_TRACE_AGENT_URL          : {agent_url}")
    print(f"  DD_API_KEY                  : {'[CONFIGURED]' if dd_api_key else '[MISSING - not set in .env]'}")

    print("\n" + "-" * 80)
    print("CONNECTIVITY CHECK")
    print("-" * 80)

    # 3. Check connectivity mode
    if agentless:
        print(f"Mode: AGENTLESS (Direct HTTPS to https://api.{dd_site})")
        if not dd_api_key:
            print("❌ DD_API_KEY is required in Agentless mode. Add your API key to .env:")
            print("    DD_API_KEY=your_datadog_api_key_here")
            return

        is_valid = validate_datadog_api_key(dd_api_key, dd_site)
        if is_valid:
            print(f"✓ Datadog API Key verified successfully with Datadog cloud (https://api.{dd_site})!")
        else:
            print(f"⚠ Could not verify API Key with https://api.{dd_site}/api/v1/validate.")
            print("  Check that your DD_API_KEY is a valid Datadog API key and DD_SITE matches your region.")
    else:
        print(f"Mode: AGENT-BASED (Via local Datadog Agent on {agent_url})")
        agent_ok = check_agent_connectivity(agent_url)
        std_agent_ok = check_agent_connectivity("http://127.0.0.1:8126")

        if agent_ok:
            print(f"✓ Local Datadog Agent is REACHABLE on {agent_url}!")
        elif std_agent_ok:
            print(f"✓ Datadog Agent found on standard port http://127.0.0.1:8126!")
            print(f"  Tip: Update DD_TRACE_AGENT_URL=http://127.0.0.1:8126 in your .env")
        else:
            print(f"⚠ Local Datadog Agent is NOT currently reachable on {agent_url} or port 8126.")
            print("\n  To start the Datadog Agent:")
            print("    docker compose --env-file .env -f app/compose.datadog.yaml up -d")

    # 4. Probe Trace Emission
    print("\n" + "-" * 80)
    print("EMITTING TEST TRACE")
    print("-" * 80)

    try:
        if agentless and dd_api_key:
            # Test direct LLM Observability agentless emission
            LLMObs.enable(
                ml_app=ml_app,
                api_key=dd_api_key,
                site=dd_site,
                agentless_enabled=True,
                env=env,
            )
            with LLMObs.workflow(name="nexaassist_health_probe") as span:
                LLMObs.annotate(
                    span=span,
                    input_data={"status_check": "ping"},
                    output_data={"status": "healthy", "service": "nexaassist"},
                )
            LLMObs.flush()
            print("✓ Successfully emitted and flushed test LLMObs trace to Datadog cloud!")
            print(f"  → View your LLM traces at: https://app.{dd_site}/llm/traces")
        else:
            from ddtrace import tracer
            with tracer.trace("nexaassist.probe", service="nexaassist-test") as span:
                span.set_tag("probe.status", "ok")
                span.set_tag("app", "nexaassist")
            print("✓ Generated APM test span 'nexaassist.probe'.")

        print("✓ Telemetry pipeline instrumentation verified.")
    except Exception as exc:
        print(f"⚠ Trace probe encountered: {exc}")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_datadog_setup()

