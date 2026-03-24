from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Tuple
from datetime import datetime

from app.models import Position, StrategySnapshot, TradeRecord
from app.services.market_data import Quote, fetch_a_share_quotes, get_now_ts


# 98只核心算力资产池 + 全市场热点标的
CORE_ASSETS = [
    # AI芯片/半导体
    ("688981", "中芯国际"), ("688256", "寒武纪"), ("688012", "中微公司"),
    ("002371", "北方华创"), ("688347", "华虹公司"), ("688608", "恒玄科技"),
    ("688521", "芯原股份"), ("688019", "安集科技"), ("688582", "芯动联科"),
    ("688325", "赛微微电"), ("688143", "长盈通"), ("600460", "士兰微"),
    ("002049", "紫光国微"), ("300672", "国科微"), ("300661", "圣邦股份"),
    ("688008", "澜起科技"), ("688048", "长光华芯"), ("688702", "盛科通信-U"),
    ("002156", "通富微电"), ("688183", "生益电子"), ("600183", "生益科技"),
    ("688411", "海博思创"), ("001389", "广合科技"), ("688662", "富信科技"),
    ("688525", "长芯博创"), ("688596", "正帆科技"), ("688401", "路维光电"),
    ("688629", "华丰科技"), ("688065", "凯赛生物"), ("603986", "兆易创新"),
    ("688148", "先导基电"), ("835179", "凯德石英"),
    
    # 光模块/CPO
    ("300308", "中际旭创"), ("300502", "新易盛"), ("300394", "天孚通信"),
    ("002281", "光迅科技"), ("300570", "太辰光"), ("601869", "长飞光纤"),
    ("688313", "仕佳光子"), ("688498", "源杰科技"), ("300757", "罗博特科"),
    ("300913", "兆龙互连"), ("603083", "剑桥科技"),
    
    # 服务器/PCB/算力硬件
    ("601138", "工业富联"), ("603019", "中科曙光"), ("000066", "中国长城"),
    ("002916", "深南电路"), ("002463", "沪电股份"), ("300476", "胜宏科技"),
    ("603228", "景旺电子"), ("300953", "震裕科技"), ("301607", "富特科技"),
    ("301392", "百川电子"), ("300625", "联合动力"), ("300870", "欧陆通"),
    
    # 算力应用/软件
    ("300418", "昆仑万维"), ("002261", "拓维信息"), ("600602", "云赛智联"),
    ("000158", "常山北明"), ("301165", "锐捷网络"), ("688072", "拓荆科技"),
    ("603236", "移远通信"), ("300236", "上海新阳"), ("300866", "安克创新"),
    ("002920", "德赛西威"), ("300587", "千里科技"), ("002179", "中航光电"),
    
    # 能源配套/储能/电力
    ("300750", "宁德时代"), ("300274", "阳光电源"), ("601012", "隆基绿能"),
    ("002837", "英维克"), ("300617", "明阳电气"), ("300499", "高澜股份"),
    ("300153", "科泰电源"), ("300068", "南都电源"), ("688800", "瑞可达"),
    ("002364", "中恒电气"), ("002922", "伊戈尔"), ("688676", "金盘科技"),
    ("002851", "麦格米特"), ("300990", "同飞股份"), ("603119", "浙江荣泰"),
    ("301155", "海力风电"), ("300748", "金力永磁"), ("002056", "横店东磁"),
    ("001267", "汇绿生态"), ("000338", "潍柴重机"),
    
    # 电力/核电
    ("601985", "中国核电"), ("600011", "华能国际"), ("600875", "东方电气"),
    ("002128", "电投能源"), ("002360", "华能蒙电"), ("300031", "中熔电气"),
]

# 决策时间点配置
DECISION_POINTS = ["09:30", "13:00", "14:50"]

