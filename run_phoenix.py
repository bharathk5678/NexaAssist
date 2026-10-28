"""Persistent standalone runner for Arize Phoenix UI and OpenInference LangChain collector."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import sys
import time

# Ensure NexaAssist repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import phoenix as px
from openinference.instrumentation.langchain import LangChainInstrumentor

port = int(os.getenv("PHOENIX_PORT", "6006"))
os.environ["PHOENIX_PORT"] = str(port)

print(f"Starting Arize Phoenix server on port {port}...")
session = px.launch_app()
LangChainInstrumentor().instrument()

url = getattr(session, "url", f"http://localhost:{port}/")
print(f"🌍 Arize Phoenix UI is active and listening at: {url}")
sys.stdout.flush()


def handle_exit(sig, frame):
    print("\nShutting down Arize Phoenix...")
    try:
        px.close_app()
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

try:
    while True:
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    handle_exit(None, None)
