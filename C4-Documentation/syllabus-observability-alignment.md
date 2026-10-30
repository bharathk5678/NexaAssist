# NexaAssist observability: syllabus and implementation alignment

> The current implementation uses Datadog. Product names inside quoted syllabus
> excerpts describe the original teaching material, not active integrations.

Evidence inspected on 19 October 2026. PDF page references below are physical pages (1–9), not an inferred session numbering scheme. Source syllabus: `1. Phase1_Enterprise_RAG_Agentic-AI_MCP_Evaluations_Full_Syllabus-.pdf`. Existing PowerPoint files were inspected through their slide XML; originals were not modified. This analysis does not establish that telemetry is visible in an authenticated Datadog account.

## Exact syllabus placement

| PDF page | Exact phase/session heading | Stated subject and objective | Appropriate treatment in this deck |
| --- | --- | --- | --- |
| 1 | Program Charter | “No live coding / no Python fundamentals.” Format: “concept explanation (15–20 min) → mapping to the pre-built implementation (~10 min) → Q&A (10 min)”; sessions 1–1.5 hours with 1–2 concept blocks. | Teach concepts, then map to existing code, then use a diagnostic exercise; do not turn the presentation into a live coding workshop. |
| 2 | Phase 1 — RAG Foundation + Offline Evaluation; Session 4, “Retrieval Service API + Deployment” | “FastAPI /retrieve contract, top-k, filters”; reusable retrieval contract beyond the agent. | Prerequisite: identify the HTTP service boundary that APM observes. Current endpoints also include `/answer`. |
| 2 | Session 5, “[CARRY-FORWARD] Production Failure Modes” | “Retrieval miss, stale index, embedding drift”; production example “Latency/empty-result alerting; scheduled re-indexing”. | Revisit empty evidence and slow retrieval as different observations; alerting/re-index scheduling are production examples, not confirmed implementations. |
| 2–3 | “Week 2 — Retrieval Quality, Evaluation & Observability” | Connect retrieval, generation, evaluation, feedback and visibility. | Use a single dated policy question throughout. |
| 3 | Session 8, “[CARRY-FORWARD] Offline Evaluation (RAGAS)” | “Faithfulness, answer relevancy, context precision/recall”; “Measuring RAG quality without humans”; “Eval must run before every deploy”; production example “RAGAS as automated CI/CD regression gate”. | Carry forward the four metrics and show the actual offline runner; distinguish an optional local gate from an automated CI deployment gate. |
| 3 | Session 8, “LLM-as-Judge” | “Judge prompt design, bias pitfalls”; “Failure modes of LLM evaluating LLM”; “Where judge fits alongside RAGAS”; production example “Judge runs on cheaper model, scheduled batch”. | Show the current structured correctness/groundedness judge and its same-model bias limit. A cheaper independent scheduled judge is a target, not the current runner. |
| 3 | Session 9, “Golden Dataset & Human Feedback Loop” | “Q&A curation, edge-case coverage, feedback loop”; “Golden dataset as a living, owned artifact”. | Explain that a bad answer trace and a user vote are investigation evidence; human verification precedes accepting a golden case. |
| 3 | Session 10, “[CARRY-FORWARD] Dev-Time Observability” | “Per-stage tracing, p95/p99 latency”; interview topic “Debugging a slow/wrong RAG response”; discussion “Per-stage tracking before Phase 4’s full observability”; production example “Langfuse/LangSmith instrumentation → evolves into OpenTelemetry in Phase 4”. | **Primary home for the current presentation.** Explain traces/spans, latency distributions, Datadog APM/LLM roles, actual request investigation and missing-trace troubleshooting. |
| 3 | Session 10, “Phase 1 Wrap-Up” | “Cost/latency/anti-pattern recap”; “Trainee design walkthroughs”. Exit checkpoint includes “RAGAS + LLM-as-Judge run at least once; trace reviewed for bottlenecks; walkthrough delivered.” | Finish with a learner walkthrough using one request, one bottleneck and one quality investigation; a unit-test pass alone does not prove this exit checkpoint. |
| 4 | Phase 2 Session 1, “LangGraph Fundamentals” | “StateGraph, nodes, edges, conditional routing”; graph runs as FastAPI service; node-level unit testing. | Future extension: carry telemetry across a future agent boundary. Do not depict agents as currently implemented. |
| 4 | Phase 2 Session 2, “[CARRY-FORWARD] Retriever Agent” | Phase 1 `/retrieve` remains “untouched”; a new `httpx` client belongs in Agent Service. | Stable API telemetry is reusable by an agent caller; no need to bypass the service or duplicate its database logic. |
| 7 | “Phase 3 → Phase 4: Limitations & Resolution” | “No visibility into live behavior” → “Observability: Datadog + Arize”; offline-only evaluation → “Online Evaluation & Drift Detection”. | Explicit bridge explaining what remains after local development telemetry. |
| 8 | Phase 4 — Production, HITL, Online Evaluation & Observability; Session 2, “Infrastructure Observability (Datadog)” | “APM traces, latency percentiles, error rates”; “Monitoring a multi-service AI system’s health”; “Infra observability vs. LLM observability — both needed”; production example “Datadog Agent sidecar per ECS task; p95/p99 dashboards”. | Label **Phase 4 preview**. Current local Agent setup is an example of collection, not proof of deployed ECS sidecars or live shared dashboards. |
| 8 | Phase 4 Session 2, “LLM Observability & Online Evaluation (Arize)” | “Groundedness, hallucination detection, drift”; “Offline eval (Phase 1) necessary but not sufficient”; “Arize SDK on live responses; scheduled automated judge sampling; drift alerts”. | Preserve the syllabus provider assignment. Current Datadog LLM telemetry/evaluation export is useful implementation, but does not satisfy the specified Arize online-evaluation/drift deliverable. |
| 8 | Phase 4 Session 3, “[CARRY-FORWARD] From Offline to Online Evaluation” | “Continuous regression detection, sampling strategy”; production example “5–10% of production traffic routed through Phase 1’s judge pattern, now scheduled”. | Future design: sampling is a syllabus example, not a configured percentage or guaranteed production requirement. |
| 8 | Phase 4 Session 3, “Cost Governance at Scale (half-session)” | “Per-service/tenant cost attribution, budget alerts”. | Distinguish recorded token usage from implemented billing attribution/budget alerting. |
| 8 | Phase 4 Session 5, “CI/CD for AI Systems” and “Incident Response & SLOs” | Build → test → golden evaluation → deploy; SLOs combine uptime/latency and quality; runbook starts with drift alert and corpus/model changes. | Dashboards, monitors, SLOs and CI are production extensions; no threshold values should be presented as configured unless code/config confirms them. |

