from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Tuple

from app.models import Position, StrategySnapshot, TradeRecord
from app.services.market_data import Quote, fetch_a_share_quotes, fetch_crypto_quotes, get_now_ts


STRATEGY_CONFIG: Dict[str, Dict] = {
    "stock_steady": {
        "display_name": "成熟稳健",
        "market_type": "stock",
        "run_frequency": "09:30 / 14:50",
        "initial_capital": 1_000_000,
        "cash": 402_500,
        "symbols": ["600519", "300750", "601318"],
        "positions": [
            {
                "symbol": "600519",
                "name": "贵州茅台",
                "weight": 0.24,
                "qty": 120,
                "cost_price": 1620.0,
                "thesis": "白酒龙头，现金流稳健，适合中期持有。",
            },
            {
                "symbol": "300750",
                "name": "宁德时代",
                "weight": 0.20,
                "qty": 700,
                "cost_price": 182.0,
                "thesis": "新能源龙头，产业链地位强，波动中寻找配置机会。",
            },
            {
                "symbol": "601318",
                "name": "中国平安",
                "weight": 0.14,
                "qty": 2500,
                "cost_price": 42.6,
                "thesis": "低估值金融蓝筹，分红与估值修复双逻辑。",
            },
        ],
        "trades": [
            {"ts": "2026-03-22 14:50:00", "name": "贵州茅台", "symbol": "600519", "action": "加仓", "price": 1688.0, "qty": 20, "reason": "尾盘资金回流消费，趋势未破，仓位小幅提升。"},
            {"ts": "2026-03-21 09:35:00", "name": "中国平安", "symbol": "601318", "action": "持有", "price": 43.2, "qty": 0, "reason": "估值仍具吸引力，暂不追高。"},
            {"ts": "2026-03-20 14:50:00", "name": "宁德时代", "symbol": "300750", "action": "减仓", "price": 191.0, "qty": 100, "reason": "短线涨幅偏快，先落袋部分利润。"},
            {"ts": "2026-03-19 09:31:00", "name": "贵州茅台", "symbol": "600519", "action": "买入", "price": 1662.0, "qty": 40, "reason": "防御资产走强，回撤后重新介入。"},
            {"ts": "2026-03-18 14:49:00", "name": "中国平安", "symbol": "601318", "action": "买入", "price": 42.2, "qty": 300, "reason": "权重金融企稳，风险收益比改善。"},
            {"ts": "2026-03-17 09:36:00", "name": "宁德时代", "symbol": "300750", "action": "买入", "price": 183.5, "qty": 100, "reason": "景气方向回暖，顺势布局。"},
        ],
    },
    "stock_scalper": {
        "display_name": "超短高手",
        "market_type": "stock",
        "run_frequency": "每小时一次",
        "initial_capital": 1_000_000,
        "cash": 518_300,
        "symbols": ["002594", "300308", "601127"],
        "positions": [
            {"symbol": "002594", "name": "比亚迪", "weight": 0.18, "qty": 300, "cost_price": 228.0, "thesis": "高弹性主线龙头，关注日内量价配合。"},
            {"symbol": "300308", "name": "中际旭创", "weight": 0.17, "qty": 260, "cost_price": 161.0, "thesis": "高景气赛道，偏强趋势下做加速。"},
            {"symbol": "601127", "name": "赛力斯", "weight": 0.13, "qty": 400, "cost_price": 91.0, "thesis": "高波动标的，适合快进快出。"},
        ],
        "trades": [
            {"ts": "2026-03-22 14:30:00", "name": "赛力斯", "symbol": "601127", "action": "止盈", "price": 96.8, "qty": 100, "reason": "冲高量能衰减，先兑现部分利润。"},
            {"ts": "2026-03-22 13:30:00", "name": "中际旭创", "symbol": "300308", "action": "加仓", "price": 166.5, "qty": 60, "reason": "分时强势回封，延续性较好。"},
            {"ts": "2026-03-22 11:30:00", "name": "比亚迪", "symbol": "002594", "action": "买入", "price": 231.6, "qty": 80, "reason": "日内量价共振，博弈午后冲高。"},
            {"ts": "2026-03-22 10:30:00", "name": "中际旭创", "symbol": "300308", "action": "持有", "price": 164.9, "qty": 0, "reason": "趋势未破，等待进一步放量。"},
            {"ts": "2026-03-22 09:30:00", "name": "赛力斯", "symbol": "601127", "action": "买入", "price": 92.4, "qty": 120, "reason": "高开承接良好，抢首波脉冲。"},
            {"ts": "2026-03-21 14:30:00", "name": "比亚迪", "symbol": "002594", "action": "减仓", "price": 236.1, "qty": 60, "reason": "短线过热，降低尾盘回撤风险。"},
        ],
    },
    "crypto_flexible": {
        "display_name": "自由发挥",
        "market_type": "crypto",
        "run_frequency": "每小时一次",
        "initial_capital": 1_000_000,
        "cash": 84_500,
        "symbols": ["BTC-USDT", "ETH-USDT", "SOL-USDT"],
        "positions": [
            {"symbol": "BTC-USDT", "name": "BTC", "weight": 0.34, "qty": 1.2, "cost_price": 81200.0, "thesis": "大盘核心资产，趋势交易为主。"},
            {"symbol": "ETH-USDT", "name": "ETH", "weight": 0.22, "qty": 12.0, "cost_price": 4020.0, "thesis": "Beta 较高，跟随主趋势灵活调整。"},
            {"symbol": "SOL-USDT", "name": "SOL", "weight": 0.16, "qty": 85.0, "cost_price": 128.0, "thesis": "强势山寨风向标，适合顺势参与。"},
        ],
        "trades": [
            {"ts": "2026-03-22 20:00:00", "name": "BTC", "symbol": "BTC-USDT", "action": "持有", "price": 84250.0, "qty": 0, "reason": "主升趋势仍在，维持核心仓位。"},
            {"ts": "2026-03-22 19:00:00", "name": "ETH", "symbol": "ETH-USDT", "action": "加仓", "price": 4180.0, "qty": 1.5, "reason": "强于大盘，补涨逻辑延续。"},
            {"ts": "2026-03-22 18:00:00", "name": "SOL", "symbol": "SOL-USDT", "action": "减仓", "price": 139.8, "qty": 10, "reason": "拉升过快，先回收部分筹码。"},
            {"ts": "2026-03-22 17:00:00", "name": "BTC", "symbol": "BTC-USDT", "action": "买入", "price": 83820.0, "qty": 0.1, "reason": "回踩后再度放量，顺势加仓。"},
            {"ts": "2026-03-22 16:00:00", "name": "ETH", "symbol": "ETH-USDT", "action": "买入", "price": 4110.0, "qty": 2.0, "reason": "相对强度提升，参与轮动。"},
            {"ts": "2026-03-22 15:00:00", "name": "SOL", "symbol": "SOL-USDT", "action": "买入", "price": 133.1, "qty": 12, "reason": "高弹性资产出现二次启动。"},
        ],
    },
    "crypto_aggressive": {
        "display_name": "勇猛精进",
        "market_type": "crypto",
        "run_frequency": "每小时一次",
        "initial_capital": 1_000_000,
        "cash": 38_000,
        "symbols": ["BTC-USDT", "ETH-USDT", "DOGE-USDT"],
        "positions": [
            {"symbol": "BTC-USDT", "name": "BTC", "weight": 0.24, "qty": 0.9, "cost_price": 80500.0, "thesis": "趋势锚点，作为高风险组合底仓。"},
            {"symbol": "ETH-USDT", "name": "ETH", "weight": 0.26, "qty": 18.0, "cost_price": 3980.0, "thesis": "波动承接能力强，适合放大收益。"},
            {"symbol": "DOGE-USDT", "name": "DOGE", "weight": 0.32, "qty": 55000.0, "cost_price": 0.168, "thesis": "高弹性投机品种，追求最大收益。"},
        ],
        "trades": [
            {"ts": "2026-03-22 20:00:00", "name": "DOGE", "symbol": "DOGE-USDT", "action": "加仓", "price": 0.182, "qty": 8000, "reason": "高波动突破，接受回撤换取更高收益。"},
            {"ts": "2026-03-22 19:00:00", "name": "ETH", "symbol": "ETH-USDT", "action": "持有", "price": 4195.0, "qty": 0, "reason": "趋势极强，不轻易下车。"},
            {"ts": "2026-03-22 18:00:00", "name": "BTC", "symbol": "BTC-USDT", "action": "减仓", "price": 84400.0, "qty": 0.05, "reason": "腾出保证金给高弹性标的。"},
            {"ts": "2026-03-22 17:00:00", "name": "DOGE", "symbol": "DOGE-USDT", "action": "买入", "price": 0.176, "qty": 12000, "reason": "追击强势币，收益优先。"},
            {"ts": "2026-03-22 16:00:00", "name": "ETH", "symbol": "ETH-USDT", "action": "加仓", "price": 4132.0, "qty": 3.0, "reason": "强趋势延续，主动提高风险暴露。"},
            {"ts": "2026-03-22 15:00:00", "name": "BTC", "symbol": "BTC-USDT", "action": "买入", "price": 83650.0, "qty": 0.08, "reason": "借回踩补仓，为高贝塔资产打底。"},
        ],
    },
}

