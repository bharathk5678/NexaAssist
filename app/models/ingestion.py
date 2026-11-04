"""Define document identity, effective dates and incremental ingestion outcomes."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class IngestRequest(BaseModel):
    """Ingestion Service contract: one source document plus its document-level metadata.

    The ninth metadata field, section_type, is set per chunk by the pipeline, as are
    clause, parent_id and checksum.

    Attributes:
        source_path: Input source document path used by ingestion.
        doc_id: Stable policy instrument identifier across stored records.
        title: Published policy or instrument title retained in citations.
        institution: Institution boundary used by corpus queries and run persistence.
        product_id: Explicit product scope, when required or supplied.
        policy_version: Published version of the cited policy instrument.
        effective_date: First policy date on which the document/version applies.
        effective_to: Optional final applicable date of the document/version.
        jurisdiction: Jurisdiction boundary retained in the policy lookup scope.
        doc_type: Registered policy document category.
        confidentiality_level: Corpus confidentiality scope applied to ingestion and retrieval.
    """

    model_config = ConfigDict(extra="forbid")

    source_path: str
    doc_id: str
    title: str
    institution: str
    product_id: str | None = None
    policy_version: str
    effective_date: date
    effective_to: date | None = None
    supersedes: str | None = None
    jurisdiction: str
    doc_type: str
    confidentiality_level: str


class IngestResponse(BaseModel):
    """Validated ingest response contract.

    Attributes:
        doc_id: Stable policy instrument identifier across stored records.
        chunk_count: Number of current clause chunks represented by the ingestion result.
        chunk_ids: Stable identifiers of the current document's clause chunks.
        embedded_count: Number of changed chunks embedded by this ingestion.
        unchanged_count: Number of existing chunks reused without new embeddings.
        embedding_model: Configured embedding model identity used in chunk compatibility checks.
    """

    model_config = ConfigDict(extra="forbid")

    doc_id: str
    chunk_count: int
    chunk_ids: list[str]
    embedded_count: int
    unchanged_count: int
    embedding_model: str
