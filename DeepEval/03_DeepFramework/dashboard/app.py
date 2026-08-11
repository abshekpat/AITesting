"""DeepEval dashboard — FastAPI app on port 8203.

Drives the same metric registry the pytest suite uses, but exposes
each metric as an interactive button in a web UI that streams live
pass/fail/score/reason. Lets the user switch between target apps
(chatbot vs RAG) and judge providers (openai/groq/ollama) without
restarting the server.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# allow imports from parent (llm_providers/, targets/, datasets/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from llm_providers import judge_info  # noqa: E402
from llm_providers.factory import PROVIDERS, _resolve_provider  # noqa: E402
from targets import BrowserBashClient, ChatbotClient, RagClient  # noqa: E402

from . import goldens_store, runs_store  # noqa: E402
from .registry import REGISTRY, REGISTRY_BY_ID, list_for_target  # noqa: E402
from .runner import run_metric  # noqa: E402

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

app = FastAPI(title="DeepEval Dashboard", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


class RunRequest(BaseModel):
    metric_id: str
    sample_idx: int = 0


class JudgeRequest(BaseModel):
    provider: str
    model: str | None = None


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/info")
def info():
    chatbot_alive = ChatbotClient().is_alive()
    rag_alive = RagClient().is_alive()
    return {
        "judge": judge_info(),
        "providers": list(PROVIDERS.keys()),
        "current_provider": _resolve_provider(),
        "targets": {
            "chatbot": {"alive": chatbot_alive, "url": ChatbotClient().base_url},
            "rag": {"alive": rag_alive, "url": RagClient().base_url},
        },
        "metric_count": len(REGISTRY),
    }


@app.get("/api/metrics")
def metrics(target: str | None = None):
    rows = list_for_target(target)
    return {
        "metrics": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "category": m.category,
                "target": m.target,
                "threshold": m.threshold,
                "higher_is_better": m.higher_is_better,
                "display_threshold": m.display_threshold,
                "sample_kind": m.sample_kind,
                "requires": m.requires,
            }
            for m in rows
        ]
    }


@app.post("/api/judge")
def set_judge(req: JudgeRequest):
    if req.provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {req.provider}")
    os.environ["JUDGE_PROVIDER"] = req.provider
    if req.model:
        cfg = PROVIDERS[req.provider]
        os.environ[cfg["model_env"]] = req.model
    return judge_info()


@app.post("/api/run")
def run(req: RunRequest):
    if req.metric_id not in REGISTRY_BY_ID:
        raise HTTPException(404, f"Unknown metric_id: {req.metric_id}")
    result = run_metric(req.metric_id, sample_idx=req.sample_idx)
    return JSONResponse(result)


@app.post("/api/run-all")
def run_all(req: dict):
    """Sequentially run every metric for the chosen target.

    Note: the UI calls /api/run per-metric for live streaming. This is
    here for completeness / curl users.
    """
    target = req.get("target") or "all"
    rows = list_for_target(target)
    out = []
    for m in rows:
        out.append(run_metric(m.id))
    return {"results": out}


# -------------------- golden datasets (view / edit / save) --------------------

class GoldensRequest(BaseModel):
    target: str
    items: list[dict]


@app.get("/api/goldens")
def get_goldens(target: str = "chatbot"):
    if target not in ("chatbot", "rag", "browserbash"):
        raise HTTPException(400, "target must be 'chatbot', 'rag' or 'browserbash'")
    return {
        "target": target,
        "fields": goldens_store.fields(target),
        "items": goldens_store.load(target),
        "overridden": goldens_store.is_overridden(target),
    }


@app.put("/api/goldens")
def put_goldens(req: GoldensRequest):
    if req.target not in ("chatbot", "rag", "browserbash"):
        raise HTTPException(400, "target must be 'chatbot', 'rag' or 'browserbash'")
    n = goldens_store.save(req.target, req.items)
    return {"saved": n, "target": req.target, "overridden": True}


@app.post("/api/goldens/reset")
def reset_goldens(req: dict):
    target = req.get("target", "chatbot")
    if target not in ("chatbot", "rag", "browserbash"):
        raise HTTPException(400, "target must be 'chatbot', 'rag' or 'browserbash'")
    n = goldens_store.reset(target)
    return {"reset": n, "target": target, "overridden": False}


# -------------------- run history (local, before Confident AI) --------------------

@app.get("/api/runs")
def get_runs(target: str | None = None):
    return {"sessions": runs_store.sessions(target)}


@app.delete("/api/runs")
def clear_runs():
    try:
        runs_store.RUNS_PATH.unlink()
    except FileNotFoundError:
        pass
    return {"cleared": True}


# -------------------- overview / analytics (parent window) --------------------

def _count_test_files(subdir: str) -> int:
    p = ROOT / "tests" / subdir
    return len(list(p.glob("test_*.py"))) if p.exists() else 0


_BB_ALIVE: bool | None = None


def _browserbash_alive() -> bool:
    """Cached liveness for the live BrowserBash bot (one bounded probe per process)."""
    global _BB_ALIVE
    if _BB_ALIVE is None:
        try:
            _BB_ALIVE = BrowserBashClient(timeout=8).is_alive()
        except Exception:
            _BB_ALIVE = False
    return _BB_ALIVE


@app.get("/api/overview")
def overview():
    by_target: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for m in REGISTRY:
        by_target[m.target] = by_target.get(m.target, 0) + 1
        by_category[m.category] = by_category.get(m.category, 0) + 1

    test_files = {
        "chatbot": _count_test_files("chatbot"),
        "rag": _count_test_files("rag"),
        "browserbash": _count_test_files("aleepup-browserbash-chatbot"),
    }
    goldens = {
        "chatbot": len(goldens_store.load("chatbot")),
        "rag": len(goldens_store.load("rag")),
        "browserbash": len(goldens_store.load("browserbash")),
    }

    sess = runs_store.sessions()
    total_cases = sum(s["total"] for s in sess)
    passed = sum(s["passed"] for s in sess)
    runs_by_target: dict[str, dict] = {}
    for s in sess:
        rt = runs_by_target.setdefault(s.get("target", "?"), {"sessions": 0, "cases": 0, "passed": 0})
        rt["sessions"] += 1
        rt["cases"] += s["total"]
        rt["passed"] += s["passed"]

    cb, rg = ChatbotClient(), RagClient()
    targets = {
        "chatbot": {
            "label": "ShopSphere Chatbot", "subsystem": "A", "alive": cb.is_alive(), "url": cb.base_url,
            "metrics": by_target.get("chatbot", 0), "goldens": goldens["chatbot"], "tests": test_files["chatbot"],
            "runs": runs_by_target.get("chatbot", {"sessions": 0, "cases": 0, "passed": 0}),
        },
        "rag": {
            "label": "RAG Explorer", "subsystem": "B", "alive": rg.is_alive(), "url": rg.base_url,
            "metrics": by_target.get("rag", 0), "goldens": goldens["rag"], "tests": test_files["rag"],
            "runs": runs_by_target.get("rag", {"sessions": 0, "cases": 0, "passed": 0}),
        },
        "browserbash": {
            "label": "BrowserBash (live)", "subsystem": "BB", "alive": _browserbash_alive(),
            "url": BrowserBashClient().bot_url, "metrics": by_target.get("browserbash", 0),
            "goldens": goldens["browserbash"], "tests": test_files["browserbash"],
            "runs": runs_by_target.get("browserbash", {"sessions": 0, "cases": 0, "passed": 0}),
        },
    }
    return {
        "metrics": {"total": len(REGISTRY), "by_target": by_target, "by_category": by_category},
        "test_files": test_files,
        "total_tests": sum(test_files.values()),
        "goldens": goldens,
        "total_goldens": sum(goldens.values()),
        "runs": {
            "sessions": len(sess),
            "cases": total_cases,
            "passed": passed,
            "failed": total_cases - passed,
            "pass_rate": round(passed / total_cases * 100) if total_cases else 0,
            "recent": sess[:6],
        },
        "targets": targets,
        "judge": judge_info(),
    }
