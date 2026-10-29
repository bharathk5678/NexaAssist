# Source evidence for the NexaAssist architecture

Open [the animated architecture](nexaassist.html) in a browser. Choose **Live**
to animate the configured relationships and **Still** to pause. Select a node
to see its source paths, line ranges and incoming/outgoing relationships. Use
**Route** to follow a directed path, **+** to reveal more detail, and **?** for
keyboard shortcuts. The explanation cards and node index sit below the diagram.

The overview covers the chat/API answer path, scoped retrieval and citations,
live RAGAS scoring, saved feedback and review, policy ingestion, batch evaluation,
and the Docker Agent connection to Datadog. Shared modules are labelled explicitly.

Automated artifact and desktop browser checks passed. Light and dark captures
were inspected; Live motion and the RAG component's source passport were also
checked in an isolated browser. Some secondary routes cross in the full overview;
select a component or use Route to isolate a relationship. The final receipts and
captures are in [review-4](review-4/nexaassist.visual-check.html).

This diagram describes the latest working files after the telemetry cleanup.
The main project history was not changed. An isolated local Git repository in
`source-snapshot/` pins only source/configuration templates for Archify validation.
It contains no real `.env`, credentials, PDFs, installed packages or trace results.
The diagram uses local-only source links; its snapshot commit is not a published
GitHub commit.

Project base commit: `2bc16cc634cca62e6153db65833235420ae66305`.

Local source snapshot: `d455ffd5b1e73bf76fac16a6bb11df9538858267`.

The architecture components represent local processes, shared Python modules,
external services and file inputs. Shared modules are not independent servers.
Motion illustrates configured relationships, not live traffic or measured latency.
No live policy, model or telemetry requests are needed to generate the diagram.

Working-tree changes present when the snapshot was taken:

```text
 M .env.example
 M AGENTS.md
 M APP_COMPONENT_GUIDE.md
 M CLAUDE.md
 M DATADOG_README.md
 M README.md
 M app/api/feedback.py
 M app/chains/answer.py
 M app/chains/context.py
 M app/chains/prompts/answer.py
 M app/chains/prompts/judge.py
 M app/chains/retrieval.py
 M app/core/config.py
 M app/core/observability.py
 M app/database/feedback.py
 M app/database/indexes.md
 M app/database/retrieval.py
 M app/evaluation/answer_evaluation.py
 M app/evaluation/live.py
 M app/evaluation/rag_failure_examples.py
 M app/evaluation/run.py
 M app/models/answer.py
 M app/models/feedback.py
 M app/models/retrieval.py
 M app/services/answer.py
 M app/services/evaluation.py
 M app/services/feedback.py
 M app/services/retrieval.py
 M app/ui/app.py
 M evaluation/datasets/answer.jsonl
 M nexa_synthetic_data/golden_qa/golden_qa.json
 M nexa_synthetic_data/golden_qa/golden_qa.jsonl
 M requirements.txt
 M tests/test_answer.py
 M tests/test_evaluation.py
 M tests/test_feedback.py
 M tests/test_hybrid_rerank.py
 M tests/test_retrieval.py
 M tests/test_telemetry.py
 M tests/test_ui.py
?? .agents/
?? .planning/
?? .streamlit/
?? "1. Phase1_Enterprise_RAG_Agentic-AI_MCP_Evaluations_Full_Syllabus-.pdf"
?? C4-Documentation/
?? DEVELOPMENT_TOOLING_GUIDE.md
?? FIX_REPORT.md
?? app/api/auth.py
?? app/evaluation/results/
?? nexa_synthetic_data/README.md
?? nexa_synthetic_data/_clause_registry.json
?? nexa_synthetic_data/build_all.sh
?? nexa_synthetic_data/policies/NexaDrive_Auto_Loan_Training_Companion.pdf
?? nexa_synthetic_data/policies/NexaFlex_Personal_Loan_Training_Companion.pdf
?? nexa_synthetic_data/policies/NexaHome_Loan_Training_Companion_2026.pdf
?? nexa_synthetic_data/uploads/
?? notebooks/
?? skills-lock.json
?? tests/test_amendments.py
?? tests/test_architecture_document.py
```
