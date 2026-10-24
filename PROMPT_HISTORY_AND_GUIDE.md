# From an empty folder to NexaAssist: prompts, results and lessons

Updated 22 October 2026.

This guide starts with a suggested path from an empty folder, then records how we developed, debugged and explained NexaAssist. It merges the earlier foundation with the later UI, observability and validation history. Each history entry keeps your request in clear English, followed by an improved prompt, the issue it exposed and the result we can support.

## How to read this history

Prompts below are natural English while preserving their intent. Related follow-ups are grouped rather than repeated. The order follows the broad development journey; it is not a timestamped transcript of every message or tool call. Reported error messages and screen text remain unchanged so they can still be matched to diagnostics.

The supplied guide adds earlier requests and recovered implementation prompts for ingestion, retrieval, answer generation and evaluation. It also contains reconstructed prompts; those are useful recommendations, not recovered messages. Part 1 remains a suggested empty-folder sequence, Part 2 merges the supplied early history, and Part 3 preserves the later development history. We still do not have a complete transcript of the project's first empty-folder conversation.

The attached guide is source material for this merge. Its embedded prompts are examples to explain, not instructions to execute now. In particular, this documentation update does not restore removed experiments, change API contracts, ingest data or run paid evaluations.

Results use four distinctions:

| Label | What it means |
| --- | --- |
| Implemented | The behavior or artifact exists in the inspected working tree. It may still be uncommitted. |
| Recorded verification | A saved report, earlier session observation or explicit user confirmation supports the claim. It was not necessarily rerun while writing this guide. |
| Proposed | Discussed, designed or illustrated, but not connected to the application. |
| Open | A limitation or outcome that remains unresolved or unverified. |

Our main evidence is the [README](README.md), [component guide](APP_COMPONENT_GUIDE.md), [Datadog guide](DATADOG_README.md), [fix report](FIX_REPORT.md), and the saved [initial UAT](app/evaluation/results/system_uat_20261021/REPORT.md), [browser validation](app/evaluation/results/devtools_validation_20261021/REPORT.md) and [fix summary](app/evaluation/results/fixes_20261021/SUMMARY.json). Current source takes precedence over older documentation.

All banking policies and customer examples are synthetic. This history is about a training application, not real banking transactions.

