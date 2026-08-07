from pydantic import BaseModel, Field
from typing import Optional


class ProfileUpdate(BaseModel):
    full_name: str
    specialty: str = ""
    bio: str = ""
    phone: str = ""


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=1000)
    duration: int = Field(default=60, ge=15, le=480)
    price: float = Field(default=0, ge=0)
    prepay: float = Field(default=0, ge=0)


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[float] = None
    prepay: Optional[float] = None
    is_active: Optional[int] = None


class ScheduleDay(BaseModel):
    day: int
    start_time: str = "09:00"
    end_time: str = "21:00"
    is_working: int = 1


class ClientCreate(BaseModel):
    name: str
    phone: str = ""
    notes: str = ""


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class BookingCreate(BaseModel):
    client_name: str
    client_phone: str = ""
    service_id: int
    date: str
    time: str
    client_id: Optional[int] = None
    notes: str = ""


class BookingStatusUpdate(BaseModel):
    status: str  # pending | confirmed | cancelled | completed


class PublicBookingCreate(BaseModel):
    client_name: str
    client_phone: str
    service_id: int
    date: str
    time: str
    telegram_username: Optional[str] = None
    telegram_user_id: Optional[int] = None


class BookingPaymentCreate(BaseModel):
    client_name: str
    client_phone: str
    service_id: int
    service_name: str
    date: str
    time: str
    amount: float
    telegram_username: Optional[str] = None
    telegram_user_id: Optional[int] = None


class StarsInvoiceCreate(BaseModel):
    service_name: str
    service_id: int
    date: str
    date_fmt: str
    time: str
    amount: float
    client_name: str
    client_phone: str
    telegram_username: Optional[str] = None
    telegram_user_id: Optional[int] = None
