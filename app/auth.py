import hashlib
import hmac
import json
import os
from urllib.parse import unquote
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


def validate_telegram_data(init_data: str) -> dict:
    """Validate Telegram WebApp initData, return user dict."""
    if DEV_MODE and init_data.startswith("dev:"):
        # Dev mode: "dev:12345678" → user_id
        user_id = int(init_data.split(":")[1])
        return {"id": user_id, "first_name": "Dev", "last_name": "User", "username": "devuser"}

    params = {}
    for part in init_data.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k] = unquote(v)

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, computed):
        raise HTTPException(status_code=401, detail="Invalid auth data")

    user_json = params.get("user", "{}")
    return json.loads(user_json)


async def get_current_user(authorization: str = Header(...)) -> dict:
    """FastAPI dependency — extracts and validates current user."""
    if not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    init_data = authorization[4:]
    return validate_telegram_data(init_data)
