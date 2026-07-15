# AITesting

Experiments in AI-assisted software testing using [CrewAI](https://github.com/crewAIInc/crewAI).
The crews use a Groq-hosted `gpt-oss-120b` model to perform QA tasks:

- **Test Analyst** – reads a feature description and generates test cases.
- **Bug Triage Crew** – pulls a bug from Jira and runs a multi-agent pipeline
  that classifies it, finds the likely root cause, and recommends tests.
- **Research & Writer Crew** – researches common web-app bug categories, then
  writes a developer bug-prevention checklist.

## Project structure

```
AITesting/
├── .gitignore
├── README.md
└── crewAI/
    └── MCP_Creation/
        ├── Test_Analyst_Agent.py         # Single-agent: generates test cases
        ├── Building_QABugTriageCrew.py    # Multi-agent: bug triage + RCA + tests
        ├── Research_Write_AI_Agent.py      # Two-agent: research + prevention checklist
        └── .env                           # API keys / secrets (not committed)
```

## Requirements

- Python 3.13
- A [Groq](https://console.groq.com) API key
- (Bug Triage only) A Jira account with an API token

## Setup

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install "crewai" python-dotenv requests
   ```

2. Add your keys to `crewAI/MCP_Creation/.env`:

   ```
   GROQ_KEY=your_groq_api_key_here

   # Required only for Building_QABugTriageCrew.py
   JIRA_EMAIL=you@example.com
   JIRA_API_TOKEN=your_jira_api_token
   ```

   This file is git-ignored and must never be committed.

## Running

### Test Analyst — generate test cases

```bash
cd crewAI/MCP_Creation
python3 01_Test_Analyst_Agent.py
```

Prints a numbered list of test cases to the terminal. To keep a copy:

```bash
python3 01_Test_Analyst_Agent.py > test_cases.md
```

To test a different feature, edit the `description` and `expected_output` of
`test_case_task`.

### Bug Triage Crew — classify, RCA, recommend tests

```bash
cd crewAI/MCP_Creation
python3 03_Building_QABugTriageCrew.py
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
python3 02_Research_Write_AI_Agent.py
```

Runs two agents in sequence:

1. **QA Research Analyst** – lists the top 5 common web-app bug categories with
   frequency, example, and impact for each.
2. **QA Documentation Writer** – turns that research into a practical
   "Bug Prevention Checklist" developers can review before opening a pull
   request.

Only needs `GROQ_KEY` — no Jira access required.

## How it works

Both scripts follow the same minimal CrewAI shape: define an **LLM**, one or more
**Agents** (personas), **Tasks** (what to produce), and a **Crew** that runs them
via `crew.kickoff()`. The Bug Triage crew adds a sequential `Process` and chains
task context so agents collaborate.

## Note on the cache-breakpoint workaround

Groq's OpenAI-compatible API rejects the `cache_breakpoint` marker CrewAI attaches
to chat messages, and the installed CrewAI version only strips it for native
providers — not for the generic path Groq uses. Both scripts work around this:

- `Test_Analyst_Agent.py` monkey-patches `LLM._format_messages_for_provider`.
- `Building_QABugTriageCrew.py` and `Research_Write_AI_Agent.py` subclass `LLM`
  as `GroqLLM` and strip the marker in `call()`.

If a newer CrewAI release handles this, the workaround can be removed.

## Configuration notes

- Secrets live in `.env` files and are loaded with `python-dotenv`. A bare
  `.env` line in `.gitignore` ignores `.env` files in every subfolder, so each
  new agent folder can keep its own `.env` without extra rules.
- `.venv/`, `.idea/`, and Python caches are git-ignored.