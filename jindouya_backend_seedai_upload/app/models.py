from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str
    name: str
    side: str = "long"
    weight: float
    qty: float
    cost_price: float
    current_price: float
    pnl_pct: float
    thesis: str = ""


class TradeRecord(BaseModel):
    ts: str
    name: str
    symbol: str
    action: str
    price: float
    qty: float
    reason: str = ""


class StrategySnapshot(BaseModel):
    strategy: str
    display_name: str
    market_type: str
    nav: float
    total_return_pct: float
    cash: float
    holdings_count: int
    run_frequency: str
    initial_capital: float
    positions: List[Position]
    recent_trades: List[TradeRecord]
    updated_at: str
    data_source: str


class DecisionRequest(BaseModel):
    strategy: str
    symbol: str
    source: Optional[str] = None
    market_data: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, Any] = Field(default_factory=dict)
    account: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    strategy: str
    action: str
    confidence: float
    reason: str
    risk_note: str
    symbol: Optional[str] = None
    qty: float = 0.0
    mode: str = "rule"
    raw_output: Optional[Dict[str, Any]] = None


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    rating: str
    target_price: str
    summary: str
    report: str


class MarketNewsItem(BaseModel):
    ts: str
    title: str
    summary: str
    impact: str
    market_focus: str


class AIPingResponse(BaseModel):
    ok: bool
    mode: str
    model: str
    base_url: str