STRATEGY_CONFIG: Dict[str, Dict] = {
    "momentum_trend": {
        "display_name": "趋势动量跟踪",
        "market_type": "stock",
        "strategy_type": "momentum_trend_following",
        "run_frequency": "09:30 / 13:00 / 14:50",
        "decision_points": DECISION_POINTS,
        "initial_capital": 2_000_000,
        "cash": 800_000,
        "max_leverage": 1.0,  # 1x杠杆，总购买力 = 净资产 × 2
        "symbols": [code for code, _ in CORE_ASSETS],
        "asset_pool": {code: {"name": name, "is_hot": False} for code, name in CORE_ASSETS},
        "positions": [
            {
                "symbol": "300308",
                "name": "中际旭创",
                "weight": 0.12,
                "qty": 800,
                "cost_price": 155.0,
                "thesis": "光模块龙头，AI算力核心标的，趋势强劲。",
                "t1_sellable": 800,  # T+1可卖数量
                "buy_date": "2026-03-20",
            },
            {
                "symbol": "688981",
                "name": "中芯国际",
                "weight": 0.10,
                "qty": 2000,
                "cost_price": 85.0,
                "thesis": "国产芯片代工龙头，算力基础设施核心。",
                "t1_sellable": 2000,
                "buy_date": "2026-03-19",
            },
            {
                "symbol": "300502",
                "name": "新易盛",
                "weight": 0.08,
                "qty": 600,
                "cost_price": 128.0,
                "thesis": "高速光模块供应商，受益于AI算力需求爆发。",
                "t1_sellable": 400,  # 部分T+1锁定
                "buy_date": "2026-03-21",
            },
            {
                "symbol": "688256",
                "name": "寒武纪",
                "weight": 0.06,
                "qty": 400,
                "cost_price": 245.0,
                "thesis": "AI芯片设计龙头，国产算力核心标的。",
                "t1_sellable": 400,
                "buy_date": "2026-03-18",
            },
            {
                "symbol": "300750",
                "name": "宁德时代",
                "weight": 0.05,
                "qty": 300,
                "cost_price": 210.0,
                "thesis": "储能+算力能源配套，趋势稳健。",
                "t1_sellable": 300,
                "buy_date": "2026-03-17",
            },
        ],
        "trades": [
            {"ts": "2026-03-24 10:30:00", "name": "中际旭创", "symbol": "300308", "action": "买入", "price": 168.5, "qty": 300, "reason": "价格突破前期阻力位，成交量配合动量增强。", "is_t1": True},
            {"ts": "2026-03-24 09:45:00", "name": "寒武纪", "symbol": "688256", "action": "加仓", "price": 258.0, "qty": 150, "reason": "AI芯片板块动量持续，趋势确认。", "is_t1": False},
            {"ts": "2026-03-23 14:50:00", "name": "新易盛", "symbol": "300502", "action": "买入", "price": 135.2, "qty": 200, "reason": "光模块板块突破，动量因子触发买入信号。", "is_t1": True},
            {"ts": "2026-03-23 11:20:00", "name": "中芯国际", "symbol": "688981", "action": "加仓", "price": 88.5, "qty": 500, "reason": "芯片代工需求增长，趋势健康。", "is_t1": False},
            {"ts": "2026-03-22 14:30:00", "name": "宁德时代", "symbol": "300750", "action": "减仓", "price": 218.0, "qty": 100, "reason": "动量减弱，锁定部分收益。", "is_t1": False},
            {"ts": "2026-03-22 10:15:00", "name": "中际旭创", "symbol": "300308", "action": "买入", "price": 162.0, "qty": 500, "reason": "算力板块趋势启动，价格突破确认。", "is_t1": False},
        ],
        "constraints": {
            "t1_enabled": True,  # T+1约束
            "lot_size": 100,     # 100股整数倍
            "max_single_position": 0.20,  # 单票最大20%
            "min_cash_ratio": 0.10,      # 最低现金比例10%
        }
    },
}


INITIAL_STRATEGY_CONFIG = deepcopy(STRATEGY_CONFIG)