## Established slide style and teaching sequence

Inspected: `../PPTs/NexaAssist_Week2_Session8.pptx` (28 slides), `NexaAssist_Week2_Session9.pptx` (28), `NexaAssist_Week2_Session10.pptx` (25), and Phase 2 Sessions 1–3 (27/28/27). Phase 2 Session 4 was discovered but its slide contents were not successfully extracted in the bounded inspection.

- Existing decks use widescreen 16:9 (`9144000 × 5143500` EMU), Cambria headings, Calibri body and occasional Courier New code. Common actual slide colors: navy `1C2745`, dark text `233348`, teal `247C83`, pale teal `DDECEF`, white, muted text `60758B` and borders `C5D6DF`.
- Cover: phase/week/session eyebrow, concrete lesson title, one-sentence goal, and three numbered learning verbs. Subsequent slides use short action-oriented headings, compact parallel cards/tables, source-code paths, explicit caveats and a takeaway strip labelled TAKEAWAY / DECISION / OBSERVE / STATUS.
- Sequence: recap and run sheet → 1–2 concept blocks → current code mapping → worked NexaBank policy case → exercise/interview question → “Four things to keep” and next-session bridge.
- Repeated visual teaching types: architecture, process flow, sequence and NexaBank example. Some diagrams are image/graphic content, so XML text extraction alone does not establish visual render quality.
- Existing slides distinguish BUILT from PROPOSED; carry this convention forward. Their example timings explicitly say illustrative/no live trace run.
- Original package slide numbers do not always match footer order because diagram slides were appended and then reordered. Use presentation order and regenerate consistent numbering in a new deck.

## Existing lesson overlap and stale evidence

The prior Session 10 already covers trace/log/metric differences, p50/p95/p99, slow-versus-wrong diagnosis, Datadog APM/LLM roles, trace content, a Phase 1 walkthrough and future agents. The new lesson should deepen real Datadog navigation and current-code evidence, rather than repeat a generic product glossary.

**Do not copy old implementation claims into the new deck:**

| Old deck / guide claim | Current evidence and correction |
| --- | --- |
| `/ask`, `RagService.ask`, `RagAnswer.timings_ms` | Current API uses `/answer` and `/retrieve`; source files are `app/api/answer.py`, `app/api/retrieval.py` and current request/response models. |
| `app/chains/timing.py`; timing keys `candidates`, `reranked`, `expanded`, `answer` | Current `RetrieveTimings` fields are `search_ms`, `parent_ms`, `total_ms` (`app/models/retrieval.py:38`). Answer generation has `generation_ms`; inspect current answer response/chain. |
| Old S10 says telemetry exports LangChain variables | Current `app/core/telemetry.py:4` calls `ddtrace.patch_all()` when enabled; only Datadog telemetry is configured by the application. |
| Old evaluation CLI flags `--judge`, `--ragas`, `--category`, `--concurrency`, `--demo`, `--live` | Current `app/evaluation/run.py:293` supports `--dataset`, `--output`, `--limit`, `--min-score`. Use `uv sync --locked --extra ui --extra evaluation`, then the current runner command. |
| Prior S8/S9 decks describe 59 Phase 1 items selected from 97 | Current runner loads `evaluation/datasets/answer.jsonl` using the `GoldenCase` contract: `input`, `expected_output`, `context`, optional `expected_status` (`run.py:35`). Do not import old dataset counts/IDs as current runner facts. |
| `SESSION8_EVALUATION_GUIDE.md` describes `PolicyVerdict`, judge pass/needs_review/fail, default semantic gate and named functions absent from the runner | Current `JudgeScore` is numeric correctness and groundedness plus rationale (`run.py:44`); current `quality_gate` returns true when no numeric threshold is supplied, and report says `not_configured` (`run.py:215,293`). Source code takes precedence over the stale guide. |
| Independent optional `EVAL_JUDGE_MODEL` | Although a config field exists, current `collect_records` uses `get_chat_model(settings)` for both generation and judge. Report explicitly records same-model bias. Do not claim the field selects a separate judge in this runner. |
| Empty-context scores skipped | Current RAGAS runner assigns all four metric values 0 to expected-answer cases without contexts; expected abstentions are excluded from RAGAS, but still receive judge/status evaluations (`run.py:157,231`). |

