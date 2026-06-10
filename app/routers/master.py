from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.database import upsert_master, update_master, get_master, master_access, get_stats
from app.models import ProfileUpdate

router = APIRouter(tags=["master"])


@router.get("/master/me")
async def get_me(user: dict = Depends(get_current_user)):
    master = await upsert_master(
        user["id"],
        user.get("username", ""),
        user.get("first_name", "") + " " + user.get("last_name", "")
    )
    access = master_access(master)
    stats = await get_stats(user["id"])
    return {**master, "access": access, "stats": stats}


@router.put("/master/profile")
async def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    master = await update_master(user["id"], **body.model_dump())
    return {**master, "access": master_access(master)}