def _load_quotes(strategy_key: str) -> Tuple[Dict[str, Quote], str]:
    cfg = STRATEGY_CONFIG[strategy_key]
    quotes = fetch_a_share_quotes(cfg["symbols"])
    source = next(iter(quotes.values())).source if quotes else "Fallback Template"
    return quotes, source


def get_account_status(strategy_key: str) -> Dict:
    """获取账户现状，用于AI决策上下文"""
    cfg = STRATEGY_CONFIG[strategy_key]
    quotes, _ = _load_quotes(strategy_key)
    
    positions_value = 0.0
    positions_detail = []
    
    for item in cfg["positions"]:
        quote = quotes.get(item["symbol"])
        current_price = quote.price if quote else item["cost_price"]
        market_value = current_price * item["qty"]
        positions_value += market_value
        
        positions_detail.append({
            "symbol": item["symbol"],
            "name": item["name"],
            "qty": item["qty"],
            "t1_sellable": item.get("t1_sellable", item["qty"]),
            "cost_price": item["cost_price"],
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "pnl_pct": round(((current_price - item["cost_price"]) / item["cost_price"] * 100), 2),
        })
    
    equity = cfg["cash"] + positions_value
    nav = equity / cfg["initial_capital"]
    
    # 计算购买力 (净资产 × 2 - 已用)
    max_purchase_power = equity * 2
    used_margin = positions_value
    available_purchase_power = max_purchase_power - used_margin
    
    return {
        "cash": cfg["cash"],
        "equity": round(equity, 2),
        "nav": round(nav, 4),
        "total_return_pct": round((nav - 1) * 100, 2),
        "positions_value": round(positions_value, 2),
        "available_purchase_power": round(available_purchase_power, 2),
        "positions": positions_detail,
        "constraints": cfg.get("constraints", {}),
    }


def get_market_context(strategy_key: str) -> Dict:
    """获取行情快照，用于AI决策上下文"""
    from app.services.news import get_news_summary_for_ai, update_asset_pool_hot_status
    
    cfg = STRATEGY_CONFIG[strategy_key]
    
    # 更新热点状态
    update_asset_pool_hot_status(cfg)
    
    quotes, source = _load_quotes(strategy_key)
    
    market_data = {}
    for symbol, quote in quotes.items():
        # 检查是否热点
        is_hot = cfg["asset_pool"].get(symbol, {}).get("is_hot", False)
        
        market_data[symbol] = {
            "name": quote.name,
            "current_price": quote.price,
            "prev_close": quote.extra.get("prev_close", quote.price),
            "change_pct": quote.change_pct,
            "high": quote.high,
            "low": quote.low,
            "volume": quote.volume,
            "is_hot": is_hot,
        }
    
    # 获取财讯摘要
    news_summary = get_news_summary_for_ai()
    
    return {
        "timestamp": get_now_ts(),
        "source": source,
        "data": market_data,
        "news_summary": news_summary,
    }


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