INITIAL_STRATEGY_CONFIG = deepcopy(STRATEGY_CONFIG)


def _load_quotes(strategy_key: str) -> Tuple[Dict[str, Quote], str]:
    cfg = STRATEGY_CONFIG[strategy_key]
    if cfg["market_type"] == "stock":
        quotes = fetch_a_share_quotes(cfg["symbols"])
    else:
        quotes = fetch_crypto_quotes(cfg["symbols"])
    source = next(iter(quotes.values())).source if quotes else "Fallback Template"
    return quotes, source


def build_snapshot(strategy_key: str) -> StrategySnapshot:
    cfg = STRATEGY_CONFIG[strategy_key]
    quotes, source = _load_quotes(strategy_key)
    positions: List[Position] = []
    positions_value = 0.0
    for item in cfg["positions"]:
        quote = quotes.get(item["symbol"])
        current_price = quote.price if quote else item["cost_price"]
        pnl_pct = ((current_price - item["cost_price"]) / item["cost_price"] * 100) if item["cost_price"] else 0.0
        positions_value += current_price * item["qty"]
        positions.append(
            Position(
                symbol=item["symbol"],
                name=item["name"],
                side="long",
                weight=item["weight"],
                qty=item["qty"],
                cost_price=item["cost_price"],
                current_price=round(current_price, 4),
                pnl_pct=round(pnl_pct, 2),
                thesis=item["thesis"],
            )
        )
    equity = cfg["cash"] + positions_value
    nav = equity / cfg["initial_capital"]
    total_return_pct = (equity / cfg["initial_capital"] - 1) * 100
    trades = [TradeRecord(**t) for t in cfg["trades"]]
    trades = sorted(trades, key=lambda x: x.ts, reverse=True)
    return StrategySnapshot(
        strategy=strategy_key,
        display_name=cfg["display_name"],
        market_type=cfg["market_type"],
        nav=round(nav, 4),
        total_return_pct=round(total_return_pct, 2),
        cash=round(cfg["cash"], 2),
        holdings_count=len(positions),
        run_frequency=cfg["run_frequency"],
        initial_capital=cfg["initial_capital"],
        positions=positions,
        recent_trades=trades,
        updated_at=get_now_ts(),
        data_source=source,
    )
