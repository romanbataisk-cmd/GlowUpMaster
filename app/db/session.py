from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


PROJECT_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_DIR / "glowup.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
engine = create_async_engine(DATABASE_URL)

SessionFactory = async_sessionmaker(
    bind= engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with SessionFactory() as session:
        yield session