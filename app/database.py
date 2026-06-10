import aiosqlite
from datetime import datetime, timedelta

DB = "glowup.db"


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS masters (
            telegram_id   INTEGER PRIMARY KEY,
            username      TEXT,
            full_name     TEXT NOT NULL DEFAULT '',
            specialty     TEXT DEFAULT '',
            bio           TEXT DEFAULT '',
            phone         TEXT DEFAULT '',
            trial_end     TEXT,
            sub_end       TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS services (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id   INTEGER NOT NULL,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            duration    INTEGER NOT NULL DEFAULT 60,
            price       REAL NOT NULL DEFAULT 0,
            prepay      REAL NOT NULL DEFAULT 0,
            is_active   INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id   INTEGER NOT NULL,
            day         INTEGER NOT NULL,
            start_time  TEXT NOT NULL DEFAULT '09:00',
            end_time    TEXT NOT NULL DEFAULT '21:00',
            is_working  INTEGER DEFAULT 1,
            UNIQUE(master_id, day)
        );
        CREATE TABLE IF NOT EXISTS days_off (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER NOT NULL,
            date      TEXT NOT NULL,
            UNIQUE(master_id, date)
        );
        CREATE TABLE IF NOT EXISTS clients (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id  INTEGER NOT NULL,
            name       TEXT NOT NULL,
            phone      TEXT DEFAULT '',
            notes      TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id         INTEGER NOT NULL,
            client_id         INTEGER,
            client_name       TEXT NOT NULL,
            client_phone      TEXT DEFAULT '',
            service_id        INTEGER NOT NULL,
            date              TEXT NOT NULL,
            time              TEXT NOT NULL,
            status            TEXT DEFAULT 'pending',
            notes             TEXT DEFAULT '',
            created_at        TEXT DEFAULT (datetime('now')),
            telegram_user_id  INTEGER
        );
        """)
        await db.commit()
        # migrations for existing databases
        for migration in [
            "ALTER TABLE bookings ADD COLUMN telegram_user_id INTEGER",
            "ALTER TABLE services ADD COLUMN prepay REAL NOT NULL DEFAULT 0",
        ]:
            try:
                await db.execute(migration)
                await db.commit()
            except Exception:
                pass


def row(r) -> dict:
    return dict(r) if r else None


def rows(rs) -> list:
    return [dict(r) for r in rs]


# ── Masters ──────────────────────────────────────────────────────────────────

async def upsert_master(telegram_id: int, username: str, full_name: str) -> dict:
    trial_end = (datetime.now() + timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO masters (telegram_id, username, full_name, trial_end)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username
        """, (telegram_id, username, full_name, trial_end))
        await db.commit()
        c = await db.execute("SELECT * FROM masters WHERE telegram_id = ?", (telegram_id,))
        return row(await c.fetchone())


async def get_master(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM masters WHERE telegram_id = ?", (telegram_id,))
        return row(await c.fetchone())


async def update_master(telegram_id: int, **fields) -> dict:
    allowed = {"full_name", "specialty", "bio", "phone"}
    data = {k: v for k, v in fields.items() if k in allowed}
    if not data:
        return await get_master(telegram_id)
    set_clause = ", ".join(f"{k} = ?" for k in data)
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(f"UPDATE masters SET {set_clause} WHERE telegram_id = ?",
                         [*data.values(), telegram_id])
        await db.commit()
        c = await db.execute("SELECT * FROM masters WHERE telegram_id = ?", (telegram_id,))
        return row(await c.fetchone())


def master_access(master: dict) -> dict:
    """Return subscription status info."""
    now = datetime.now()
    trial_ok = master.get("trial_end") and datetime.fromisoformat(master["trial_end"]) > now
    sub_ok = master.get("sub_end") and datetime.fromisoformat(master["sub_end"]) > now
    active = bool(trial_ok or sub_ok)
    days_left = 0
    if trial_ok:
        days_left = (datetime.fromisoformat(master["trial_end"]) - now).days + 1
        mode = "trial"
    elif sub_ok:
        days_left = (datetime.fromisoformat(master["sub_end"]) - now).days + 1
        mode = "subscription"
    else:
        mode = "expired"
    return {"active": active, "mode": mode, "days_left": days_left}


async def activate_subscription(telegram_id: int, days: int = 30):
    now = datetime.now()
    async with aiosqlite.connect(DB) as db:
        c = await db.execute("SELECT sub_end FROM masters WHERE telegram_id = ?", (telegram_id,))
        r = await c.fetchone()
        base = datetime.fromisoformat(r[0]) if r and r[0] and datetime.fromisoformat(r[0]) > now else now
        new_end = (base + timedelta(days=days)).isoformat()
        await db.execute("UPDATE masters SET sub_end = ? WHERE telegram_id = ?", (new_end, telegram_id))
        await db.commit()


# ── Services ─────────────────────────────────────────────────────────────────

async def get_services(master_id: int, active_only=False) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM services WHERE master_id = ?"
        if active_only:
            q += " AND is_active = 1"
        q += " ORDER BY id"
        c = await db.execute(q, (master_id,))
        return rows(await c.fetchall())


async def create_service(master_id: int, name: str, description: str, duration: int, price: float, prepay: float = 0) -> dict:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "INSERT INTO services (master_id, name, description, duration, price, prepay) VALUES (?,?,?,?,?,?)",
            (master_id, name, description, duration, price, prepay))
        await db.commit()
        c = await db.execute("SELECT * FROM services WHERE id = ?", (c.lastrowid,))
        return row(await c.fetchone())


