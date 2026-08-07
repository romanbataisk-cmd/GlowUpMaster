import os
import uuid
import math
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user
from app.database import (get_bookings, create_booking, update_booking_status,
                          get_available_slots, get_master)
from app.schemas import (BookingCreate, BookingStatusUpdate, PublicBookingCreate,
                        BookingPaymentCreate, StarsInvoiceCreate)

router = APIRouter(tags=["bookings"])


async def _get_bot():
    """Создаёт экземпляр aiogram Bot."""
    from aiogram import Bot
    return Bot(token=os.getenv("BOT_TOKEN", ""))


# ── Authenticated endpoints ───────────────────────────────────────────────────

@router.get("/bookings")
async def list_bookings(date: str = None, status: str = None,
                        user: dict = Depends(get_current_user)):
    return await get_bookings(user["id"], date=date, status=status)


@router.post("/bookings")
async def add_booking(body: BookingCreate, user: dict = Depends(get_current_user)):
    return await create_booking(
        user["id"], body.client_name, body.client_phone,
        body.service_id, body.date, body.time,
        client_id=body.client_id, notes=body.notes
    )


@router.put("/bookings/{booking_id}/status")
async def change_status(booking_id: int, body: BookingStatusUpdate,
                        user: dict = Depends(get_current_user)):
    valid = {"pending", "confirmed", "cancelled", "completed"}
    if body.status not in valid:
        raise HTTPException(400, f"Status must be one of: {valid}")
    result = await update_booking_status(booking_id, user["id"], body.status)
    if not result:
        raise HTTPException(404, "Booking not found")

    # Уведомить клиента при подтверждении или отмене
    client_tg_id = result.get("telegram_user_id")
    if client_tg_id and body.status in ("confirmed", "cancelled"):
        try:
            bot_token = os.getenv("BOT_TOKEN")
            if bot_token:
                master = await get_master(user["id"])
                master_name = master.get("full_name", "") if master else ""
                date_fmt = ".".join(reversed(result["date"].split("-")))
                if body.status == "confirmed":
                    msg = (f"✅ <b>Запись подтверждена!</b>\n\n"
                           f"Мастер <b>{master_name}</b> ждёт вас:\n"
                           f"💼 {result.get('service_name', '')}\n"
                           f"📅 {date_fmt} в {result['time']}")
                else:
                    msg = (f"❌ <b>Запись отменена</b>\n\n"
                           f"Мастер <b>{master_name}</b> отменил вашу запись:\n"
                           f"💼 {result.get('service_name', '')}\n"
                           f"📅 {date_fmt} в {result['time']}")
                bot = await _get_bot()
                await bot.send_message(chat_id=client_tg_id, text=msg, parse_mode="HTML")
                await bot.session.close()
        except Exception:
            pass
    return result


@router.get("/bookings/slots")
async def available_slots(date: str, service_id: int,
                          user: dict = Depends(get_current_user)):
    return await get_available_slots(user["id"], date, service_id)


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.get("/public/master/{master_id}")
async def public_master(master_id: int):
    master = await get_master(master_id)
    if not master:
        raise HTTPException(404, "Master not found")
    return {k: master[k] for k in ("telegram_id", "username", "full_name", "specialty", "bio")}


@router.get("/public/master/{master_id}/slots")
async def public_slots(master_id: int, date: str, service_id: int):
    return await get_available_slots(master_id, date, service_id)


# ВАЖНО: этот маршрут должен быть до /public/bookings/{master_id}
@router.post("/public/bookings/yookassa_webhook")
async def booking_yookassa_webhook(request: Request):
    """YooKassa webhook: создаёт запись после успешной оплаты картой."""
    try:
        body = await request.json()
        if body.get("event") == "payment.succeeded":
            meta = body.get("object", {}).get("metadata", {})
            if meta.get("type") == "booking":
                master_id = int(meta.get("master_id", 0))
                booking = await create_booking(
                    master_id,
                    meta.get("client_name", ""),
                    meta.get("client_phone", ""),
                    int(meta.get("service_id", 0)),
                    meta.get("date", ""),
                    meta.get("time", ""),
                    telegram_user_id=meta.get("telegram_user_id"),
                )
                await _notify_master_paid(master_id, booking, meta, paid_via="💳 Картой (ЮКасса)")
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/public/bookings/{master_id}")
async def public_create_booking(master_id: int, body: PublicBookingCreate):
    """Бесплатная запись от клиента."""
    slots = await get_available_slots(master_id, body.date, body.service_id)
    if body.time not in slots:
        raise HTTPException(400, "This time slot is no longer available")
    booking = await create_booking(
        master_id, body.client_name, body.client_phone,
        body.service_id, body.date, body.time,
        telegram_user_id=body.telegram_user_id
    )
    await _notify_master_new(master_id, booking, body)
    return booking