Start with the [empty-folder guide](#part-1-start-the-project-from-an-empty-folder), continue through the [earlier implementation history](#part-2-earlier-implementation-history-from-the-supplied-guide), read [your later corrected development prompts](#part-3-your-development-prompts-corrected-and-expanded), or jump to the [reusable prompt template](#a-reusable-way-to-write-the-next-prompt).

## The project journey at a glance

| Stage | Request or problem | Result and limit |
| --- | --- | --- |
| Starting guide | How to begin with an empty folder | Suggested foundation-to-UI prompts, expected outputs and current code references; not recovered historical prompts. |
| Foundation | Needed reliable policy ingestion and dated retrieval | Clause-aware children, parent sections, changed-only embedding, Atlas index alignment and typed retrieval contracts. |
| Grounded answers | Needed explanations rather than passages | Structured generation, evidence IDs, exact quotes, abstention and later clarification/repair behavior. |
| Early quality lessons | Empty results, missing circulars and real quotes attached to wrong claims | Separate network/index/filter problems, evidence coverage and semantic correctness. |
| Chat UI | Familiar conversational interface over existing RAG | Streamlit chat, sources, session history, feedback and review; earlier messages are not sent as model memory. |
| Observability | HTTP responses existed but traces seemed absent | Docker collection, API workflow identity and targeted searches were checked; the user confirmed particular APM/LLM traces. |
| Quality | Needed RAGAS for new questions | Evaluated-answer route scores the final answer against the same evidence; reference-dependent metrics can be unavailable. |
| Feedback | Needed thumbs in Datadog | MongoDB persistence first, optional span-linked Datadog feedback, retry IDs and protected review. |
| Validation | Passing tests missed wrong fee facts | Complete circulars, stronger scope checks, bounded citation repair and additional regressions. |
| Tooling | Needed dependable commits and readable guidance | Pre-commit configuration and development guide; authentication failure was reported, not confirmed resolved. |
| Simplification | Wanted one telemetry platform | Project-owned LangSmith integration removed; an indirect package dependency remains. |
| Teaching | Needed architecture, recap and the next-phase introduction | Diagrams, decks and a three-slide RAG-to-agents example; agent integration remains planned. |
| Latest UI | Wanted dark mode | App-specific light config changed to dark; rendered chat and sidebar were checked. |

## Part 1. Start the project from an empty folder

This is a **suggested starting sequence**, reconstructed from the current architecture and the lessons recorded later in this guide. These are not recovered historical prompts, and the expected outputs below are targets for a new project, not claims that we built another copy during this update.

Follow one step at a time. Check its output before moving to the next layer. Start with the current Datadog-only approach; there is no need to recreate the earlier LangSmith integration just to remove it later.

### Before you send the first prompt

Create a separate empty folder for the new project. For example, from its intended parent directory:

```bash
mkdir nexaassist
cd nexaassist
uv init --bare --python 3.14 --vcs git
```

These are setup instructions only; they were not executed as part of this documentation update. They require `uv`, Git and an available Python 3.14 interpreter, or permission for `uv` to obtain one. Do not run the initialization steps over the existing `Week_1_code` repository.

Open the new folder in your coding assistant. Before asking it to write application code, create `AGENTS.md` and `CLAUDE.md` using Step 0 below. Provide the syllabus and synthetic policy documents when needed. Keep real credentials outside the prompts and out of Git. A blank `.env.example` template can describe the required variables; the real values belong in an ignored local `.env` file.

### Step 0. Create AGENTS.md and CLAUDE.md before application code

Start by telling the assistant how this project should be built. These files keep the project rules in the repository, so you do not have to repeat the architecture and quality expectations in every prompt.

| File | Purpose | What to put in it |
| --- | --- | --- |
| `AGENTS.md` | Project instructions for Codex | Project goal, layer boundaries, approved stack, development workflow and verification rules. |
| `CLAUDE.md` | Project instructions for Claude Code | The same shared project rules, with any instructions specific to Claude Code clearly identified. |

Place both files at the project root, beside `pyproject.toml`. This follows the documented project instruction locations for [Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [Claude Code](https://support.claude.com/en/articles/14553240-give-claude-context-claude-md-and-better-prompts). Do not assume every coding assistant automatically reads both filenames.

```text
nexaassist/
├── AGENTS.md
├── CLAUDE.md
└── pyproject.toml
```

**Suggested prompt**

```text
Before writing application code, create AGENTS.md and CLAUDE.md in this new
project's root. AGENTS.md should guide Codex, and CLAUDE.md should guide
Claude Code. Use the correct filename in each heading and keep their shared
project rules consistent.

The project is NexaAssist, an enterprise policy and compliance assistant for
a fictional bank using synthetic documents. Write clear, practical rules:

1. Use Python 3.14+, uv, LangChain/langchain-core, MongoDB Atlas Vector Search,
   FastAPI with Pydantic v2, Streamlit, Datadog and RAGAS/structured judges.
   Use langchain_mongodb, not a deprecated community vector-store wrapper.
2. Build one working layer at a time: LangChain and MongoDB foundation,
   then FastAPI, then Streamlit. LangGraph and an application MCP server
   are future extensions; do not implement them without a current need.
3. Keep chains free of FastAPI and Streamlit imports, routers thin, database
   operations in database modules, and business logic out of the UI.
4. Use LCEL Runnable composition, typed contracts, pydantic-settings and
   strict Pydantic v2 request validation. Handle I/O without blocking the API.
5. Do not invent model names, credentials, Atlas settings or library methods.
   Inspect supplied configuration, verify official documentation, and ask
   focused questions when a required input is missing.
6. Ground policy answers in retrieved evidence. Preserve product, policy-date,
   amendment and citation scope. Never add unsupported financial facts.
7. Use Datadog for operational and LLM telemetry, structlog for JSON logs,
   and local golden datasets for quality evaluation. Do not add LangSmith.
   Add ten source-grounded golden QAs when introducing the first chain.
8. Keep secrets out of code, logs and prompts. Document variable names in
   .env.example and ignore the real .env file in Git.
9. Reproduce failures from exact errors, fix the owning layer, preserve
   validation and add meaningful regression coverage. Run the checks relevant
   to each change and distinguish local tests from live/cloud verification.
10. Make the smallest complete change. Report changed files, verification
    results and remaining limits. Never claim an untested feature is ready.

Include the intended app/chains, app/database, app/services, app/api, app/ui,
app/core, app/models, app/evaluation and tests boundaries. Document setup and
check commands as they become available; do not claim they already work in
an empty project. Mention skills, hooks or MCP tools only when configured
and available. Do not write application code in this step.
```

**Expected output:** Two readable root instruction files with consistent project rules, before the first chain, API route or UI is created. This is a suggested setup prompt, not a claim that these were the original project messages.

Review both files before continuing. When a shared rule changes, update both in the same change; editing one does not automatically update the other. Keep credentials and temporary debugging transcripts out of them. Commit the instruction files with the project so another developer can use the same guidance.

For a new coding session, use this short opening prompt:

```text
Follow the applicable project instructions: AGENTS.md for Codex or CLAUDE.md
for Claude Code. Briefly summarize the active layer, relevant constraints
and verification needed for this task. Then work only on [next milestone].
```

**Current repo reference:** [Codex project instructions](AGENTS.md) and [Claude project instructions](CLAUDE.md). The files already exist in this repository; this step explains how to establish them in a new project, without replacing the current files.

### A. Explain the project and agree on the first milestone

**Suggested prompt**

```text
I am starting NexaAssist in an empty folder. It is an enterprise policy and
compliance assistant for a fictional bank, using synthetic documents.

Use Python 3.14+, uv, LangChain, MongoDB Atlas Vector Search, FastAPI,
Streamlit, Datadog and RAGAS. Follow the project instructions created in
Step 0 and read the syllabus I provide.
Build in layers: foundation first, then API, then UI. LangGraph and an
application MCP server are future extensions.

First, describe the architecture, the minimum project structure and one
small end-to-end milestone. Identify missing inputs, such as policy files,
model configuration and Atlas settings. Do not implement every layer at once.
```

**Expected output:** A brief architecture and milestone plan, with the inputs needed to proceed. The first goal is one working document-to-evidence path, not a complete agent platform.

**Current repo reference:** [Layer boundaries](AGENTS.md) and [system overview](README.md).

### B. Set up the foundation and configuration

**Suggested prompt**

```text
Set up the initial NexaAssist project in this new folder. Create only the
active foundation directories, pyproject.toml, .gitignore, .env.example,
app/core/config.py and the shared ingestion contracts.

Use pydantic-settings and strict Pydantic v2 request models. Keep model,
embedding and Atlas settings configurable. Use placeholders for credentials;
do not invent working URLs, model choices or secrets. Add the development
checks needed now and verify configuration and validation locally.
```

**Expected output:** An installable foundation with explicit configuration, strict input contracts and a small local verification. Future `agents/` and `mcp/` implementations are not needed yet.

**Current repo reference:** [Project configuration](pyproject.toml), [settings](app/core/config.py) and [ingestion models](app/models/ingestion.py).

### C. Turn policy PDFs into useful chunks

**Suggested prompt**

```text
Implement parsing and chunking for the supplied synthetic policies. Preserve
headings, tables and clause numbers. For these born-digital PDFs, use the
existing pdfplumber approach. Keep each table with its introducing clause.

Create child chunks for search and parent sections for wider context. Use
structure first and size limits second. Add source identity and scope metadata
to every chunk. Test table boundaries, oversized narrative and missing metadata
without calling an external model or database.
```

**Expected output:** Inspectable child chunks and parent sections that preserve the policy's meaning and identity. No embedding or production database write is needed to prove the parser works.

**Current repo reference:** [Parsing](app/chains/parsing.py), [chunking](app/chains/chunking.py) and the [Session 2 notebook](notebooks/phase1_session2_chunking.ipynb).

### D. Configure embeddings and MongoDB Atlas

**Suggested prompt**

```text
Add one shared embedding client for ingestion and retrieval, using the model
and dimensions I supply. Configure MongoDBAtlasVectorSearch from
langchain_mongodb with explicit collection, embedding and index name.

Document the exact manual Atlas Vector Search index JSON, including the
scope and date filters the read path will need. Keep parent sections in a
separate unembedded collection. Verify wiring with local substitutes first;
perform a live Atlas check only within the authorized scope.
```

**Expected output:** Shared embedding configuration, separate child/parent stores and a reviewable index definition. A client object alone does not prove that the actual index is queryable.

**Current repo reference:** [Embeddings](app/chains/embeddings.py), [MongoDB stores](app/database/mongo.py) and [index definitions](app/database/indexes.md).

### E. Build one complete ingestion chain

**Suggested prompt**

```text
Build the first LCEL ingestion chain: read the authoritative document register,
parse, chunk, enrich, compare checksums, embed changed children and update the
stores. Use deterministic IDs, skip unchanged chunks and remove stale chunks
only within the intended document scope.

Preserve existing parent evidence if embedding fails. Explain the limits of
multi-collection writes rather than claiming a transaction we do not have.
Prove the flow locally, then ingest one approved synthetic document before
expanding to the complete register. Add ten source-checked golden Q&A cases
when introducing the chain, as required by AGENTS.md.
```

**Expected output:** One repeatable document-ingestion path, observable stage results, source-backed golden cases and tests for unchanged content, changed clauses and failure preservation.

**Current repo reference:** [Ingestion chain](app/chains/ingestion.py), [ingestion service](app/services/ingestion.py) and [golden dataset](evaluation/datasets/answer.jsonl).

### F. Retrieve evidence and generate a cited answer

**Suggested prompt**

```text
Implement a pure LangChain read path before adding HTTP routes. Filter by
institution, policy date, product, jurisdiction and confidentiality. Validate
parent scope and include complete applicable linked circulars.

Build a token-budgeted answer chain over that evidence. Return exact source
quotes and valid citation IDs. If evidence is missing or required amendments
cannot fit, abstain. Permit at most one citation-repair draft using the same
evidence. Test current, historical, conflicting-scope and unsupported questions.
```

**Expected output:** A directly callable retrieval and answer workflow, with explicit evidence, timing and failure behavior. A few semantically checked golden answers demonstrate the milestone; they do not establish full-corpus quality.

**Current repo reference:** [Retrieval](app/chains/retrieval.py), [context assembly](app/chains/context.py), [answer chain](app/chains/answer.py) and [answer tests](tests/test_answer.py).

### G. Expose the working chain through FastAPI and Datadog

**Suggested prompt**

```text
Wrap the tested foundation with thin FastAPI routes and injected services.
Add /retrieve, /answer, /health and process-local metrics using strict request
and response contracts. Keep LLM logic out of routers and database setup in
app/database.

Add structlog JSON logging and ddtrace instrumentation. Document how to load
settings before ddtrace-run starts the process. Configure the Docker Datadog
Agent and align application destinations with its published ports. Verify a
provider-free HTTP trace before an approved live answer request.
```

**Expected output:** A working serving boundary and separately verified telemetry path. Health is liveness; local counters are not fleet-wide monitoring, and a collector receipt is not cloud confirmation.

**Current repo reference:** [FastAPI app](app/main.py), [routes](app/api/answer.py), [Docker Agent](app/compose.datadog.yaml) and [Datadog guide](DATADOG_README.md).

### H. Add the Streamlit chat interface

**Suggested prompt**

```text
Use developing-with-streamlit to build a chat UI over the existing FastAPI
endpoints. Include policy date/product scope, Answer and Evidence modes,
citations, a bottom composer and per-session chats. Use a native dark theme.

Keep business logic and database access out of the UI. Describe session-local
history accurately; do not imply previous messages reach the model unless we
implement that contract. Verify initial rendering, question submission, retries
and source expansion with AppTest and an isolated browser.
```

**Expected output:** A usable policy chat that consumes the tested API. Model answers and retrieval are not reimplemented inside Streamlit.

**Current repo reference:** [UI entrypoint](app/streamlit_app.py), [chat implementation](app/ui/app.py) and [app theme](app/.streamlit/config.toml).

### I. Add evaluation and feedback in separate, verifiable slices

**Suggested prompt**

```text
First add live and batch evaluation using our local golden cases. Score the
final answer against the same evidence used for generation. Preserve separate
scored, unavailable and error states. Support supplied reference answers and
send available RAGAS scores to the matching Datadog workflow, without score
cards in Streamlit.

Then add persisted feedback, stable retry IDs, reviewer-token protection and
optional span-linked Datadog thumbs. Verify each slice before starting the next.
Preserve answers and saved feedback when optional telemetry fails.
```

**Expected output:** Reproducible evaluation inputs and outputs, reference-aware scores, durable feedback records and clearly described best-effort telemetry delivery. The sequence intentionally separates evaluation from feedback rather than building both at once.

**Current repo reference:** [Live evaluation](app/services/evaluation.py), [batch evaluation](app/evaluation/run.py), [feedback service](app/services/feedback.py) and [feedback routes](app/api/feedback.py).

### J. Validate, document and prepare the handoff

**Suggested prompt**

```text
Review the complete RAG application against realistic synthetic user journeys.
Check answers against policy sources, not just HTTP status or a model score.
Reproduce valid findings, apply targeted fixes and add meaningful regressions.

Run the appropriate tests, lint, formatting and type checks. Configure
pre-commit and document setup, architecture, code mappings and remaining gaps.
Separate offline tests, live observations and cloud confirmation. Organize
commits only within the authorized scope, and do not claim production readiness
from local test results.
```

**Expected output:** A reviewable working system, a verification report with honest limits, useful operating documentation and a clear list of unresolved work.

**Current repo reference:** [Fix report](FIX_REPORT.md), [quality hooks](.pre-commit-config.yaml) and [development guide](DEVELOPMENT_TOOLING_GUIDE.md).

### K. Introduce agents only after the RAG foundation is ready

**Suggested prompt**

```text
Plan the Phase 2 agent extension around the existing RAG service. Keep /retrieve
unchanged and use HTTP adapters in a separate Agent Service. Start with state,
nodes, edges and conditional routing, then wire Orchestrator and Retriever
before adding Validator and Action responsibilities in later slices.

Use the synthetic customer and mock banking APIs for examples. Keep validation,
idempotency and any required human approval explicit. Do not present a queued
service request as a completed banking change. Application MCP is a later step.
```

**Expected output:** A small extension plan or the specifically authorized next slice. In the current project, the agent and application MCP integrations remain planned; the separate banking mock API already exists.

**Current repo reference:** [Mock banking server](nexa_synthetic_data/api/mock_server/server.py) and the [three-slide Phase 2 introduction](../PPTs/NexaAssist_RAG_to_Agents_20261022/exports/NexaAssist_RAG_to_Agents_20261022_053910.pptx).

## Part 2. Earlier implementation history from the supplied guide

These twelve entries combine related earlier requests without repeating the full starting tutorial. Wording labelled “English corrected” preserves the intent of requests quoted in the supplied guide. An “initial issue” describes that guide's account rather than claiming a recovered user quotation. Improved prompts below are reusable adaptations, including current verification rules.

### F1. Continue the ingestion foundation and explain the changes

**Earlier prompts (English corrected):** “Understand the repository and start Phase 1, Week 1, Session 2.” “Explain in simple language why we added the Session 2 changes.” “What is the purpose of these classes?”

**Improved prompt**

```text
Read the project instructions, document register, parser, ingestion chain,
MongoDB helpers and ingestion tests. Explain what Session 1 already provides
and why Session 2 needs clause-aware chunks, stable identities and parents.

Implement only that ingestion improvement. Keep tables with their introducing
clauses, split oversized narrative with overlap, preserve front matter and
metadata, and embed only changed children. Reject empty output before replacing
stored content. Explain the local _Clause builder and immutable Chunk output;
do not move local processing types into shared API models without a caller need.

Check unchanged re-ingestion, changed clauses, removed clauses, embedding
configuration changes and failure preservation. Describe the write sequence
and its remaining consistency limits. Provide a notebook walkthrough.
```

**Result:** The supplied history records the Session 1 foundation in `12c1b45` and Session 2 ingestion changes in `9c19d96`; the chunker reached a commit in `8d01b1a`. Current [ingestion](app/chains/ingestion.py), [chunking](app/chains/chunking.py) and [MongoDB adapters](app/database/mongo.py) implement child/parent records and checksum comparison. The current checksum metadata includes both embedding model and dimensions, correcting the older guide's dimensions-only gap. Changed children are written before parent updates; cross-collection publication remains nontransactional.

**Lesson:** Explain the problem each new structure solves. A repeated run with no new embeddings is a useful observation; it does not prove atomic publication or safe concurrent ingestion.

### F2. Separate parsing, embeddings and index readiness

**Initial issues from the supplied guide:** A notebook showed an Atlas warning and no chunks; the user suspected a missing chat model. Later investigation distinguished embeddings, network connectivity, index readiness and metadata filters.

**Improved prompt**

```text
Trace this exact ingestion/search path before changing configuration. Inspect
the parsed PDF elements, registered metadata, stored vectors and Atlas index.
Separate query embeddings from chat generation. Do not add a chat model to
repair a search-only problem or treat an unconditional warning as index status.

Preserve the existing pdfplumber path for born-digital PDFs and the non-PDF
partitioning path. Check headings, tables and ordering against the source.
Document the supported layout and lack of an OCR fallback.

Verify the configured database, collection, index name, embedding model,
dimensions and every filter field. Use the exact index JSON in indexes.md.
Keep open-ended effective_to metadata while indexing effective_to_search.
Do not change embedding models or weaken TLS as a troubleshooting guess.
```

**Result:** [Parsing](app/chains/parsing.py) uses `pdfplumber` for PDFs rather than an implemented OCR pipeline. The current [index definition](app/database/indexes.md) includes `institution` alongside product, jurisdiction, dates, document type and confidentiality. Open-ended dates use `9999-12-31` for search. The older index JSON should therefore not be copied over today's definition. The recorded embedding configuration is `text-embedding-3-small` with 1536 dimensions; these are project settings, not a fresh provider-access check.

**Lesson:** Matching vector lengths is necessary but does not prove compatible embedding spaces. For an intentional migration, rebuild a complete separate collection and matching index, evaluate it, then switch the serving configuration together.

### F3. Agree on the Week 1 retrieval contract before implementing it

**Earlier prompt (English corrected):** “Understand the information in `.planning` and use it as context for the next implementation.” The supplied guide also preserves a more detailed Week 1 code-generation prompt.

**Improved prompt — adapted from the recovered implementation prompt**

```text
Start from the committed code and inspect the working tree, project instructions,
README, planning records and existing app modules. Implement the agreed Week 1
retrieval milestone in layer order, preserving the ingestion path.

Add clause-aware chunking and an indexable effective-date upper bound where
missing. Define strict Pydantic v2 retrieval contracts, an async LangChain
Runnable, dependency wiring in services/ and a thin POST /retrieve router.

Accept query, as_of, top_k, product_id and jurisdiction. Return ranked child
hits, parent context, citations and timings. Add /health, /metrics and the app
factory. Handle empty searches explicitly and backend failures safely.

Respect this task's allowed file scope. If edits are restricted to app/, report
required dependency/test changes outside it without silently expanding scope.
Run available checks and state what remains unverified. Do not add UI or agents.
```

**Result:** The supplied history associates the Sessions 3–5 milestone with `8d01b1a`. Current [request/response models](app/models/retrieval.py), [retrieval router](app/api/retrieval.py), [service](app/services/retrieval.py) and [chain](app/chains/retrieval.py) preserve those layers. `query` is stripped and must contain 1–2000 characters; `as_of` is required; `top_k` defaults to 5 and permits 1–20. Unknown request fields are rejected. Current retrieval also returns an additive `amendments` list for complete linked instruments.

**Lesson:** Preserve the repository's existing snake_case fields and public routes. A generic API style example is not a reason to rename a working contract or remove later optional fields.

### F4. Make a committed-only demonstration reproducible

**Earlier prompt (English corrected):** “Provide a prompt to generate the files that have not been committed.” The supplied guide also contains a separate prompt for rebuilding a committed-only copy.

**Improved prompt — adapted from the recovered rebuilding prompt**

```text
Inspect the target checkout and its project instructions. Identify required
imports whose files are absent from the commit. Use the agreed planning records
as read-only requirements; do not copy an implementation from another directory.

For the historical Week 1 rebuilding exercise, recreate the missing chunking,
retrieval models/chain/service/router, operational routes and app factory under
app/. Update ingestion and index documentation only where that milestone needs it.
Preserve existing public contracts and the allowed file scope.

Run available checks and report required dependency/test changes outside app/.
Keep this reconstruction separate from the already working main checkout.
```

**Result:** The initial guide records a copy of `9c19d96` that imported an untracked chunker and could not reproduce the working directory. The later `8d01b1a` commit includes that file. This is a historical reproducibility issue, not a request to recreate or overwrite current application files.

**Lesson:** Review `git status` and required imports before calling a commit runnable. A green working directory can depend on files that have never reached Git.

### F5. Diagnose empty retrieval using the exact request

**Earlier prompt (English corrected):** “Validate that the application in the current directory can run the `/retrieve` API correctly.”

**Improved prompt**

```text
Validate the existing /retrieve path with the application's interpreter and
Settings. Start with schema/routing checks, then inspect the exact live request
within the authorized scope. Keep network, TLS, index readiness and filters
separate from answer quality.

For empty results, compare an unfiltered diagnostic with the intended scoped
query without weakening the serving filters. Check product_id against stored
metadata and test the historical date boundary. Record the result, evidence
coverage and timings. Repeat the original request after the identified fix.
```

**Result:** The supplied guide records an Atlas network-access correction after TLS failures, an index that initially was not queryable, and a caller using `POL-HL` where stored product metadata required `NEXA-HL`. It also records different policy versions for `2024-03-31` and `2024-04-01`. Its collection count of 177 children and 80 parents is a historical observation. No live count, connectivity check or retrieval call was repeated for this merge.

**Lesson:** HTTP 200 with `results: []`, a liveness response and a TCP connection each answer different questions. None proves the required evidence is available.

### F6. Teach retrieval misses, staleness and embedding compatibility

**Earlier prompts (English corrected):** “Retrieval is complete. The next session should cover retrieval misses, stale indexes and embedding drift.” “Use the Week 1 code to provide three to five detailed examples of each issue, including how to identify and resolve it.”

**Improved prompt**

```text
Build teaching examples around the existing retrieval pipeline and golden
evidence. For each case, give the question, observed signal, file/record to
inspect, resolution and confirmation check. Start with offline fixtures and
inject faults into local copies only. Label any read-only live observation.

Separate empty results, nonempty evidence misses, missing parents and stale
parent text. Compare direct child-reference coverage with expanded context.
Check model labels, vector lengths and index configuration before calling a
failure embedding drift. Do not claim statistical drift without measurements.
```

**Result:** The supplied guide describes R1–R4 retrieval, S1–S5 staleness/parent and E1–E4 embedding cases in [the failure examples](app/evaluation/rag_failure_examples.py), supported by [offline diagnostics](app/evaluation/rag_failure_modes.py). A generic fee query historically missed an applicable circular at top five while a focused query recovered it. Later fixes now retrieve linked circulars as complete scoped instruments; the earlier diagnostic remains useful history, not proof that today's code still has the same omission.

**Lesson:** Finding a related passage is weaker evidence than finding the right policy, applicability clause and conditions. Increasing `top_k` is a diagnostic control, not a universal fix.

### F7. Record the reranker experiment and its later changes honestly

**Earlier prompts (English corrected):** “Give me a single-file prompt to create or update the reranker for a practical demonstration.” “Revert the reranker changes.” “Some reranker and reciprocal rank fusion code still remains.”

**Improved prompt — adapted from the recovered single-file prompt**

```text
For a separate historical demonstration only, inspect the retrieval interfaces
and create or update app/chains/reranking.py. Use the explicitly selected
cross-encoder/ms-marco-MiniLM-L6-v2 model with sentence-transformers.

Provide cached get_reranker(model_name) and async rerank_documents(model_name,
query, documents), returning scores in document order. Move model loading and
prediction to asyncio.to_thread. Preserve an existing public API if present.

Edit no other files, install nothing and download no model for this step.
Explain prerequisites and that this does not wire reranking into retrieval.
Do not run this historical restoration prompt against today's app by default.
```

**Result:** The supplied guide records a local cross-encoder experiment, its removal and earlier 26/28-test reports. Today's working tree later reintroduced optional Atlas hybrid/RRF retrieval and a different [Qwen-style reranker adapter](app/chains/rerank.py), supporting Ollama or OpenAI-compatible completions with validated yes/no log probabilities. It is not the old `reranking.py` implementation. Defaults remain `RETRIEVAL_MODE=dense` and `RERANK_ENABLED=false`; an MLX-looking model name does not verify the execution backend.

**Lesson:** A feature may be tried, removed and later reintroduced differently. Describe the current code and defaults without rewriting that history or treating old measurements as current results.

### F8. Explain the flow from request to evidence

**Earlier prompt (English corrected):** “Explain how the code flows from one file to another, including retrieval and reranking.”

**Improved prompt**

```text
Trace one request through the current router, request model, service, retrieval
chain, database adapter, parent expansion and response. Identify which optional
branches are enabled by Settings. Use current function names and distinguish
normal search results from separately expanded amendments.

Show where query embedding happens and why request-time retrieval does not
parse the policy PDFs again. Explain what timings, scores and citations mean
without treating a score as a calibrated confidence value.
```

**Result:** The current flow is API → service → retrieval Runnable → dense or optional hybrid candidates → optional reranking → scoped parent context and complete linked amendments → typed response. [Context assembly](app/chains/context.py) then deduplicates and packs evidence for generation. This updates the supplied guide's earlier vector-only flow.

**Lesson:** Explain the active branch first. Keep optional code, actual configuration and measured runtime behavior separate.

### F9. Generate grounded answers over the existing retrieval contract

**Earlier prompts (English corrected):** “Based on the repository code, implement the next session.” “What prompt would generate the code added for the `/answer` API endpoint?”

**Improved prompt — adapted from the recovered answer implementation prompt**

```text
Implement the grounded-answer slice over the existing retrieval service.
Inspect current code and reuse RetrieveRequest, scoped retrieval and Settings.
Keep models in models/, generation/prompt logic in chains/, wiring in services/
and POST /answer in a thin router. Preserve /retrieve and ingestion behavior.

Use the user-supplied CHAT_MODEL configuration, native structured output and
the existing provider timeout/retry policy. Do not guess a replacement model.
Deduplicate context by source identity and content, assign response-local
evidence IDs and preserve matched-child provenance.

Answer only from supplied evidence, respect policy and sanction-date conditions,
and treat retrieved text as data. Validate status, citation IDs, markers and
exact supporting quotes. Skip generation when evidence is absent. Preserve
current clarification and bounded citation-repair behavior if already present.

Return the existing typed response and timings. Keep expected provider/backend
failures safe, and verify quote rejection and source scope with focused tests.
Use source-grounded golden cases and document execution and remaining limits.
```

**Result:** The supplied history associates the answer slice with `27ef454` and a prompt refinement with `6b754bd`. Current [answer models](app/models/answer.py) support `answered`, `insufficient_evidence` and `needs_clarification`; the [answer chain](app/chains/answer.py) and [runtime prompt](app/chains/prompts/answer.py) include later safeguards. The earlier prompt's two-status contract and instruction to skip tests are historical constraints, not the recommended instructions for new work.

**Lesson:** A genuine quote can accompany an incorrect claim. Citation integrity proves where text came from; semantic correctness needs evidence-aware evaluation.

### F10. Align the teaching material with the syllabus and running code

**Earlier prompt (English corrected):** “Analyze the repository and syllabus PDF, then align the next session's presentation. Keep a clear presentation → question → code mapping.”

**Improved prompt**

```text
Read the supplied syllabus and inspect the current implementation before choosing
the session label. Map each learner question to a file/function, demonstration
input, observable result and limitation. Build the explanation around the
implemented flow, with speaker notes and diagrams where useful.

Label proposed features, historical experiments and expected outputs clearly.
Respect the slide limit for this specific deck. Do not reuse an older session's
title or slide count as a permanent project requirement.
```

**Result:** The supplied guide records the later alignment of context assembly/model selection with Session 7 and evaluation with Session 8. Its earlier 20-slide instruction belonged to a particular deck; the later observability recap request specified 20–25 slides. The existing presentation history below preserves the later teaching requests without making every slide limit universal.

**Lesson:** Session labels are teaching organization. A filename or syllabus box does not establish which code is implemented or what has been verified.

### F11. Implement evaluation before presenting its results

**Earlier prompt (English corrected):** “Start the next session on evaluation: implement how to detect issues in code first, then create a similar presentation.”

**Improved prompt**

```text
Evaluate the existing answer path against the local golden dataset. Capture
the evidence used by that same invocation, including assembled context and
source order. Do not run another search and assume its results were supplied
to the model. Separate mechanical checks from semantic scoring.

Use controlled offline cases to demonstrate a valid answer, a wrong amount
with a real quote, an invented quote, missing circular evidence and abstention.
Label semantic scores as unmeasured in that demo.

Add or reuse live RAGAS and the current structured judge. Keep metric errors,
unavailable references and pipeline errors explicit. Inspect the actual report
and gate implementation rather than inheriting an older schema. Document
provider costs, output behavior and the configured threshold. Create teaching
material only after the behavior and limits are clear.
```

**Result:** [The controlled demo](app/evaluation/failure_demo.py) retains the ₹9 crore claim with a genuine ₹7.5 crore quote to show the limit of citation checks. Today's batch runner uses [judge.py](app/chains/prompts/judge.py), with numeric correctness/groundedness and separate status agreement; it does not use the supplied snapshot's `evaluation.py` pass/fail/needs_review judge. The current gate is `not_configured` without `--min-score`. A requested threshold checks the implemented score inputs; it is not a universal release certification. Live UI evaluation and Datadog export are covered in the later history.

**Lesson:** Read both the metric and the gate. A successful offline demonstration, a high score and a passed release decision are different claims.

### F12. Run one slice, then choose the next gap

**Earlier prompts (English corrected):** “How do I run the code added today?” “Continue with the next session using the existing code, AGENTS.md and README.md.”

**Improved prompt**

```text
Inspect current code, Git status, instructions and saved verification notes.
List what exists, what was actually checked and the next unresolved user-facing
behavior. Provide the exact current module/CLI commands and their effects.

Choose one next slice in layer order. Explain its required inputs, files,
contract constraints and acceptance check. Do not infer readiness from an old
plan or slide. Keep local checks, live reads, model calls and database writes
distinct, and do not execute them beyond the authorized scope.
```

**Result:** The supplied guide records an attempted offline evaluation that failed while reading a Google Drive-backed configuration file. That was a filesystem error, not a quality score. Those files were readable during this merge. No evaluation was rerun, so that historical failure has not been converted into a new passing result. Current command differences are listed below.

**Lesson:** The next step should follow an observed gap. Keep historical verification attached to its revision and purpose instead of adding every later syllabus feature at once.

### Current contracts and commands to use with the early prompts

The API/interface review for this merge is documentary: it checks the examples against today's models, routers and runner. It does not change the API or claim a new runtime test.

| Boundary | Current behavior to preserve |
| --- | --- |
| Retrieval input | `query`, required `as_of`, `top_k` 1–20, optional `product_id` and `jurisdiction`; extra request fields are forbidden. |
| Retrieval scope | Institution, jurisdiction, confidentiality, product when selected, inclusive dates, and source-consistent parent/amendment context. |
| Retrieval output | `results` respects `top_k`; `amendments` supplies complete linked instruments separately; `timings` remains present. |
| Answer output | Three statuses, exact-quote citations, timings and optional `datadog_span_id`; preserve existing consumers. |
| Error behavior | Keep actual FastAPI validation/HTTP error responses; do not invent a replacement error envelope in documentation. The retrieval/answer routers map handled backend failures to 503; validation failures remain 422. |
| Evaluation | `app.evaluation.run` is the live batch entry point. Current CLI flags include `--dataset`, `--output`, `--limit` and `--min-score`; the old `--demo` and `--live` flags are absent. |
| Runtime prompts | Development prompts guide code changes. [answer.py](app/chains/prompts/answer.py) guides generation; [judge.py](app/chains/prompts/judge.py) guides evaluation. Keep their live source authoritative rather than copying stale modules into this guide. |

Commands below are instructions for a later run, **not commands executed during this merge**. Run them from the repo root after configuring the local environment and installing the UI/evaluation extras. Follow the [README](README.md) for dependency setup and the [Datadog guide](DATADOG_README.md) for Docker readiness and telemetry settings.

```bash
# Offline retrieval diagnostics; no paid generation or Atlas mutation.
uv run --no-sync --env-file .env python -m app.evaluation.rag_failure_modes

# FastAPI with the configured Datadog Agent.
uv run --no-sync --env-file .env ddtrace-run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Streamlit in a separate terminal.
uv run --no-sync --env-file .env env DD_SERVICE=nexaassist-ui ddtrace-run python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501

# Live batch evaluation: Atlas/model/judge calls and a report-file write.
uv run --no-sync --env-file .env ddtrace-run python -m app.evaluation.run --limit 1 --output /private/tmp/nexaassist-evaluation.json
```

The evaluation output path is explicit because the runner writes the selected file; choose a new filename to retain previous results. It does not automatically allocate the older guide's timestamped report directory. Ingestion is a separate Atlas-writing operation, documented in the README; it is not a prerequisite to repeat whenever you start the UI.

### What was merged and what was updated

| Supplied guide sections | Where the information appears now |
| --- | --- |
| 1–2: prompting method, decisions and milestones | Introduction, the project journey, F1–F12 and the reusable prompt template. |
| 3–5: foundation, parser and ingestion evolution | Starting steps B–E and F1–F2, including the chunking types and publication limits. |
| 6–8: embeddings, index, API and operations | F2–F5, current contracts and later Datadog history. Use today's institution-aware index and Datadog-only setup. |
| 9–10: failure labs and historical reranker | F6–F8. The old cross-encoder and removal remain history; current optional reranking is described separately. |
| 11–13: answers, teaching alignment and evaluation | F9–F11 and later RAGAS/fix entries, with current statuses and judge/CLI behavior. |
| 14–15: issue resolutions and debugging method | F2/F4/F5/F6 and the reusable diagnosis prompts below. Later circular and scope fixes take precedence over old open-gap descriptions. |
| 16–17: execution and choosing the next slice | F12, the current command examples and the existing README/Datadog guides. |
| 18 and 22: sources, earlier checks and execution limitation | Provenance here and the verification limits at the end. The 22/26/28-test counts remain historical reports. |
| 19: four recovered code-generation prompts | Adapted prompts in F3 (Week 1), F4 (rebuild), F7 (single-file reranker) and F9 (answer endpoint). They are not verbatim transcripts. |
| 20: recorded request excerpts | Corrected and grouped throughout F1–F12; overlapping requests are not repeated as new events. |
| 21: answer/judge source snapshots | Live source links in F9/F11 and the contracts table; stale runtime code is not presented as today's implementation. |

**Merge provenance:** The supplied file was read from `NEXAASSIST_PROMPTING_AND_IMPLEMENTATION_GUIDE.md` in Downloads, with SHA-256 `cc02bf0785ed56471613f9ae2b91aa8c4925106292eb5ac6982673337d05a2c3`. Its reconstructed sections, embedded commands and older scope restrictions were treated as historical source material. The uploaded file was left unchanged. Current code and saved later reports resolve conflicts; no original prompt was inferred where the source supplies only a reconstruction.

**Checks for this merge:** The twelve starting prompts, twelve early stages, all 29 unchanged later entries, local links, navigation and Markdown structure were checked. Current CLI flags and key schema claims were compared with source. The [six-page Design Report companion](NEXAASSIST_PROMPTING_DESIGN_REPORT.docx) was rendered and visually inspected, including its contents-page numbers and table layout. The supplied attachment, retained template and tracked application files remain unchanged. No application suite, paid evaluation or live cloud check was run for this documentation merge.

## Part 3. Your development prompts, corrected and expanded

The following entries retain your requests in clear English, followed by a more detailed prompt, the recorded result and the lesson. They describe the existing project's history; the starting sequence above is a separate guide for a new project.


## 1. Build a familiar chat interface without changing the use case

**Your prompt (English corrected):** “Create a Streamlit chat interface similar to ChatGPT or Claude, while preserving my current use case and existing information.”

**Improved prompt**

```text
Use developing-with-streamlit to improve the existing NexaAssist UI into a
conversational workspace. Preserve the FastAPI contracts and policy use case.
Include a bottom composer, per-session chats, evidence citations, policy scope
and feedback. Keep chain definitions and database access out of the UI.
Verify the existing interactions and the rendered browser layout.
```

**Result:** Implemented in [app/ui/app.py](app/ui/app.py), with coverage in [tests/test_ui.py](tests/test_ui.py). The UI supports Answer/Evidence modes, suggestions, recent chats, references and feedback. The history is session-local. Showing earlier messages does not make the underlying RAG conversation-aware.

**Lesson:** Name the interaction you want and the architecture you must preserve. “Like ChatGPT” alone does not define memory, persistence or API behavior.

## 2. Understand why Datadog showed only MongoDB commands

**Your prompt (English corrected):** “I cannot see any traces when I submit a query through the Streamlit UI.”

The visible resources included `hello 1` and `ismaster 1`. Those are MongoDB driver commands, not proof that a question traversed FastAPI and the model.

**Improved prompt**

```text
Diagnose missing question traces. Inspect the current service, environment,
operation, span kind and time filters before changing instrumentation.
Distinguish MongoDB client spans from the FastAPI request and LLM workflow.
Start with a provider-free health request, then correlate one approved answer
request by trace ID. Report what each observation proves.
```

**Result:** The investigation separated database activity, HTTP requests and LLM workflows. Searches needed the appropriate operation and time range. Later evidence also exposed application-grouping behavior; a filter explanation alone did not account for every empty search.

**Lesson:** “Some spans exist” and “this question is observable” are different claims.

## 3. Explain the Datadog screen using an actual request

**Your prompts (English corrected):** “Explain each section of the Datadog UI and when to use it.” “Also, explain the main Datadog concepts.”

**Improved prompt**

```text
Explain Datadog through one NexaAssist POST /answer request. Map service,
resource, trace, span, duration, status, logs and evaluations to this code.
Explain when to use APM versus LLM Observability, and distinguish request
latency, retrieval latency and answer quality. Use the existing Datadog guide.
```

**Result:** The [Datadog guide](DATADOG_README.md) documents concepts, local setup, navigation and troubleshooting. HTTP METHOD and STATUS CODE may be absent on database-command rows because those rows describe a different operation.

**Lesson:** A concrete request is a better teaching anchor than an isolated product glossary.

## 4. Recover from an occupied FastAPI port

**Reported error (unchanged):** `address already in use` on `127.0.0.1:8000`.

**Improved prompt**

```text
FastAPI cannot bind to port 8000. Identify the listening process and determine
whether it is the existing application before stopping anything. Reuse the
healthy server where appropriate. If the port changes, update the UI API URL
and verify connectivity. Do not terminate unrelated processes.
```

**Result:** The error was a local listener conflict, not evidence of a Datadog failure. Later terminal output showed FastAPI serving successfully on port 8000. The available record does not establish which earlier process was stopped or reused.

**Lesson:** Verify ownership before killing a process. A startup failure occurs before normal application-request tracing can help.

## 5. Start Docker Desktop before diagnosing Compose

**Reported error (unchanged):** `failed to connect to the docker API ... docker.sock: no such file or directory`.

**Improved prompt**

```text
Diagnose this macOS Docker connection error before editing Compose. Check
whether Docker Desktop is running, which Docker context is active, and whether
DOCKER_HOST or DOCKER_CONTEXT overrides the intended connection. Once the
engine is reachable, start the existing Datadog Compose service and inspect it.
Never display API keys or rendered secret values.
```

**Result:** Docker setup and engine/context checks were incorporated into [DATADOG_README.md](DATADOG_README.md). The user later confirmed Docker was started. An installed Docker CLI alone does not establish a running engine.

**Lesson:** Separate the CLI, engine, container and collector. They can fail independently.

## 6. Move collection from the native macOS Agent to Docker

**Your prompt (English corrected):** “Stop the native Datadog Agent on my MacBook and use my Docker Agent instead.”

**Improved prompt**

```text
Switch this project's telemetry collection to the existing Docker Datadog
Agent. Inspect listeners first, avoid two collectors competing for ports,
and align both APM and DogStatsD destinations with the Compose mappings.
Verify collector health and application connectivity. Preserve credentials,
and document the change and restart requirements.
```

**Result:** The current [Compose file](app/compose.datadog.yaml) maps host TCP `18126` to container `8126` and host UDP `18125` to container `8125`. The guides record Docker as the active collection path and the native Agent as inactive in the checked setup. This is a historical observation, not a fresh check of today's processes.

**Lesson:** Configure the application's host destination, not the container's internal port. APM and runtime metrics use different protocols and ports.

## 7. Investigate HTTP 200 responses that did not appear in Datadog searches

**Your prompt (English corrected):** “FastAPI returns HTTP 200 for my request, but I cannot see any traces in the Datadog UI.”

**Improved prompt**

```text
Trace one approved request from FastAPI through the Docker Agent to Datadog.
Check the running process's destination, receiver/forwarder evidence, site and
organization, then use a direct trace link and an appropriate time window.
Inspect workflow application identity for UI-originated calls. Do not change
global sampling or retention based only on an empty search.
```

**Result:** The user confirmed a health trace and later confirmed both the successful answer's direct APM trace and its LLM question/answer. A direct 422 trace also exposed recorded FastAPI span details. Earlier rolling windows excluded an older request, but a fresh empty search showed that time mismatch did not explain everything.

The code now explicitly identifies API LLM workflows with `agent_service=settings.dd_service`. Older UI-originated runs could be grouped under `nexaassist-ui`; new API workflows use the API identity. The [recorded investigation](DATADOG_README.md#traces-from-streamlit--application-grouping) preserves these distinctions.

**Lesson:** A search result is one observation. Collector acceptance, cloud ingestion, direct trace visibility and indexed-search availability are separate checks.

## 8. Add live RAGAS evaluation for questions submitted now

**Your prompt (English corrected):** “I would also like to see my RAGAS metrics.” — later clarified as both Streamlit and Datadog.

**Improved prompt**

```text
Add live RAGAS evaluation for a newly submitted policy question. Retrieve once,
generate once except for bounded citation repair, and score the final returned
answer against the exact context used for generation. Isolate evaluator errors
so scoring failure preserves the answer. Submit available scores to its Datadog
workflow span and return explicit metric availability states.
```

**Result:** Implemented through [app/services/evaluation.py](app/services/evaluation.py), [app/evaluation/live.py](app/evaluation/live.py) and `POST /answer/evaluated`. The user confirmed a particular live run with four scores in Datadog. This does not guarantee every later evaluation is scored or delivered.

**Lesson:** Evaluating a regenerated answer would measure a different user experience. Score what the user actually received.

## 9. Explain “Not scored” without inventing missing values

**Reported screen text (unchanged):** “Context precision — Not scored ... Provide a reference answer, or use an exactly matching golden case.”

**Improved prompt**

```text
Explain why particular RAGAS metrics are unavailable for this request. Check
retrieved evidence, answer status and reference matching. Provide a supported
question, policy date, product and reference answer from the golden dataset.
Do not substitute zero for unavailable/error results or promise perfect scores.
```

**Result:** In this implementation, context precision and recall require a reference answer. The UI accepts one, or the service can select an exactly matching golden case. Missing evidence and abstention also affect applicability. Metric exceptions are distinct from unavailable inputs.

**Lesson:** A missing measurement is not a poor measurement. Preserve `scored`, `unavailable` and `error` as different states.

## 10. Keep RAGAS scores in Datadog, not in the chat

**Your prompt (English corrected):** “I do not want RAGAS metrics displayed in Streamlit. Show them in the Datadog UI instead.”

**Improved prompt**

```text
Remove RAGAS score cards from Streamlit while preserving evaluation, optional
reference input and Datadog export. Show the answer, citations and evaluation
link. Keep the UI free of business logic and verify existing feedback and
question flows still work.
```

**Result:** Implemented. Streamlit retains the evaluation controls and Datadog link, while numeric score cards are hidden. This later request superseded the earlier request to display scores in both places.

**Lesson:** State whether a change affects computation, storage, export or display. Removing the display should not silently remove evaluation.

## 11. Send answer feedback to Datadog safely

**Your prompt (English corrected):** “Enable feedback in Datadog as well.”

**Improved prompt**

```text
Extend existing feedback persistence with optional Datadog thumbs feedback.
Target the answer's exported span and actual API application identity rather
than a hard-coded example ID. Save to MongoDB first. Preserve feedback when
the SDK is unavailable, and make identical client retries idempotent.
Document whether successful submission means queued or confirmed delivered.
```

**Result:** [The feedback service](app/services/feedback.py) saves first, then optionally calls `LLMObs.submit_feedback`. Stable submitter/submission IDs prevent duplicate retry attempts. Conflicting contents under the same ID return 409. Listing/review require a reviewer token. There is no durable Datadog-delivery outbox.

**Lesson:** Persistence, authorization, deduplication and telemetry delivery are different responsibilities. An anonymous session UUID is not an authenticated end-user identity.

## 12. Recover when the collector is unavailable

**Reported errors (unchanged):** “Connection refused” and “dropping 44 traces ... http://127.0.0.1:18126”.

**Improved prompt**

```text
Investigate refused telemetry connections at the configured local collector.
Check Docker engine availability, container health, TCP APM and UDP DogStatsD
mappings, then the running application's settings. Preserve the working API.
After recovery, generate fresh traffic and verify it; do not assume dropped
telemetry will be recovered automatically.
```

**Result:** The user reported starting Docker. The recorded configuration uses the published collector ports. Requests dropped while the collector was unavailable cannot be treated as successfully delivered because it later recovered.

**Lesson:** A working answer and a working telemetry pipeline are independent outcomes.

## 13. Review the repository without deleting useful behavior

**Your prompt (English corrected):** “Review and validate the repository. Check its features and functionality, and remove redundant code.”

**Improved prompt**

```text
Use codebase-recon to map entrypoints, callers and existing tests, then review
correctness, layer boundaries, failure handling and duplication. Rank findings
with file evidence. Apply the smallest supported fixes and remove code only
after checking its callers and contracts. Report remaining risks and the exact
checks performed; do not describe a static audit as full runtime validation.
```

**Result:** Recon, audit and fix work is reflected in the component guide, regression suite and reports. Later realistic tests found issues despite earlier passing checks. No benchmark establishes project-specific savings from Ponytail; its gain command is not a measurement of this repository.

**Lesson:** An audit is an input to verification, not a declaration that every feature is correct.

## 14. Test realistic user journeys rather than HTTP status alone

**Your prompt (English corrected):** “Test the entire system using realistic scenarios that real-world users may encounter.”

**Improved prompt**

```text
Test realistic synthetic journeys across Streamlit, FastAPI, retrieval,
answering, evaluation and feedback. Include current and historical policies,
amendments, ambiguous questions, conflicting scope, unsupported requests,
invalid inputs and retries. Judge outcomes against source evidence as well as
HTTP/schema checks. Preserve responses and separate simulated users from
recruited-user research. Identify live calls before executing them.
```

**Result:** The initial saved UAT recorded 98 application tests and 22 separate mock API tests passing. Nineteen live answer journeys all returned HTTP 200, yet adjudication found two failed user outcomes and other incomplete/recovery cases. These were simulated scenarios, not nineteen recruited users.

**Lesson:** HTTP success, schema validity, exact citations and semantic correctness need separate verdicts.

## 15. Fix outdated fee answers by retrieving the complete amendment

**Your prompt (English corrected):** “Based on the two previous reports, fix the issues they recommended addressing.”

The earlier default search returned the old processing fee. Raising the source count alone also failed to yield a usable answer in a recorded run.

**Improved prompt**

```text
Reproduce the incorrect Home Loan fee using the actual UI defaults. Compare
ranked evidence with the effective circular, including applicability and
grandfathering. Fix evidence selection before weakening the answer prompt.
Keep complete required amendments inside the context budget or abstain.
Add regressions for both sides of the sanction cutoff and earlier sanctions.
```

**Result:** Complete linked circulars are loaded separately from ranked similarity hits. Effective chains are followed, inconsistent instrument metadata fails closed, and required amendments receive context priority. Targeted final answers used the revised fee and sanction-date condition. This did not establish that all future questions or model calls will succeed.

**Code:** [amendment lookup](app/database/retrieval.py), [retrieval chain](app/chains/retrieval.py), [amendment tests](tests/test_amendments.py).

**Lesson:** The highest-ranked paragraph may omit a legally relevant condition. More `top_k` is not a universal remedy.

## 16. Keep child and parent evidence in the same scope

**Related request (English corrected):** “Fix the issues recommended in the review reports.” This entry covers the scope checks identified during that follow-up.

**Improved prompt**

```text
Check scope across the whole retrieval path, including parent expansion and
linked circulars. Enforce institution, product, jurisdiction, confidentiality,
document/version and effective windows where applicable. Reproduce a parent
from the wrong scope before fixing it. Retain scoped child evidence when its
parent is missing or mismatched, and test both dense and hybrid paths.
```

**Result:** Institution filters and parent metadata validation were strengthened. Missing or mismatched parents fall back to the child; inconsistent circular records return an error. The saved review found issues that earlier test coverage had missed.

**Code:** [retrieval](app/chains/retrieval.py), [parent regressions](tests/test_retrieval.py), [Atlas index definition](app/database/indexes.md).

**Lesson:** A filtered child does not make an unrestricted parent safe. Verify every expansion step.

## 17. Correct the reference when the test expected unsupported detail

**Your decision (English corrected):** “Keep the source-grounded wording.” This applies to the NexaFlex foreclosure GST reference.

**Improved prompt**

```text
Compare this failing answer with the exact source clauses before changing the
model or reference. Preserve the six-EMI lock-in and four-percent foreclosure
charge plus GST. Do not transfer the GST percentage from processing fees into
a foreclosure clause that does not specify it. Update affected golden mirrors
and assertions together, explaining the corrected test expectation.
```

**Result:** The foreclosure reference now says “plus GST” and explicitly notes that the clause does not specify a GST percentage. Earlier reports retain the original disagreement as historical evidence.

**Lesson:** A failing assertion can reveal a bad evaluation reference. The source must outrank the expected answer.

## 18. Recover from invalid citations without disabling validation

**Reported issue:** An evaluated fee response abstained after citation validation failed.

**Improved prompt**

```text
Reproduce the invalid citation path. Permit at most one repair draft using the
same retrieved evidence; never remove exact quote and citation-ID checks.
After two invalid drafts, abstain. Score only the final returned answer,
include total generation latency, and test both successful repair and exhaustion.
```

**Result:** A bounded second draft was added. The saved final fee sample returned an answer with faithfulness 1.000, relevancy 0.859, precision approximately 1.000 and recall 1.000; Datadog submission was queued. The intervening failing sample remains in the record. These are particular measured results, not acceptance thresholds or guarantees.

**Lesson:** A recovery path must retain the safety property that caused the initial rejection.

## 19. Use an independent review as evidence, not as a pass certificate

**Your prompts (English corrected):** “Use Codex CLI for the independent review.” “Run this exact read-only command.”

**Improved prompt**

```text
Prepare an independent review of a frozen patch and synthetic test evidence.
Show the exact model, command, sandbox and outgoing material before any required
approval. Classify each returned finding against code evidence, reproduce
valid findings and map fixes to regressions. Record which patch was reviewed
and whether the final patch received another independent review.
```

**Result:** User-approved read-only reviews produced actionable findings. Reconciliation and patch hashes were saved. The fix summary explicitly says the external review was not rerun after the follow-up changes; the final local regressions and earlier reviewed patch are different evidence.

**Lesson:** A review of one patch does not certify a later patch. Do not silently broaden an approval to another command or run.

## 20. Configure quality hooks and organize commits

**Your prompts (English corrected):** “Commit only my working code in three commits.” “Also, configure pre-commit.”

**Improved prompt**

```text
Inspect staged and unstaged changes, then group the intended working code into
three coherent feature commits. Keep secrets, scratch outputs and unrelated
work out. Configure pre-commit for YAML/TOML, conflict markers, private keys,
Ruff lint and formatting using project tools. Explain skipped hooks and run
appropriate tests separately. Do not push without authorization.
```

**Result:** [.pre-commit-config.yaml](.pre-commit-config.yaml) exists. Current recent Git history contains RAG, observability and UI feature commits plus a separate pre-commit setup commit. The working tree still contains later uncommitted changes, so “everything is committed in three commits” would be inaccurate. Pytest and mypy are separate from these hooks.

A later HTTPS push failed because password authentication was rejected. The available record does not confirm that authentication was subsequently fixed or that a push succeeded.

**Lesson:** A hook marked “Skipped” can be correct when no staged file matches. Commit organization and remote authentication are separate tasks.

## 21. Write guides that explain the working implementation

**Your prompts (English corrected):** “Write DEVELOPMENT_TOOLING_GUIDE.md in natural, easy-to-read English.” “Update README.md and APP_COMPONENT_GUIDE.md with the latest information.”

**Improved prompt**

```text
Update the existing documentation from current code and saved evidence. Use
plain language: purpose, when to use it, example and limitation. Distinguish
skills available on this machine, skills used during development, Git hooks
and the application's future MCP capability. Check file links and commands.
Do not promote a local plugin or a passing unit test into a runtime guarantee.
```

**Result:** The [tooling guide](DEVELOPMENT_TOOLING_GUIDE.md), [README](README.md) and [component guide](APP_COMPONENT_GUIDE.md) describe layers, operations, skills, hooks, MCP status and limits. Older planning records remain historical and may describe an earlier parser or earlier scope.

**Lesson:** Human-readable documentation needs accurate boundaries, not just shorter sentences.

## 22. Remove project-owned LangSmith integration

**Your prompt (English corrected):** “Remove all project code that uses LangSmith.”

**Improved prompt**

```text
Remove project-owned LangSmith imports, decorators, configuration, direct
dependencies and active documentation. Preserve LangChain behavior, Datadog
instrumentation, RAGAS and local evaluation reports. Inspect dependency metadata
before removing an indirect requirement. Verify application behavior and report
any package that must remain transitively installed.
```

**Result:** Active application integration was removed. The current app/test/config/direct-dependency search found no LangSmith integration references. LangChain still requires the package indirectly; uninstalling it would not be a complete or safe integration removal. Historical reports and quoted syllabus references can still mention the earlier tooling.

**Lesson:** Removing an integration does not necessarily mean removing every package with that name from the dependency graph.

## 23. Align training decks with the syllabus and code

**Your prompts (English corrected):** “Create a PowerPoint presentation aligned with the syllabus and code.” Later: “Keep the presentation between 20 and 25 slides.” For the separate agent introduction: “Create two or three slides explaining the concepts with a real-world example.”

**Improved prompt**

```text
Create a separate deck for the named lesson using the local syllabus PDF and
current code. Use the requested slide range, clear code mappings and a single
synthetic policy example. Mark built, proposed and unverified behavior. Include
speaker notes and validate the editable export. Treat the later three-slide
agent introduction as its own deliverable, not a recap-deck size change.
```

**Result:** Observability and recap artifacts exist under `../PPTs/`. The separate [three-slide agent introduction](../PPTs/NexaAssist_RAG_to_Agents_20261022/exports/NexaAssist_RAG_to_Agents_20261022_053910.pptx) has three editable slides and three speaker-note pages, with a passing export postflight. It uses synthetic customer NXC-0010 and the circular opt-in request. Native PowerPoint rendering was not inspected in that export pass.

**Lesson:** Specify the audience, lesson and artifact separately. A new slide-count request should not silently reshape an unrelated earlier deck.

## 24. Create a source-backed animated architecture

**Your prompt (English corrected):** “Use the appropriate skill to create a detailed, animated architecture diagram based on the latest implementation.” You selected Archify for this request.

**Improved prompt**

```text
Use archify to diagram the latest working implementation, including answer,
evaluation, feedback, ingestion and Docker telemetry paths. Distinguish shared
libraries from running processes, and mark future agents/MCP as planned.
Attach verified source ranges, validate the native artifact and browser behavior,
and describe animation as illustrative. Preserve the main repository history.
```

**Result:** The [Archify diagram](.archify/architecture-nexaassist-20261021-214925/nexaassist.html) contains twelve components, eighteen relationships and thirty-five source ranges. Final delivery/browser checks passed; Live motion and a source passport were exercised, and light/dark captures inspected. Some secondary routes still cross; selecting a component or route helps isolate them.

An isolated local source snapshot pinned the uncommitted implementation without changing the main project's Git history. It was not published to GitHub. See [source notes](.archify/architecture-nexaassist-20261021-214925/SOURCE_NOTES.md).

**Lesson:** A checked diagram can still have visual trade-offs. Animation demonstrates authored relationships, not measured traffic or elapsed time.

## 25. Clarify which “next session” the instructor means

**Your prompt (English corrected):** “How should I introduce the next session using the code and syllabus PDF?”

The initial answer assumed Phase 1 Session 3 from the two existing teaching notebooks. Your clarification, edited for English: “I mean the next phase: agentic AI after RAG.”

**Improved prompt**

```text
Prepare a five-to-ten-minute introduction to Phase 2 Session 1: From RAG to
Agents and LangGraph Fundamentals. The audience has completed the RAG lessons.
Use syllabus pages four and five and current code. Explain what stays unchanged,
what remains planned, and one request that needs customer data and an action.
Do not implement all four agents in this introductory task.
```

**Result:** The introduction was corrected to Phase 2. It preserves `/retrieve` as a service capability and introduces state, nodes, edges and conditional routing before the later agent roles. The three-slide follow-up follows this corrected scope.

**Lesson:** Repository implementation progress does not identify the last lesson actually taught. Name the phase and session.

## 26. Demonstrate the gap between policy answers and customer actions

**Your prompt (English corrected):** “Provide two or three queries that my current RAG cannot complete but an agent workflow could handle.”

**Improved prompt**

```text
Give three realistic requests that require capabilities beyond the current
policy chat. Ground them in existing synthetic customers and mock API contracts.
For each, separate policy explanation, customer lookup, validation and write.
Label the agent integration as proposed and distinguish recorded requests from
completed banking changes.
```

**Result:** Examples included NXC-0010 opt-in eligibility/request creation, NXC-0023 already-opted-in handling, and an interest-certificate request with loan-ownership validation. Mock endpoints exist separately; the agent workflow is not implemented. `RECEIVED` means a request was recorded, not that an opt-in was applied.

**Lesson:** An agent needs tools and explicit validation. Naming an agent cannot provide access to customer data or permission to act.

## 27. Explain query-related errors without turning every rejection into an incident

**Your prompt (English corrected):** “What query-related errors could I see in Datadog?”

**Improved prompt**

```text
Map the example requests to current RAG failures and future tool outcomes.
Use the actual HTTP/error contracts. Separate invalid input, business rejection,
dependency failure and a successful HTTP response that misses the user goal.
Explain where to inspect each in Datadog without claiming unimplemented agent
spans already exist.
```

**Result:** The guide distinguished current 422 input validation and handled 503 answer-service failures from mock 409 already-opted-in, 422 ownership/applicability, 400 missing-idempotency-key and injected 503/504 outcomes. These are expected code paths, not failures triggered during that explanation. A 4xx response need not be marked `status:error` on its server span.

**Lesson:** A correct business rejection can be a successful workflow outcome. Conversely, HTTP 200 can still fail the user's task.

## 28. Apply dark mode at the configuration that actually wins

**Your prompt (English corrected):** “I would like to use a dark theme in Streamlit.”

**Improved prompt**

```text
Use developing-with-streamlit to inspect the effective theme and all relevant
config locations. Apply dark colors through native configuration, preserving
layout, typography and behavior. Check the running browser's chat, sidebar,
inputs and contrast. Do not submit model questions just to verify a theme.
```

**Result:** The root `.streamlit/config.toml` was already dark, but [the app-specific config](app/.streamlit/config.toml) was light. Its colors and sidebar were changed to dark; the root file was preserved. Browser inspection confirmed main background `#0B0E14`, sidebar `#11151C`, light text, no application exception and no horizontal overflow. A screenshot was inspected. Existing framework form-markup issues were not fixed by this theme change.

**Lesson:** Inspect effective configuration and browser output before adding CSS or restarting unrelated services.

## 29. Supply usable RAGAS question/reference pairs

**Your prompt (English corrected):** “Provide a few questions I can ask the RAG application, along with reference answers for RAGAS evaluation.”

**Improved prompt**

```text
Select five questions and expected reference answers from the current golden
JSONL. Include the exact question, policy date, product and source count for each.
Explain where to paste the reference and where scores appear. Include a
historical-policy boundary case. Do not invent references, measured scores or
unsupported tax details.
```

**Result:** The examples covered the Home Loan maximum, LTV at eighty lakh, Personal Loan foreclosure, Auto Loan new/used LTV and the last day of Home Loan v1. The first four use 2026-10-01; the historical question uses 2024-03-31. References were checked against [the golden dataset](evaluation/datasets/answer.jsonl); no fresh evaluations were run for that answer.

**Lesson:** RAGAS needs an expected reference answer, not another reference question. Question, date and product must describe the same evaluation case.

## A reusable way to write the next prompt

A useful prompt answers six questions: what exists, what should change, what must remain true, what evidence is available, how success will be checked, and what should be returned.

```text
Task: [one concrete outcome]

Context:
This is NexaAssist: LangChain + MongoDB Atlas, thin FastAPI routes,
Streamlit UI, RAGAS/structured judges and Datadog telemetry.
Follow the applicable project instructions (AGENTS.md for Codex or CLAUDE.md
for Claude Code), and inspect current code and callers before editing.

Current problem:
[expected behavior, actual behavior, exact error or saved failing example]

Scope and constraints:
[files/contracts to preserve; current layer; relevant dependency constraints]
Keep the change small. Keep secrets out of outputs and source control.
Identify proposed behavior separately from implemented behavior.

Verification:
[reproduction, meaningful regression, relevant checks, browser check if UI]
Distinguish local/mock tests, live observations and cloud confirmation.
Do not make provider calls or external writes beyond the authorized scope.

Return:
Changed files, concise diagnosis with evidence, verification results,
remaining limits, and a reviewable artifact where appropriate.
```

You do not need every paragraph for a small task. For “change the theme”, the configuration, preservation constraint and browser check are enough. For an observability failure, the exact request time, service, environment and trace ID are more useful than a screenshot saying “nothing appears”. Ask for a concise evidence summary rather than private internal reasoning.

## Copyable prompts for common follow-ups

### A. Diagnose an incorrect policy answer

```text
For this exact question, date and product, compare the answer with the source
policy and circular. Capture retrieval, parent expansion, amendment evidence,
context budget and final citations. Locate the first evidence/contract failure.
Reproduce it in one regression, fix the owning layer and rerun relevant checks.
Do not lower validation standards or change the reference without source proof.
```

### B. Diagnose a missing Datadog trace

```text
The request at [time + timezone] returned [status]. Expected service is
[service], environment [env], collector [host/port], trace ID [if available].
Check app instrumentation, collector receipt/forwarding, organization/site,
workflow identity and query filters in that order. Use a provider-free probe
first. State exactly which delivery boundary is verified and which is still open.
```

### C. Review a patch without expanding the task

```text
Review the current diff and connected callers for correctness, scope, error
handling and useful test coverage. Give prioritized file-backed findings.
Apply the smallest authorized fixes, preserve unrelated work, and record
which checks passed. Do not run a new external review, commit, push or deploy
unless that action is already authorized.
```

### D. Prepare a code-backed teaching artifact

```text
Create [artifact] for [phase/session], [audience], lasting [duration], with
[slide/page count]. Use the local syllabus and current code. Follow one
synthetic worked example. Include code mappings and label existing, planned
and unverified behavior. Preserve the requested format and validate the export.
```

## What the tools contributed

| Tool or skill | Useful contribution | Boundary |
| --- | --- | --- |
| Ponytail | Small, complete changes and attention to existing callers | Not proof of measured cost/speed savings |
| codebase-recon | Repository/history map before a broad review | Not an end-to-end test |
| Observability/debugging skills | Delivery-boundary checks and evidence-led diagnosis | Logs or Agent counters alone do not prove cloud visibility |
| test-engineer and browser-testing-with-devtools | Regression scenarios and real rendered interactions | Simulated journeys are not recruited-user research |
| doubt-driven-development / independent review | Fresh scrutiny and explicit finding reconciliation | Approval and review scope apply to the exact run/patch |
| developing-with-streamlit | Installed-version documentation and native configuration | Browser behavior still needs inspection |
| C4 skills and Archify | Architecture explanation, source mapping and checked HTML | Diagrams do not establish deployment or live traffic |
| PPT Master | Structured slide authoring, speaker notes and native export checks | Package validation is not a native PowerPoint visual review |
| Git pre-commit hooks | Staged-file syntax, conflict, key and Ruff checks | Not a replacement for pytest, mypy or secret review |
| Development MCP tools | Browser inspection and artifact/tool access | Separate from an MCP server inside NexaAssist; that layer is future work |

The [development tooling guide](DEVELOPMENT_TOOLING_GUIDE.md) explains setup and usage in more detail. Choose the skill that fits the task; listing every skill in every prompt adds noise.

## Smaller tooling issues worth remembering

| Issue encountered | Recovery used | What was not claimed |
| --- | --- | --- |
| `python` executable absent during diagram authoring | Used the available `python3` executable | No application dependency change was needed. |
| Archify canvas labels fell below the desktop readability floor | Compacted the existing layout and reran the full delivery checks | A later alternate placement failed; the passing original was restored. Secondary crossovers remain. |
| Standard PDF conversion lacked PyMuPDF | Used installed pdfplumber to extract the supplied PDF and retained the original alongside Markdown | No new dependency was added to the app for document extraction. |
| Slide live editor lacked Flask | Continued authoring/export with that preview unavailable | No live-editor or native PowerPoint visual review was claimed. |
| Presentation export lacked Pillow/python-pptx in the initially selected runtime | Used available app tooling where sufficient, then an isolated uv presentation environment | Application dependencies and lockfile were not changed for the slide export. |
| Browser screenshot path was rejected by the tool's workspace checks | Used the supported screenshot response and inspected the returned image | A rejected file write was not counted as a screenshot success. |

## What we can honestly say at the end

The saved initial UAT had **98 application tests** passing and still found a wrong fee answer. The saved fix run later had **121 application tests and 22 separate mock API tests** passing, with Ruff and mypy passing, and twelve targeted saved live policy cases. These counts describe those recorded runs; this guide does not claim a freshly rerun suite or full-dataset semantic quality.

The user confirmed selected Datadog APM/LLM traces and four scores in an earlier session. Later saved fix runs reported SDK queuing without a fresh authenticated cloud check. Both statements can be true. The final local test does not overwrite the limits of earlier evidence, and an earlier successful trace does not guarantee current collector health.

Still open or limited: probabilistic date-intent classification, restored-sidebar layout shift, some framework form markup, the ddtrace non-LLM prompt-template warning, best-effort feedback export without an outbox, sustained load, full accessibility/usability, disaster recovery and production deployment. Agentic customer actions and application MCP remain planned. Current normal retrieval defaults to dense mode with reranking disabled; an optional code path is not proof of measured live hybrid/reranker quality.

The most useful habit from this project is to keep the chain visible: **prompt → expected behavior → observed evidence → fix → verification → remaining limit**. That makes the next request easier to write and the result easier to trust.
