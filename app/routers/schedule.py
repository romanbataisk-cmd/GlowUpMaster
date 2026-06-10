from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.database import get_schedule, save_schedule, get_days_off, toggle_day_off
from app.models import ScheduleDay
from typing import List

router = APIRouter(tags=["schedule"])


@router.get("/schedule")
async def get_my_schedule(user: dict = Depends(get_current_user)):
    return await get_schedule(user["id"])


@router.put("/schedule")
async def update_schedule(body: List[ScheduleDay], user: dict = Depends(get_current_user)):
    await save_schedule(user["id"], [d.model_dump() for d in body])
    return await get_schedule(user["id"])


@router.get("/days-off")
async def list_days_off(user: dict = Depends(get_current_user)):
    return await get_days_off(user["id"])


@router.post("/days-off/{date}")
async def toggle_off(date: str, user: dict = Depends(get_current_user)):
    await toggle_day_off(user["id"], date)
    return {"days_off": await get_days_off(user["id"])}
