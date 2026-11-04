# Live implementation verification — 4 November 2026

Branch: `feat/prepayment-validator`; inspected HEAD: `de00625024197006eed228aef5dc67ee5ee51a8e`.
Application and test source were not changed. Existing untracked work was preserved.

## Scope and environment

The user requested live operations after the earlier source/offline review. Started the existing four-service Make stack on loopback: RAG 8000, Agent 8001, synthetic bank 8080, Streamlit 8501. Actual configured chat/embedding providers and MongoDB Atlas were used. Current retrieval profile is dense, with reranking disabled. No corpus ingestion, index changes, baseline changes or production banking calls were performed.

## Live HTTP and workflow results

`http.json` retains 25 passing HTTP assertions and full synthetic responses:

- Actual Atlas retrieval and a generated, cited policy answer.
- Unauthenticated run start: 403. Foreign customer: 403. Unsafe input: 422.
- Durable proposal prepared and loaded, self-approval denied (403), stale proposal hash denied (409), different-reviewer rejection recorded.
- Statement copy, callback, re-KYC reminder, interest certificate and prepayment opt-in each prepared, paused, approved by the configured separate reviewer, and submitted successfully.
- Each successful run replay returned its original receipt. Bank receipts NXSR-000001 through NXSR-000005 have status RECEIVED, which does not establish completion of the underlying operation.

`recovery.json` records a sixth synthetic bank receipt, NXSR-000006. A separate harness used the real service, model, HTTP retrieval, Atlas checkpoints and synthetic bank, injecting only the bank's documented `commit-then-timeout` fault. The first bank write returned 504; the service raised its expected RunError 503 and retained an unconfirmed run. A fresh invocation recovered that exact saved operation with the same key, body and bank identity. The bank returned 201 with `Idempotent-Replayed: true`. A further service retry returned the retained receipt without another banking POST. The first harness expected a returned unconfirmed result rather than an exception; recovery used the original run rather than creating a replacement.

`feedback.json` records one labelled synthetic feedback item: persisted successfully, replay returned the same ID, unauthenticated listing was denied (401), and authorized review accepted the item.

Synthetic runs/checkpoints were retained for inspection under their normal application retention policy. The banking mock's receipts are process-local. No reset endpoint was called.

## UI observations

A real browser rendered a policy answer and loaded an actual submitted run, including the bank receipt and policy evidence. Temporary UI credentials were cleared and the temporary credential bridge was removed. Screenshots: `ui-answer.png`, `ui-submitted.png`.

At 564 × 695, the measured document had no horizontal overflow. This is one narrow viewport, not a complete device/browser matrix.

Observed friction: the Home loan limits suggestion supplied a product-specific question while the sidebar product was blank. The API safely requested scope clarification. Entering NEXA-HL produced the cited answer ₹7.5 crore. The caption states that suggestions use sidebar scope, but the click does not populate a matching product. Relevant source: `app/ui/app.py:374-395`, request construction at line 420. Suggested minimal improvement: carry the known product with each suggestion and populate its request scope explicitly.

The submitted-run screen displays large raw validation/submission JSON blocks, repeats source material, and retains a historical validation reason saying no request was created. The top-level submitted status and acceptance-versus-completion message are correct. Relevant source: `app/ui/agent.py:158-168`. Suggested improvement: render a short receipt/status summary and label retained validation as the pre-submission snapshot; keep full JSON in optional detail panels.

### Design-system visual audit

Scores are qualitative observations from the rendered dark UI, not accessibility certification.

| Dimension | Score | Evidence / smallest improvement |
|---|---:|---|
| Color consistency | 8/10 | Consistent dark surfaces and restrained accents; retain shared theme settings. |
| Typography hierarchy | 8/10 | Clear page titles, body and captions; use readable summaries for the JSON at `app/ui/agent.py:165`. |
| Spacing rhythm | 8/10 | Consistent native form/control spacing in observed views; no change justified. |
| Component consistency | 8/10 | Shared native Streamlit inputs, buttons and expanders; no change justified. |
| Responsive behavior | 7/10 | No horizontal overflow at the measured narrow viewport; wider/mobile matrix not measured. |
| Dark mode | 8/10 | Observed surfaces and controls coherent; light mode not inspected. |
| Animation | N/A | No custom animation behavior tested. |
| Accessibility | 7/10 | Labeled controls and password masking observed; keyboard/focus/contrast audit incomplete. |
| Information density | 5/10 | Repeated raw policy JSON overwhelms the request result (`app/ui/agent.py:164-168`). |
| Polish | 6/10 | Safe errors and receipt states exist; product suggestion and historical validation wording create friction. |

