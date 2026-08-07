"""
GlowUp Master — единый лаунчер
Запускает: FastAPI сервер + SSH туннель + Telegram бот (aiogram 3)
"""
import asyncio
import os
import json
import subprocess
import sys
import time
import threading

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv, set_key
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


def banner(text):
    print(f"\n  {'='*44}")
    print(f"  {text}")
    print(f"  {'='*44}")


def kill_bot_processes():
    """Убить другие запущенные экземпляры бота."""
    import signal
    try:
        result = subprocess.run(
            ["pgrep", "-f", "launch.py"],
            capture_output=True, text=True
        )
        current_pid = str(os.getpid())
        pids = [p for p in result.stdout.strip().split() if p and p != current_pid]
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
                print(f"  ⚠ Остановлен старый процесс бота (PID {pid})")
            except Exception:
                pass
        if pids:
            time.sleep(1)
    except Exception:
        pass


def free_port(port: int):
    """Убить процесс, занимающий порт."""
    import signal
    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGKILL)
                print(f"  ⚠ Освобождён порт {port} (PID {pid})")
        if pids:
            time.sleep(1)
    except Exception:
        pass


def start_server():
    """Запустить FastAPI в подпроцессе."""
    print("  [1/3] Запуск FastAPI сервера...")
    free_port(8000)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    if proc.poll() is not None:
        print("  ОШИБКА: сервер не запустился")
        sys.exit(1)
    print("  ✓ Сервер: http://localhost:8000")
    return proc


def start_tunnel():
    """Запустить ngrok и получить HTTPS-адрес."""
    print("  [2/3] Создание HTTPS туннеля через ngrok...")

    tunnel_url = [None]

    def run_tunnel():
        cmd = ["ngrok", "http", "8000", "--log", "stdout", "--log-format", "json"]
        static_domain = os.getenv("NGROK_DOMAIN", "")
        if static_domain:
            cmd += ["--domain", static_domain]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        for line in proc.stdout:
            try:
                data = json.loads(line)
                if data.get("msg") == "started tunnel":
                    url = data.get("url", "")
                    if url.startswith("https://"):
                        tunnel_url[0] = url
            except Exception:
                pass

    t = threading.Thread(target=run_tunnel, daemon=True)
    t.start()

    for _ in range(20):
        time.sleep(1)
        if tunnel_url[0]:
            break

    if not tunnel_url[0]:
        print("  ⚠ ngrok не запустился.")
        print("    Убедитесь что ngrok настроен: ngrok config add-authtoken <TOKEN>")
        print("    Токен: https://dashboard.ngrok.com/get-started/your-authtoken")
        return None

    print(f"  ✓ Туннель: {tunnel_url[0]}")
    return tunnel_url[0]


async def setup_bot_menu(webapp_url: str):
    """Установить кнопку меню бота."""
    from aiogram import Bot
    from aiogram.types import MenuButtonWebApp, WebAppInfo

    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        print(f"  ✓ Бот: @{me.username}")
        set_key(ENV_FILE, "BOT_USERNAME", me.username)

        discover_url = f"{webapp_url.rstrip('/')}/discover.html"
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="⌁ Студии рядом",
                web_app=WebAppInfo(url=discover_url)
            )
        )
        print(f"  ✓ Кнопка приложения установлена → {webapp_url}")
    except Exception as e:
        print(f"  ⚠ Не удалось настроить кнопку: {e}")
    finally:
        await bot.session.close()


