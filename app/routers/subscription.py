import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user
from app.database import get_master, master_access, activate_subscription

router = APIRouter(tags=["subscription"])

PRICE_STARS = int(os.getenv("SUBSCRIPTION_PRICE_STARS", "299"))
PRICE_RUB   = int(os.getenv("SUBSCRIPTION_PRICE_RUB",   "299"))


@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    master = await get_master(user["id"])
    if not master:
        return {"active": False, "mode": "expired", "days_left": 0}
    return master_access(master)


@router.post("/subscription/activate")
async def manual_activate(user: dict = Depends(get_current_user)):
    """Called by bot after successful Telegram Stars payment."""
    await activate_subscription(user["id"], days=30)
    master = await get_master(user["id"])
    return master_access(master)


@router.get("/subscription/price")
async def get_price():
    return {"stars": PRICE_STARS, "rub": PRICE_RUB,
            "label": f"{PRICE_STARS} ⭐ / месяц"}


@router.post("/subscription/yookassa")
async def create_yookassa_subscription(user: dict = Depends(get_current_user)):
    """Create a YooKassa payment for subscription."""
    shop_id    = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")

    if not shop_id or not secret_key:
        raise HTTPException(400, "YooKassa не настроена. Добавьте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY в .env")

    try:
        from yookassa import Configuration, Payment
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key
        master_id = user["id"]

        def _create():
            return Payment.create({
                "amount": {"value": f"{PRICE_RUB}.00", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{webapp_url}/?sub_paid=1"
                },
                "capture": True,
                "description": "Подписка GlowUp Master — 30 дней",
                "metadata": {"type": "subscription", "master_id": str(master_id)},
                "notification_url": f"{webapp_url}/api/subscription/yookassa/webhook",
            }, str(uuid.uuid4()))

        payment = await asyncio.to_thread(_create)
        return {"payment_url": payment.confirmation.confirmation_url}
    except Exception as e:
        raise HTTPException(500, f"Ошибка создания платежа: {e}")


@router.post("/subscription/yookassa/webhook")
async def yookassa_sub_webhook(request: Request):
    """YooKassa webhook for subscription payments."""
    try:
        body = await request.json()
        if body.get("event") == "payment.succeeded":
            meta = body.get("object", {}).get("metadata", {})
            if meta.get("type") == "subscription":
                master_id = int(meta.get("master_id", 0))
                if master_id:
                    await activate_subscription(master_id, days=30)
    except Exception:
        pass
    return {"status": "ok"}
