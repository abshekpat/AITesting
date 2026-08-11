"""Local fixtures for the RAG (Subsystem B) test suite.

Seeds the vector store exactly once before any RAG test runs so retrieval has
documents to pull from. Tolerant of the app being down — the `needs_rag` marker
(root conftest) skips the actual tests in that case, so seeding just no-ops.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def rag_seeded(rag):
    """Reset + seed the RAG index once per session (no-op if the app is down)."""
    if rag.is_alive():
        try:
            rag.seed(reset=True)
        except Exception:
            pass
    yield
