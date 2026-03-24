from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

from app.models import MarketNewsItem

TIMEOUT = 10
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# 热点关键词映射
HOT_KEYWORDS = {
    "AI": ["人工智能", "AI芯片", "算力", "大模型", "ChatGPT", "AIGC", "算力租赁"],
    "芯片": ["半导体", "芯片", "光刻机", "晶圆", "封测", "EDA", "国产替代"],
    "光模块": ["光模块", "CPO", "光通信", "光芯片", "800G", "1.6T"],
    "新能源": ["锂电池", "储能", "光伏", "风电", "宁德时代", "比亚迪"],
    "机器人": ["机器人", "人形机器人", "减速器", "伺服电机", "谐波减速器"],
    "汽车": ["新能源汽车", "智能驾驶", "激光雷达", "车联网", "汽车零部件"],
    "金融": ["券商", "银行", "保险", "金融科技", "数字货币"],
    "医药": ["创新药", "CXO", "医疗器械", "中药", "生物制药"],
}

# 股票代码映射（用于热点识别）
STOCK_KEYWORDS = {
    "300308": ["中际旭创", "光模块", "CPO"],
    "300502": ["新易盛", "光模块"],
    "688981": ["中芯国际", "芯片", "半导体"],
    "688256": ["寒武纪", "AI芯片", "算力"],
    "300750": ["宁德时代", "锂电池", "储能"],
    "601138": ["工业富联", "服务器", "算力"],
    "603019": ["中科曙光", "服务器", "算力"],
    "002371": ["北方华创", "半导体设备"],
    "300418": ["昆仑万维", "AI", "大模型"],
    "300274": ["阳光电源", "光伏", "储能"],
}


