import os
import json
import requests


BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").strip().rstrip("/")
API_KEY = os.getenv("ARK_API_KEY", "").strip()
MODEL = os.getenv("ARK_MODEL", "").strip()
USE_REAL_AI = os.getenv("USE_REAL_AI", "false").strip().lower() == "true"


def _rule_fallback(strategy: str, symbol: str):
    return {
        "strategy": strategy,
        "action": "持有",
        "confidence": 0.72,
        "reason": "以控制回撤为核心，优先等待更有性价比的位置。",
        "risk_note": "避免追涨，单一标的仓位不宜过重。（真实AI调用失败，已回退规则引擎）",
        "symbol": symbol,
        "qty": 0,
        "mode": "rule",
        "raw_output": {},
    }


def _normalize_action(action: str) -> str:
    mapping = {
        "buy": "买入",
        "sell": "卖出",
        "hold": "持有",
        "increase": "加仓",
        "reduce": "减仓",
        "买入": "买入",
        "卖出": "卖出",
        "持有": "持有",
        "加仓": "加仓",
        "减仓": "减仓",
    }
    key = (action or "").strip()
    return mapping.get(key.lower(), mapping.get(key, "持有"))


def _call_ark(messages):
    if not API_KEY or not MODEL:
        raise ValueError("缺少 ARK_API_KEY 或 ARK_MODEL")

    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
    }

    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        json=body,
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Ark HTTP {resp.status_code}: {resp.text}")

    return resp.json()


def decide(strategy: str, symbol: str, market_data: dict, position: dict, account: dict, constraints: dict) -> dict:
    if not USE_REAL_AI:
        return _rule_fallback(strategy, symbol)

    system_prompt = (
        "你是一个A股短线交易决策助手。"
        "你必须只返回 JSON，不要输出 markdown，不要输出解释性前缀。"
        'JSON 格式为：{"action":"买入/卖出/持有/加仓/减仓","confidence":0到1之间的小数,'
        '"reason":"简短理由","risk_note":"风险提示","qty":整数}'
    )

    user_payload = {
        "strategy": strategy,
        "symbol": symbol,
        "market_data": market_data or {},
        "position": position or {},
        "account": account or {},
        "constraints": constraints or {},
    }

    try:
        result = _call_ark([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ])

        content = result["choices"][0]["message"]["content"].strip()

        try:
            parsed = json.loads(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(content[start:end + 1])
            else:
                raise ValueError(f"模型未返回合法 JSON: {content}")

        return {
            "strategy": strategy,
            "action": _normalize_action(parsed.get("action", "持有")),
            "confidence": float(parsed.get("confidence", 0.7)),
            "reason": parsed.get("reason", ""),
            "risk_note": parsed.get("risk_note", ""),
            "symbol": symbol,
            "qty": int(parsed.get("qty", 0)),
            "mode": "real_ai",
            "raw_output": result,
        }
    except Exception as e:
        import traceback
        print("AI_DECISION_ERROR:", repr(e))
        traceback.print_exc()
        return _rule_fallback(strategy, symbol)


def generate_decision(payload) -> dict:
    data = payload.dict() if hasattr(payload, "dict") else payload
    return decide(
        data.get("strategy", "金豆芽"),
        data.get("symbol", ""),
        data.get("market_data", {}),
        data.get("position", {}),
        data.get("account", {}),
        data.get("constraints", {}),
    )
