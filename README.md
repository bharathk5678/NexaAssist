# NexaAssist

A policy, product and lending advisor for the staff of NexaBank (a fictional bank), built as the hands-on codebase for the **Enterprise Agentic RAG** training program. Everything is synthetic.

This repository contains the Week 1 ingestion and retrieval paths, plus the first Week 2 answer-generation slice. Ingestion turns policy PDFs into versioned clause chunks and parent sections in MongoDB Atlas; `/retrieve` returns filtered, cited evidence using vector search. `/answer` uses the same retrieval service and `gpt-6-luna` to generate a response with quoted evidence. Seven selected synthetic golden cases have completed live retrieval, generation and evaluation; Datadog score visibility is verified. Two answerable cases incorrectly abstained, so full-dataset quality is not established.

| | |
|---|---|
| Language | Python 3.14+ |
| Orchestration | LangChain (LCEL runnables) |
| Vector store | MongoDB Atlas Vector Search via `langchain-mongodb` |
| Embeddings | OpenAI `text-embedding-3-small`, 1536 dimensions |
| PDF parsing | `pdfplumber` (tables and headings), `unstructured` (element types) |
| Chunking | Clause-aware rules in `app/chains/chunking.py`, `langchain-text-splitters` for oversized clauses |
| Config and logging | `pydantic-settings`, `structlog` (JSON), optional `ddtrace` |
| Package manager | `uv` |

## Table of contents

