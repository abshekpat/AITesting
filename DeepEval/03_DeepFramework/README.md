# 03 · DeepEval Framework (Subsystem C)

An LLM-as-judge evaluation harness that scores **three** apps under test with
[DeepEval](https://github.com/confident-ai/deepeval) — on relevancy, faithfulness,
hallucination, correctness, bias, toxicity and PII leakage. One metric registry
drives **two surfaces**: a `pytest` / `deepeval test run` suite for CI, and an
interactive web **dashboard** for teaching and demos.

## Apps under test

| # | Subsystem | What it is | Reached at |
|---|-----------|------------|------------|
| A | **ShopSphere Chatbot** | local React + FastAPI + Groq support bot | `http://localhost:8201/chat` |
| B | **RAG Explorer** | Ollama-embed + ChromaDB + Groq retrieval pipeline | `http://localhost:8202/api/chat` |
| BB | **BrowserBash (live)** | the live black-box bot on `aleeup.com` (DeepSeek server-side) | `https://aleeup.com/api/bots/<id>/chat` |

The judge LLM is separate from every app under test — that separation is the
whole point of LLM-as-judge.

## Switchable judge LLMs

Set `JUDGE_PROVIDER` to one of:

- **`openai`** → `OPENAI_API_KEY`, default `gpt-4o-mini` (override with `JUDGE_MODEL_OPENAI`, e.g. `gpt-5-mini`)
- **`groq`** → `GROQ_API_KEY`, default `openai/gpt-oss-120b` (override with `JUDGE_MODEL_GROQ`)
- **`ollama`** → local Ollama at `http://localhost:11434/v1`, default `gpt-oss:20b` (override with `JUDGE_MODEL_OLLAMA`)
- **`openrouter`** → `OPENROUTER_API_KEY`, default `openai/gpt-4o-mini` (override with `JUDGE_MODEL_OPENROUTER`) — useful as a fallback judge when your OpenAI/Groq quota is exhausted, since it draws from a separate account/billing pool

One `CompatibleJudge` class works for all four (OpenAI-compatible wire +
`instructor` for structured output). Reasoning judges (`gpt-5-*`, `o1`/`o3`/`o4`)
only allow the default temperature, so `base.py` drops `temperature=0` for them
automatically. The BrowserBash suite always judges with OpenAI `gpt-5-mini`.

## The dashboard

```bash
uvicorn dashboard.app:app --port 8203
# open http://localhost:8203
```

A collapsible-sidebar UI with four panels:

- **Overview** — analytics across all three subsystems: metric / golden / test-file
  counts, per-subsystem health + pass rates, metric coverage, and recent runs.
- **Golden Datasets** — view, edit, add, delete and **save** the goldens for the
  chatbot, RAG and BrowserBash bots (saved edits become a local override the
  runner evaluates against).
- **Run Metrics** — run any metric individually or all at once; live
  score / pass / fail / reason.
- **Runs & Logs** — every run captured locally **before** any Confident AI push,
  grouped by date/time with per-metric pass/fail and expandable
  input / output / judge-reason. Dashboard runs *and* `deepeval test run` runs are
  captured automatically.

## Quick start

```bash
cd 03_DeepFramework
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# pick a judge (.env is loaded automatically by conftest / the dashboard)
export JUDGE_PROVIDER=openai JUDGE_MODEL_OPENAI=gpt-5-mini

# pytest (CI) — per-golden cases
pytest tests/chatbot/test_01_chatbot_answer_relevancy.py -v

# push every case to the Confident AI cloud dashboard
deepeval test run tests/chatbot/test_01_chatbot_answer_relevancy.py

# or the interactive dashboard
uvicorn dashboard.app:app --port 8203
```

## File map

```
03_DeepFramework/
├── conftest.py                 fixtures (judge, chatbot, rag, goldens) + run-history capture hook
├── pytest.ini                  markers (chatbot/rag/browserbash/quality/safety/...)
├── llm_providers/
│   ├── base.py                 CompatibleJudge (OpenAI/Groq/Ollama; reasoning-model safe)
│   └── factory.py              get_judge() / get_openai_judge() from JUDGE_PROVIDER
├── targets/
│   ├── chatbot.py              HTTP client → Subsystem A
│   ├── rag_pipeline.py         HTTP client → Subsystem B
│   └── aleepup_browserbash.py  HTTP client → live BrowserBash bot (BB)
├── datasets/
│   ├── chatbot_goldens.py             19 goldens + 13 safety prompts
│   ├── rag_goldens.py                 8 goldens with expected sources/keywords
│   └── aleepup_browserbash_goldens.py 14 goldens + safety + PII probes
├── dashboard/
│   ├── app.py                  FastAPI app on :8203 (UI + REST)
│   ├── registry.py             29 MetricDef rows — single source of truth
│   ├── runner.py               runs one metric end-to-end (target-aware)
│   ├── goldens_store.py        editable/savable goldens (chatbot/rag/browserbash)
│   ├── runs_store.py           local run history (the Runs & Logs tab)
│   ├── templates/dashboard.html
│   └── static/dashboard.css
├── docs/                       static "how it works" pages + reports
└── tests/
    ├── test_00_smoke.py
    ├── chatbot/                7 chatbot metric suites (test_01..07)
    ├── rag/                    11 RAG metric suites (test_01..11)
    └── aleepup-browserbash-chatbot/  7 live-bot metric suites (test_01..07)
```

## Scoring conventions

| Direction | Metrics |
|-----------|---------|
| Higher is better (threshold = floor) | answer relevancy, faithfulness, contextual precision/recall/relevancy, correctness & other G-Evals, conversation completeness |
| Lower is better (threshold = ceiling) | hallucination, bias, toxicity, PII leakage |

DeepEval handles the inversion automatically via `is_successful()`.
