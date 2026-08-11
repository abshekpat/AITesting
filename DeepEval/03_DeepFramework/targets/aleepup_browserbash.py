"""HTTP client for the live BrowserBash chatbot on the aleepup.com platform.

This is the *live* target for the ``aleepup-browserbash-chatbot`` suite. Unlike
the local FastAPI chatbot (``targets/chatbot.py``) it:

* takes ``{"message": ..., "visitorId": ...}`` (no ``history`` field), and
* answers with **plain text** (``Content-Type: text/plain``), not JSON.

So ``chat()`` returns ``response.text`` rather than a parsed body. The model
doing the answering is DeepSeek on the server side — we never see it directly,
we just treat the bot as a black box reached over HTTP.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests

# The widget bot id is part of the URL. Override either piece via env if the
# bot is ever re-deployed under a different id / host.
_DEFAULT_BOT_ID = "NqLIxxNfaoPeChEFeF8nj"
_DEFAULT_HOST = "https://aleeup.com"


@dataclass
class BrowserBashReply:
    reply: str
    model: str          # informational — the server-side model under test
    mode: str           # "live"


class BrowserBashClient:
    """Thin wrapper around the live aleepup BrowserBash bot chat endpoint."""

    def __init__(
        self,
        bot_url: str | None = None,
        visitor_id: str | None = None,
        timeout: int = 60,
        model_under_test: str = "deepseek-v4-flash",
    ):
        host = os.getenv("BROWSERBASH_HOST", _DEFAULT_HOST).rstrip("/")
        bot_id = os.getenv("BROWSERBASH_BOT_ID", _DEFAULT_BOT_ID)
        self.bot_url = bot_url or os.getenv(
            "BROWSERBASH_CHAT_URL", f"{host}/api/bots/{bot_id}/chat"
        )
        # A stable visitor id keeps the bot's per-visitor session coherent.
        self.visitor_id = visitor_id or os.getenv("BROWSERBASH_VISITOR_ID", "i6a1en43eu")
        self.timeout = timeout
        self.model_under_test = model_under_test
        self._referer = f"{host}/widget/{bot_id}"
        self._origin = host

    def _headers(self) -> dict:
        # Origin/Referer are required by the platform's CORS check — the bot
        # rejects calls that don't look like they come from its own widget.
        return {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": self._origin,
            "referer": self._referer,
            "user-agent": "aleepup-browserbash-deepeval/1.0",
        }

    def chat(self, message: str) -> BrowserBashReply:
        r = requests.post(
            self.bot_url,
            json={"message": message, "visitorId": self.visitor_id},
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return BrowserBashReply(
            reply=r.text.strip(),
            model=self.model_under_test,
            mode="live",
        )

    def is_alive(self) -> bool:
        """Cheap liveness probe — used by the conftest to auto-skip the suite
        when the bot is unreachable (offline, rate-limited, CORS changed)."""
        try:
            return bool(self.chat("ping").reply)
        except Exception:
            return False
