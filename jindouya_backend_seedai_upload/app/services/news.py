from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import List

import requests

from app.models import MarketNewsItem


TIMEOUT = 6
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def _fallback_news() -> List[MarketNewsItem]:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    items = [
        ("北向资金净流入回暖", "外资风险偏好改善，有利于权重蓝筹估值修复。", "偏多", "A股"),
        ("AI 产业链景气度持续", "算力、光模块与高景气科技成长板块仍可能反复活跃。", "偏多", "A股"),
        ("市场继续博弈政策与业绩双线索", "高股息与高景气成长仍可能轮动占优。", "中性", "A股"),
        ("美联储政策预期再平衡", "全球风险资产波动上升，A股风险偏好也可能受扰动。", "中性偏空", "全球市场"),
        ("券商板块成交活跃", "若风险偏好提升，金融权重有望接力稳定指数。", "偏多", "A股"),
    ]
    return [
        MarketNewsItem(ts=now, title=title, summary=summary, impact=impact, market_focus=focus)
        for title, summary, impact, focus in items
    ]


def _guess_impact(text: str) -> str:
    content = (text or "").lower()
    positive_words = ["上涨", "回暖", "增长", "利好", "突破", "走强", "净流入", "反弹", "修复"]
    negative_words = ["下跌", "承压", "回落", "利空", "风险", "波动", "流出", "走弱", "收紧"]
    pos = sum(1 for w in positive_words if w in content)
    neg = sum(1 for w in negative_words if w in content)
    if pos > neg:
        return "偏多"
    if neg > pos:
        return "偏空"
    return "中性"


def get_market_news() -> List[MarketNewsItem]:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        url = "https://news.google.com/rss/search?q=A%E8%82%A1%20OR%20%E6%B2%AA%E6%8C%87%20OR%20%E6%B7%B1%E6%88%90%E6%8C%87%20OR%20%E5%88%9B%E4%B8%9A%E6%9D%BF%20when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        resp = requests.get(url, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items: List[MarketNewsItem] = []

        for item in root.findall(".//item")[:10]:
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()

            text = f"{title} {description}"
            focus = "A股" if any(k in text for k in ["A股", "沪指", "深成指", "创业板", "北向资金", "券商", "白酒", "新能源"]) else "全球市场"

            items.append(
                MarketNewsItem(
                    ts=pub_date or now,
                    title=title[:120] or "市场资讯",
                    summary=(description or title)[:160],
                    impact=_guess_impact(text),
                    market_focus=focus,
                )
            )

        return items or _fallback_news()
    except Exception:
        return _fallback_news()