def _round_to_lot(qty: int, lot_size: int = 100) -> int:
    """将数量调整为整数倍"""
    return (qty // lot_size) * lot_size


def apply_decision_to_strategy(strategy_key: str, decision: Dict) -> bool:
    """应用AI决策到策略，包含T+1约束和风控检查"""
    if strategy_key not in STRATEGY_CONFIG:
        return False

    cfg = STRATEGY_CONFIG[strategy_key]
    constraints = cfg.get("constraints", {})
    
    symbol = (decision.get("symbol") or "").strip()
    action = (decision.get("action") or "").strip()
    qty = int(decision.get("qty") or 0)
    reason = (decision.get("reason") or "").strip()
    
    # 100股整数倍约束
    lot_size = constraints.get("lot_size", 100)
    qty = _round_to_lot(qty, lot_size)
    
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
    today = datetime.now().strftime("%Y-%m-%d")

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
                "is_t1": False,
            },
        )
        cfg["trades"] = cfg["trades"][:20]
        return True

    if action in ("买入", "加仓"):
        if qty <= 0 or price <= 0:
            return False
        
        # 检查单票仓位限制
        max_position = constraints.get("max_single_position", 0.20)
        cost = price * qty
        
        # 计算当前总权益
        positions_value = sum(p["qty"] * price for p in cfg["positions"])
        equity = cfg["cash"] + positions_value
        
        if target:
            target_value = (target["qty"] + qty) * price
        else:
            target_value = qty * price
        
        if target_value / equity > max_position:
            return False
        
        # 检查购买力 (1x杠杆)
        max_purchase_power = equity * 2
        used_margin = positions_value
        available_power = max_purchase_power - used_margin
        
        if cost > available_power:
            return False
        
        # 检查最低现金比例
        min_cash_ratio = constraints.get("min_cash_ratio", 0.10)
        if (cfg["cash"] - cost) / equity < min_cash_ratio:
            return False

        cfg["cash"] -= cost

        if target:
            old_qty = float(target["qty"])
            old_cost = float(target["cost_price"])
            new_qty = old_qty + qty
            target["cost_price"] = round(((old_qty * old_cost) + cost) / new_qty, 4)
            target["qty"] = new_qty
            # 更新T+1可卖数量（当日买入不可卖）
            target["t1_sellable"] = target.get("t1_sellable", old_qty)
        else:
            cfg["positions"].append(
                {
                    "symbol": symbol,
                    "name": name,
                    "weight": 0.0,
                    "qty": qty,
                    "cost_price": round(price, 4),
                    "thesis": reason or "AI 动量趋势跟踪建仓",
                    "t1_sellable": 0,  # 当日买入，T+1不可卖
                    "buy_date": today,
                }
            )
            
    elif action in ("卖出", "减仓"):
        if not target or qty <= 0 or price <= 0:
            return False
        
        # T+1约束检查
        if constraints.get("t1_enabled", True):
            t1_sellable = target.get("t1_sellable", target["qty"])
            if qty > t1_sellable:
                qty = t1_sellable  # 只能卖T+1可卖数量
        
        sell_qty = min(float(target["qty"]), qty)
        if sell_qty <= 0:
            return False
            
        cfg["cash"] += price * sell_qty
        target["qty"] = float(target["qty"]) - sell_qty
        target["t1_sellable"] = target.get("t1_sellable", target["qty"]) - sell_qty
        
        if target["qty"] <= 0:
            cfg["positions"] = [p for p in cfg["positions"] if p["symbol"] != symbol]
    else:
        return False

    # 更新权重
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
            "is_t1": action in ("买入", "加仓"),
        },
    )
    cfg["trades"] = cfg["trades"][:20]
    return True


def reset_strategy(strategy_key: str) -> bool:
    if strategy_key not in STRATEGY_CONFIG or strategy_key not in INITIAL_STRATEGY_CONFIG:
        return False

    STRATEGY_CONFIG[strategy_key] = deepcopy(INITIAL_STRATEGY_CONFIG[strategy_key])
    return True


def eod_processing(strategy_key: str) -> Dict:
    """日终结算：更新T+1可卖额度"""
    if strategy_key not in STRATEGY_CONFIG:
        return {}
    
    cfg = STRATEGY_CONFIG[strategy_key]
    today = datetime.now().strftime("%Y-%m-%d")
    
    for item in cfg["positions"]:
        buy_date = item.get("buy_date", today)
        if buy_date != today:
            # 非当日买入，全部可卖
            item["t1_sellable"] = item["qty"]
    
    # 生成结算报告
    snapshot = build_snapshot(strategy_key)
    
    return {
        "date": today,
        "nav": snapshot.nav,
        "total_return_pct": snapshot.total_return_pct,
        "cash": snapshot.cash,
        "positions_count": snapshot.holdings_count,
        "updated_at": get_now_ts(),
    }
