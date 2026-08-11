"""Local fixtures + guards for the aleepup-browserbash-chatbot suite.

This suite points the seven chatbot metrics at the *live* BrowserBash bot on the
aleepup.com platform. Two things differ from the local-chatbot suite:

1. The target is remote and black-box — replies are plain text from the bot's
   widget API (``targets/aleepup_browserbash.py``). The model answering is
   DeepSeek server-side.
2. The judge is **always** OpenAI ``gpt-5-mini`` — this conftest overrides the
   repo-wide ``judge`` fixture so ``JUDGE_PROVIDER`` in ``.env`` is ignored here.

Tests marked ``needs_browserbash`` auto-skip when the live bot is unreachable, so
the suite degrades gracefully offline / when rate-limited.
"""
from __future__ import annotations

import pytest

from llm_providers import get_openai_judge
from targets import BrowserBashClient


# -------------------- judge (overrides the root fixture) --------------------

@pytest.fixture(scope="session")
def judge():
    """Always OpenAI gpt-5-mini for this suite (overrides the repo judge)."""
    return get_openai_judge()


# -------------------- target --------------------

@pytest.fixture(scope="session")
def browserbash_chatbot():
    return BrowserBashClient()


# -------------------- liveness guard (checked once per session) --------------------

_ALIVE: bool | None = None


def _bot_alive() -> bool:
    global _ALIVE
    if _ALIVE is None:
        _ALIVE = BrowserBashClient().is_alive()
    return _ALIVE


def pytest_runtest_setup(item):
    if item.get_closest_marker("needs_browserbash") and not _bot_alive():
        pytest.skip(
            "Live BrowserBash bot unreachable (offline / rate-limited / CORS) — "
            "skipping aleepup-browserbash-chatbot suite"
        )


def pytest_report_header(config):
    return "aleepup-browserbash-chatbot judge provider=openai model=gpt-5-mini"