## Current code-backed observability scope

1. **Startup and collection:** `app/main.py:20` calls telemetry/log initialization. `app/core/telemetry.py:4` documents that FastAPI must launch with `ddtrace-run` before application construction. `DATADOG_README.md` supplies `.env`-before-SDK launch commands, Agent setup, log collection and SDK configuration. A lifespan hook alone is too late to rely on for complete request instrumentation.
2. **Structured logs:** `app/core/logging.py:8` and `app/core/observability.py:23` connect JSON logs and returned model token usage. Retrieval service logs result count and total latency; raw request contents and model tracing require appropriate access/retention policy.
3. **Local operational endpoints:** `/health`, `/metrics`, `/metrics/latency` (`app/api/operations.py:11,16,26`). Percentiles are nearest-rank over at most the last 1,000 successful retrievals in a single Python process (`app/core/observability.py:12`). They are not fleet-wide request percentiles, durable history or an automatically exported Datadog metric stream.
4. **LangChain and Datadog:** named Runnable invocations and local LCEL run collection support evaluation reports. Datadog APM/LLM spans, submitted RAGAS scores and feedback provide the configured telemetry view.
5. **Offline evaluation export:** `policy_answer_evaluation` workflow wraps each evaluated answer; the runner annotates and exports its span, then submits existing judge, RAGAS and status-match evaluations against it (`run.py:81,231,265`). This is offline, on-demand export, not live sampled evaluation of every UI question.
6. **Current gate:** a `--min-score` value explicitly enables quality gating; it checks RAGAS means, each judge numeric score and status agreement. RAGAS per-case regression detection is not equivalent to comparing aggregate means. No default production quality threshold is specified.

## Suggested presentation scope

Suggested title: **NexaAssist — Dev-Time Observability with Datadog**. Subtitle: **Phase 1, Week 2, Session 10 · implementation walkthrough · Phase 4 production bridge**.

Suggested 90-minute plan: 10 min recap and syllabus boundary; 20 min context/container/component architecture plus telemetry concepts; 15 min current instrumentation/code walk; 20 min Datadog UI investigation and missing-trace exercise; 15 min quality/evaluation correlation; 10 min walkthrough/Q&A and production gaps. Durations are a proposed lesson plan, not additional syllabus assignments.

Use a C4 context and container view for application/telemetry boundaries. Add one component view mapping API, service, chain and logging/evaluation code. A C4 container is a separately running application or data store; a Python module or LangChain Runnable is a component, not a container. Depict future ECS/Arize/agent layers as future scope only.

Worked investigation: submit an actual `/answer` request → select recent Live Search and service/environment → open `fastapi.request`/server span → inspect child dependency spans → correlate logs and AI context → inspect offline quality report for a reproduced case. Contrast MongoDB `hello`/`ismaster` heartbeat spans with real API request spans, and distinguish saved time-window exclusion from missing instrumentation. Label any example durations or screenshots that are not captured live.

## Implementation gaps and evidence boundaries

- No evidence in this inspection establishes deployed ECS sidecars, ALB/autoscaling, configured shared dashboards, monitors, SLOs, RUM, Arize, sampled online judges or drift alerts.
- No evidence establishes fleet-wide durable custom metrics or automatic Datadog scraping of local `/metrics` JSON.
- A MongoDB heartbeat in APM proves only that some database spans arrived; it does not establish parent FastAPI spans or a complete UI-to-API distributed trace.
- Tests can prove instrumentation behavior locally without proving searchable retention or visibility in the user's signed-in account.
- Do not claim the Phase 1 exit checkpoint is complete without a real RAGAS/judge run and trainee trace review; this mapping inspection ran neither production queries nor paid evaluations.
- Existing lesson material and `SESSION8_EVALUATION_GUIDE.md` need later correction if reused; this task created documentation only and did not modify those originals or application code.