def _parse_time(ts_str: str) -> Optional[datetime]:
    """解析各种时间格式"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y年%m月%d日 %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def _get_time_bucket(dt: datetime) -> str:
    """根据时间分配到时段桶"""
    hour = dt.hour
    if 0 <= hour < 12:
        return "morning"  # 早间 00:00-11:59
    elif 12 <= hour < 16:
        return "noon"     # 午间 12:00-15:59
    else:
        return "evening"  # 晚间 16:00-23:59


def _guess_impact(text: str) -> str:
    """判断市场影响"""
    content = (text or "").lower()
    positive_words = ["上涨", "回暖", "增长", "利好", "突破", "走强", "净流入", "反弹", "修复", "大涨", "涨停", "飙升"]
    negative_words = ["下跌", "承压", "回落", "利空", "风险", "波动", "流出", "走弱", "收紧", "大跌", "跌停", "暴跌"]
    pos = sum(1 for w in positive_words if w in content)
    neg = sum(1 for w in negative_words if w in content)
    if pos > neg:
        return "偏多"
    if neg > pos:
        return "偏空"
    return "中性"


def _extract_hot_sectors(text: str) -> List[str]:
    """提取热点板块"""
    hot_sectors = []
    for sector, keywords in HOT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            hot_sectors.append(sector)
    return hot_sectors


def _extract_hot_stocks(text: str) -> List[str]:
    """提取热点股票代码"""
    hot_stocks = []
    for code, keywords in STOCK_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            hot_stocks.append(code)
    return hot_stocks


def _fallback_news() -> Dict[str, List[MarketNewsItem]]:
    """备用财讯数据"""
    now = datetime.now()
    
    morning_items = [
        ("北向资金净流入回暖", "外资风险偏好改善，有利于权重蓝筹估值修复。", "偏多", "A股"),
        ("AI 产业链景气度持续", "算力、光模块与高景气科技成长板块仍可能反复活跃。", "偏多", "A股"),
        ("券商板块成交活跃", "若风险偏好提升，金融权重有望接力稳定指数。", "偏多", "A股"),
    ]
    
    noon_items = [
        ("市场继续博弈政策与业绩双线索", "高股息与高景气成长仍可能轮动占优。", "中性", "A股"),
        ("光模块板块异动拉升", "中际旭创、新易盛等龙头放量上涨，资金关注度提升。", "偏多", "A股"),
    ]
    
    evening_items = [
        ("美联储政策预期再平衡", "全球风险资产波动上升，A股风险偏好也可能受扰动。", "中性偏空", "全球市场"),
        ("芯片板块尾盘走强", "国产替代逻辑持续发酵，中芯国际、寒武纪等获资金青睐。", "偏多", "A股"),
    ]
    
    def create_items(items, base_time):
        return [
            MarketNewsItem(
                ts=(base_time + timedelta(minutes=i*10)).strftime("%Y-%m-%d %H:%M:%S"),
                title=title,
                summary=summary,
                impact=impact,
                market_focus=focus,
                hot_sectors=_extract_hot_sectors(title + summary),
                hot_stocks=_extract_hot_stocks(title + summary),
            )
            for i, (title, summary, impact, focus) in enumerate(items)
        ]
    
    return {
        "morning": create_items(morning_items, now.replace(hour=9, minute=30)),
        "noon": create_items(noon_items, now.replace(hour=13, minute=0)),
        "evening": create_items(evening_items, now.replace(hour=20, minute=0)),
    }


def fetch_eastmoney_news() -> List[Dict]:
    """从东方财富获取7x24快讯"""
    try:
        url = "https://www.eastmoney.com/api/news/getNewsList"
        params = {
            "type": "7x24",
            "pageSize": 30,
        }
        resp = requests.get(url, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") == 0 and "data" in data:
            return data["data"]
        return []
    except Exception:
        return []


def fetch_10jqka_news() -> List[Dict]:
    """从同花顺获取财经快讯"""
    try:
        url = "https://basic.10jqka.com.cn/api/stockph/livenews"
        params = {
            "page": 1,
            "limit": 30,
        }
        resp = requests.get(url, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status_code") == 0 and "data" in data:
            return data["data"]
        return []
    except Exception:
        return []


def fetch_sina_finance_news() -> List[Dict]:
    """从新浪财经获取财经新闻"""
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        params = {
            "pageid": 153,
            "lid": 2516,
            "num": 30,
            "versionNumber": "1.2.4",
        }
        resp = requests.get(url, headers=UA, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("result") and "data" in data["result"]:
            return data["result"]["data"]
        return []
    except Exception:
        return []


def parse_news_item(item: Dict, source: str) -> Optional[MarketNewsItem]:
    """解析不同来源的新闻数据"""
    try:
        if source == "eastmoney":
            title = item.get("title", "")
            content = item.get("content", "")
            ts_str = item.get("showTime", "")
            
        elif source == "10jqka":
            title = item.get("title", "")
            content = item.get("content", "")
            ts_str = item.get("time", "")
            
        elif source == "sina":
            title = item.get("title", "")
            content = item.get("summary", "")
            ts_str = item.get("ctime", "")
            
        else:
            return None
        
        if not title:
            return None
        
        # 解析时间
        dt = _parse_time(ts_str) or datetime.now()
        
        # 合并文本用于分析
        full_text = f"{title} {content}"
        
        # 判断市场聚焦
        focus = "A股" if any(k in full_text for k in ["A股", "沪指", "深成指", "创业板", "北向资金", "券商", "白酒", "新能源", "芯片", "半导体"]) else "全球市场"
        
        return MarketNewsItem(
            ts=dt.strftime("%Y-%m-%d %H:%M:%S"),
            title=title[:120],
            summary=content[:200] if content else title[:160],
            impact=_guess_impact(full_text),
            market_focus=focus,
            hot_sectors=_extract_hot_sectors(full_text),
            hot_stocks=_extract_hot_stocks(full_text),
        )
    except Exception:
        return None


def get_market_news() -> Dict[str, List[MarketNewsItem]]:
    """获取分时段的市场财讯"""
    all_news = []
    
    # 聚合多个数据源
    sources = [
        (fetch_eastmoney_news(), "eastmoney"),
        (fetch_10jqka_news(), "10jqka"),
        (fetch_sina_finance_news(), "sina"),
    ]
    
    for news_list, source in sources:
        for item in news_list:
            parsed = parse_news_item(item, source)
            if parsed:
                all_news.append(parsed)
    
    # 如果没有获取到数据，使用备用数据
    if not all_news:
        return _fallback_news()
    
    # 按时间排序
    all_news.sort(key=lambda x: x.ts, reverse=True)
    
    # 分配到时段桶
    buckets = {"morning": [], "noon": [], "evening": []}
    
    for news in all_news:
        dt = _parse_time(news.ts)
        if dt:
            bucket = _get_time_bucket(dt)
            if len(buckets[bucket]) < 10:  # 每个时段最多10条
                buckets[bucket].append(news)
    
    # 确保每个时段都有数据
    fallback = _fallback_news()
    for bucket in buckets:
        if not buckets[bucket]:
            buckets[bucket] = fallback[bucket]
    
    return buckets


def get_news_summary_for_ai() -> Dict:
    """生成用于AI决策的财讯摘要"""
    buckets = get_market_news()
    
    # 提取热点板块和股票
    all_hot_sectors = set()
    all_hot_stocks = set()
    impact_summary = {"偏多": 0, "偏空": 0, "中性": 0}
    
    for bucket_name, items in buckets.items():
        for item in items:
            all_hot_sectors.update(item.hot_sectors or [])
            all_hot_stocks.update(item.hot_stocks or [])
            if item.impact in impact_summary:
                impact_summary[item.impact] += 1
    
    # 生成摘要文本
    summary_parts = []
    
    # 市场情绪
    if impact_summary["偏多"] > impact_summary["偏空"]:
        sentiment = "偏多"
    elif impact_summary["偏空"] > impact_summary["偏多"]:
        sentiment = "偏空"
    else:
        sentiment = "中性"
    
    summary_parts.append(f"市场情绪: {sentiment}")
    
    # 热点板块
    if all_hot_sectors:
        summary_parts.append(f"热点板块: {', '.join(list(all_hot_sectors)[:5])}")
    
    # 热点个股
    if all_hot_stocks:
        stock_names = []
        for code in list(all_hot_stocks)[:5]:
            for c, keywords in STOCK_KEYWORDS.items():
                if c == code:
                    stock_names.append(keywords[0])
                    break
        if stock_names:
            summary_parts.append(f"关注个股: {', '.join(stock_names)}")
    
    return {
        "sentiment": sentiment,
        "impact_distribution": impact_summary,
        "hot_sectors": list(all_hot_sectors)[:10],
        "hot_stocks": list(all_hot_stocks)[:10],
        "summary": "; ".join(summary_parts),
        "latest_news": [
            {
                "title": item.title,
                "impact": item.impact,
                "hot_sectors": item.hot_sectors,
            }
            for bucket in buckets.values()
            for item in bucket[:3]
        ],
    }


def update_asset_pool_hot_status(strategy_config: Dict) -> None:
    """更新资产池的热点标记状态"""
    news_summary = get_news_summary_for_ai()
    hot_stocks = set(news_summary.get("hot_stocks", []))
    
    asset_pool = strategy_config.get("asset_pool", {})
    for code in asset_pool:
        asset_pool[code]["is_hot"] = code in hot_stocks