1. [Architecture](#1-architecture)
2. [Project layout](#2-project-layout)
3. [How a document flows through the system](#3-how-a-document-flows-through-the-system)
4. [Classes and functions](#4-classes-and-functions)
5. [Data model: the chunk record](#5-data-model-the-chunk-record)
6. [Getting started](#6-getting-started)
7. [Using the project, including how to execute the code](#7-using-the-project)
8. [Testing and quality checks](#8-testing-and-quality-checks)
9. [Design decisions](#9-design-decisions)
10. [Roadmap](#10-roadmap)

---

## 1. Architecture

The system has two paths that share a store, not a service. Ingestion is bursty and throughput-bound; retrieval is latency-bound. Keeping them separate means a slow re-index cannot slow a loan officer.

```mermaid
flowchart LR
    subgraph WRITE["Write path: built in Sessions 1 and 2"]
        direction LR
        SRC["Policy PDFs and circulars"] --> LOAD["Load via document register"]
        LOAD --> PARSE["Parse: tables, headings"]
        PARSE --> CHUNK["Chunk by clause"]
        CHUNK --> ENRICH["Enrich: header, metadata,<br/>parent_id, checksum"]
        ENRICH --> COMPARE["Compare checksums"]
        COMPARE --> EMBED["Embed only<br/>new or changed"]
    end

    EMBED --> ATLAS[("MongoDB Atlas<br/>chunks + vector index")]
    ENRICH --> PARENTS[("MongoDB Atlas<br/>parent sections")]

    subgraph READ["Read path: Session 4"]
        direction LR
        CALLER["API caller"] --> RET["FastAPI /retrieve"]
        RET --> QEMB["Embed query<br/>same model"]
        QEMB --> SEARCH["Vector search + filters"]
        SEARCH --> CITED["Cited chunks"]
    end

    ATLAS -.-> SEARCH
    PARENTS -.-> CITED
```

Why version metadata matters: a circular can supersede a single clause of a manual. If the write path does not stamp `policy_version` and `effective_date` on every chunk, the read path cannot tell a current clause from a superseded one, and similarity search alone will happily return the old one.

### Layered build order

The project is built one layer at a time (see [CLAUDE.md](CLAUDE.md)). Dependencies only point downward.

```mermaid
flowchart TB
    L6["Layer 6: Evaluation and observability"] -.-> L1
    L5["Layer 5: FastMCP server"] --> L4
    L4["Layer 4: LangGraph agents"] --> L2
    L3["Layer 3: Streamlit UI"] --> L2
    L2["Layer 2: FastAPI services"] --> L1
    L1["Layer 1: LangChain + MongoDB Atlas"]

    classDef built fill:#d1fae5,stroke:#047857,color:#064e3b
    classDef todo fill:#f3f4f6,stroke:#9ca3af,color:#374151
    class L1,L2 built
    class L3,L4,L5,L6 todo
```

Green is implemented in code; live Atlas verification is still required.

### C4 model views

The architecture is also documented with the [C4 model](https://c4model.com/): a system landscape, then context, container and component diagrams, and a dynamic diagram for one request. Everything drawn is implemented in code, except the elements marked as planned or not integrated. Live Atlas and OpenAI verification is still pending (see [Design decisions](#9-design-decisions)).

The diagrams use Mermaid flowcharts and sequence diagrams rather than Mermaid's experimental `C4Context` syntax, because that syntax hard-codes line and label colors that are hard to read on a dark background. Every node here sets its own fill, border and text color, so the diagrams read in both GitHub light and dark themes.

#### Diagram key (applies to all C4 diagrams below)

```mermaid
flowchart LR
    kp(["Person"]):::person
    ks["Software system in scope"]:::system
    kc["Container"]:::container
    kk["Component"]:::component
    kd[("Data store")]:::store
    ke["External system"]:::external
    kn["Planned or not integrated"]:::planned

    kp -->|"Solid arrow: unidirectional call, labeled with purpose and [technology]"| ks
    kc -.->|"Dashed arrow: optional or not yet built"| ke

    classDef person fill:#08427b,stroke:#93c5fd,color:#ffffff,stroke-width:2px
    classDef system fill:#1e40af,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef container fill:#2563eb,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef component fill:#bfdbfe,stroke:#1d4ed8,color:#0f172a,stroke-width:2px
    classDef store fill:#2563eb,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef external fill:#475569,stroke:#cbd5e1,color:#ffffff,stroke-width:2px
    classDef planned fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:2px,stroke-dasharray:5 4
    linkStyle default stroke:#8b949e,stroke-width:2px
```

Abbreviations: LCEL is the LangChain Expression Language, APM is application performance monitoring, and `as_of` is the date a question is answered for.

#### System landscape: NexaBank

Scope: the part of the fictional NexaBank estate that this repository touches. A landscape is a context diagram without a single focus, so it also shows what is planned or only mocked.

```mermaid
---
title: "System landscape: NexaBank (implemented slice)"
---
flowchart TB
    staff(["NexaBank staff<br/>[Person]<br/>Loan officers and policy specialists"]):::person

    subgraph BANK["NexaBank (fictional) - enterprise boundary"]
        nexa["NexaAssist<br/>[Software System]<br/>Retrieves date-correct policy evidence<br/>and generates cited answers"]:::system
        planned["Planned layers<br/>[Software System: not built]<br/>Streamlit UI, LangGraph agents,<br/>FastMCP server"]:::planned
        core["Case and Core API<br/>[Software System: mock only]<br/>OpenAPI spec and mock server<br/>in nexa_synthetic_data/api"]:::planned
    end

    atlas["MongoDB Atlas<br/>[External System]<br/>Vector Search and document storage"]:::external
    openai["OpenAI API<br/>[External System]<br/>Embeddings and chat model"]:::external
    obs["Datadog and LangSmith<br/>[External Systems, optional]<br/>APM, LLM traces, evaluations"]:::external

    staff -->|"Asks policy questions [HTTPS/JSON]"| nexa
    nexa -->|"Stores and searches policy chunks [pymongo]"| atlas
    nexa -->|"Embeds text, generates answers [HTTPS]"| openai
    nexa -.->|"Sends traces and metrics [ddtrace, LangSmith SDK]"| obs
    planned -.->|"Will call the NexaAssist API [HTTPS/JSON]"| nexa
    nexa -.->|"Not integrated yet"| core

    classDef person fill:#08427b,stroke:#93c5fd,color:#ffffff,stroke-width:2px
    classDef system fill:#1e40af,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef external fill:#475569,stroke:#cbd5e1,color:#ffffff,stroke-width:2px
    classDef planned fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:2px,stroke-dasharray:5 4
    style BANK fill:none,stroke:#8b949e,stroke-width:2px,stroke-dasharray:6 4
    linkStyle default stroke:#8b949e,stroke-width:2px
```

#### Level 1: System context

Scope: the NexaAssist software system. Primary elements: the people who use it and the systems it depends on.

```mermaid
---
title: "System context: NexaAssist"
---
flowchart TB
    staff(["NexaBank staff<br/>[Person]<br/>Asks as-of policy questions"]):::person
    ops(["Ingestion operator<br/>[Person]<br/>Runs policy ingestion"]):::person

    nexa["NexaAssist<br/>[Software System]<br/>Ingests policy PDFs into versioned clause chunks.<br/>Returns filtered, cited evidence and answers."]:::system

    files["Policy corpus<br/>[External System: files]<br/>document_register.json,<br/>policy and circular PDFs"]:::external
    atlas["MongoDB Atlas<br/>[External System]<br/>Hosts the vector index and collections"]:::external
    openai["OpenAI API<br/>[External System]<br/>text-embedding-3-small and chat model"]:::external
    obs["Datadog and LangSmith<br/>[External Systems, optional]<br/>APM, LLM traces, evaluations"]:::external

    staff -->|"Calls /retrieve and /answer [HTTPS/JSON]"| nexa
    ops -->|"Runs the ingestion command [shell]"| nexa
    nexa -->|"Reads register and PDFs [filesystem]"| files
    nexa -->|"Writes chunks, searches with filters [pymongo]"| atlas
    nexa -->|"Embeds text, generates answers [HTTPS]"| openai
    nexa -.->|"Sends traces and metrics [ddtrace, LangSmith SDK]"| obs

    classDef person fill:#08427b,stroke:#93c5fd,color:#ffffff,stroke-width:2px
    classDef system fill:#1e40af,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef external fill:#475569,stroke:#cbd5e1,color:#ffffff,stroke-width:2px
    linkStyle default stroke:#8b949e,stroke-width:2px
```

#### Level 2: Containers

Scope: NexaAssist. Primary elements: the separately running processes and data stores. The write path and the read path never call each other; they share only the data stores.

```mermaid
---
title: "Containers: NexaAssist"
---
flowchart TB
    staff(["NexaBank staff<br/>[Person]"]):::person
    ops(["Ingestion operator<br/>[Person]"]):::person
    files["Policy corpus<br/>[External System: files]<br/>register and PDFs"]:::external
    openai["OpenAI API<br/>[External System]<br/>Embeddings and chat model"]:::external
    obs["Datadog<br/>[External System, optional]<br/>APM"]:::external

    subgraph NEXA["NexaAssist [Software System boundary]"]
        direction TB
        cli["Ingestion CLI<br/>[Container: Python, asyncio]<br/>python -m app.services.ingestion.<br/>Parses, chunks by clause, embeds only<br/>new or changed chunks, retires stale chunks."]:::container
        api["NexaAssist API<br/>[Container: FastAPI, uvicorn]<br/>Serves /retrieve, /answer,<br/>/health and /metrics."]:::container
        chunks[("Chunks collection and vector index<br/>[Data store: MongoDB Atlas]<br/>One document per clause chunk,<br/>with version and date metadata")]:::store
        parents[("Parent sections collection<br/>[Data store: MongoDB Atlas]<br/>Whole sections keyed by parent_id,<br/>not embedded")]:::store
    end

    ops -->|"Runs [shell]"| cli
    staff -->|"POST /retrieve, POST /answer [HTTPS/JSON]"| api
    cli -->|"Reads register and PDFs [filesystem]"| files
    cli -->|"Embeds changed chunks [HTTPS]"| openai
    cli -->|"Upserts and deletes chunks [pymongo]"| chunks
    cli -->|"Replaces sections [pymongo]"| parents
    api -->|"Embeds query, generates answer [HTTPS]"| openai
    api -->|"Vector search with pre-filters [pymongo]"| chunks
    api -->|"Reads parent sections [pymongo]"| parents
    api -.->|"Traces [ddtrace]"| obs
    cli -.->|"Traces [ddtrace]"| obs

    classDef person fill:#08427b,stroke:#93c5fd,color:#ffffff,stroke-width:2px
    classDef container fill:#2563eb,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef store fill:#2563eb,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef external fill:#475569,stroke:#cbd5e1,color:#ffffff,stroke-width:2px
    style NEXA fill:none,stroke:#8b949e,stroke-width:2px,stroke-dasharray:6 4
    linkStyle default stroke:#8b949e,stroke-width:2px
```

#### Level 3: Components of the NexaAssist API (read path)

Scope: the API container. The layers follow the rules in [CLAUDE.md](CLAUDE.md): routers call services, services call chains, and only `database/` touches `pymongo`.

```mermaid
---
title: "Components: NexaAssist API"
---
flowchart TB
    staff(["NexaBank staff<br/>[Person]"]):::person
    openai["OpenAI API<br/>[External System]"]:::external
    chunks[("Chunks collection<br/>and vector index<br/>[Data store]")]:::store
    parents[("Parent sections<br/>collection<br/>[Data store]")]:::store

    subgraph API["NexaAssist API [Container: FastAPI]"]
        direction TB
        rops["Operations router<br/>[Component: APIRouter]<br/>GET /health, GET /metrics"]:::component
        rret["Retrieval router<br/>[Component: APIRouter]<br/>POST /retrieve"]:::component
        rans["Answer router<br/>[Component: APIRouter]<br/>POST /answer"]:::component
        sret["Retrieval service<br/>[Component: services/retrieval.py]<br/>retrieve_policy and counters"]:::component
        sans["Answer service<br/>[Component: services/answer.py]<br/>answer_policy"]:::component
        cret["Retrieval chain<br/>[Component: LCEL runnable]<br/>As-of and product filters,<br/>parent expansion, citations"]:::component
        cans["Answer chain<br/>[Component: LCEL runnable]<br/>Dedupes context, calls the model,<br/>validates citations and quotes"]:::component
        prompt["Answer prompt<br/>[Component: ChatPromptTemplate]"]:::component
        factory["Model and embedding factories<br/>[Component: chains/llm.py, embeddings.py]"]:::component
        mongo["Store factories<br/>[Component: database/mongo.py]<br/>get_vector_store, get_parent_store"]:::component
        core["Settings, logging, telemetry<br/>[Component: core/]<br/>pydantic-settings, structlog, ddtrace"]:::component
    end

    staff -->|"HTTPS/JSON"| rret
    staff -->|"HTTPS/JSON"| rans
    staff -->|"HTTPS/JSON"| rops
    rret -->|"Calls"| sret
    rans -->|"Calls"| sans
    rops -->|"Reads counters"| sret
    sans -->|"Passes retrieval as a runnable"| cans
    cans -->|"Retrieves evidence through"| sret
    cans -->|"Formats messages with"| prompt
    sret -->|"Builds and invokes"| cret
    sret -->|"Gets clients from"| factory
    sret -->|"Gets stores from"| mongo
    sans -->|"Gets chat model from"| factory
    factory -->|"Embeds query, generates answer [HTTPS]"| openai
    mongo -->|"Vector search [pymongo]"| chunks
    mongo -->|"Reads sections [pymongo]"| parents
    core -.->|"Configures every component"| rops

    classDef person fill:#08427b,stroke:#93c5fd,color:#ffffff,stroke-width:2px
    classDef component fill:#bfdbfe,stroke:#1d4ed8,color:#0f172a,stroke-width:2px
    classDef store fill:#2563eb,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef external fill:#475569,stroke:#cbd5e1,color:#ffffff,stroke-width:2px
    style API fill:none,stroke:#8b949e,stroke-width:2px,stroke-dasharray:6 4
    linkStyle default stroke:#8b949e,stroke-width:2px
```

#### Level 3: Components of the Ingestion CLI (write path)

Scope: the ingestion container. The chain steps run in the order shown.

```mermaid
---
title: "Components: Ingestion CLI"
---
flowchart LR
    ops(["Ingestion operator<br/>[Person]"]):::person
    files["Policy corpus<br/>[External System: files]"]:::external
    openai["OpenAI API<br/>[External System]"]:::external
    chunks[("Chunks collection<br/>and vector index<br/>[Data store]")]:::store
    parents[("Parent sections<br/>collection<br/>[Data store]")]:::store

    subgraph CLI["Ingestion CLI [Container: Python]"]
        direction LR
        entry["Register loader<br/>[Component: services/ingestion.py]<br/>requests_from_register, ingest"]:::component
        parse["parse<br/>[Component: chains/parsing.py]<br/>Title, text and table elements"]:::component
        chunk["chunk<br/>[Component: chains/chunking.py]<br/>chunk_by_clause"]:::component
        enrich["enrich<br/>[Component: chains/ingestion.py]<br/>Header, metadata, chunk_id,<br/>parent_id, checksum"]:::component
        compare["compare<br/>[Component: chains/ingestion.py]<br/>Checksums against stored chunks"]:::component
        upsert["embed_and_upsert<br/>[Component: chains/ingestion.py]<br/>Embeds changed chunks only"]:::component
        stale["delete_stale_chunks<br/>[Component: database/mongo.py]"]:::component
    end

    ops -->|"python -m app.services.ingestion [shell]"| entry
    entry -->|"Reads register [filesystem]"| files
    entry -->|"One IngestRequest per document"| parse
    parse -->|"Reads PDF [pdfplumber]"| files
    parse -->|"Elements"| chunk
    chunk -->|"Clause chunks"| enrich
    enrich -->|"Parent sections [pymongo]"| parents
    enrich -->|"Child documents"| compare
    compare -->|"Reads stored checksums [pymongo]"| chunks
    compare -->|"Changed chunks"| upsert
    upsert -->|"Embeds text [HTTPS]"| openai
    upsert -->|"Upserts chunks [pymongo]"| chunks
    entry -->|"After each document"| stale
    stale -->|"Deletes chunks the source no longer has [pymongo]"| chunks

    classDef person fill:#08427b,stroke:#93c5fd,color:#ffffff,stroke-width:2px
    classDef component fill:#bfdbfe,stroke:#1d4ed8,color:#0f172a,stroke-width:2px
    classDef store fill:#2563eb,stroke:#bfdbfe,color:#ffffff,stroke-width:2px
    classDef external fill:#475569,stroke:#cbd5e1,color:#ffffff,stroke-width:2px
    style CLI fill:none,stroke:#8b949e,stroke-width:2px,stroke-dasharray:6 4
    linkStyle default stroke:#8b949e,stroke-width:2px
```

#### Dynamic diagram: answering one question

Scope: one `POST /answer` request, shown as a sequence between the containers and components above. Dynamic diagrams are for recurring or complicated interactions, and this is the one that matters most. It uses the sequence style, which the C4 model allows.

```mermaid
---
title: "Dynamic: POST /answer"
---
sequenceDiagram
    autonumber
    actor Staff as NexaBank staff
    participant API as NexaAssist API
    participant RS as Retrieval service
    participant AT as MongoDB Atlas
    participant OAI as OpenAI API
    participant AC as Answer chain

    Staff->>API: POST /answer (query, as_of, optional product_id) [HTTPS/JSON]
    API->>AC: answer_policy builds the chain
    AC->>RS: retrieve_policy(request)
    RS->>OAI: embed the query [HTTPS]
    OAI-->>RS: query vector
    RS->>AT: vector search with date, jurisdiction, confidentiality and product pre-filters [pymongo]
    AT-->>RS: top_k child chunks
    RS->>AT: read parent sections by parent_id [pymongo]
    AT-->>RS: parent sections
    RS-->>AC: ranked hits with citations and timings
    alt no hits
        AC-->>API: insufficient_evidence, no citations
    else hits found
        AC->>AC: dedupe parent sections and number them as evidence_id
        AC->>OAI: structured-output request with as_of, question and numbered context [HTTPS]
        OAI-->>AC: AnswerDraft (status, answer, evidence quotes)
        AC->>AC: check [n] markers equal evidence ids and every quote appears in its parent text
        AC-->>API: answered with citations, or insufficient_evidence if a check fails
    end
    API-->>Staff: AnswerResponse (status, answer, citations, timings) [HTTPS/JSON]
```

#### C4 checklist applied

| Check | How these diagrams meet it |
|---|---|
| Title | Every diagram has a title naming its type and scope |
| Type and scope | The type (landscape, context, container, component, dynamic) and the scoped system or container are in the title and the text above each diagram |
| Key | One shared key covers shapes, colors, solid and dashed arrows |
| Elements | Each shows a name, a type in brackets, the technology where it matters, and a short description |
| Relationships | Arrows are unidirectional, labeled with their purpose and `[technology]` for cross-process calls |
| Acronyms | Explained under the key |
| Theme | Fills, borders and text colors are explicit, with white text on dark fills and dark text on light fills, so both light and dark themes stay readable |

---

## 2. Project layout

```text
.
├── README.md
├── CLAUDE.md                       Rules for how the code is written
├── pyproject.toml                  Dependencies and tool config
├── .env.example                    Template for required environment variables
├── notebooks/
│   ├── phase1_session1_ingestion.ipynb Standalone teaching notebook for Session 1
│   └── phase1_session2_chunking.ipynb  Standalone teaching notebook for Session 2
│
├── app/
│   ├── core/                       Cross-cutting infrastructure
│   │   ├── config.py               Settings: every env var, typed
│   │   ├── logging.py              JSON logging setup
│   │   └── telemetry.py            Datadog APM switch
│   ├── models/
│   │   ├── ingestion.py            IngestRequest, IngestResponse
│   │   └── retrieval.py            RetrieveRequest, RetrieveResponse, citations
│   ├── chains/                     Pure LangChain: no web or UI imports
│   │   ├── parsing.py              PDF to structured elements
│   │   ├── chunking.py             Clause-aware chunking (structure first, size second)
│   │   ├── embeddings.py           OpenAI embeddings client
│   │   ├── ingestion.py            The write-path chain: enrich, checksum, compare, upsert
│   │   └── retrieval.py            Atlas filters, ranked chunks, parent expansion
│   ├── database/
│   │   ├── mongo.py                Vector store, parent store, stale-chunk removal
│   │   └── indexes.md              The Atlas Vector Search index JSON (created by hand), parent collection
│   ├── services/
│   │   ├── ingestion.py            Entry point: register to requests, run the chain
│   │   └── retrieval.py            Retrieval wiring and operational counters
│   ├── api/                       FastAPI retrieval, health and metrics routes
│   └── main.py                    FastAPI application
│
├── tests/
│   ├── test_ingestion.py           Ingestion checks
│   └── test_retrieval.py           Retrieval and API checks
│
└── nexa_synthetic_data/            The corpus (see its own README.md)
    ├── document_register.json      Controlled library: versions, windows, supersession
    ├── policies/                   8 PDFs
    ├── golden_qa/                  97 Q&As for evaluation (used from Week 2)
    ├── catalog/  customers/  uploads/  api/  generator/
    └── README.md
```

### Layer rules

- `chains/` has no FastAPI or Streamlit imports.
- `database/` is the only place that creates a MongoDB client.
- `services/` bridges chains to the ingestion command and FastAPI.
- Settings are read once through `app/core/config.py`. No other module calls `os.getenv`.

### Module dependencies

```mermaid
flowchart TD
    SVC["services/ingestion.py"] --> CHAIN["chains/ingestion.py"]
    SVC --> EMB["chains/embeddings.py"]
    SVC --> DB["database/mongo.py"]
    SVC --> MODELS["models/ingestion.py"]
    SVC --> CFG["core/config.py"]
    SVC --> LOG["core/logging.py"]
    SVC --> TEL["core/telemetry.py"]

    CHAIN --> PARSE["chains/parsing.py"]
    CHAIN --> CHUNKING["chains/chunking.py"]
    CHAIN --> MODELS
    CHAIN --> CFG

    EMB --> CFG
    DB --> CFG
```

---

## 3. How a document flows through the system

One run of `python -m app.services.ingestion <register>` does this:

```mermaid
sequenceDiagram
    autonumber
    participant CLI as services.ingestion
    participant REG as document_register.json
    participant CH as Ingestion chain
    participant PDF as parse_document
    participant UNS as chunk_by_clause
    participant OAI as OpenAI Embeddings
    participant DB as Atlas: chunks
    participant PSEC as Atlas: parent sections

    CLI->>REG: read entries
    REG-->>CLI: register entries
    CLI->>CLI: requests_from_register filters authoritative entries and builds IngestRequests
    loop for each IngestRequest
        CLI->>CH: ainvoke(request)
        CH->>PDF: parse
        PDF-->>CH: Title, NarrativeText, Table elements
        CH->>UNS: chunk
        UNS-->>CH: one chunk per clause (tables kept with their clause)
        CH->>CH: enrich: header line, metadata, chunk_id, parent_id, checksum
        CH->>DB: compare: read stored checksums by chunk_id
        DB-->>CH: checksums
        CH->>PSEC: clear old sections and write current sections
        alt changed chunks exist
            CH->>OAI: embed changed chunks
            OAI-->>CH: vectors
            CH->>DB: upsert changed chunks by chunk_id
        else all chunks are unchanged
            CH->>CH: skip embedding and vector upsert
        end
        CH-->>CLI: IngestResponse
        CLI->>DB: delete_stale_chunks: retire chunks the source no longer has
        CLI->>CLI: log document_ingested
    end
```

### What each stage does

| # | Stage | Function | Result |
|---|---|---|---|
| 1 | Load | `requests_from_register` | One `IngestRequest` per authoritative document in the register. Files not in the register are never indexed. |
| 2 | Parse | `parse_document` | Ordered `Title`, `NarrativeText` and `Table` elements. Tables are extracted whole as HTML; page headers and footers are dropped. |
| 3 | Chunk | `chunk_by_clause` | One chunk per numbered clause. A table or footnote stays with the clause that introduces it, and a table is never split. Only a clause over `CHUNK_MAX_CHARACTERS` is split, at sentence boundaries, with `CHUNK_OVERLAP_CHARACTERS` of overlap. |
| 4 | Enrich + hash | `enrich` (inside the chain) | A LangChain `Document` per child chunk: identity header line, deterministic `chunk_id`, `parent_id`, clause fields, metadata and a `checksum`. Also one parent `Document` per section. |
| 5 | Compare | `compare` (inside the chain) | The children whose checksum differs from the one stored under the same `chunk_id`. |
| 6 | Embed + upsert | `embed_and_upsert` (inside the chain) | Parent sections rewritten; vectors from OpenAI for the changed children only, written to Atlas by `chunk_id`. |
| 7 | Retire | `delete_stale_chunks` (called by the service) | Chunks of this document that the latest ingest no longer produced are deleted. |

---

## 4. Classes and functions

### Class diagram

```mermaid
classDiagram
    class Settings {
        +SecretStr mongodb_uri
        +str mongodb_db
        +str mongodb_collection
        +str vector_index_name
        +str mongodb_parent_collection
        +SecretStr openai_api_key
        +str embedding_model
        +int embedding_dimensions
        +int embedding_batch_size
        +int chunk_max_characters
        +int chunk_overlap_characters
        +str institution
        +str jurisdiction
        +str confidentiality_level
        +str log_level
        +bool dd_trace_enabled
    }

    class IngestRequest {
        +str source_path
        +str doc_id
        +str title
        +str institution
        +str product_id
        +str policy_version
        +date effective_date
        +date effective_to
        +str supersedes
        +str jurisdiction
        +str doc_type
        +str confidentiality_level
    }

    class IngestResponse {
        +str doc_id
        +int chunk_count
        +list~str~ chunk_ids
        +int embedded_count
        +int unchanged_count
        +str embedding_model
    }

    class Chunk {
        +str text
        +int section_number
        +str section
        +str clause
        +str clause_heading
        +bool has_table
    }

    class BaseSettings
    class BaseModel

    BaseSettings <|-- Settings
    BaseModel <|-- IngestRequest
    BaseModel <|-- IngestResponse
    IngestRequest ..> IngestResponse : chain turns one into the other
```

Both models use `extra="forbid"`, so an unknown or misspelled field raises a validation error instead of being silently dropped.

### `app/core/`

| Item | Signature | Purpose |
|---|---|---|
| `Settings` | class, extends `BaseSettings` | Typed view of every environment variable. Reads `.env`. Secrets are `SecretStr`, so they never print in logs. |
| `get_settings` | `() -> Settings` | Cached accessor; the app builds `Settings` once. |
| `configure_logging` | `(level: str) -> None` | Configures `structlog` to write JSON lines to stdout, ready for Datadog. |
| `init_telemetry` | `(enabled: bool) -> None` | Calls `ddtrace.patch_all()` when enabled so PyMongo is traced. Does nothing when disabled. |

### `app/models/ingestion.py`

| Item | Purpose |
|---|---|
| `IngestRequest` | The Ingestion Service contract: one source document plus its document-level metadata. |
| `IngestResponse` | What an ingest returns: the document, how many chunks, their IDs, how many were embedded and how many were skipped as unchanged, and the embedding model used. |

### `app/chains/`

| Item | Signature | Purpose |
|---|---|---|
| `parse_document` | `(path: str) -> list[Element]` | Entry point for parsing. PDFs go to `_parse_pdf`; other formats go to `unstructured.partition`. |
| `_parse_pdf` | `(path: str) -> list[Element]` | Uses `pdfplumber`. Tables come from ruling lines, headings from font size larger than the body text, and header and footer lines are cropped by page margin. Output is in reading order. |
| `_table_element` | `(rows) -> Table` | Builds a `Table` element with an HTML rendering, so each value stays attached to its column. |
| `get_embeddings` | `(settings) -> OpenAIEmbeddings` | Pins model, dimension and batch size from settings. The read path must use the same values. |
| `Chunk` | frozen dataclass | One child chunk before enrichment: text, section, clause number and heading, and whether it holds a table. |
| `chunk_by_clause` | `(elements, max_characters, overlap) -> list[Chunk]` | Hybrid chunking. Structure first: one chunk per numbered clause, tables kept with their clause. Size second: an oversized clause is split with `RecursiveCharacterTextSplitter`, tables staying whole. |
| `chunk_checksum` | `(text, metadata) -> str` | SHA-256 over the chunk text and metadata. The metadata includes `embedding_model`, so a model change forces a re-embed. |
| `parent_key_prefix` | `(doc_id) -> str` | Key prefix of a document's parent sections (`POL-HL-V3_s`). |
| `build_ingestion_chain` | `(vector_store, parent_store, settings) -> Runnable` | Composes the write path as one LCEL chain: `parse`, `chunk`, `enrich`, `compare`, `embed_and_upsert`. Input is `{"request": IngestRequest}`; run it with `ainvoke`. Each stage has a `run_name`, so a LangSmith trace shows the time spent per stage. It depends only on the `VectorStore` and `BaseStore` interfaces, so tests pass in-memory stores. |

### `app/database/mongo.py`

| Item | Signature | Purpose |
|---|---|---|
| `get_vector_store` | `(settings, embedding) -> MongoDBAtlasVectorSearch` | Returns the chunk store with collection, embedding and index name passed explicitly. It never creates the index; that is manual (see [Section 6](#6-getting-started)). |
| `get_parent_store` | `(settings) -> MongoDBDocStore` | Key-value store of whole sections, keyed by `parent_id`, in the `MONGODB_PARENT_COLLECTION` collection. Not embedded, no search index. |
| `delete_stale_chunks` | `(collection, doc_id, keep_ids) -> int` | Deletes chunks of a document whose IDs the latest ingest did not produce. Returns how many were removed. |

### `app/services/ingestion.py`

| Item | Signature | Purpose |
|---|---|---|
| `DOC_TYPES` | `dict[str, str]` | Maps a `doc_id` prefix to a document type: `POL` is `policy`, `CIR` is `circular`. |
| `requests_from_register` | `(register_path, settings) -> list[IngestRequest]` | Reads `document_register.json`, keeps authoritative entries, and fills `institution`, `jurisdiction` and `confidentiality_level` from settings. |
| `ingest` | `async (requests) -> list[IngestResponse]` | Builds the stores and chain once, then for each request runs the chain, retires stale chunks, and logs one `document_ingested` event with `embedded_count`, `unchanged_count` and `stale_chunks_removed`. |
| `main` | `() -> None` | Command-line entry point. Takes the register path as its only argument. |

---

## 5. Data model: the chunk record

Each child chunk is stored in MongoDB as one document. Metadata sits at the top level beside the text and vector.

```json
{
  "_id": "POL-HL-V3_3.4_c01",
  "text": "[POL-HL-V3 | NexaHome Loan Policy v3.0 | 3. Eligibility]\n3.4 FOIR limit. The maximum FOIR depends on net monthly income as shown below.\n<table><tr><td>Net monthly income</td><td>Maximum FOIR</td></tr><tr><td>Below ₹1,00,000</td><td>50%</td></tr> ...</table>",
  "embedding": [0.012, -0.044, "... 1536 floats"],

  "doc_id": "POL-HL-V3",
  "title": "NexaHome Loan Policy",
  "chunk_id": "POL-HL-V3_3.4_c01",
  "parent_id": "POL-HL-V3_s03",
  "section": "3. Eligibility",
  "clause": "3.4",
  "clause_heading": "FOIR limit",
  "institution": "NexaBank",
  "product_id": "NEXA-HL",
  "policy_version": "3.0",
  "effective_date": "2025-10-01",
  "effective_to": null,
  "supersedes": "POL-HL-V2",
  "jurisdiction": "IN",
  "doc_type": "policy",
  "section_type": "table",
  "confidentiality_level": "internal",
  "embedding_model": "text-embedding-3-small",
  "checksum": "sha256:2f50cb38..."
}
```

The nine metadata fields from the training deck are `institution`, `product_id`, `policy_version`, `effective_date`, `supersedes`, `jurisdiction`, `doc_type`, `section_type` and `confidentiality_level`. Eight come from the request; `section_type` (`text` or `table`) is set per chunk.

Session 2 adds:

| Field | Meaning |
|---|---|
| header line in `text` | `[doc_id \| title vversion \| section]`. It is embedded with the clause, so a chunk read on its own still says where it is from. |
| `chunk_id` | `{doc_id}_{clause}_c{nn}`. Built from the clause, not a running position, so inserting a clause does not renumber (and re-embed) the rest. Text outside a numbered clause uses the section number, for example `POL-HL-V3_0_c01` for the front matter. |
| `clause`, `clause_heading`, `section` | The citable unit. The golden Q&A set cites sources as `{doc_id, clause}`. |
| `parent_id` | Key of the whole section in the parent collection: `{doc_id}_s{NN}`. |
| `checksum` | SHA-256 of text + metadata (including `embedding_model`). Ingestion skips a chunk whose stored checksum matches. |
| `effective_to_search` | ISO upper bound for Atlas as-of filtering; `9999-12-31` for open-ended policies while source `effective_to` stays null. |

### The parent record

Each section is stored once, as plain text, in the collection named by `MONGODB_PARENT_COLLECTION` (default `policy_sections`). It has no embedding. `/retrieve` searches children and returns the matching parent text.

```json
{
  "_id": "POL-HL-V3_s06",
  "page_content": "[POL-HL-V3 | NexaHome Loan Policy v3.0 | 6. Fees and charges]\n6.1 General. ...\n6.2 Processing fee. ...\n6.5 Other costs. ...",
  "parent_id": "POL-HL-V3_s06",
  "section": "6. Fees and charges",
  "doc_id": "POL-HL-V3",
  "policy_version": "3.0",
  "effective_date": "2025-10-01",
  "...": "the other document-level fields"
}
```

### Where the metadata comes from

```mermaid
flowchart LR
    REG["document_register.json"] -->|"doc_id, title, product_id,<br/>version, effective window,<br/>supersedes"| REQ["IngestRequest"]
    ENV[".env"] -->|"institution, jurisdiction,<br/>confidentiality_level"| REQ
    PFX["doc_id prefix"] -->|"doc_type"| REQ
    REQ -->|"model_dump"| META["chunk metadata"]
    PIPE["pipeline"] -->|"chunk_id, parent_id, clause,<br/>section_type, embedding_model,<br/>checksum"| META
```

---

## 6. Getting started

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/) and Python 3.14+ installed.
- An **OpenAI API key**.
- A **MongoDB Atlas** cluster on a tier that supports Vector Search.

### Step 1: install

```bash
uv lock  # refresh the checked-in lock for Python 3.14+ and FastAPI
uv sync --python 3.14 --locked
source .venv/bin/activate  # macOS
.venv\Scripts\activate     # Windows
```

> **Heads-up:** `uv sync` creates `.venv` inside the project folder. If the folder is synced by Google Drive, point it elsewhere first:
> `export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/nexaassist"`

### Step 2: configure

```bash
cp .env.example .env
```

Edit `.env`. These are required:

| Variable | Example | Meaning |
|---|---|---|
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster.mongodb.net` | Atlas connection string |
| `MONGODB_DB` | `nexaassist` | Database name |
| `MONGODB_COLLECTION` | `policy_chunks` | Collection that holds chunks |
| `OPENAI_API_KEY` | `sk-...` | Used for embeddings only |
| `INSTITUTION` | `NexaBank` | Stamped on every chunk |
| `JURISDICTION` | `IN` | Stamped on every chunk |
| `CONFIDENTIALITY_LEVEL` | `internal` | Stamped on every chunk |

These have defaults and are optional:

| Variable | Default | Meaning |
|---|---|---|
| `VECTOR_INDEX_NAME` | `policy_chunks_v1` | Must match the index you create in Atlas |
| `MONGODB_PARENT_COLLECTION` | `policy_sections` | Collection that holds whole sections (parent documents) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Pinned; never mix models in one index |
| `EMBEDDING_DIMENSIONS` | `1536` | Must match the Atlas index |
| `EMBEDDING_BATCH_SIZE` | `100` | Chunks per embedding request |
| `CHUNK_MAX_CHARACTERS` | `1200` | Target size. Only a clause above it is split; a table can exceed it |
| `CHUNK_OVERLAP_CHARACTERS` | `150` | Text repeated between the pieces of a split clause |
| `LOG_LEVEL` | `INFO` | `structlog` level |
| `DD_TRACE_ENABLED` | `false` | Turn on only with a Datadog Agent running |

`.env.example` also lists `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY` and `LANGCHAIN_PROJECT`. LangChain reads these itself; set `LANGCHAIN_TRACING_V2=true` to see per-stage traces in LangSmith.

### Step 3: create the Atlas Vector Search index (once, by hand)

In the Atlas UI go to **Atlas Search, Create Search Index, Atlas Vector Search, JSON editor**. Choose your database and collection, name the index `policy_chunks_v1`, and paste the exact JSON from [app/database/indexes.md](app/database/indexes.md). Existing collections need that index rebuilt and the document register re-ingested before `/retrieve` can filter on `effective_to_search`. If you change the model or dimension, create a new index version (`policy_chunks_v2`) and re-embed everything.

---

## 7. Using the project

### How to execute the code

Run everything from the project root (the folder that contains `pyproject.toml`). There are three ways to run it, depending on what you have.

```mermaid
flowchart TD
    START{"Do you have OpenAI and<br/>Atlas credentials?"}
    START -->|Yes| A["Option A: full ingestion<br/>writes to Atlas"]
    START -->|No| B{"What do you want to see?"}
    B -->|"Prove the code works"| C["Option B: run the tests"]
    B -->|"See the pipeline run"| D["Option C: offline dry run<br/>or the notebook"]
```

| Option | Needs credentials | Writes to Atlas | Use it to |
|---|---|---|---|
| A. Full ingestion | Yes | Yes | Load the corpus for real |
| B. Tests | No | No | Check parsing, chunking, metadata and idempotency |
| C. Offline dry run | No | No | Watch all eight PDFs go through the real chain with fake embeddings |

#### Option A: full ingestion (needs `.env` and the Atlas index)

Complete [Section 6](#6-getting-started) first, then:

```bash
uv sync                                 
python -m app.services.ingestion nexa_synthetic_data/document_register.json
```

What happens, in order: settings load from `.env`, logging is configured, the register is read, and each of the eight documents is parsed, chunked, embedded and upserted. It finishes after eight `document_ingested` log lines (see below). To ingest a different register or a copy of it, pass its path as the argument.

#### Retrieval API (needs `.env`, re-ingested chunks, and the rebuilt index)

```bash
uv run uvicorn app.main:app --host 127.0.0.1
curl -X POST http://127.0.0.1:8000/retrieve -H 'Content-Type: application/json' \
  -d '{"query":"What is the NexaHome processing fee?","as_of":"2026-10-01","top_k":5,"product_id":"NEXA-HL","jurisdiction":"IN"}'
```

`/retrieve` returns ranked child passages, citations (`doc_id`, title, version, clause, effective date), parent-section text, and search/parent/total timings in milliseconds. `as_of` is required; `top_k` defaults to 5 and is limited to 1–20. Invalid bodies return 422, and retrieval failures return a generic 503. `GET /health` reports process liveness; `GET /metrics` reports per-process retrieval requests, errors, empty results, and accumulated latency. To enable Datadog APM, run with a Datadog Agent and `uv run --env-file .env ddtrace-run uvicorn app.main:app --host 127.0.0.1`.

The API has no authentication because this is a synthetic training corpus. Keep it bound to localhost until an access-control contract is defined. The as-of filter handles document effective windows; it does not yet resolve a circular that supersedes only selected clauses in a still-current policy.

#### Session 5: RAG production failure modes

Retrieval is already implemented. The next lesson reproduces **retrieval misses, stale indexed chunks, and embedding compatibility failures** using the existing response models and ingestion checksum function:

```bash
uv run python -m app.evaluation.rag_failure_modes
```

The command emits one structured JSON log with healthy and deliberately faulty examples. It does not load `.env`, contact Atlas or OpenAI, download a model, or change indexed data.

For thirteen examples using both real Atlas collections (four retrieval, five
staleness and four embedding cases), use the
[Session 5 runner](app/evaluation/rag_failure_examples.py).

The [Session 5 teaching deck](../PPTs/5.NexaAssist_Week1_Session5.pptx) lives in the
sibling `PPTs` directory of the training workspace.

Run the examples from the project root:

```bash
uv run python -m app.evaluation.rag_failure_examples       # all 13 cases
uv run python -m app.evaluation.rag_failure_examples R3    # child citations versus parent context
uv run python -m app.evaluation.rag_failure_examples S5    # missing/stale parent, local replay
```

This second runner reads the configured chunk and parent collections and makes OpenAI embedding calls for retrieval. Fault injections modify local copies only. It never changes stored data or indexes. The parent-aware observation in `app/evaluation/datasets/session5_atlas_parent_observation.json` includes 177 chunks, 80 parent sections, source freshness and both explicit-citation and expanded-context coverage. Ranks and scores can vary on another run.

| Function in `app/evaluation/rag_failure_modes.py` | Inputs | What it reports |
|---|---|---|
| `diagnose_retrieval` | Existing `RetrieveResponse` and expected document/clause references | Empty results and nonempty results that omit expected evidence |
| `diagnose_expanded_context` | Response, expected references and stored source chunks | Verbatim required-clause availability inside returned `parent_text`, separately from child citations |
| `diagnose_parent_links` | Stored child documents and parent map | Missing parents, policy-scope mismatches, missing child bodies and unreferenced parents |
| `diagnose_staleness` | Current source and stored `ChunkSnapshot` manifests | Missing, changed-checksum, and unexpected chunk IDs |
| `diagnose_embeddings` | Stored snapshots, expected embedding model and dimension | Model/dimension mismatches; an empty snapshot is not evaluated |

The functions can also consume real snapshots supplied by a caller, but this lesson does not add a live Atlas audit adapter. A source snapshot must be regenerated from current source chunks with the existing `chunk_checksum(text, metadata)` logic, excluding the `checksum` field itself. Compare complete manifests covering the same corpus and configuration; a sample cannot prove the whole index fresh. Stored dimensions must describe the actual vector length. `diagnose_staleness` checks stored chunk freshness, not Atlas Search index readiness or parent-section consistency.

Matching model names and dimensions establishes compatibility, **not absence of statistical embedding drift**. The report explicitly returns `distribution_drift: not_measured`. To investigate behavioral drift, compare the same golden queries and expected citations across versioned runs, then inspect corpus and incoming-query changes. No drift threshold is assumed.

The existing `/metrics` endpoint exposes process-local JSON counters.
`/metrics/latency` provides nearest-rank p50/p95/p99 retrieval timings from the last
1,000 successful requests in this process. Neither detects nonempty retrieval
misses. Fleet aggregation, latency histograms, alert thresholds, scheduled
ingestion and Atlas index-readiness checks remain production work.

#### Option B: run the tests (no credentials)

```bash
uv run pytest -q
```

The offline suite covers ingestion, retrieval, reranking, grounded answers,
evaluation, telemetry, feedback and Streamlit interactions. It uses controlled
provider responses and local stores; it does not measure live Atlas relevance.

#### Option C: offline dry run (no credentials)

Save this as `dry_run.py` in the project root and run `uv run python dry_run.py`. It uses the real parser and chain, but an in-memory store and fake embeddings, so nothing leaves your machine.

```python
import asyncio
from pathlib import Path

from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.stores import InMemoryStore
from langchain_core.vectorstores import InMemoryVectorStore

from app.chains.ingestion import build_ingestion_chain
from app.core.config import Settings
from app.services.ingestion import requests_from_register

settings = Settings(
    _env_file=None,
    mongodb_uri="mongodb://unused", mongodb_db="unused", mongodb_collection="unused",
    openai_api_key="unused",
    institution="NexaBank", jurisdiction="IN", confidentiality_level="internal",
)
store = InMemoryVectorStore(DeterministicFakeEmbedding(size=1536))
chain = build_ingestion_chain(store, InMemoryStore(), settings)


async def main() -> None:
    register = Path("nexa_synthetic_data/document_register.json")
    for request in requests_from_register(register, settings):
        response = await chain.ainvoke({"request": request})
        print(
            f"{response.doc_id:<13}{response.chunk_count:>4} chunks,"
            f"{response.embedded_count:>4} embedded"
        )
    print("total:", len(store.store))


asyncio.run(main())
```

Expected output:

```text
POL-HL-V1      31 chunks,  31 embedded
POL-HL-V2      31 chunks,  31 embedded
POL-HL-V3      32 chunks,  32 embedded
CIR-2026-07     8 chunks,   8 embedded
POL-PL-V1      18 chunks,  18 embedded
POL-LAP-V1     19 chunks,  19 embedded
POL-AL-V1      17 chunks,  17 embedded
POL-OPS-001    21 chunks,  21 embedded
total: 177
```

The notebook [phase1_session2_chunking.ipynb](notebooks/phase1_session2_chunking.ipynb) does the same thing step by step and falls back to this offline mode automatically.

#### What a successful full run looks like

One JSON log line per document, eight in total:

```json
{"doc_id": "POL-HL-V3", "chunk_count": 32, "embedded_count": 32, "unchanged_count": 0, "stale_chunks_removed": 0, "embedding_model": "text-embedding-3-small", "policy_version": "3.0", "effective_date": "2025-10-01", "event": "document_ingested", "level": "info", "timestamp": "..."}
```

Expected chunk counts for the synthetic corpus:

| Document | Chunks |
|---|---|
| POL-HL-V1, POL-HL-V2 | 31 each |
| POL-HL-V3 | 32 |
| CIR-2026-07 | 8 |
| POL-PL-V1 | 18 |
| POL-LAP-V1 | 19 |
| POL-AL-V1 | 17 |
| POL-OPS-001 | 21 |
| **Total** | **177** |

Each count is the document's numbered clauses plus one front-matter chunk. The parent collection ends up with 80 sections.

Running it again is safe and cheap. A second run logs `"embedded_count": 0` for every document, because every stored checksum matches and no embedding call is made.

**Upgrading a collection that Session 1 filled:** the chunk IDs changed from `POL-HL-V3_c007` to `POL-HL-V3_3.4_c01`. The first Session 2 run embeds all 177 new chunks and reports the 128 old ones under `stale_chunks_removed` as it deletes them. No manual cleanup is needed.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ValidationError ... Field required` naming `mongodb_db`, `openai_api_key`, `institution`, etc. | A required variable is missing from `.env`, or `.env` was not found | Run from the project root and compare `.env` with `.env.example` |
| `command not found: uv` | `uv` is not installed | Install it from https://docs.astral.sh/uv/ |
| `AuthenticationError` from OpenAI | Wrong or placeholder `OPENAI_API_KEY` | Set a real key (`sk-...`) |
| `ServerSelectionTimeoutError` from PyMongo | Bad `MONGODB_URI`, or your IP is not on the Atlas network access list | Check the URI and add your IP in Atlas |
| Ingestion succeeds but the collection holds fewer or more documents than 128 | A different `MONGODB_COLLECTION` than you are inspecting, or older data in it | Check the collection name; clear old documents if you changed the chunking |
| Vector search later returns nothing | The Atlas index does not exist, is still building, or has a different name or dimension | Check index status; `VECTOR_INDEX_NAME` and `EMBEDDING_DIMENSIONS` must match |
| `libmagic is unavailable` warning | Optional file-type helper not installed | Safe to ignore |
| Tests or commands cannot find `app` | Not run from the project root | `cd` to the folder containing `pyproject.toml` |

### Check the result in Atlas

In the Atlas data explorer, the collection should hold 128 documents, each with an `embedding` array of 1536 numbers and the metadata fields from [Section 5](#5-data-model-the-chunk-record).

### Use the pieces from your own code

```python
import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.services.ingestion import ingest, requests_from_register

settings = get_settings()
requests = requests_from_register(Path("nexa_synthetic_data/document_register.json"), settings)

# Ingest only the circular
circular = [r for r in requests if r.doc_id == "CIR-2026-07"]
responses = asyncio.run(ingest(circular))
print(responses[0].chunk_count)  # 8
```

To ingest a document that is not in the register, build an `IngestRequest` yourself and pass it to `ingest`. All fields except `product_id`, `effective_to` and `supersedes` are required.

### Walk through it as a lesson: the notebook

There is one notebook per session: [phase1_session1_ingestion.ipynb](notebooks/phase1_session1_ingestion.ipynb) (architecture and the Session 1 baseline) and [phase1_session2_chunking.ipynb](notebooks/phase1_session2_chunking.ipynb) (tokens, embeddings, clause-aware chunking, parent documents, checksums, scaling arithmetic). Each is a teaching version of this same pipeline. It does not import `app/`, and it maps each section to the file it mirrors. Open it with the project's environment as the kernel and run it from the project root.

If `MONGODB_URI` and `OPENAI_API_KEY` are not set, it switches to **offline mode** (in-memory store, fake embeddings). Every stage still runs, but the similarity ranking in the last section is arbitrary. With real credentials, that section shows several policy versions competing for the same question, which is the reason version metadata exists.

### Adapting it

| To change | Where |
|---|---|
| Chunk size and overlap | `CHUNK_MAX_CHARACTERS`, `CHUNK_OVERLAP_CHARACTERS` in `.env`, no code change |
| What counts as a clause or section | The two regular expressions at the top of [app/chains/chunking.py](app/chains/chunking.py) |
| Embedding model or dimension | `.env`, then create a new Atlas index version and re-embed |
| The corpus | Add the file to the register, then re-run the command |
| What is stored per chunk | `enrich` inside [app/chains/ingestion.py](app/chains/ingestion.py) |
| Parsing rules | [app/chains/parsing.py](app/chains/parsing.py) |

---

### Next session: from retrieved evidence to an answer

The earlier R1–R4 questions are executable examples in
`app/evaluation/rag_failure_examples.py`. The next session adds answer generation
on top of the same retrieval implementation:

```text
POST /answer (same request schema as /retrieve)
  -> app/api/answer.py                 HTTP validation and safe service errors
  -> app/services/answer.py            Wires the existing retrieval service and chat model
  -> app/chains/answer.py              Retrieval, context assembly, generation, citation checks
     -> app/services/retrieval.py     Existing Atlas retrieval and counters
     -> app/chains/prompts/answer.py  Evidence-only instructions and applicability rules
     -> app/chains/llm.py             ChatOpenAI with the Responses API
  -> app/models/answer.py              Structured answer, quotes, sources and timings
```

`CHAT_MODEL=gpt-6-luna` is the configured default. It uses the existing
`OPENAI_API_KEY`; the existing embedding model and Atlas index are unchanged.
The chat model receives the question and retrieved policy context. Optional
LangChain tracing also records chain inputs and outputs when enabled.

Start the API from the repository root:

```bash
uv run uvicorn app.main:app --host 127.0.0.1
```

In another terminal, start with a straightforward fact:

```bash
curl -sS -X POST http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the maximum loan amount for a NexaHome Loan?","as_of":"2026-10-01","product_id":"NEXA-HL","top_k":5}'
```

Then reuse the Session 5 circular experiment:

```bash
curl -sS -X POST http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  -d '{"query":"What processing fee does Circular CIR-2026-07 prescribe in revised clause 6.2, and which loans sanctioned from 1 July 2026 does it cover?","as_of":"2026-10-01","product_id":"NEXA-HL","top_k":20}'
```

Compare it with the generic current-fee question at top 5. Do not assume adding
generation fixes the known retrieval miss: a model cannot reliably discover a
missing amendment from evidence it never receives. Exact generated wording and
the quality of applicability reasoning require live evaluation.

Finish with an unsupported question such as "What is the current NRLR?". Its
current value comes from the catalog, which the PDF ingestion path does not
index. The expected behavior is `insufficient_evidence`, rather than guessing a
rate from policy examples. The ten teaching cases, including the historical
boundary and abstention cases, are in `evaluation/datasets/answer.jsonl`. They
are evaluation inputs and expectations, not a claim that generation has passed.

#### Reading the answer response

- `status`: `answered` or `insufficient_evidence`.
- `answer`: generated text with `[1]`-style evidence markers, or a fixed
  insufficient-evidence message.
- `citations`: each has `evidence_id`, an exact supporting `quote`, and the
  `matched_child` citation from retrieval. The quote can come from another
  clause in the child's parent section; `matched_child.clause` is not a claim
  that the quote belongs to that clause.
- `retrieval_timings`: the existing search and parent-fetch timings.
- `generation_ms`: prompt/model duration, excluding retrieval; zero for an
  empty retrieval where no generation call is made.

Repeated parent text is deduplicated within a document/version before prompting.
The first matching child's citation is retained for that context. Source IDs
are local to each response and are not MongoDB document IDs.

The application rejects answered drafts with missing/unknown citation IDs,
unmatched inline markers, or quotes absent from the referenced context. Such
drafts become `insufficient_evidence`. Empty retrieval also skips generation;
upstream provider/database/parser failures return a generic HTTP 503.

These are mechanical citation checks, not a semantic correctness guarantee.
Applicability and amendment handling are prompt instructions, not a deterministic
policy-precedence engine. The generation slice does not expand retrieval scope
or repair missing/stale records. Inspect the evidence and compare against the
golden answers before relying on an answer.

Official integration references: [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [LangChain structured output](https://docs.langchain.com/oss/python/integrations/chat/openai#structured-output).

### Session 8: evaluate answers and investigate failures

The evaluation CLI reuses `build_answer_chain` and evaluates the exact evidence
used for generation. The ten cases in `evaluation/datasets/answer.jsonl` cover
current policies, amendments, historical boundaries and expected abstentions.

Install the existing UI and evaluation extras together, then begin with one case:

```bash
uv sync --locked --extra ui --extra evaluation
uv run --no-sync --env-file .env ddtrace-run python -m app.evaluation.run --limit 1 --output app/evaluation/results/one_case.json
```

This calls Atlas, the configured generation model, the existing judge and RAGAS.
The runner uses `CHAT_MODEL` for generation and `EVAL_JUDGE_MODEL` for judging and
RAGAS, falling back to `CHAT_MODEL` when the judge setting is unset or blank.
Its report records the actual judge model and explains the limits of automated
judging. Batch and live RAGAS share the Responses API structured-output adapter
and the configured embedding model and dimensions.
The evaluation extra pins `langchain-community==0.3.31` because RAGAS 0.4.3 imports
a wrapper removed in community 0.4.

To run all ten cases, omit `--limit` and choose a separate report path:

```bash
uv run --no-sync --env-file .env ddtrace-run python -m app.evaluation.run --output app/evaluation/results/all_cases.json
```

Reports include generated answers, actual retrieved and reference contexts,
retrieval/generation timings, compact LangChain traces, judge rationales and
four RAGAS scores. Expected abstentions skip RAGAS. An answerable case with no
retrieved context receives zero RAGAS scores; non-finite metrics fail the run.
Out-of-range scores also fail; only floating-point roundoff at zero and one is
normalized. Each external RAGAS metric has a 120-second timeout.

With LLM Observability enabled, each answer has a `policy_answer_evaluation`
workflow span. Judge correctness, groundedness, status matching and the applicable
RAGAS scores are attached to that span. Local reports retain its Datadog IDs.
See [Datadog web traces and evaluations](DATADOG_README.md#view-traces-and-evaluations-on-the-web)
for the application link, filters and export verification.

A completed run without `--min-score` reports `gate.status=not_configured`.
To apply an explicitly chosen teaching threshold:

```bash
uv run --no-sync --env-file .env ddtrace-run python -m app.evaluation.run --min-score 0.8 --output app/evaluation/results/gated_cases.json
```

The gate checks the RAGAS metric means, each case's judge scores and matching
answer/abstention status. A failed gate or pipeline error exits 1. The example
0.8 is a teaching choice, not a calibrated production threshold. A subset result
does not validate the full dataset. Keep separate output paths when preserving
runs: this runner writes to the requested path and can replace an existing file.
Reports contain synthetic policy text and model responses.

For controlled offline checks without provider calls, run
`uv run --no-sync pytest tests/test_answer.py tests/test_evaluation.py`.
Constructed fixtures test wiring and citation behavior; they do not measure
semantic model quality. Existing LangSmith tracing settings apply independently.

## 8. Testing and quality checks

```bash
uv run pytest -q              # 15 tests, no network or credentials needed
uv run ruff check app tests   # lint
uv run mypy app tests         # type check
```

The tests run the real parser and chain over your synthetic PDFs, with an in-memory vector store and fake embeddings in place of Atlas and OpenAI.

| Test | What it proves |
|---|---|
| `test_register_maps_to_requests` | The register yields 8 requests with correct dates, types and a null product for the operations policy |
| `test_every_document_parses_and_chunks` | All 8 PDFs ingest and every chunk has the nine metadata fields plus `clause`, `parent_id` and `checksum` |
| `test_version_metadata_is_stamped_on_every_chunk` | Product, version, effective date and `supersedes` appear on every chunk |
| `test_tables_are_kept_whole` | The FOIR table is one chunk with all three rows intact, together with the sentence of clause 3.4 that introduces it |
| `test_running_headers_and_footers_are_dropped` | Page headers and footers do not leak into chunk text |
| `test_reingesting_is_idempotent` | Ingesting the same document twice leaves the chunk count unchanged |
| `test_every_registered_clause_is_exactly_one_chunk` | For all 8 documents, the clause chunks match the register's clause list one to one, numbers and headings |
| `test_every_golden_citation_resolves_to_a_chunk` | Every `{doc_id, clause}` cited by the 97 golden Q&As exists as a chunk |
| `test_chunk_carries_identity_header_and_clause_id` | Clause 6.2 has the ID `POL-HL-V3_6.2_c01`, starts with the header line, and holds no other clause |
| `test_oversized_clause_splits_narrative_with_overlap_but_never_the_table` | Above the size limit, narrative splits at sentences with overlap and the table stays whole |
| `test_parent_section_holds_every_clause_of_the_section` | The parent of clause 6.2 contains clauses 6.1 to 6.5 and nothing from section 7 |
| `test_reingesting_replaces_parent_sections` | A second ingest leaves the same parent keys, with no duplicate-key error |
| `test_only_new_or_changed_chunks_are_embedded` | A re-run sends nothing to the embedding model; one stale checksum re-embeds exactly one chunk |
| `test_changing_the_embedding_model_re_embeds_everything` | A different `embedding_model` changes every checksum |
| `test_stale_chunks_are_deleted_and_current_ones_kept` | `delete_stale_chunks` removes only the named document's leftover IDs |

What the tests do **not** cover: real embedding quality, Atlas index behaviour, search results, or the write to a live Atlas collection (the stores are in-memory; only `delete_stale_chunks` runs against a mock MongoDB collection). Those need credentials and are verified by running the ingestion command and checking Atlas.

---

## 9. Design decisions

- **The register drives ingestion, not a folder listing.** `document_register.json` records which documents are authoritative, their effective windows and what supersedes what. Customer uploads in `nexa_synthetic_data/uploads/` are deliberately not indexed as policy.
- **Version metadata on every chunk.** Similarity search cannot tell a current clause from a superseded one; metadata filters can. This is the main finance-specific design point of the deck.
- **Tables are kept whole and stored as HTML.** A fee or threshold table flattened to text loses which value belongs to which band.
- **Deterministic chunk IDs keyed by clause.** `{doc_id}_{clause}_c{nn}` makes writes idempotent, and a new clause does not shift the IDs of the clauses after it.
- **Structure first, size second.** The clause is the unit the policies are written in and the unit the golden Q&A set cites, so it is the chunk. Size rules only apply to a clause over the limit, and never to a table.
- **Identity header in the embedded text.** Every chunk starts with document, version and section, so a piece of a split clause, or a table, is never anonymous.
- **Embed the child, store the parent.** Clauses are embedded for precise matching; whole sections sit in a separate, unembedded collection keyed by `parent_id`.
- **One checksum per chunk, not a timestamp per file.** The hash covers text, metadata and embedding model. A re-saved file with no text change embeds nothing; a model change re-embeds everything.
- **Retired, not left behind.** After each document, chunks whose IDs were not produced are deleted, so a withdrawn clause cannot keep answering.
- **`pdfplumber` for PDFs.** Unstructured's fast mode split table cells into stray headings, and its table-aware mode needs poppler, tesseract and large model downloads. `pdfplumber` is lighter and works on born-digital PDFs. Scanned PDFs would need a different parser.
- **Config in the environment.** Model names and chunk size can change without a redeploy.
- **Manual Atlas index.** The index definition is version-controlled in `indexes.md` rather than created by code.

### Known limitations

- The clause and section patterns fit this corpus ("6. Fees and charges", "6.2 Processing fee. ..."). A document numbered differently would fall into one front-matter chunk per section until the patterns in `chunking.py` are extended.
- With the default `CHUNK_MAX_CHARACTERS`, no clause in the corpus is over the limit, so the size rule is exercised by a test and the notebook, not by a normal run.
- The header line is added on top of the size limit, so a chunk can exceed `CHUNK_MAX_CHARACTERS` by the header length.
- Parent sections are rewritten on every run. They are not embedded, so this costs no model calls.
- The write is not transactional: a crash between the chunk upsert, parent upsert and stale-data cleanup can leave a mixed state until a successful rerun. Embedding failures leave the previous parent evidence intact. Run one ingestion job at a time.
- `/retrieve` falls back to the child passage and logs a warning if a parent section is missing.
- `section_type` is only `text` or `table`.
- The Atlas filter fields cover product, jurisdiction, confidentiality and both sides of the effective-date window. The index must be rebuilt and the register re-ingested after this change.
- Offline tests cover ingestion, retrieval, answers, feedback and telemetry. Seven selected synthetic cases have separately exercised Atlas, OpenAI and Datadog evaluation export on Python 3.14. These checks do not verify every case, ingestion writes or cloud deployment.
- Scaling beyond a loop (queue, worker pool, sharded index) is covered as design in Session 2, not as code.

---

## 10. Roadmap

```mermaid
flowchart LR
    S1["S1: Architecture +<br/>ingestion"]:::done --> S2["S2: Clause-aware chunking,<br/>parent docs, checksums"]:::done
    S2 --> S3["S3: Embeddings and<br/>vector index"]:::offline
    S3 --> S4["S4: Retrieval API<br/>/retrieve"]:::offline
    S4 --> S5["S5: Failure modes,<br/>Week 1 checkpoint"]:::offline
    S5 --> W2["Week 2: /answer slice done;<br/>evaluation, observability"]:::partial
    W2 --> P2["Phases 2 to 4: agents,<br/>MCP, production"]:::planned

    classDef done fill:#d1fae5,stroke:#047857,color:#064e3b
    classDef offline fill:#dbeafe,stroke:#1d4ed8,color:#1e3a8a
    classDef partial fill:#fef3c7,stroke:#b45309,color:#78350f
    classDef planned fill:#f3f4f6,stroke:#6b7280,color:#374151
```

**Legend:** 🟩 done · 🟦 implemented offline, live verification pending · 🟨 first slice implemented, rest pending · ⬜ planned

| Session | Adds |
|---|---|
| 2 (done) | Clause-aware chunking with a `clause` field, parent documents, checksum-based incremental re-ingest |
| 3 (implemented offline) | Embedding model and dimension decisions, the Atlas index in depth; Python 3.14 dependency install pending |
| 4 (implemented offline) | `/retrieve` endpoint (FastAPI) with filters including `as_of`, parent-document expansion, citations and timings |
| 5 (implemented offline) | Empty/failure logging, `/health`, `/metrics`, and a runnable miss/staleness/embedding-compatibility lab; live alert thresholds and statistical drift detection pending |
| Week 2 (partial live verification) | `/answer`, parent context, quoted citations and ten golden QAs; the evaluation runner publishes per-case judge/RAGAS scores to Datadog. Seven selected cases have run live, with two incorrect abstentions; web-visible scores are verified and full-dataset quality remains unproven. |

Phases 2 to 4 (agents, MCP, production) wrap this service without rewriting it, so the ingestion contract and the chunk record shape should stay stable.

---

## Streamlit and endpoint coverage

Install the UI and evaluation extras, then run the API and UI in separate terminals
from the project root. Load `.env` before `ddtrace-run` so the tracer receives the
Datadog settings before application imports:

```bash
uv sync --extra ui --extra evaluation
uv run --no-sync --env-file .env ddtrace-run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
uv run --no-sync --env-file .env env DD_SERVICE=nexaassist-ui ddtrace-run python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

To find question traces, open [Datadog Trace Explorer](https://app.datadoghq.com/apm/traces?query=service%3Anexaassist-api%20env%3Adev),
select **Live Search** / **Past 15 minutes**, and send a new question. Start with
`service:nexaassist-api env:dev`; then select `fastapi.request` and resource
`POST /answer/evaluated` with quality scoring enabled, `POST /answer` with it disabled,
or `POST /retrieve` in Evidence mode. A service page filtered to
`pymongo.cmd` / client spans shows database calls rather than the API request entry.
Clear those filters and refresh any saved absolute time window before diagnosing
missing traces. See [DATADOG_README.md](DATADOG_README.md) for Agent diagnostics.

The UI uses `API_BASE_URL` (default `http://127.0.0.1:8000`) and `UI_TIMEZONE`
(default `Asia/Kolkata`). Streamlit 1.66+ loads the app's blue and slate theme from
`app/.streamlit/config.toml`. The chat interface includes a bottom message composer,
suggested policy questions, a **New chat** action, and recent chats in the sidebar.
Chats are stored only in the current Streamlit session, without database persistence.
Each question is sent independently to the existing API; previous messages are displayed
for reference and are not sent as model context. Include relevant details in each question.

Use **Policy scope** in the sidebar to set the policy date, an optional product ID,
the source limit, and **Answer** or **Evidence** mode. Each message retains its submitted
scope even if the sidebar changes. Failed requests offer **Try again** with that original scope.
Source clauses and per-answer feedback appear below each response. Select **Review feedback**
in the sidebar to load and review saved feedback.
With Datadog LLM Observability enabled, **Send feedback** also queues a `thumbs`
rating and optional correction on the matching API answer span. An anonymous
browser-session UUID identifies the submitter. MongoDB saving remains available
if Datadog fails or an older answer has no span reference; see the
[Datadog feedback guide](DATADOG_README.md#end-user-feedback-from-streamlit).

**Answer quality → Evaluate with RAGAS** is enabled for new questions by default.
RAGAS metrics appear in **Datadog only**; Streamlit shows the answer, citations
and a **View evaluation in Datadog** link. Add an expected answer in **Reference answer for the next question**
to measure all four metrics. Exact golden-case matches can supply that reference
automatically; missing references or scorer failures remain explicit in the API
result and are not exported as numeric scores. The reference applies to one
question and is then cleared. Scoring uses
additional model calls and reuses the generated answer's exact retrieved evidence.
Successful scores are also queued against the `policy_answer_live_evaluation`
workflow in Datadog; use **View evaluation in Datadog** below the answer.
See the [live RAGAS guide](DATADOG_README.md#ragas-scores-in-datadog-for-streamlit-questions).

The UI covers six of nine application operations:

| Method and endpoint | Streamlit control |
| --- | --- |
| `POST /answer/evaluated` | Answer mode with Evaluate with RAGAS enabled |
| `POST /answer` | Answer mode with Evaluate with RAGAS disabled |
| `POST /retrieve` | Policy chat → Evidence → send a message |
| `POST /feedback` | Send feedback below an answer |
| `GET /feedback` | Review feedback → Load feedback for review |
| `POST /feedback/{feedback_id}/review` | Save review with a reviewer, decision and note |
| `GET /health` | No existing UI control; tested directly |
| `GET /metrics` | No existing UI control; tested directly |
| `GET /metrics/latency` | No existing UI control; tested directly |

Liveness does not verify MongoDB or model readiness; counters and latency samples
belong to one API process. The three operational endpoints have no controls in
the UI.

`tests/test_ui.py` connects Streamlit AppTest to the real ASGI routes, discovers
the application endpoints and reports the three operations not reached by UI actions. It
uses controlled retrieval/answer responses and an in-memory feedback store;
these tests do not measure Atlas ranking or real model quality.

The UI tests also verify chat switching, retained history, policy filters, suggestions,
request retries, and feedback isolation between answers. Feedback inputs no longer carry
over from one answer to the next.

```bash
LANGCHAIN_TRACING_V2=false LANGSMITH_TRACING=false RAGAS_DO_NOT_TRACK=true uv run --extra ui --extra evaluation pytest tests/
```

## Local Datadog tracing

See [Datadog for NexaAssist and LLM applications](DATADOG_README.md) for local
macOS and cloud setup, API/UI launch commands, a traced RAG example, dashboards,
troubleshooting and the distinction between telemetry and AI evaluations. The
guide documents the existing Agent-based setup on `datadoghq.com`, including
configuration loading before `ddtrace-run` and the current PyMongo compatibility
constraint.

## Further reading

- [CLAUDE.md](CLAUDE.md): coding rules and layer boundaries
- [nexa_synthetic_data/README.md](nexa_synthetic_data/README.md): the corpus, golden Q&A, customer data and mock API
- [app/database/indexes.md](app/database/indexes.md): the Atlas index definition
