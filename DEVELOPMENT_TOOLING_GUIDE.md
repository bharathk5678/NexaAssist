# How we use skills, hooks and MCP in NexaAssist

This guide explains the tools that helped us build and review NexaAssist,
when to use them, and how to get started.

It reflects the repository and local development setup checked on
**21 October 2026**, based on commit `2bc16cc`.

## Start with these three ideas

A **skill** gives the AI assistant a way to approach a task. For example,
Ponytail helps it make a small, complete change without adding unnecessary code.

A **hook** runs automatically when something happens. Our Git hook checks
staged files when you run `git commit`.

**MCP** lets an AI assistant connect to tools or data outside the conversation.
Some MCP tools are configured on this development machine. NexaAssist itself
does not have an MCP server yet.

The project rules live in [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md).
Read them before changing code. They explain where each kind of code belongs:
LangChain logic in `app/chains/`, database access in `app/database/`, business
logic in `app/services/`, API routes in `app/api/`, and the UI in `app/ui/`.

## What do I need to work on this repo?

Start with Git, `uv`, Python 3.14+, the project dependencies, and the pre-commit
hook described below. You also need Docker Desktop if you are using our Docker
Datadog Agent.

Live questions need your Atlas and model credentials. The offline application
tests use fake model responses and local stores, so they do not need those
services.

AI skills are helpful, but they are not required to run the application. For
most coding tasks, start with Ponytail. Add a more specific skill when the task
calls for it, such as Streamlit development or architecture documentation.

## Skills: which one should I use?

### Making a code change

**`ponytail:ponytail` — keep the solution small and complete.**

We used this approach while removing RAGAS score cards from Streamlit, adding
Datadog feedback, and setting up pre-commit. It encourages the assistant to
read the existing code, reuse what is already there, preserve error handling,
and check the result.

For example, the feedback change reused the existing
[feedback service](app/services/feedback.py). It saves feedback in MongoDB first,
then sends it to Datadog. A Datadog error does not undo the saved feedback.

You can ask the assistant:

```text
Use ponytail:ponytail for this change. Read AGENTS.md, check the callers,
make the smallest complete fix, and verify it.
```

### Understanding or reviewing the repo

| Skill | When to use it | What it helps you do |
| --- | --- | --- |
| `codebase-recon` | Before a broad repo review | Read Git history to find files that change often and areas worth inspecting |
| `ponytail:ponytail-audit` | When reviewing the whole codebase | Find bugs, risky failure paths, slow code and code we can remove |
| `ponytail:ponytail-review` | Before committing a particular change | Check the change, its callers, its contracts and its tests |
| `ponytail:ponytail-gain` | When learning about the plugin's claimed benefits | Read its author's benchmark; these figures are not measurements of NexaAssist |

These skills were requested during the earlier repository review. The
[component guide](APP_COMPONENT_GUIDE.md) records the recon findings and audit
fixes. An audit reports findings; applying a fix is a separate coding task.

Example request:

```text
Use codebase-recon to understand the repo, then ponytail:ponytail-review
for the feedback changes. Explain the findings before changing code.
```

### Working on the Streamlit UI

Use **`developing-with-streamlit`** when changing the chat UI. It helps the
assistant find documentation for the installed Streamlit version and work
correctly with forms, cached clients and chat state.

We used it for [the chat UI](app/ui/app.py). The
[UI tests](tests/test_ui.py) use Streamlit AppTest to check interactions and
make sure feedback stays attached to the right answer.

```text
Use developing-with-streamlit for this UI change. Keep business logic out
of the UI, keep RAGAS scores in Datadog, and test the chat interactions.
```

**`debugging-streamlit`** is also available for interactive troubleshooting.
Check its requirements first: this repo does not currently have a `make debug`
target. AppTest is our existing automated UI check.

### Explaining the architecture

The **`c4-architecture`** and **`c4-architecture-c4-architecture`** skills were
requested for the architecture and training work. They help explain the system,
its running processes, its components, and how a question moves through them.
See the diagrams in [README.md](README.md).

