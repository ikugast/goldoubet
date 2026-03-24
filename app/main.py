from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.models import AIPingResponse, DecisionRequest, ResearchRequest
from app.services.ai_decision import generate_decision
from app.services.news import get_market_news
from app.services.research import generate_research
from app.services.strategies import (
    STRATEGY_CONFIG, 
    apply_decision_to_strategy, 
    build_snapshot, 
    reset_strategy,
    get_account_status,
    get_market_context,
    eod_processing,
    DECISION_POINTS
)

settings = get_settings()

app = FastAPI(title="金豆芽AI模拟交易系统", version="4.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DecisionContextRequest(BaseModel):
    strategy: str
    decision_point: Optional[str] = None


class DecisionContextResponse(BaseModel):
    strategy: str
    decision_point: str
    account_status: Dict[str, Any]
    market_context: Dict[str, Any]
    timestamp: str


@app.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True,
        "env": settings.app_env,
        "live_data": settings.use_live_data,
        "real_ai": settings.use_real_ai,
        "ark_model": settings.ark_model,
        "decision_points": DECISION_POINTS,
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


@app.get("/api/strategies/{strategy}/context", response_model=DecisionContextResponse)
def get_strategy_context(strategy: str, decision_point: Optional[str] = None):
    """获取AI决策所需的完整上下文（账户现状 + 行情快照）"""
    if strategy not in STRATEGY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    
    # 如果没有提供决策点，使用当前时间最接近的
    if not decision_point:
        now = datetime.now().strftime("%H:%M")
        decision_point = min(DECISION_POINTS, key=lambda x: abs(
            int(x.replace(":", "")) - int(now.replace(":", ""))
        ))
    
    account_status = get_account_status(strategy)
    market_context = get_market_context(strategy)
    
    return DecisionContextResponse(
        strategy=strategy,
        decision_point=decision_point,
        account_status=account_status,
        market_context=market_context,
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/admin/strategies/{strategy}/reset")
def reset_strategy_endpoint(strategy: str):
    if strategy not in STRATEGY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    if not reset_strategy(strategy):
        raise HTTPException(status_code=500, detail="Reset failed")
    return build_snapshot(strategy)


@app.post("/api/admin/strategies/{strategy}/eod")
def end_of_day_processing(strategy: str):
    """日终结算：更新T+1可卖额度"""
    if strategy not in STRATEGY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    
    result = eod_processing(strategy)
    if not result:
        raise HTTPException(status_code=500, detail="EOD processing failed")
    
    return {
        "success": True,
        "eod_report": result,
        "snapshot": build_snapshot(strategy),
    }


@app.post("/api/strategies/decision")
def make_decision(payload: DecisionRequest, x_scheduler_secret: Optional[str] = Header(default=None)):
    # 验证调度密钥
    if settings.scheduler_secret and x_scheduler_secret == settings.scheduler_secret:
        pass
    elif settings.scheduler_secret and payload.source == "supabase_cron":
        raise HTTPException(status_code=401, detail="Invalid scheduler secret")

    data = payload.dict()
    strategy_key = data.get("strategy")

    if strategy_key in STRATEGY_CONFIG:
        # 获取完整上下文
        account_status = get_account_status(strategy_key)
        market_context = get_market_context(strategy_key)
        
        # 注入镜像上下文
        data["account_status"] = account_status
        data["market_context"] = market_context
        data["decision_point"] = data.get("decision_point", datetime.now().strftime("%H:%M"))
        
        # 获取策略配置
        cfg = STRATEGY_CONFIG[strategy_key]
        data["constraints"] = cfg.get("constraints", {})
        data["asset_pool"] = list(cfg.get("asset_pool", {}).keys())

    decision = generate_decision(data)
    
    # 如果是定时任务触发，自动应用决策
    if data.get("source") == "supabase_cron":
        # 处理可能的多条决策
        actions = decision.get("actions", [])
        if actions:
            for action in actions:
                apply_decision_to_strategy(strategy_key, {
                    "symbol": action.get("code"),
                    "action": action.get("action"),
                    "qty": action.get("volume", 0),
                    "reason": action.get("logic", ""),
                })
        else:
            # 兼容单条决策格式
            apply_decision_to_strategy(strategy_key, decision)
    
    return decision


@app.post("/api/strategies/{strategy}/execute")
def execute_strategy_decision(strategy: str, decision: Dict[str, Any]):
    """手动执行AI决策（用于测试或人工干预）"""
    if strategy not in STRATEGY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    
    results = []
    actions = decision.get("actions", [])
    
    if actions:
        for action in actions:
            success = apply_decision_to_strategy(strategy, {
                "symbol": action.get("code"),
                "action": action.get("action"),
                "qty": action.get("volume", 0),
                "reason": action.get("logic", ""),
            })
            results.append({
                "code": action.get("code"),
                "action": action.get("action"),
                "success": success,
            })
    else:
        # 单条决策
        success = apply_decision_to_strategy(strategy, decision)
        results.append({
            "code": decision.get("symbol"),
            "action": decision.get("action"),
            "success": success,
        })
    
    return {
        "strategy": strategy,
        "results": results,
        "snapshot": build_snapshot(strategy),
    }


@app.post("/api/research/generate")
def research_generate(payload: ResearchRequest):
    return generate_research(payload.query)


@app.get("/api/news/market")
def market_news():
    """获取分时段的市场财讯"""
    return get_market_news()


@app.get("/api/news/summary")
def market_news_summary():
    """获取财讯摘要（用于AI决策）"""
    from app.services.news import get_news_summary_for_ai
    return get_news_summary_for_ai()


@app.post("/api/news/update-hot")
def update_hot_stocks(strategy: str):
    """手动更新资产池热点状态"""
    if strategy not in STRATEGY_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    
    from app.services.news import update_asset_pool_hot_status
    update_asset_pool_hot_status(STRATEGY_CONFIG[strategy])
    
    # 返回热点股票列表
    asset_pool = STRATEGY_CONFIG[strategy].get("asset_pool", {})
    hot_stocks = [code for code, info in asset_pool.items() if info.get("is_hot", False)]
    
    return {
        "strategy": strategy,
        "hot_stocks": hot_stocks,
        "total_hot": len(hot_stocks),
    }


@app.get("/api/config/decision-points")
def get_decision_points():
    """获取决策时间点配置"""
    return {
        "decision_points": DECISION_POINTS,
        "description": {
            "09:30": "开盘动能 - 捕捉早盘趋势启动",
            "13:00": "午间盘整 - 评估上午走势，调整仓位",
            "14:50": "尾盘收官 - 锁定收益，控制隔夜风险",
        }
    }
