from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "dev")
    frontend_origins: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500"
        ).split(",")
        if origin.strip()
    ]
    use_live_data: bool = os.getenv("USE_LIVE_DATA", "true").lower() == "true"
    news_use_rss: bool = os.getenv("NEWS_USE_RSS", "true").lower() == "true"

    use_real_ai: bool = os.getenv("USE_REAL_AI", "false").lower() == "true"
    ark_api_key: str = os.getenv("ARK_API_KEY", "")
    ark_base_url: str = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ark_model: str = os.getenv("ARK_MODEL", "")
    ark_timeout_seconds: int = int(os.getenv("ARK_TIMEOUT_SECONDS", "45"))
    ark_use_json_object: bool = os.getenv("ARK_USE_JSON_OBJECT", "true").lower() == "true"
    scheduler_secret: str = os.getenv("SCHEDULER_SECRET", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