A related skill, **`c4-codebase-architecture`**, is installed locally in
`.agents/skills/` and recorded in `skills-lock.json`. Use it to build architecture
docs from entrypoints, routes, services and deployment files. Choose one C4
workflow that fits the task; you do not need to run all three.

### Preparing charts or training material

**`data-analytics:visualize-data`** was requested during the wider validation
work. Use it when turning evaluation or latency results into charts. Base the
chart on actual results, and keep “not scored” separate from a score of zero.
The [evaluation runner](app/evaluation/run.py) is one place to start looking
for the underlying data.

**`ppt-master`** is available for creating or revising a training presentation.
Use it to connect the syllabus, code examples and slide content. It is not
needed to run NexaAssist.

These requests and available tools do not establish that a particular chart
or finished presentation was produced with them.

### How do I enable a skill?

Select the installed skill in your AI client, or name it in your request as
shown above. These examples are messages to the assistant, not shell commands.
The client must have access to the skill's `SKILL.md`; naming a missing skill
does not install it.

Most of our skills are installed in the developer's user-level plugin folders.
They do not come with a normal `git clone`. The local `skills-lock.json` lists
only `c4-codebase-architecture`, from
`lmammino/c4-codebase-architecture-skill`.

At the time of this check, `.agents/`, `skills-lock.json` and
`C4-Documentation/` were untracked. Review what should be shared before
committing them. Keep private client settings and plugin caches out of Git.

## Git hooks: checks before a commit

Our pre-commit setup catches common mistakes before they enter Git history.
The shared settings are in [.pre-commit-config.yaml](.pre-commit-config.yaml).

| Check | What it looks for |
| --- | --- |
| `check-yaml` | Invalid YAML, such as a broken Compose file |
| `check-toml` | Invalid TOML in project or Streamlit settings |
| `check-merge-conflict` | Merge-conflict markers left in a file |
| `detect-private-key` | Recognizable private keys accidentally added to a file |
| `ruff-check` | Python lint errors |
| `ruff-format` | Python code that needs formatting |

The hook is installed on this machine. For a new clone, run these commands
from the repo root:

```bash
uv sync --locked --extra ui --extra evaluation
uv run --locked --no-sync pre-commit install --install-hooks
uv run --locked --no-sync pre-commit validate-config
uv run --locked --no-sync pre-commit run --all-files
```

After that, `git commit` runs the checks on matching staged files. If no staged
file matches a check, it shows `Skipped`. For example, Ruff normally skips a
commit containing only Markdown files.

The Ruff hooks use the version in [uv.lock](uv.lock) and respect the exclusions
in [pyproject.toml](pyproject.toml), including notebooks and synthetic-data code.
They report problems without changing your files. To fix formatting and check
again:

```bash
uv run --no-sync ruff format app tests
uv run --locked --no-sync pre-commit run --all-files
```

Stage any fixes before retrying the commit. When sharing the hook setup,
remember to include the configuration file itself:

```bash
git add .pre-commit-config.yaml pyproject.toml uv.lock README.md
```

Keep `uv` on your PATH when committing. The first hook setup needs network
access. Private-key detection does not catch every API token, so keep `.env`
untracked and review what you stage.

