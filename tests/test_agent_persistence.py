from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agents.orchestrator import AgentState
from app.core.config import Settings
from app.database import agent_runs
from app.database.agent_runs import MongoRunStore
from app.models.agent import AgentRequest


def test_workflow_mongo_client_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    constructor = Mock()
    agent_runs._agent_client.cache_clear()
    monkeypatch.setattr(agent_runs, "MongoClient", constructor)
    agent_runs._agent_client("mongodb://unused")
    constructor.assert_called_once_with(
        "mongodb://unused",
        timeoutMS=5000,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
        w="majority",
        journal=True,
        readConcernLevel="majority",
    )
    agent_runs._agent_client.cache_clear()


def test_atomic_lease_and_institution_isolation(
    run_store: MongoRunStore, workflow_settings: Settings
) -> None:
    async def run() -> None:
        assert await run_store.get("missing") is None
        await run_store.create({"_id": "run", "status": "running"})
        assert await run_store.claim("run", "first", 30) is not None
        assert await run_store.claim("run", "second", 30) is None
        assert await run_store.update("run", "wrong", status="submitted") is False
        await run_store.release("run", "wrong", "submitted")
        record = await run_store.get("run")
        assert record is not None and record["lease_id"] == "first"
        assert await run_store.update(
            "run", "first", lease_until=datetime.now(UTC) - timedelta(seconds=1)
        )
        assert await run_store.claim("run", "second", 30) is not None
        await run_store.release("run", "second", "pending_approval")
        record = await run_store.get("run")
        assert record is not None and record["status"] == "pending_approval"
        assert record["purge_at"] > datetime.now(UTC) + timedelta(days=6)
        assert run_store.collection.index_information()["purge_at_1"]["expireAfterSeconds"] == 0
        foreign = MongoRunStore(workflow_settings.model_copy(update={"institution": "OtherBank"}))
        assert await foreign.get("run") is None
        assert await foreign.claim("run", "foreign", 30) is None

    asyncio.run(run())


def test_real_checkpointer_round_trips_typed_state_after_reconstruction(
    run_store: MongoRunStore, workflow_settings: Settings
) -> None:
    async def run() -> None:
        builder = StateGraph(AgentState)
        builder.add_node("retain", lambda state: state)
        builder.add_edge(START, "retain")
        builder.add_edge("retain", END)
        config: RunnableConfig = {"configurable": {"thread_id": "typed-roundtrip"}}
        request = AgentRequest(query="Published policy question")
        await builder.compile(checkpointer=run_store.checkpointer).ainvoke(
            {"request": request}, config, durability="sync"
        )
        restored = MongoRunStore(workflow_settings)
        state = await builder.compile(checkpointer=restored.checkpointer).aget_state(config)
        assert state.values["request"] == request
        assert isinstance(state.values["request"], AgentRequest)

    asyncio.run(run())
