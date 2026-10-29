from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: SecretStr
    mongodb_db: str
    mongodb_collection: str
    vector_index_name: str = "policy_chunks_v1"
    mongodb_parent_collection: str = "policy_sections"
    mongodb_feedback_collection: str = "policy_feedback"
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
    eval_judge_model: str | None = None
    retrieval_mode: Literal["dense", "hybrid"] = "dense"
    text_index_name: str = "policy_text_v1"
    retrieval_candidates: int = Field(default=20, ge=20, le=50)
    rerank_enabled: bool = False
    context_max_tokens: int = Field(default=6000, ge=256)
    rerank_model: str = "nexaassist-reranker:0.6b-mlx"
    rerank_api: Literal["ollama", "openai"] = "ollama"
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
    phoenix_enabled: bool = False
    phoenix_port: int = 6006

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
    ui_timezone: str = "Asia/Kolkata"


@lru_cache
def get_ui_settings() -> UISettings:
    return UISettings()


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rag_base_url: HttpUrl = HttpUrl("http://127.0.0.1:8000/")
    agent_http_timeout_seconds: float = Field(default=60, gt=0, le=300)
    agent_run_timeout_seconds: float = Field(default=180, gt=0, le=600)


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
