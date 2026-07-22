# AITesting

Experiments in AI-assisted software testing using [CrewAI](https://github.com/crewAIInc/crewAI),
with Groq-hosted models doing the QA work:

- **Test Analyst** – reads a feature description and generates test cases.
- **Bug Triage Crew** – pulls a bug from Jira and runs a multi-agent pipeline
  that classifies it, finds the likely root cause, and recommends tests.
- **Research & Writer Crew** – researches common web-app bug categories, then
  writes a developer bug-prevention checklist.
- **QA Pipeline** – fetches a Jira ticket over MCP and generates a full test
  plan, detailed test cases, and Playwright automation scripts.
- **Production QA Pipeline** – the QA Pipeline's successor: same Jira MCP
  fetch, plus a Jira-importable CSV of the test cases and Playwright code
  scaffolded straight into an Advanced Playwright Framework layout (Page
  Object Model + Module pattern). Drivable from the CLI or a Streamlit UI.

The first three use `gpt-oss-120b`. The QA Pipeline and Production QA
Pipeline use `llama-3.3-70b-versatile` — see [Model choice](#model-choice).

There's also `DeepEval/Excercises/`, a separate set of
[DeepEval](https://github.com/confident-ai/deepeval) pytest exercises for
LLM-output evaluation (answer relevancy, hallucination) — unrelated to the
CrewAI pipelines above. See [DeepEval exercises](#deepeval-exercises).

## Project structure

```
AITesting/
├── .env                                    # API keys / secrets (not committed)
├── .gitignore
├── README.md
├── pyproject.toml                          # Dependencies
├── uv.lock                                 # Pinned versions (committed)
├── DeepEval/
│   └── Excercises/
│       ├── test_01_Basic_Anwser_Relevancy.py         # AnswerRelevancy + Hallucination basics
│       └── test_02_Groq_Llama4_vs_Openrouter_Judge.py # Groq-answered, OpenRouter-judged test case
└── crewAI/
    ├── MCP_Creation/
    │   ├── 01_Test_Analyst_Agent.py        # Single-agent: generates test cases
    │   ├── 02_Research_Write_AI_Agent.py   # Two-agent: research + prevention checklist
    │   └── 03_Building_QABugTriageCrew.py  # Multi-agent: bug triage + RCA + tests
    ├── CrewAI_QA_Pipeline/
    │   ├── main.py                         # Entry point
    │   ├── crew.py                         # 4-agent crew + Jira MCP wiring
    │   └── output/                         # Generated artifacts (not committed)
    └── CrewAI_production_QA_Pipeline/
        ├── main.py                         # Entry point
        ├── crew.py                         # 4-agent crew + Jira MCP wiring + CSV/Playwright scaffolding
        ├── ui/
        │   └── app.py                      # Streamlit UI for this pipeline
        ├── docs/ARCHITECTURE.html          # Advanced Playwright Framework layer reference
        ├── templates/
        │   ├── testplan.md                 # 12-section test plan template
        │   ├── jira_test_cases_header.csv  # Header row for the Jira-import CSV
        │   └── playwright-framework/       # Framework boilerplate copied into every run's output
        └── output/                         # Generated artifacts, one folder per ticket (not committed)
```

A single `.env` at the repo root serves every script. `load_dotenv()` walks up
from each script's own directory, so both `MCP_Creation/` and
`CrewAI_QA_Pipeline/` find it without any path juggling.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- A [Groq](https://console.groq.com) API key
- (Bug Triage and QA Pipeline only) A Jira account with an API token

## Setup

1. Install dependencies. `uv sync` creates `.venv` and installs the exact
   versions pinned in `uv.lock`:

   ```bash
   uv sync
   ```

2. Add your keys to `.env` in the repo root:

   ```
   GROQ_KEY=your_groq_api_key_here

   # Required for 03_Building_QABugTriageCrew.py and the QA Pipeline
   JIRA_EMAIL=you@example.com
   JIRA_API_TOKEN=your_jira_api_token

   # QA Pipeline only
   JIRA_URL=https://your-workspace.atlassian.net

   # DeepEval exercises only — judges the LLM output on OpenRouter
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

   This file is git-ignored and must never be committed.

## Running

### Test Analyst — generate test cases

```bash
cd crewAI/MCP_Creation
uv run 01_Test_Analyst_Agent.py
```

Prints a numbered list of test cases to the terminal. To keep a copy:

```bash
uv run 01_Test_Analyst_Agent.py > test_cases.md
```

To test a different feature, edit the `description` and `expected_output` of
`test_case_task`.

### Bug Triage Crew — classify, RCA, recommend tests

```bash
cd crewAI/MCP_Creation
uv run 03_Building_QABugTriageCrew.py
```

The crew fetches a Jira ticket (the ID is set in the `fetch_jira_ticket(...)`
call near the bottom of the file) and runs three specialists in sequence:

1. **Bug Triage Analyst** – assigns severity (P0–P4), category, component, and
   sprint priority.
2. **Root Cause Analysis Specialist** – traces the issue through the UI → API →
   Service → Database layers and suggests where to investigate.
3. **Test Strategy Advisor** – recommends verification, regression, and edge-case
   tests (Playwright/TypeScript style).

Each task passes its output as context to the next via `context=[...]`, so later
agents build on earlier findings.

### Research & Writer Crew — bug-prevention checklist

```bash
cd crewAI/MCP_Creation
uv run 02_Research_Write_AI_Agent.py
```

Runs two agents in sequence:

1. **QA Research Analyst** – lists the top 5 common web-app bug categories with
   frequency, example, and impact for each.
2. **QA Documentation Writer** – turns that research into a practical
   "Bug Prevention Checklist" developers can review before opening a pull
   request.

Only needs `GROQ_KEY` — no Jira access required.

### QA Pipeline — test plan, test cases, Playwright scripts

```bash
cd crewAI/CrewAI_QA_Pipeline
uv run main.py AIT-2
```

The ticket ID is a command-line argument (defaults to `AIT-2`). Unlike the
Bug Triage crew, which calls the Jira REST API directly with `requests`, this
one talks to Jira through the [mcp-atlassian](https://github.com/sooperset/mcp-atlassian)
MCP server, launched as a subprocess over STDIO via `uvx`. The first run
downloads that server, so it takes a little longer.

Four agents run in sequence:

1. **Jira Analyst** – fetches the ticket via MCP tools and extracts testable
   requirements, acceptance criteria, edge cases, and risks.
2. **Test Plan Writer** – produces a 12-section ISTQB-style test plan.
3. **Test Case Writer** – writes 12–15 detailed cases covering positive,
   negative, edge, UI, and API scenarios.
4. **Playwright Coder** – generates TypeScript automation scripts.

Results are written to `output/` (`test_plan.md`, `test_cases.md`,
`playwright_tests.md`) and are git-ignored, since every run regenerates them.

The MCP server exposes ~58 Jira tools, but every tool schema is added to the
system prompt and eats the token budget. `crew.py` filters down to
`jira_get_issue` and `jira_search`, which is all Agent 1 needs.

### Production QA Pipeline — test plan, Jira-import CSV, Playwright framework

```bash
cd crewAI/CrewAI_production_QA_Pipeline
uv run main.py AIT-2
```

Same four-agent shape as the QA Pipeline (Jira Analyst → Test Plan Writer →
Test Case Writer → Playwright Coder), with three differences in what it
produces per ticket, all written to `output/<ticket_id>/`:

- `test_cases_jira.csv` – the test cases table converted to a CSV that
  imports straight into Jira, using `templates/jira_test_cases_header.csv`
  for the header row.
- `advanced-playwright-framework/` – `templates/playwright-framework/` is
  copied in as the scaffold (config, tsconfig, shared utils already in
  place), and the Playwright Coder agent fills in `src/pages/`,
  `src/modules/`, `src/tests/`, `src/api/`, and `src/fixtures/` per the
  layer rules in `docs/ARCHITECTURE.html` — Page classes hold locators only,
  Modules hold business logic on top of Pages, specs import `test`/`expect`
  from the single `src/fixtures/index.ts`.
- A per-ticket output folder rather than one shared `output/`, since the
  Streamlit UI below can run several tickets in one session.

Tasks don't use CrewAI's `output_file` (its path validator silently rewrites
absolute paths to be CWD-relative); `run_crew()` writes every artifact
itself from each task's raw output instead.

#### Streamlit UI

```bash
uv run streamlit run crewAI/CrewAI_production_QA_Pipeline/ui/app.py
```

Enter one or more Jira ticket IDs (comma- or newline-separated) and the app
runs the pipeline above once per ticket, then shows the output tree, previews
the test plan and test cases, renders the CSV as a table, lists the generated
Playwright files, and offers a download button for each artifact plus a zip
of the whole per-ticket folder. The UI holds no pipeline logic itself — it
only calls `crew.run_crew()` and displays what comes back.

## DeepEval exercises

```bash
uv run pytest DeepEval/Excercises/
```

Two standalone pytest exercises using [DeepEval](https://github.com/confident-ai/deepeval)
to evaluate LLM output — separate from the CrewAI pipelines above, and not
using CrewAI at all:

- **`test_01_Basic_Anwser_Relevancy.py`** – the fundamentals: an
  `LLMTestCase` with a hardcoded input/output, scored against
  `AnswerRelevancyMetric` and `HallucinationMetric`.
- **`test_02_Groq_Llama4_vs_Openrouter_Judge.py`** – asks a real question of
  a Groq-hosted model, then scores the answer with the same two metrics.

Both need `GROQ_KEY` (or `GROQ_API_KEY`) and `OPENROUTER_API_KEY` in `.env`.
The judge model is built explicitly as an `OpenRouterModel(...)` instance and
passed to each metric via `model=`, rather than passing a plain model-name
string — DeepEval's provider auto-routing reads its settings from the
environment once, at the moment the `deepeval` pytest plugin is imported
(before any test file runs), so an env var set inside the test file itself
is always too late to affect that routing. Passing an explicit model
instance sidesteps that entirely and works regardless of which env vars
happen to be set at process start.

`deepeval` is capped below 4.x in `pyproject.toml` — see
[Dependency notes](#dependency-notes).

## How it works

Every script follows the same minimal CrewAI shape: define an **LLM**, one or more
**Agents** (personas), **Tasks** (what to produce), and a **Crew** that runs them
via `crew.kickoff()`. The Bug Triage crew adds a sequential `Process` and chains
task context so agents collaborate. The QA Pipeline goes one step further and
injects MCP tools into its first agent, letting it fetch from Jira itself rather
than being handed the ticket.

## Groq workarounds

CrewAI targets OpenAI's API closely enough that two things break on Groq's
OpenAI-compatible endpoint. Both are worked around in the scripts, and both can
go if a newer CrewAI release handles them.

**1. The `cache_breakpoint` marker.** Groq rejects the marker CrewAI attaches to
chat messages, and the installed CrewAI version only strips it for native
providers — not the generic path Groq uses.

- `01_Test_Analyst_Agent.py` monkey-patches `LLM._format_messages_for_provider`.
- `02_Research_Write_AI_Agent.py`, `03_Building_QABugTriageCrew.py`, and the QA
  Pipeline subclass `LLM` as `GroqLLM` and strip the marker in `call()`.

**2. Strict-mode tool schemas** (QA Pipeline only, and only because it uses
tools). CrewAI forces *every* parameter into a schema's `required` array and
sets `strict: True`. OpenAI honours that by constraining decoding, so a model
physically cannot omit an optional argument. Groq doesn't constrain decoding —
it validates the tool call after the fact and rejects it for omitting
parameters that have defaults, so every Jira call fails with
`tool_use_failed`. `GroqLLM.call()` drops `strict` and rebuilds `required` from
the parameters that genuinely lack a default.

## Model choice

The QA Pipeline uses `llama-3.3-70b-versatile` rather than `gpt-oss-120b`. On
Groq's free tier `gpt-oss-120b` caps at 8000 tokens per minute, and four
sequential tasks accumulating context blow past it partway through. The pipeline
dies with a rate-limit error after task 1. `llama-3.3-70b-versatile` sits at
30k TPM on the same tier, which comfortably fits the whole crew. Swap back if
you upgrade tiers.

## Dependency notes

Two entries in `pyproject.toml` aren't obvious from reading the imports, and
removing them breaks things in confusing ways:

- **`crewai[litellm]`** — CrewAI calls `litellm.completion()` at runtime, but
  `litellm` is an *optional* extra and the import is lazy. A bare `crewai`
  install therefore looks fine until an agent actually makes an LLM call.
- **`fastapi`** — nothing imports it directly. LiteLLM reaches into its proxy
  module whenever MCP tools are attached to a completion, and that import chain
  needs it.

Also note that `crewai-tools` wraps its `mcp`, `mcp.types`, and `mcpadapt`
imports in one `try/except ImportError`, so a missing `mcpadapt` reports
*"You are missing the 'mcp' package"* even when `mcp` is installed fine. The
`[mcp]` extra pulls in `mcpadapt`.

- **`deepeval`** — capped below 4.x. `deepeval>=4.1.3` needs
  `posthog>=7.0.0`, but `crewai`'s `chromadb` pin (`<1.2`) needs
  `posthog<6.0.0`, so newer `deepeval` can't resolve alongside `crewai` in
  this project. `3.9.6` works fine for the [DeepEval exercises](#deepeval-exercises),
  just slower on some calls than 4.1.3 was.

## Configuration notes

- Secrets live in a single root `.env` loaded with `python-dotenv`. A bare
  `.env` line in `.gitignore` ignores `.env` files at every level, so a
  per-folder `.env` still works if a script ever needs its own keys — it just
  takes precedence, since `load_dotenv()` stops at the first match walking up.
- `.venv/`, `.idea/`, Python caches, and generated `output/` are git-ignored.
- `uv.lock` **is** committed — it pins the whole dependency tree so a fresh
  clone gets a known-working environment.