@router.post("/public/bookings/{master_id}/pay_yookassa")
async def create_booking_payment_yookassa(master_id: int, body: BookingPaymentCreate):
    """Создать ссылку на оплату через ЮКасса."""
    shop_id    = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")

    if not shop_id or not secret_key:
        raise HTTPException(400, "YooKassa не настроена")

    slots = await get_available_slots(master_id, body.date, body.service_id)
    if body.time not in slots:
        raise HTTPException(400, "Слот уже занят")

    try:
        from yookassa import Configuration, Payment
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key

        payload_meta = {
            "type": "booking",
            "master_id": str(master_id),
            "client_name": body.client_name,
            "client_phone": body.client_phone,
            "service_id": str(body.service_id),
            "date": body.date,
            "time": body.time,
            "telegram_username": body.telegram_username or "",
            "telegram_user_id": str(body.telegram_user_id or ""),
        }

        def _create():
            return Payment.create({
                "amount": {"value": f"{body.amount:.2f}", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{webapp_url}/book.html?master={master_id}&paid=1",
                },
                "capture": True,
                "description": f"Запись: {body.service_name}",
                "metadata": payload_meta,
                "notification_url": f"{webapp_url}/api/public/bookings/yookassa_webhook",
            }, str(uuid.uuid4()))

        payment = await asyncio.to_thread(_create)
        return {"payment_url": payment.confirmation.confirmation_url}
    except Exception as e:
        raise HTTPException(500, f"Ошибка создания платежа: {e}")


@router.post("/public/bookings/{master_id}/stars_invoice")
async def create_stars_invoice(master_id: int, body: StarsInvoiceCreate):
    """Создать ссылку на оплату через Telegram Stars."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise HTTPException(400, "Бот не настроен")

    stars = max(1, math.ceil(body.amount / 2))  # ~2 руб за 1 Stars

    try:
        from aiogram import Bot
        from aiogram.types import LabeledPrice

        payload_str = json.dumps({
            "type": "booking",
            "master_id": master_id,
            "client_name": body.client_name,
            "client_phone": body.client_phone,
            "service_id": body.service_id,
            "date": body.date,
            "time": body.time,
            "telegram_username": body.telegram_username,
            "telegram_user_id": body.telegram_user_id,
        })

        bot = Bot(token=bot_token)
        link = await bot.create_invoice_link(
            title=f"Запись: {body.service_name}",
            description=f"{body.date_fmt} в {body.time}",
            payload=payload_str,
            currency="XTR",
            prices=[LabeledPrice(label="Запись", amount=stars)],
        )
        await bot.session.close()
        return {"invoice_url": link, "stars": stars}
    except Exception as e:
        raise HTTPException(500, f"Ошибка создания инвойса: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _notify_master_new(master_id: int, booking: dict, body: PublicBookingCreate):
    """Отправить мастеру уведомление о новой записи."""
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            return
        date_fmt = ".".join(reversed(body.date.split("-")))
        tg_line = ""
        if body.telegram_username:
            tg_line = f'\n✈️ @{body.telegram_username}'
        elif body.telegram_user_id:
            tg_line = f'\n✈️ <a href="tg://user?id={body.telegram_user_id}">{body.client_name}</a>'
        msg = (f"🔔 <b>Новая запись!</b>\n\n"
               f"👤 {body.client_name}\n"
               f"📞 {body.client_phone}"
               f"{tg_line}\n"
               f"💼 {booking.get('service_name', '')}\n"
               f"📅 {date_fmt} в {body.time}")
        bot = await _get_bot()
        await bot.send_message(chat_id=master_id, text=msg, parse_mode="HTML")
        await bot.session.close()
    except Exception:
        pass


async def _notify_master_paid(master_id: int, booking: dict, meta: dict, paid_via: str):
    """Отправить мастеру уведомление об оплаченной записи."""
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            return
        date_fmt = ".".join(reversed(meta.get("date", "").split("-")))
        client_name = meta.get("client_name", "")
        tg_line = ""
        if meta.get("telegram_username"):
            tg_line = f'\n✈️ @{meta["telegram_username"]}'
        elif meta.get("telegram_user_id"):
            uid = meta["telegram_user_id"]
            tg_line = f'\n✈️ <a href="tg://user?id={uid}">{client_name}</a>'
        msg = (f"💰 <b>Новая оплаченная запись!</b>\n\n"
               f"👤 {client_name}\n"
               f"📞 {meta.get('client_phone', '')}"
               f"{tg_line}\n"
               f"💼 {booking.get('service_name', '')}\n"
               f"📅 {date_fmt} в {meta.get('time', '')}\n"
               f"✅ Оплачено: {paid_via}")
        bot = await _get_bot()
        await bot.send_message(chat_id=master_id, text=msg, parse_mode="HTML")
        await bot.session.close()
    except Exception:
        pass
