from __future__ import annotations

from app.models import ResearchResponse


KEYWORDS = {
    "茅台": ("买入", "1980 元"),
    "宁德": ("增持", "215 元"),
    "平安": ("增持", "52 元"),
    "比亚迪": ("买入", "278 元"),
    "BTC": ("增持", "95000 USDT"),
    "ETH": ("增持", "5200 USDT"),
}


def generate_research(query: str) -> ResearchResponse:
    rating, target_price = ("中性", "待评估")
    for key, value in KEYWORDS.items():
        if key.lower() in query.lower():
            rating, target_price = value
            break
    summary = f"围绕 {query} 的基本面、估值与交易节奏进行综合判断，当前给出 {rating} 评级，目标价为 {target_price}。短期关注业绩、政策与市场风险偏好的边际变化。"
    report = (
        f"一、投资结论\n"
        f"我们对 {query} 给出 {rating} 评级，目标价 {target_price}。\n\n"
        f"二、核心逻辑\n"
        f"1. 行业景气与公司竞争力共同决定中期估值中枢。\n"
        f"2. 当前市场关注盈利兑现、现金流质量和风险偏好修复。\n"
        f"3. 若后续催化兑现，估值有望继续抬升。\n\n"
        f"三、主要催化剂\n"
        f"1. 财报超预期。\n2. 政策改善。\n3. 行业需求回暖。\n\n"
        f"四、风险提示\n"
        f"宏观波动、行业竞争加剧、市场风格切换均可能影响目标价兑现。"
    )
    return ResearchResponse(rating=rating, target_price=target_price, summary=summary, report=report)