async def run_bot(webapp_url: str):
    """Запустить Telegram-бот на aiogram 3."""
    from aiogram import Bot, Dispatcher, F
    from aiogram.types import (
        Message, InlineKeyboardMarkup, InlineKeyboardButton,
        WebAppInfo, LabeledPrice, PreCheckoutQuery
    )
    from aiogram.filters import CommandStart, Command
    from aiogram.filters.command import CommandObject

    os.environ["WEBAPP_URL"] = webapp_url

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ── /start ────────────────────────────────────────────────────────────────
    @dp.message(CommandStart())
    async def cmd_start(message: Message, command: CommandObject):
        user = message.from_user
        args = command.args or ""

        # Deep link: /start book_MASTERID
        if args.startswith("book_"):
            master_id = args[5:]
            booking_url = f"{webapp_url}/book.html?master={master_id}"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📅 Записаться к мастеру",
                    web_app=WebAppInfo(url=booking_url)
                )
            ]])
            await message.answer(
                f"Привет, {user.first_name}! 👋\n\nНажмите кнопку ниже, чтобы выбрать удобное время:",
                reply_markup=keyboard
            )
            return

        # Deep link: /start subscribe
        if args == "subscribe":
            await send_invoice(message)
            return

        # Обычный запуск
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="⌁ Найти студию рядом",
                web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/discover.html")
            )],
            [InlineKeyboardButton(
                text="✨ Кабинет мастера",
                web_app=WebAppInfo(url=webapp_url)
            )]
        ])
        await message.answer(
            f"Привет, {user.first_name}! 👋\n\n"
            "🚀 <b>GlowUp Master</b> — управляй клиентами и записями прямо в Telegram.\n\n"
            "✅ Пробный период — <b>7 дней бесплатно</b>\n"
            "👑 Подписка — <b>299 ⭐ в месяц</b>\n\n"
            "Нажмите кнопку ниже чтобы открыть приложение:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    # ── /subscribe ────────────────────────────────────────────────────────────
    @dp.message(Command("subscribe"))
    async def cmd_subscribe(message: Message):
        await send_invoice(message)

    async def send_invoice(message: Message):
        await message.answer_invoice(
            title="GlowUp Master — подписка",
            description="Полный доступ на 30 дней: неограниченные записи, клиенты, расписание.",
            payload="glowup_sub_30d",
            currency="XTR",
            prices=[LabeledPrice(label="GlowUp Master (30 дней)", amount=299)],
        )

    # ── Pre-checkout ──────────────────────────────────────────────────────────
    @dp.pre_checkout_query()
    async def on_pre_checkout(query: PreCheckoutQuery):
        await query.answer(ok=True)

    # ── Successful payment ────────────────────────────────────────────────────
    @dp.message(F.successful_payment)
    async def on_successful_payment(message: Message):
        import json as _json
        from app.database import init_db

        await init_db()
        payment = message.successful_payment

        try:
            payload = _json.loads(payment.invoice_payload)
            pay_type = payload.get("type", "subscription")
        except Exception:
            pay_type = "subscription"

        if pay_type == "booking":
            from app.database import create_booking
            try:
                master_id = int(payload["master_id"])
                booking = await create_booking(
                    master_id,
                    payload.get("client_name", ""),
                    payload.get("client_phone", ""),
                    int(payload.get("service_id", 0)),
                    payload.get("date", ""),
                    payload.get("time", ""),
                    telegram_user_id=payload.get("telegram_user_id"),
                )
                date_fmt = ".".join(reversed(payload["date"].split("-")))
                await message.answer(
                    f"✅ <b>Оплата получена! Запись подтверждена.</b>\n\n"
                    f"💼 {booking.get('service_name', '')}\n"
                    f"📅 {date_fmt} в {payload['time']}",
                    parse_mode="HTML"
                )
                # Уведомить мастера
                try:
                    client_name = payload.get("client_name", "")
                    tg_uname = payload.get("telegram_username")
                    tg_uid   = payload.get("telegram_user_id")
                    tg_line  = ""
                    if tg_uname:
                        tg_line = f"\n✈️ @{tg_uname}"
                    elif tg_uid:
                        tg_line = f'\n✈️ <a href="tg://user?id={tg_uid}">{client_name}</a>'
                    msg = (f"⭐ <b>Новая оплаченная запись (Stars)!</b>\n\n"
                           f"👤 {client_name}\n"
                           f"📞 {payload.get('client_phone', '')}"
                           f"{tg_line}\n"
                           f"💼 {booking.get('service_name', '')}\n"
                           f"📅 {date_fmt} в {payload['time']}")
                    await bot.send_message(chat_id=master_id, text=msg, parse_mode="HTML")
                except Exception:
                    pass
            except Exception:
                await message.answer("✅ Оплата получена!")
        else:
            # Подписка
            from app.database import activate_subscription
            await activate_subscription(message.from_user.id, days=30)
            await message.answer(
                "🎉 <b>Оплата прошла!</b>\n\nGlowUp Master активирован на 30 дней.",
                parse_mode="HTML"
            )

    print("  ✓ Бот запущен и ожидает сообщений...\n")
    await dp.start_polling(bot)
    await bot.session.close()


def main():
    banner("GlowUp Master — запуск")
    print()

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("  ОШИБКА: BOT_TOKEN не задан в .env")
        sys.exit(1)

    kill_bot_processes()

    # 1. Сервер
    server_proc = start_server()

    # 2. Туннель
    # Если в .env уже есть статический домен — передаём его ngrok как --domain
    # и всё равно запускаем ngrok, чтобы туннель был активен
    static_domain = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
    if static_domain.startswith("https://"):
        domain = static_domain.replace("https://", "")
        os.environ["NGROK_DOMAIN"] = domain
        print(f"  [2/3] Запуск ngrok со статическим доменом: {domain}")
    webapp_url = start_tunnel()

    if not webapp_url:
        print()
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║  ngrok не настроен — бот не может стартовать ║")
        print("  ║  Telegram требует HTTPS для Mini App          ║")
        print("  ╠══════════════════════════════════════════════╣")
        print("  ║  Варианты:                                    ║")
        print("  ║                                               ║")
        print("  ║  1) Установить и настроить ngrok:             ║")
        print("  ║     https://ngrok.com/download                ║")
        print("  ║     ngrok config add-authtoken <TOKEN>        ║")
        print("  ║                                               ║")
        print("  ║  2) Вписать готовый HTTPS-URL в .env:         ║")
        print("  ║     WEBAPP_URL=https://ваш-сайт.ru            ║")
        print("  ╚══════════════════════════════════════════════╝")
        print()
        print("  FastAPI сервер работает: http://localhost:8000")
        print("  API docs: http://localhost:8000/docs")
        print()
        input("  Нажмите Enter для остановки...")
        server_proc.terminate()
        sys.exit(0)

    set_key(ENV_FILE, "WEBAPP_URL", webapp_url)

    # 3. Кнопка меню бота
    asyncio.run(setup_bot_menu(webapp_url))

    banner("Всё запущено!")
    print(f"\n  Приложение:  {webapp_url}")
    print(f"  API docs:    http://localhost:8000/docs")
    print(f"\n  Открой бота в Telegram и нажми кнопку!")
    print(f"\n  Для остановки нажми Ctrl+C\n")

    # 4. Бот (блокирующий)
    try:
        asyncio.run(run_bot(webapp_url))
    except KeyboardInterrupt:
        print("\n  Остановка...")
    finally:
        server_proc.terminate()
        print("  Сервер остановлен.")


if __name__ == "__main__":
    main()
