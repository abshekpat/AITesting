"""Auto-bootstrap goldens by chatting with the live BrowserBash bot.

Run this to (re)capture the bot's *current* answers for every golden input and
write them to ``datasets/aleepup_browserbash_snapshot.json``. Use the snapshot to
refresh the canonical ``expected_output`` / ``context`` in
:mod:`datasets.aleepup_browserbash_goldens` whenever the bot's knowledge changes.

    python -m datasets.generate_aleepup_browserbash_goldens                 # all golden inputs
    python -m datasets.generate_aleepup_browserbash_goldens "Custom Q?"     # ad-hoc questions

This is a *generation* tool, not a test — it makes live calls to the bot only
(no judge / OpenAI calls), so it's cheap to run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from datasets.aleepup_browserbash_goldens import BROWSERBASH_GOLDENS
from targets import BrowserBashClient

SNAPSHOT = Path(__file__).resolve().parent / "aleepup_browserbash_snapshot.json"


def main(argv: list[str]) -> int:
    bot = BrowserBashClient()
    if not bot.is_alive():
        print("Bot unreachable — aborting.", file=sys.stderr)
        return 1

    questions = argv[1:] or [g.input for g in BROWSERBASH_GOLDENS]
    captured = []
    for q in questions:
        print(f"→ {q}")
        reply = bot.chat(q).reply
        print(f"  {reply[:160].replace(chr(10), ' ')}…\n")
        captured.append({"input": q, "live_reply": reply})

    SNAPSHOT.write_text(json.dumps(captured, indent=2, ensure_ascii=False))
    print(f"Wrote {len(captured)} captures → {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
