# 金豆芽后端（真实AI决策版）

这版在真实行情基础上，增加了火山方舟 Seed 模型的真实AI决策。

## 1. 启动
```bash
cd ~/Downloads/jindouya_backend_seedai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 2. 配置火山方舟
编辑 `.env`：
```env
USE_REAL_AI=true
ARK_API_KEY=你的API Key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=你控制台里的模型ID
```

如果不填 `ARK_API_KEY` 或 `ARK_MODEL`，`/api/strategies/decision` 会自动回退到规则引擎，不会报死。

## 3. 核对接口
- `GET /healthz`
- `GET /api/admin/ai/ping`
- `POST /api/strategies/decision`

## 4. decision 示例
```json
{
  "strategy": "stock_steady",
  "symbol": "600519",
  "market_data": {
    "price": 1688,
    "change_pct": 1.42,
    "volume_ratio": 1.3
  },
  "position": {
    "has_position": true,
    "qty": 120,
    "cost_price": 1620
  },
  "account": {
    "cash": 402500,
    "nav": 1.0234
  },
  "constraints": {
    "max_single_position_pct": 0.25,
    "max_daily_trades": 3
  }
}
```

## 5. 返回示例
```json
{
  "strategy": "stock_steady",
  "action": "持有",
  "confidence": 0.82,
  "reason": "估值与趋势尚可，继续持有观察。",
  "risk_note": "注意消费板块回撤风险。",
  "symbol": "600519",
  "qty": 0,
  "mode": "real_ai",
  "raw_output": {
    "action": "hold",
    "symbol": "600519",
    "qty": 0,
    "confidence": 0.82,
    "reason": "估值与趋势尚可，继续持有观察。",
    "risk_note": "注意消费板块回撤风险。"
  }
}
```
