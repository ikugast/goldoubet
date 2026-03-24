from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import requests


TIMEOUT = 6
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    change_pct: float
    high: float
    low: float
    volume: float
    turnover: float
    extra: Dict[str, float | str]
    source: str


def _cn_code(symbol: str) -> str:
    symbol = symbol.strip()
    if symbol.startswith(("5", "6", "9")):
        return f"sh{symbol}"
    return f"sz{symbol}"


def fetch_a_share_quotes(symbols: Iterable[str]) -> Dict[str, Quote]:
    symbols = [s.strip() for s in symbols if s.strip()]
    if not symbols:
        return {}
    url = "https://qt.gtimg.cn/q=" + ",".join(_cn_code(s) for s in symbols)
    text = requests.get(url, headers=UA, timeout=TIMEOUT).text
    result: Dict[str, Quote] = {}
    for line in text.split(";"):
        if "~" not in line:
            continue
        parts = line.split("~")
        if len(parts) < 38:
            continue
        try:
            code = parts[2].strip()
            name = parts[1].strip() or code
            price = float(parts[3])
            close_prev = float(parts[4]) if parts[4] else price
            high = float(parts[33]) if parts[33] else price
            low = float(parts[34]) if parts[34] else price
            volume = float(parts[36]) if parts[36] else 0.0
            turnover = float(parts[37]) if parts[37] else 0.0
            change_pct = ((price - close_prev) / close_prev * 100) if close_prev else 0.0
            result[code] = Quote(
                symbol=code,
                name=name,
                price=price,
                change_pct=round(change_pct, 2),
                high=high,
                low=low,
                volume=volume,
                turnover=turnover,
                extra={"prev_close": close_prev},
                source="Tencent Quote",
            )
        except (TypeError, ValueError):
            continue
    return result


def get_now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
