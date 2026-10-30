# C4 code inventory: app/evaluation/datasets

**Language:** JSON data; no executable code or callable signatures.

**Purpose:** stored teaching observations for Session 5. These snapshots are not the default golden answer evaluation dataset.

**Location:** [app/evaluation/datasets](../app/evaluation/datasets)

## Files

- [app/evaluation/datasets/session5_atlas_observation.json](../app/evaluation/datasets/session5_atlas_observation.json) — top-level structure: `captured_at`, `target`, `configured_index`, `indexes`, `chunk_count`, `documents`, `embedding_inventory`, `embedding_contract`, `cases`, `source_freshness`.
- [app/evaluation/datasets/session5_atlas_parent_observation.json](../app/evaluation/datasets/session5_atlas_parent_observation.json) — top-level structure: `captured_at`, `target`, `configured_index`, `indexes`, `chunk_count`, `parent_target`, `parent_count`, `parent_integrity`, `documents`, `embedding_inventory`, `embedding_contract`, `cases`, `source_freshness`, `parent_source_freshness`.

## Dependencies and interpretation

The default executable answer evaluation uses `evaluation/datasets/answer.jsonl` at repository root (10 golden cases, including two expected abstentions). These JSON observations require their capture context and timestamps; they are not proof of the current Atlas state. The generated results directory is excluded from this inventory.
