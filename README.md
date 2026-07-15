# AITesting

Experiments in AI-assisted software testing using [CrewAI](https://github.com/crewAIInc/crewAI).
The first agent is a **QA Engineer** that reads a feature description and generates
a set of test cases for it.

## Project structure

```
AITesting/
├── .gitignore
├── README.md
└── crewAI/
    └── MCP_Creation/
        ├── Test_Analyst_Agent.py   # QA test-case generation crew
        └── .env                    # API keys (not committed)
```

## Requirements

- Python 3.13
- A [Groq](https://console.groq.com) API key

## Setup

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install "crewai" python-dotenv
   ```

2. Add your API key to `crewAI/MCP_Creation/.env`:

   ```
   GROQ_KEY=your_groq_api_key_here
   ```

   This file is git-ignored and must never be committed.

## Running

```bash
cd crewAI/MCP_Creation
python3 Test_Analyst_Agent.py
```

The crew runs the QA Engineer agent and prints a numbered list of test cases
to the terminal. To keep a copy, redirect the output to a file:

```bash
python3 Test_Analyst_Agent.py > test_cases.md
```

## How it works

`Test_Analyst_Agent.py` wires up a minimal CrewAI pipeline:

1. **LLM** – a Groq-hosted `openai/gpt-oss-120b` model, keyed from `GROQ_KEY`.
2. **Agent** – a senior QA Engineer persona.
3. **Task** – "create 5–10 test cases", with the target feature described in
   `expected_output` (currently the app.vwo.com login page).
4. **Crew** – runs the agent against the task via `crew.kickoff()`.

To test a different feature, edit the `description` and `expected_output` of
`test_case_task`.

## Note on the cache-breakpoint shim

The script monkey-patches `LLM._format_messages_for_provider` to strip CrewAI's
`cache_breakpoint` marker before requests reach Groq. Groq's OpenAI-compatible
API rejects that marker, and the installed CrewAI version (1.15.2) only strips
it for native providers, not for the generic litellm path Groq uses. If a newer
CrewAI release handles this, the shim can be removed.

## Configuration notes

- Secrets live in `.env` files and are loaded with `python-dotenv`. A bare
  `.env` line in `.gitignore` ignores `.env` files in every subfolder, so each
  new agent folder can keep its own `.env` without extra rules.
- `.venv/`, `.idea/`, and Python caches are git-ignored.