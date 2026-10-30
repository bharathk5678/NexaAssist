# Architecture explorer validation

Validated on **21 October 2026**, against the current working tree. This records
checks of [the architecture artifact](nexaassist-architecture.html), separately
from the application's saved functional test results.

| Check | Observed result |
|---|---|
| Diagram data and code links | 28 catalog entries; all mapped source files exist; node, edge and walkthrough references resolve |
| Four views | Context: 7 nodes; containers: 8; API components: 11; ingestion: 10. Browser geometry checks found no overflowing node text or labels overlapping boxes |
| Walkthroughs | 27 steps across the four views; each references existing relationships and a visible component |
| Playback | Moving markers and animated arrows appear on Play; the timer advances the step; Pause removes markers and pauses arrow motion |
| Navigation | Next, Previous, numbered steps, Restart and first/last-step boundaries work; view switching resets and pauses the walkthrough |
| Details and keyboard | Selecting a node updates its purpose and code links. Tab followed by Space selects the next component |
| Mobile | At 390 × 844, page width stays at 390; the diagram scrolls within its panel and details stack below it |
| Reduced motion | In a separate Chrome process with `--force-prefers-reduced-motion`, the media query matches, startup is paused, Play creates no moving markers/CSS animation, and manual navigation works |
| Accessibility | Desktop and mobile Lighthouse snapshots scored 100; the visible-label/accessibility-name check also passed after adding spacing between SVG text elements |
| Best practices | Desktop and mobile Lighthouse snapshots scored 100 |
| Console and network | No page console errors, warnings or issues; the standalone page made no external resource requests |
| Source checks | JavaScript syntax check, Ruff lint/format, the artifact pytest and `git diff --check` passed |
| Telemetry cleanup | Application-owned tracing imports/decorators and connection settings were removed; all 125 application tests passed, including Datadog workflow, prompt and evaluation checks; mypy passed for 56 application files |

The browser checks used an isolated headless Chrome profile, with no signed-in
sessions. Node interaction used native browser input; page JavaScript inspection
was read-only. The preview is a paused container walkthrough at the Docker Agent
step. The HTML starts with an overview and waits for user input.

Executed checks:

```sh
.venv/bin/ruff check tests/test_architecture_document.py
.venv/bin/ruff format --check tests/test_architecture_document.py
.venv/bin/pytest tests/test_architecture_document.py -q
git diff --check
```

The inline JavaScript was also extracted to a temporary file and checked with
`node --check`. The artifact pytest passed **1 test**, included in the full
**125-test** application run after the telemetry cleanup. Earlier functional
and live-scenario evidence remains in the
[application fix report](../app/evaluation/results/fixes_20261021/FIX_REPORT.md).

Lighthouse's local-file audits flag unavailable `robots.txt` and `llms.txt`.
Those website discovery files do not apply to this portable offline document.
Automated accessibility scores are not a full manual accessibility certification.

No live API, Atlas, OpenAI or Datadog request was sent. The animation illustrates
implemented relationships and does not prove running-service health, telemetry
receipt or production readiness. Safari and Firefox were not tested.
