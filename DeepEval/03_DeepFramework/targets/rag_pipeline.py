"""HTTP client for Subsystem B (RAG Explorer)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests


@dataclass
class RagReply:
    answer: str
    sources: list[str]
    retrieval_context: list[str] = field(default_factory=list)
    hits: list[dict] = field(default_factory=list)
    mode: str = "live"
    model: str = ""


class RagClient:
    def __init__(self, base_url: str | None = None, timeout: int = 60):
        self.base_url = (base_url or os.getenv("RAG_URL", "http://localhost:8202")).rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        r = requests.get(f"{self.base_url}/api/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def is_alive(self) -> bool:
        try:
            self.health()
            return True
        except Exception:
            return False

    def seed(self, reset: bool = True) -> dict:
        r = requests.post(f"{self.base_url}/api/ingest/seed", params={"reset": reset}, timeout=120)
        r.raise_for_status()
        return r.json()

    def search(self, query: str, top_k: int = 4) -> dict:
        r = requests.post(
            f"{self.base_url}/api/search",
            json={"query": query, "top_k": top_k},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def chat(self, message: str, top_k: int = 4, history: list[dict] | None = None) -> RagReply:
        r = requests.post(
            f"{self.base_url}/api/chat",
            json={"message": message, "top_k": top_k, "history": history or []},
            timeout=self.timeout,
        )
        r.raise_for_status()
        d = r.json()
        return RagReply(
            answer=d["answer"],
            sources=d.get("sources", []),
            retrieval_context=d.get("retrieval_context", []),
            hits=d.get("hits", []),
            mode=d.get("mode", "live"),
            model=d.get("model", ""),
        )
