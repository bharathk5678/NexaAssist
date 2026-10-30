from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.validation import AgentPrincipal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: SecretStr
    mongodb_db: str
    mongodb_collection: str
    vector_index_name: str = "policy_chunks_v1"
    mongodb_parent_collection: str = "policy_sections"
    mongodb_feedback_collection: str = "policy_feedback"
    mongodb_agent_runs_collection: str = "agent_runs"
    mongodb_agent_checkpoints_collection: str = "agent_checkpoints"
    mongodb_agent_writes_collection: str = "agent_checkpoint_writes"
    mongodb_agent_retention_seconds: int = Field(default=604800, ge=172800, le=31536000)
    feedback_reviewer_token: SecretStr | None = Field(default=None, min_length=32)

    @field_validator("feedback_reviewer_token", mode="before")
    @classmethod
    def empty_reviewer_token(cls, value: object) -> object:
        return None if value == "" else value

    openai_api_key: SecretStr
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=1536, gt=0)
    embedding_batch_size: int = Field(default=100, ge=1, le=100)
    chat_model: str = "gpt-6-luna"
    chat_max_output_tokens: int | None = Field(default=None, ge=256, le=32768)
    eval_judge_model: str | None = None
    retrieval_mode: Literal["dense", "hybrid"] = "dense"
    text_index_name: str = "policy_text_v1"
    retrieval_candidates: int = Field(default=20, ge=20, le=50)
    rerank_enabled: bool = False
    context_max_tokens: int = Field(default=6000, ge=256)
    rerank_model: str = "nexaassist-reranker:0.6b-mlx"
    rerank_api: Literal["ollama", "openai", "llamacpp"] = "ollama"
    rerank_base_url: str = "http://127.0.0.1:11434"
    rerank_api_key: SecretStr = SecretStr("ollama")
    rerank_max_tokens: int = Field(default=4000, ge=256)
    token_encoding: str = "o200k_base"

    chunk_max_characters: int = Field(default=1200, gt=0)
    chunk_overlap_characters: int = Field(default=150, ge=0)

    # Corpus-wide metadata that the document register does not carry.
    institution: str
    jurisdiction: str
    confidentiality_level: str

    log_level: str = "INFO"
    dd_trace_enabled: bool = False
    dd_service: str = "nexaassist-api"
    dd_site: str = Field(default="datadoghq.com", pattern=r"^[a-z0-9.-]+$")

    @model_validator(mode="after")
    def valid_overlap(self) -> Settings:
        if self.chunk_overlap_characters >= self.chunk_max_characters:
            raise ValueError("CHUNK_OVERLAP_CHARACTERS must be smaller than CHUNK_MAX_CHARACTERS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


class UISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str = "http://127.0.0.1:8000"
    agent_api_base_url: str = "http://127.0.0.1:8001"
    ui_timezone: str = "Asia/Kolkata"


@lru_cache
def get_ui_settings() -> UISettings:
    return UISettings()


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    rag_base_url: HttpUrl = HttpUrl("http://127.0.0.1:8000/")
    agent_http_timeout_seconds: float = Field(default=60, gt=0, le=300)
    agent_run_timeout_seconds: float = Field(default=180, gt=0, le=600)
    banking_base_url: HttpUrl = HttpUrl("http://127.0.0.1:8080/")
    banking_api_token: SecretStr | None = Field(default=None, min_length=1)
    agent_validation_token: SecretStr | None = Field(default=None, min_length=32)
    agent_allowed_customer_ids: frozenset[str] = Field(default_factory=frozenset)
    agent_principals: list[AgentPrincipal] = Field(default_factory=list)
    agent_allow_direct_submit: bool = False
    agent_approval_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    agent_model_max_output_tokens: int = Field(default=2048, ge=256, le=32768)
    agent_model_max_calls: int = Field(default=3, ge=1, le=3)
    agent_model_token_budget: int = Field(default=64000, ge=1024, le=256000)

    @model_validator(mode="after")
    def unique_principals(self) -> AgentSettings:
        names = [principal.principal_id for principal in self.agent_principals]
        tokens = [principal.token.get_secret_value() for principal in self.agent_principals]
        if len(set(names)) != len(names) or "training" in names or len(set(tokens)) != len(tokens):
            raise ValueError(
                "Agent identities and credentials must be unique; training is reserved"
            )
        if (
            self.agent_validation_token is not None
            and self.agent_validation_token.get_secret_value() in tokens
        ):
            raise ValueError(
                "Agent identity credentials must differ from the legacy training token"
            )
        return self

    @field_validator("banking_api_token", "agent_validation_token", mode="before")
    @classmethod
    def empty_validation_token(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
