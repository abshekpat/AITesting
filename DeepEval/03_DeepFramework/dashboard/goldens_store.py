"""Editable golden datasets for the dashboard.

The dashboard lets a user view, edit, add, delete and SAVE goldens for both the
chatbot and the RAG pipeline. Saved edits are written to a JSON override file in
this folder; when present, the override is what the dashboard runner evaluates
against (the original .py datasets remain the seed / fallback for pytest).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from datasets.aleepup_browserbash_goldens import BROWSERBASH_GOLDENS
from datasets.chatbot_goldens import CHATBOT_GOLDENS
from datasets.rag_goldens import RAG_GOLDENS

HERE = Path(__file__).resolve().parent
FILES = {
    "chatbot": HERE / "goldens_chatbot.json",
    "rag": HERE / "goldens_rag.json",
    "browserbash": HERE / "goldens_browserbash.json",
}
FIELDS = {
    "chatbot": ["input", "expected_output", "context", "categories"],
    "rag": ["input", "expected_output", "expected_context_keywords", "expected_sources", "categories"],
    "browserbash": ["input", "expected_output", "context", "categories"],
}
LIST_FIELDS = {"context", "categories", "expected_context_keywords", "expected_sources"}

_SEEDS = {
    "chatbot": CHATBOT_GOLDENS,
    "rag": RAG_GOLDENS,
    "browserbash": BROWSERBASH_GOLDENS,
}


def _seed(target: str) -> list[dict[str, Any]]:
    return [asdict(g) for g in _SEEDS[target]]


def load(target: str) -> list[dict[str, Any]]:
    """Return the current goldens (override if saved, else the seed dataset)."""
    f = FILES[target]
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return _seed(target)


def save(target: str, items: list[dict[str, Any]]) -> int:
    """Persist edited goldens to the override file. Returns number saved."""
    norm: list[dict[str, Any]] = []
    for it in items:
        row: dict[str, Any] = {}
        for k in FIELDS[target]:
            v = it.get(k, [] if k in LIST_FIELDS else "")
            if k in LIST_FIELDS:
                if isinstance(v, str):
                    v = [s.strip() for s in v.split("|") if s.strip()]
                elif not isinstance(v, list):
                    v = []
            else:
                v = (v or "").strip() if isinstance(v, str) else v
            row[k] = v
        if row.get("input"):
            norm.append(row)
    FILES[target].write_text(json.dumps(norm, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(norm)


def reset(target: str) -> int:
    """Drop the override so the seed dataset is used again."""
    f = FILES[target]
    if f.exists():
        f.unlink()
    return len(_seed(target))


def as_objects(target: str) -> list[SimpleNamespace]:
    """Goldens as attribute objects, for the runner (golden.input, .context, ...)."""
    return [SimpleNamespace(**row) for row in load(target)]


def is_overridden(target: str) -> bool:
    return FILES[target].exists()


def fields(target: str) -> list[str]:
    return FIELDS[target]
