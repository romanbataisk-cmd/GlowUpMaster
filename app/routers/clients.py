from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_clients, create_client, update_client, delete_client, get_bookings
from app.models import ClientCreate, ClientUpdate

router = APIRouter(tags=["clients"])


@router.get("/clients")
async def list_clients(search: str = "", user: dict = Depends(get_current_user)):
    return await get_clients(user["id"], search=search)


@router.post("/clients")
async def add_client(body: ClientCreate, user: dict = Depends(get_current_user)):
    return await create_client(user["id"], body.name, body.phone, body.notes)


@router.put("/clients/{client_id}")
async def edit_client(client_id: int, body: ClientUpdate, user: dict = Depends(get_current_user)):
    result = await update_client(client_id, user["id"], **body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Client not found")
    return result


@router.delete("/clients/{client_id}")
async def remove_client(client_id: int, user: dict = Depends(get_current_user)):
    await delete_client(client_id, user["id"])
    return {"ok": True}


@router.get("/clients/{client_id}/bookings")
async def client_bookings(client_id: int, user: dict = Depends(get_current_user)):
    all_bookings = await get_bookings(user["id"])
    return [b for b in all_bookings if b.get("client_id") == client_id]
