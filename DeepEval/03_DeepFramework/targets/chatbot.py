"""HTTP client for Subsystem A (the React/FastAPI chatbot)."""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests


@dataclass
class ChatbotReply:
    reply: str
    model: str
    mode: str


class ChatbotClient:
    def __init__(self, base_url: str | None = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("CHATBOT_URL", "http://localhost:8201")).rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        r = requests.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def is_alive(self) -> bool:
        try:
            self.health()
            return True
        except Exception:
            return False

    def chat(self, message: str, history: list[dict] | None = None) -> ChatbotReply:
        r = requests.post(
            f"{self.base_url}/chat",
            json={"message": message, "history": history or []},
            timeout=self.timeout,
        )
        r.raise_for_status()
        d = r.json()
        return ChatbotReply(reply=d["reply"], model=d["model"], mode=d["mode"])