async def update_service(service_id: int, master_id: int, **fields) -> dict | None:
    allowed = {"name", "description", "duration", "price", "prepay", "is_active"}
    data = {k: v for k, v in fields.items() if k in allowed}
    if not data:
        return None
    set_clause = ", ".join(f"{k} = ?" for k in data)
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            f"UPDATE services SET {set_clause} WHERE id = ? AND master_id = ?",
            [*data.values(), service_id, master_id])
        await db.commit()
        c = await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        return row(await c.fetchone())


async def delete_service(service_id: int, master_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM services WHERE id = ? AND master_id = ?", (service_id, master_id))
        await db.commit()


# ── Schedule ─────────────────────────────────────────────────────────────────

async def get_schedule(master_id: int) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM schedule WHERE master_id = ? ORDER BY day", (master_id,))
        existing = {r["day"]: dict(r) for r in await c.fetchall()}

    result = []
    defaults = [(0, "09:00", "21:00", 1), (1, "09:00", "21:00", 1), (2, "09:00", "21:00", 1),
                (3, "09:00", "21:00", 1), (4, "09:00", "21:00", 1), (5, "09:00", "21:00", 1),
                (6, "09:00", "21:00", 0)]
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for day, start, end, working in defaults:
        if day in existing:
            d = existing[day]
        else:
            d = {"master_id": master_id, "day": day, "start_time": start, "end_time": end, "is_working": working}
        d["day_name"] = day_names[day]
        result.append(d)
    return result


async def save_schedule(master_id: int, schedule: list):
    async with aiosqlite.connect(DB) as db:
        for item in schedule:
            await db.execute("""
                INSERT INTO schedule (master_id, day, start_time, end_time, is_working)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(master_id, day) DO UPDATE SET
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    is_working = excluded.is_working
            """, (master_id, item["day"], item["start_time"], item["end_time"], item["is_working"]))
        await db.commit()


async def get_days_off(master_id: int) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT date FROM days_off WHERE master_id = ? ORDER BY date", (master_id,))
        return [r["date"] for r in await c.fetchall()]


async def toggle_day_off(master_id: int, date: str):
    async with aiosqlite.connect(DB) as db:
        c = await db.execute("SELECT id FROM days_off WHERE master_id = ? AND date = ?", (master_id, date))
        if await c.fetchone():
            await db.execute("DELETE FROM days_off WHERE master_id = ? AND date = ?", (master_id, date))
        else:
            await db.execute("INSERT INTO days_off (master_id, date) VALUES (?, ?)", (master_id, date))
        await db.commit()


# ── Clients ──────────────────────────────────────────────────────────────────

async def get_clients(master_id: int, search: str = "") -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        if search:
            c = await db.execute(
                "SELECT * FROM clients WHERE master_id = ? AND (name LIKE ? OR phone LIKE ?) ORDER BY name",
                (master_id, f"%{search}%", f"%{search}%"))
        else:
            c = await db.execute("SELECT * FROM clients WHERE master_id = ? ORDER BY name", (master_id,))
        return rows(await c.fetchall())


async def create_client(master_id: int, name: str, phone: str, notes: str) -> dict:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "INSERT INTO clients (master_id, name, phone, notes) VALUES (?, ?, ?, ?)",
            (master_id, name, phone, notes))
        await db.commit()
        c = await db.execute("SELECT * FROM clients WHERE id = ?", (c.lastrowid,))
        return row(await c.fetchone())


async def update_client(client_id: int, master_id: int, **fields) -> dict | None:
    allowed = {"name", "phone", "notes"}
    data = {k: v for k, v in fields.items() if k in allowed}
    if not data:
        return None
    set_clause = ", ".join(f"{k} = ?" for k in data)
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(f"UPDATE clients SET {set_clause} WHERE id = ? AND master_id = ?",
                         [*data.values(), client_id, master_id])
        await db.commit()
        c = await db.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        return row(await c.fetchone())


async def delete_client(client_id: int, master_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM clients WHERE id = ? AND master_id = ?", (client_id, master_id))
        await db.commit()


# ── Bookings ─────────────────────────────────────────────────────────────────

async def get_bookings(master_id: int, date: str = None, status: str = None) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        q = """
            SELECT b.*, s.name as service_name, s.duration, s.price
            FROM bookings b
            JOIN services s ON b.service_id = s.id
            WHERE b.master_id = ?
        """
        params = [master_id]
        if date:
            q += " AND b.date = ?"
            params.append(date)
        if status:
            q += " AND b.status = ?"
            params.append(status)
        q += " ORDER BY b.date, b.time"
        c = await db.execute(q, params)
        return rows(await c.fetchall())


async def create_booking(master_id: int, client_name: str, client_phone: str,
                         service_id: int, date: str, time: str,
                         client_id: int = None, notes: str = "",
                         telegram_user_id: int = None) -> dict:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("""
            INSERT INTO bookings (master_id, client_id, client_name, client_phone, service_id, date, time, notes, telegram_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (master_id, client_id, client_name, client_phone, service_id, date, time, notes, telegram_user_id))
        await db.commit()
        c = await db.execute("""
            SELECT b.*, s.name as service_name, s.duration, s.price
            FROM bookings b JOIN services s ON b.service_id = s.id
            WHERE b.id = ?
        """, (c.lastrowid,))
        return row(await c.fetchone())


async def update_booking_status(booking_id: int, master_id: int, status: str) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE bookings SET status = ? WHERE id = ? AND master_id = ?",
            (status, booking_id, master_id))
        await db.commit()
        c = await db.execute("""
            SELECT b.*, s.name as service_name, s.duration, s.price
            FROM bookings b JOIN services s ON b.service_id = s.id
            WHERE b.id = ?
        """, (booking_id,))
        return row(await c.fetchone())


async def get_available_slots(master_id: int, date: str, service_id: int) -> list:
    """Returns list of available time strings for a given date and service."""
    from datetime import datetime as dt, timedelta

    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row

        # Get service duration
        c = await db.execute("SELECT duration FROM services WHERE id = ? AND master_id = ?", (service_id, master_id))
        svc = await c.fetchone()
        if not svc:
            return []
        duration = svc["duration"]

        # Check if day off
        c = await db.execute("SELECT 1 FROM days_off WHERE master_id = ? AND date = ?", (master_id, date))
        if await c.fetchone():
            return []

        # Get working hours for this weekday
        weekday = dt.strptime(date, "%Y-%m-%d").weekday()
        c = await db.execute(
            "SELECT start_time, end_time, is_working FROM schedule WHERE master_id = ? AND day = ?",
            (master_id, weekday))
        sched = await c.fetchone()
        if sched:
            if not sched["is_working"]:
                return []
            start_h, start_m = map(int, sched["start_time"].split(":"))
            end_h, end_m = map(int, sched["end_time"].split(":"))
        else:
            start_h, start_m = 9, 0
            end_h, end_m = 21, 0

        # Get booked slots
        c = await db.execute("""
            SELECT b.time, s.duration FROM bookings b
            JOIN services s ON b.service_id = s.id
            WHERE b.master_id = ? AND b.date = ? AND b.status NOT IN ('cancelled')
        """, (master_id, date))
        booked = [(r["time"], r["duration"]) for r in await c.fetchall()]

    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    booked_ranges = [(to_minutes(t), to_minutes(t) + d) for t, d in booked]

    slots = []
    cur = start_h * 60 + start_m
    end = end_h * 60 + end_m

    # Don't show slots in the past for today
    now = dt.now()
    today = now.strftime("%Y-%m-%d")
    min_cur = 0
    if date == today:
        min_cur = now.hour * 60 + now.minute + 30

    while cur + duration <= end:
        if cur >= min_cur:
            slot_end = cur + duration
            conflict = any(s < slot_end and cur < e for s, e in booked_ranges)
            if not conflict:
                slots.append(f"{cur // 60:02d}:{cur % 60:02d}")
        cur += 30
    return slots


async def get_stats(master_id: int) -> dict:
    from datetime import datetime as dt
    today = dt.now().strftime("%Y-%m-%d")
    week_start = (dt.now() - timedelta(days=dt.now().weekday())).strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB) as db:
        c = await db.execute(
            "SELECT COUNT(*) FROM bookings WHERE master_id = ? AND date = ? AND status != 'cancelled'",
            (master_id, today))
        today_count = (await c.fetchone())[0]

        c = await db.execute(
            "SELECT COUNT(*) FROM bookings WHERE master_id = ? AND date >= ? AND status != 'cancelled'",
            (master_id, week_start))
        week_count = (await c.fetchone())[0]

        c = await db.execute("SELECT COUNT(*) FROM clients WHERE master_id = ?", (master_id,))
        clients_count = (await c.fetchone())[0]

        c = await db.execute(
            "SELECT COALESCE(SUM(s.price),0) FROM bookings b JOIN services s ON b.service_id=s.id "
            "WHERE b.master_id = ? AND b.date >= ? AND b.status = 'completed'",
            (master_id, week_start))
        week_revenue = (await c.fetchone())[0]

    return {
        "today_bookings": today_count,
        "week_bookings": week_count,
        "total_clients": clients_count,
        "week_revenue": round(week_revenue, 2),
    }
