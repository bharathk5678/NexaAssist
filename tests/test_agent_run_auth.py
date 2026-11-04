from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.api.auth import get_validation_access
from app.core.config import AgentSettings


def configuration() -> AgentSettings:
    return AgentSettings(
        _env_file=None,
        agent_principals=[
            {"principal_id": "owner", "token": "o" * 32, "customer_ids": ["NXC-0010"]},
            {
                "principal_id": "reviewer",
                "token": "r" * 32,
                "customer_ids": ["NXC-0010"],
                "can_approve": True,
            },
        ],
    )


@pytest.mark.parametrize(
    "token,principal,reviewer", [("o" * 32, "owner", False), ("r" * 32, "reviewer", True)]
)
def test_identity_scope_comes_from_server_configuration(
    token: str, principal: str, reviewer: bool
) -> None:
    access = get_validation_access(
        configuration(), HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    assert access is not None
    assert access.principal_id == principal
    assert access.can_approve is reviewer
    assert access.customer_ids == {"NXC-0010"}


@pytest.mark.parametrize(
    "credentials", [None, HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")]
)
def test_bad_identity_has_no_access(credentials: HTTPAuthorizationCredentials | None) -> None:
    assert get_validation_access(configuration(), credentials) is None


@pytest.mark.parametrize(
    "change", ["duplicate_name", "duplicate_token", "reserved", "bad_customer", "legacy_collision"]
)
def test_ambiguous_identity_configuration_is_rejected(change: str) -> None:
    body = configuration().model_dump()
    if change == "duplicate_name":
        body["agent_principals"][1]["principal_id"] = "owner"
    if change == "duplicate_token":
        body["agent_principals"][1]["token"] = body["agent_principals"][0]["token"]
    if change == "reserved":
        body["agent_principals"][0]["principal_id"] = "training"
    if change == "bad_customer":
        body["agent_principals"][0]["customer_ids"] = {"unknown"}
    if change == "legacy_collision":
        body["agent_validation_token"] = "o" * 32
    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None, **body)
    assert AgentSettings(_env_file=None).agent_allow_direct_submit is False


def test_configuration_errors_do_not_echo_credentials() -> None:
    token = "private-test-token"
    with pytest.raises(ValidationError) as caught:
        AgentSettings(_env_file=None, agent_validation_token=token)
    assert token not in str(caught.value)


@pytest.mark.parametrize("already_configured", [False, True])
def test_credential_setup_preserves_existing_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    already_configured: bool,
) -> None:
    script = Path("app/get_bearer_token.py").resolve()
    initial = "UNRELATED_SETTING=preserve-me\n"
    if already_configured:
        initial += 'AGENT_PRINCIPALS=\'[{"principal_id":"existing-owner"}]\'\n'
    environment = tmp_path / ".env"
    environment.write_text(initial)
    monkeypatch.chdir(tmp_path)
    if already_configured:
        with pytest.raises(SystemExit, match="leaving them unchanged"):
            runpy.run_path(str(script), run_name="__main__")
        assert environment.read_text() == initial
        assert not capsys.readouterr().out
    else:
        runpy.run_path(str(script), run_name="__main__")
        output = capsys.readouterr().out
        values = dotenv_values(environment)
        assert values["UNRELATED_SETTING"] == "preserve-me"
        principals = json.loads(values["AGENT_PRINCIPALS"] or "null")
        config = AgentSettings(_env_file=None, agent_principals=principals)
        assert len(config.agent_principals) == 2
        assert [p.can_approve for p in config.agent_principals] == [False, True]
        assert all(p.customer_ids == {"NXC-0010"} for p in config.agent_principals)
        assert len(output.splitlines()) == 2
