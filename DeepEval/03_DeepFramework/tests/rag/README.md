# RAG test suite (Subsystem B)

Eleven DeepEval metric suites for the **RAG Explorer** running on `:8202`.
Same structure as the chatbot suite (`tests/chatbot/test_0*_chatbot_*.py`) but pointed at
the retrieval pipeline. Config + thresholds come from `dashboard/registry.py`
(the `rag.*` rows) so pytest and the interactive dashboard stay in lock-step.

| # | File | Metric | Direction | Drives with |
|---|------|--------|-----------|-------------|
| 1 | `test_01_rag_contextual_precision.py` | Contextual Precision | ↑ | RAG goldens |
| 2 | `test_02_rag_contextual_relevancy.py` | Contextual Relevancy | ↑ | RAG goldens |
| 3 | `test_03_rag_faithfulness.py` | Faithfulness | ↑ | RAG goldens |
| 4 | `test_04_rag_answer_relevancy.py` | Answer Relevancy | ↑ | RAG goldens |
| 5 | `test_05_rag_hallucination.py` | Hallucination | ↓ ceiling | RAG goldens |
| 6 | `test_06_rag_geval_correctness.py` | G-Eval · Correctness | ↑ | RAG goldens |
| 7 | `test_07_rag_geval_citation.py` | G-Eval · Citation Quality | ↑ | RAG goldens |
| 8 | `test_08_rag_safety.py` | Bias + Toxicity | ↓ ceiling | SAFETY_PROMPTS |
| 9 | `test_09_rag_geval_summarization.py` | G-Eval · Summarization | ↑ | summary tasks |
| 10 | `test_10_rag_conversational.py` | Conversation Completeness | ↑ | multi-turn |
| 11 | `test_11_rag_geval_helpfulness.py` | G-Eval · Helpfulness | ↑ | RAG goldens |

↑ = higher is better · ↓ = lower is better (threshold is a ceiling)

## Run

```bash
# start the RAG Explorer first (Subsystem B) on :8202
deepeval test run tests/rag/            # captures every case (pushes to Confident AI if configured)
pytest tests/rag/ -m rag                # plain pytest
pytest tests/rag/ -m "rag and retrieval"   # just the retrieval-quality metrics
```

If the RAG app is not reachable on `:8202`, every test auto-skips (the `needs_rag`
marker in the root `conftest.py`). `conftest.py` here seeds the vector store once
per session before the suite runs.

## Test-case fields

- **`actual_output`** — the live answer from `POST /api/chat`.
- **`retrieval_context`** — the chunks the pipeline actually retrieved (live), with
  the golden's `expected_output` as a fallback.
- **`expected_output`** — the golden reference answer (precision / correctness).
- **`context`** (hallucination) — `RagGolden` has no `context` field, so we use
  `[expected_output]` as ground truth, exactly like `dashboard/runner.py`.