pytest and mypy remain separate checks. We have not configured a pre-push test
hook or a CI workflow through this setup. More details are in the
[pre-commit documentation](https://pre-commit.com/).

## Assistant hooks: keeping Ponytail active

Ponytail also has hooks inside the coding assistant. They help maintain its
working style throughout a session.

| Event | What the hook does |
| --- | --- |
| `SessionStart` | Loads Ponytail when a session starts or resumes |
| `UserPromptSubmit` | Tracks requests to change the Ponytail mode |
| `SubagentStart` | Passes Ponytail instructions to a subagent, if one is started |

The local Ponytail 5.3.2 plugin defines these in
`hooks/claude-codex-hooks.json`, and the Codex settings record their state.
Ponytail full mode was active during the recent development work.

In a supporting assistant client, use `/ponytail full`, `/ponytail lite`,
`/ponytail ultra` or `/ponytail off`. The plugin and client need to support
these commands. These hooks do not run the Git checks or become part of the
NexaAssist application.

## MCP: what is available today?

MCP gives an AI client a standard way to call external tools. You can read the
[official introduction](https://modelcontextprotocol.io/docs/getting-started/intro)
for the protocol itself.

For this project, it helps to ask two separate questions: “Can my coding
assistant use an MCP tool?” and “Does NexaAssist expose an MCP server?”

### Tools on the development machine

**`node_repl`** is listed in the local Codex configuration, and Node REPL tools
are available in this assistant session. They can help with JavaScript-based
development tasks and supported artifact tools.

**`cua_repl`** is also listed locally. It can support computer or UI automation,
but a working connection was not tested for this guide.

These entries show what is configured. They do not tell us which tool created
a particular file in the repo.

### Saving context between coding sessions

The project instructions ask for **context0** to carry context between AI tools.
The intended workflow is to call `get_context` when starting a session and
`save_context` when the user asks to save or hand off the work.

A useful handoff includes what changed, what remains, blockers, tests, changed
files, and the current repo, branch and commit.

Context0 was not found in the inspected MCP settings, and its tools were not
available in this session. The instructions alone do not connect it. Until it
is configured, leave a clear handoff summary through the tools you have.

### An MCP server for NexaAssist

FastMCP is still a planned layer. There is no `app/mcp/` directory or declared
FastMCP dependency yet. We have not added MCP discovery, Inspector checks or
MCP contract tests.

Today, Streamlit calls FastAPI over HTTP. MongoDB, model providers and Datadog
use their existing SDK integrations. Those connections are not implemented
through MCP.

If you need a development MCP server, configure it in your AI client, reload
the client, confirm its tools appear, and try a small read-only request. Server
installation and credentials depend on the tool; this guide does not install
or connect them.

## What about the hooks inside the application?

The application also has startup work and callbacks that help us understand
what happened during a request:

- [FastAPI startup](app/main.py) sets up telemetry and JSON logging, then warms
  the tokenizer.
- [Datadog setup](app/core/telemetry.py) patches supported integrations when
  enabled. We launch with `ddtrace-run` so instrumentation starts early.
- [TokenUsageLogger](app/core/observability.py), attached in the
  [model factory](app/chains/llm.py), logs token usage when a model call ends.
- The [live evaluation service](app/services/evaluation.py) uses a Datadog
  workflow and RAGAS scores to help inspect answer quality.
- The [feedback service](app/services/feedback.py) connects a saved human rating
  and optional correction to the matching answer span in Datadog.

These run with the application. RAGAS scores stay in Datadog; Streamlit shows
the answer, citations, evaluation link and feedback form. A queued Datadog
submission does not confirm cloud receipt. See [DATADOG_README.md](DATADOG_README.md)
for setup and troubleshooting.

## A simple routine for your next change

1. Read `AGENTS.md` and the code you want to change.
2. Choose the skill that fits. Start with Ponytail; add Streamlit or C4 guidance
   when needed.
3. Make the change in the right layer and add a focused test where it matters.
4. Review the change and run the checks below.
5. Check `git diff`, stage only the intended files, and commit.
6. When handing off the work, save context if the tool is connected, or write
   a clear summary of what is done and what comes next.

For the normal offline checks:

```bash
RAGAS_DO_NOT_TRACK=true \
DD_TRACE_ENABLED=false DD_LLMOBS_ENABLED=false \
uv run --locked --no-sync pytest tests/ -q
uv run --locked --no-sync mypy .
uv run --locked --no-sync pre-commit run --all-files
```

The separate synthetic banking API suite needs `openapi-spec-validator`, which
is not in the current dev dependencies. Running `pytest tests/` does not run
that separate suite.

This guide is based on the repo files, local tool settings, and the earlier
review notes in [APP_COMPONENT_GUIDE.md](APP_COMPONENT_GUIDE.md). It does not
check live Atlas, model-provider or Datadog health. No MCP server, skill or
runtime setting was installed or changed while writing it.
