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


def fetch_crypto_quotes_binance(symbols: Iterable[str]) -> Dict[str, Quote]:
    symbols = [s.strip().replace("-", "") for s in symbols if s.strip()]
    if not symbols:
        return {}
    url = "https://api.binance.com/api/v3/ticker/24hr"
    resp = requests.get(url, params={"symbols": json.dumps(symbols)}, headers=UA, timeout=TIMEOUT)
    items = resp.json()
    result: Dict[str, Quote] = {}
    for item in items:
        sym = item["symbol"]
        human = sym.replace("USDT", "-USDT") if sym.endswith("USDT") else sym
        result[human] = Quote(
            symbol=human,
            name=human,
            price=float(item["lastPrice"]),
            change_pct=round(float(item["priceChangePercent"]), 2),
            high=float(item["highPrice"]),
            low=float(item["lowPrice"]),
            volume=float(item["volume"]),
            turnover=float(item["quoteVolume"]),
            extra={},
            source="Binance Public API",
        )
    return result


def fetch_crypto_quotes_okx(symbols: Iterable[str]) -> Dict[str, Quote]:
    result: Dict[str, Quote] = {}
    for symbol in [s.strip() for s in symbols if s.strip()]:
        url = "https://www.okx.com/api/v5/market/ticker"
        resp = requests.get(url, params={"instId": symbol}, headers=UA, timeout=TIMEOUT)
        payload = resp.json().get("data", [])
        if not payload:
            continue
        item = payload[0]
        result[symbol] = Quote(
            symbol=symbol,
            name=symbol,
            price=float(item["last"]),
            change_pct=0.0,
            high=float(item["high24h"]),
            low=float(item["low24h"]),
            volume=float(item["vol24h"]),
            turnover=float(item["volCcy24h"]),
            extra={},
            source="OKX Public API",
        )
    return result


def fetch_crypto_quotes(symbols: Iterable[str], provider: str = "binance") -> Dict[str, Quote]:
    try:
        if provider == "okx":
            data = fetch_crypto_quotes_okx(symbols)
            if data:
                return data
        data = fetch_crypto_quotes_binance(symbols)
        if data:
            return data
    except Exception:
        pass
    try:
        return fetch_crypto_quotes_okx(symbols)
    except Exception:
        return {}


def get_now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