No gratuitous gradients or glass effects were observed. No design-token files or redesign were generated because this task requested verification.

## Runtime / telemetry

`runtime.json` records healthy RAG, Agent and UI endpoints, 17 HTTP retrieval samples, zero retrieval errors/empty results, and a reachable local Datadog Agent 7.84.4. Observed retrieval p50 was 655.6 ms and p95/p99 4629.77 ms; this small sample is not a load benchmark. The separate batch evaluation accesses retrieval directly and is not included in those HTTP counters.

The standalone fault-recovery harness loaded application Settings but did not bootstrap the Datadog process environment, so its trace exporter attempted localhost:8126 and dropped a trace. The Make-launched services use the configured environment. Local Agent availability does not prove cloud receipt or dashboard visibility.

## Findings requiring follow-up

1. **Real-Atlas test fixture naming:** `tests/conftest.py:24` constructs a 48-byte database name. This configured Atlas cluster rejected it with a 38-byte maximum. The unchanged real-Atlas suite therefore initially failed during fixture setup. A temporary external pytest plugin shortened isolated test database names while preserving assertions and cleanup. This is an adapted harness result, not an unchanged-suite pass. A minimal future fix is a shorter unique test database identifier.
2. **Evaluation CLI telemetry initialization:** `app/evaluation/run.py:393-396` configures logging and runs evaluation without the application telemetry startup. Check the actual evaluation report's Datadog status; environment settings alone do not prove export.
3. **UI scope and density:** described above; no source fixes were applied.

## Recon and limitations

Git history remains 34 commits / 8 branches, one recorded contributor, no new tracked code changes. Prior all-history recon remains applicable; no new recon file was created. MCP is still absent, and these successful operations do not implement MCP.

No sustained load, AWS deployment, hybrid/reranker profile, exhaustive adversarial prompt benchmark or Datadog cloud-receipt verification was performed. Real financial systems were not contacted. The separate quality and real-Atlas test results are recorded alongside this report when complete.

## Final live quality result — release gate FAILED

`phase1-dense-live.json` is the fresh full ten-case provider/Atlas evaluation; `phase1-dense-summary.json` records the comparator outcome. Protocol matches the unchanged dense baseline: gpt-6-luna generation, gpt-6.1-sol judge, RAGAS 0.4.3, dense retrieval, no reranking.

All ten cases completed, with eight answerable cases scored by all four RAGAS metrics. Expected statuses matched 9/10. Case 9, “What is the current NRLR?”, returned `needs_clarification` rather than required `insufficient_evidence`. The separate judge assigned correctness 0.5 on that case. The official comparator stopped with “Golden answer statuses failed”; it did not accept the release.

| Mean | Current observation | Retained dense baseline |
|---|---:|---:|
| Faithfulness | 1.000000 | 0.982143 |
| Answer relevancy | 0.724309 | 0.710260 |
| Context precision | 0.586111 | 0.586111 |
| Context recall | 0.958333 | 0.958333 |
| Judge correctness | 0.950000 | 1.000000 |
| Judge groundedness | 1.000000 | 1.000000 |

The mean comparison is diagnostic because the official gate stopped first on the status failure. No rebaseline or repeated scoring was used to obtain a pass. One stochastic observation does not identify the root cause; investigate the NRLR answer's abstention/clarification behavior before release.

The evaluation report explicitly records `datadog.status: disabled`, confirming no scored-result export for this CLI run. The reachable local Agent is not evidence that this evaluation reached Datadog.

## Final real-Atlas persistence result

`atlas-persistence-summary.json` and `atlas-persistence-tests.xml` record **72 passed, 0 failed, 0 skipped, 248.76 seconds**, using the temporary short-database-name harness described above. A fresh-process checkpoint read executed against Atlas. Cleanup confirmed zero remaining temporary test databases. Models and banking in this persistence suite remained deterministic test boundaries; the separate HTTP checks and fault-recovery harness supplied live provider/HTTP coverage.

## Review outcome

The implemented scoped agentic workflow functions with the configured model, Atlas and synthetic bank. Approval/security/replay checks and all five submission types passed. This verification does **not** establish a release-ready build: the current live AI-quality gate failed, the unchanged Atlas test fixture needs a naming fix, and evaluation CLI telemetry was disabled. No application/test source changes were made. The localhost stack was left running for review; see `make run` for lifecycle management.
