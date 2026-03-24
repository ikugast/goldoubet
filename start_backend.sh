#!/bin/bash
cd /Users/bytedance/Downloads/jindouya_backend_seedai
set -a
source .env
export FRONTEND_ORIGINS="http://127.0.0.1:5500,http://localhost:5500,https://aidragon.pages.dev"
set +a
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
