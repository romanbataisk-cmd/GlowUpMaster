from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class Service(Base):
    __tablename__ = "services"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    master_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        default="",
    )
    duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )
    prepay: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )