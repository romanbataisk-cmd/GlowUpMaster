import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import master, services, schedule, bookings, clients, subscription


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="GlowUp Master API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(master.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(subscription.router, prefix="/api")

@app.get("/api/config")
async def get_config():
    return {
        "bot_username": os.getenv("BOT_USERNAME", ""),
        "webapp_url": os.getenv("WEBAPP_URL", ""),
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")
