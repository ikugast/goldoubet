from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import AIPingResponse, DecisionRequest, ResearchRequest
from app.services.ai_decision import generate_decision
from app.services.news import get_market_news
from app.services.research import generate_research
from app.services.strategies import STRATEGY_CONFIG, apply_decision_to_strategy, build_snapshot

settings = get_settings()

app = FastAPI(title="金豆芽后端（真实AI决策版）", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True,
        "env": settings.app_env,
        "live_data": settings.use_live_data,
        "real_ai": settings.use_real_ai,
        "ark_model": settings.ark_model,
    }


@app.get("/api/admin/ai/ping", response_model=AIPingResponse)
def ai_ping():
    return AIPingResponse(
        ok=bool(settings.ark_api_key and settings.ark_model),
        mode="real_ai" if settings.use_real_ai else "rule",
        model=settings.ark_model,
        base_url=settings.ark_base_url,
    )


@app.get("/api/strategies/{strategy}/snapshot")
def get_strategy_snapshot(strategy: str):
    if strategy not in STRATEGY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    return build_snapshot(strategy)


@app.post("/api/strategies/decision")
def make_decision(payload: DecisionRequest, x_scheduler_secret: Optional[str] = Header(default=None)):
    if settings.scheduler_secret and x_scheduler_secret == settings.scheduler_secret:
        pass
    elif settings.scheduler_secret and payload.source == "supabase_cron":
        raise HTTPException(status_code=401, detail="Invalid scheduler secret")

    data = payload.dict()

    if data.get("source") == "supabase_cron" and data.get("strategy") in STRATEGY_CONFIG:
        snapshot = build_snapshot(data["strategy"])

        matched_position = {}
        for p in snapshot.positions:
            if p.symbol == data.get("symbol"):
                matched_position = p.dict()
                break

        matched_quote = None
        for p in snapshot.positions:
            if p.symbol == data.get("symbol"):
                matched_quote = {
                    "symbol": p.symbol,
                    "name": p.name,
                    "current_price": p.current_price,
                    "pnl_pct": p.pnl_pct,
                }
                break

        data["market_data"] = {
            **(data.get("market_data") or {}),
            "symbol": data.get("symbol"),
            "snapshot_updated_at": snapshot.updated_at,
            "data_source": snapshot.data_source,
            "market_type": snapshot.market_type,
            "quote": matched_quote or {},
            "a_share_market_news": [
                item.dict()
                for item in get_market_news()
                if item.market_focus in ("A股", "全球市场")
            ][:5],
        }

        data["position"] = data.get("position") or matched_position
        data["account"] = data.get("account") or {
            "cash": snapshot.cash,
            "nav": snapshot.nav,
            "total_return_pct": snapshot.total_return_pct,
            "holdings_count": snapshot.holdings_count,
            "initial_capital": snapshot.initial_capital,
        }
        data["constraints"] = data.get("constraints") or {
            "strategy_style": snapshot.display_name,
            "run_frequency": snapshot.run_frequency,
            "market_type": snapshot.market_type,
        }

    decision = generate_decision(data)
    if data.get("source") == "supabase_cron":
        apply_decision_to_strategy(data["strategy"], decision)
    return decision


@app.post("/api/research/generate")
def research_generate(payload: ResearchRequest):
    return generate_research(payload.query)


@app.get("/api/news/market")
def market_news():
    return get_market_news()
