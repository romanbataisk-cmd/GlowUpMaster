import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000")
PRICE_STARS = int(os.getenv("SUBSCRIPTION_PRICE_STARS", "299"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "⌁ Найти студию рядом",
            web_app=WebAppInfo(url=f"{WEBAPP_URL.rstrip('/')}/discover.html")
        )],
        [InlineKeyboardButton(
            "✨ Кабинет мастера",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "🚀 <b>GlowUp Master</b> — управляй своими клиентами и записями прямо в Telegram.\n\n"
        "✅ Бесплатный пробный период — <b>7 дней</b>\n"
        "👑 Затем подписка GlowUp Master — всего 299 ⭐ в месяц",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send Telegram Stars invoice for subscription."""
    await update.message.reply_invoice(
        title="GlowUp Master — подписка",
        description="Полный доступ ко всем функциям на 30 дней: неограниченные записи, клиенты, расписание.",
        payload="glowup_subscription_30d",
        currency="XTR",
        prices=[LabeledPrice("GlowUp Master (30 дней)", PRICE_STARS)],
    )


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Activate subscription via DB directly
    import sys
    sys.path.insert(0, ".")
    from app.database import activate_subscription, init_db
    await init_db()
    await activate_subscription(user_id, days=30)
    await update.message.reply_text(
        "🎉 Оплата прошла успешно!\n\n"
        "👑 <b>GlowUp Master</b> активирован на 30 дней.\n"
        "Открывайте приложение и работайте!",
        parse_mode="HTML"
    )


def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: BOT_TOKEN не задан в .env")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", send_invoice))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    print("🤖 GlowUp Bot запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
