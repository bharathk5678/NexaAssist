from __future__ import annotations

from unittest.mock import Mock, patch
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda

from app.core.phoenix import init_phoenix, get_phoenix_session


def test_phoenix_initialization():
    session = init_phoenix(port=6006)
    assert session is not None
    assert get_phoenix_session() is session


def test_phoenix_langchain_tracing():
    init_phoenix(port=6006)
    prompt = PromptTemplate.from_template("Test prompt: {x}")
    chain = prompt | RunnableLambda(lambda p: f"Echo: {p.text}")
    res = chain.invoke({"x": "NexaAssist"})
    assert res == "Echo: Test prompt: NexaAssist"
