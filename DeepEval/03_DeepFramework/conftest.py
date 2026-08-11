"""Shared pytest fixtures for the DeepEval framework.

Loads .env, builds the judge from JUDGE_PROVIDER, exposes HTTP clients for the
apps under test (Subsystems A + B), and the golden datasets. Tests marked
`needs_chatbot` / `needs_rag` auto-skip when the target app is not running.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env that sits next to this file (never committed — holds the real keys).
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from datasets.chatbot_goldens import CHATBOT_GOLDENS, SAFETY_PROMPTS
from llm_providers import get_judge, judge_info
from targets import ChatbotClient, RagClient


# -------------------- judge --------------------

@pytest.fixture(scope="session")
def judge():
    """The LLM-as-judge built from JUDGE_PROVIDER (.env)."""
    return get_judge()


# -------------------- targets --------------------

@pytest.fixture(scope="session")
def chatbot():
    return ChatbotClient()


@pytest.fixture(scope="session")
def rag():
    return RagClient()


# -------------------- datasets --------------------

@pytest.fixture
def chatbot_goldens():
    return CHATBOT_GOLDENS


@pytest.fixture
def safety_prompts():
    return SAFETY_PROMPTS


# -------------------- liveness guards --------------------

def pytest_runtest_setup(item):
    """Skip tests whose target app is not reachable."""
    if item.get_closest_marker("needs_chatbot") and not ChatbotClient().is_alive():
        pytest.skip("Chatbot (Subsystem A) not reachable at CHATBOT_URL — start it on :8201")
    if item.get_closest_marker("needs_rag") and not RagClient().is_alive():
        pytest.skip("RAG Explorer (Subsystem B) not reachable at RAG_URL — start it on :8202")


def pytest_report_header(config):
    try:
        info = judge_info()
        return f"judge provider={info['provider']} model={info['model']}"
    except Exception as e:  # pragma: no cover
        return f"judge: not configured ({e})"


# -------------------- run-history capture --------------------
# Mirror every pytest / `deepeval test run` session into the dashboard's local
# run store, so the "Runs & Logs" tab shows CLI runs too (date/time basis) — no
# Confident AI round-trip needed.

_CACHE_SNAPSHOT: set[str] = set()


def pytest_sessionstart(session):
    try:
        from dashboard import runs_store
        global _CACHE_SNAPSHOT
        _CACHE_SNAPSHOT = runs_store.cache_keys()
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    try:
        from datetime import datetime

        from dashboard import runs_store
        run_id = "pytest-" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        judge = os.getenv("JUDGE_MODEL_OPENAI") or os.getenv("JUDGE_PROVIDER") or ""
        recs = runs_store.cache_records(
            run_id, source="pytest", judge=judge, keys_to_skip=_CACHE_SNAPSHOT,
        )
        runs_store.record_many(recs)
    except Exception:
        pass
