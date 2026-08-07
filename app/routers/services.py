from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_services, create_service, update_service, delete_service
from app.schemas import ServiceCreate, ServiceUpdate

router = APIRouter(tags=["services"])


@router.get("/services")
async def list_services(user: dict = Depends(get_current_user)):
    return await get_services(user["id"])


@router.post("/services")
async def add_service(body: ServiceCreate, user: dict = Depends(get_current_user)):
    return await create_service(user["id"], body.name, body.description, body.duration, body.price, body.prepay)


@router.put("/services/{service_id}")
async def edit_service(service_id: int, body: ServiceUpdate, user: dict = Depends(get_current_user)):
    result = await update_service(service_id, user["id"], **body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Service not found")
    return result


@router.delete("/services/{service_id}")
async def remove_service(service_id: int, user: dict = Depends(get_current_user)):
    await delete_service(service_id, user["id"])
    return {"ok": True}


@router.get("/public/master/{master_id}/services")
async def public_services(master_id: int):
    return await get_services(master_id, active_only=True)