def apply_decision_to_strategy(strategy_key: str, decision: Dict) -> bool:
    if strategy_key not in STRATEGY_CONFIG:
        return False

    cfg = STRATEGY_CONFIG[strategy_key]
    symbol = (decision.get("symbol") or "").strip()
    action = (decision.get("action") or "").strip()
    qty = int(decision.get("qty") or 0)
    reason = (decision.get("reason") or "").strip()

    if not symbol or qty < 0:
        return False

    quotes, _ = _load_quotes(strategy_key)
    quote = quotes.get(symbol)
    price = quote.price if quote else 0.0

    target = None
    for item in cfg["positions"]:
        if item["symbol"] == symbol:
            target = item
            break

    name = target["name"] if target else (quote.name if quote else symbol)

    if action in ("持有", ""):
        cfg["trades"].insert(
            0,
            {
                "ts": get_now_ts(),
                "name": name,
                "symbol": symbol,
                "action": "持有",
                "price": round(price, 4),
                "qty": 0,
                "reason": reason,
            },
        )
        cfg["trades"] = cfg["trades"][:20]
        return True

    if action in ("买入", "加仓"):
        if qty <= 0 or price <= 0:
            return False
        cost = price * qty
        if cfg["cash"] < cost:
            return False

        cfg["cash"] -= cost

        if target:
            old_qty = float(target["qty"])
            old_cost = float(target["cost_price"])
            new_qty = old_qty + qty
            target["cost_price"] = round(((old_qty * old_cost) + cost) / new_qty, 4)
            target["qty"] = new_qty
        else:
            cfg["positions"].append(
                {
                    "symbol": symbol,
                    "name": name,
                    "weight": 0.0,
                    "qty": qty,
                    "cost_price": round(price, 4),
                    "thesis": reason or "AI 自动建仓",
                }
            )
    elif action in ("卖出", "减仓"):
        if not target or qty <= 0 or price <= 0:
            return False
        sell_qty = min(float(target["qty"]), qty)
        cfg["cash"] += price * sell_qty
        target["qty"] = float(target["qty"]) - sell_qty
        if target["qty"] <= 0:
            cfg["positions"] = [p for p in cfg["positions"] if p["symbol"] != symbol]
    else:
        return False

    quotes, _ = _load_quotes(strategy_key)
    total_equity = float(cfg["cash"])
    for item in cfg["positions"]:
        q = quotes.get(item["symbol"])
        px = q.price if q else float(item["cost_price"])
        total_equity += px * float(item["qty"])

    for item in cfg["positions"]:
        q = quotes.get(item["symbol"])
        px = q.price if q else float(item["cost_price"])
        value = px * float(item["qty"])
        item["weight"] = round(value / total_equity, 4) if total_equity > 0 else 0.0

    cfg["trades"].insert(
        0,
        {
            "ts": get_now_ts(),
            "name": name,
            "symbol": symbol,
            "action": action,
            "price": round(price, 4),
            "qty": qty,
            "reason": reason,
        },
    )
    cfg["trades"] = cfg["trades"][:20]
    return True

def reset_strategy(strategy_key: str) -> bool:
    if strategy_key not in STRATEGY_CONFIG or strategy_key not in INITIAL_STRATEGY_CONFIG:
        return False

    STRATEGY_CONFIG[strategy_key] = deepcopy(INITIAL_STRATEGY_CONFIG[strategy_key])
    return True
