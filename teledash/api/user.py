import fastapi
from teledash import schemas as schemas
from teledash import config
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_db, get_async_session
from teledash.utils.db import user as uu
from teledash.utils.db import channel as uc
from teledash.utils.channel_messages import update_chats_periodically
from teledash.db import models as db_models
from teledash.utils.db import tg_client as ut
import asyncio
from teledash.utils import telegram
from teledash.utils.users import active_user


router = fastapi.APIRouter()
CHAT_UPDATE_TASKS = {}


@router.get("/api/active_collection_of_user")
async def get_current_active_collection_of_user(
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    try:        
        response = await uu.get_active_collection(db, user.id)
        return response
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400,
            detail=str(e)
        )
    

@router.post("/api/set_active_collection_of_user")
async def set_active_collection_of_user(
    collection_title: str,
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    collection_in_db = await uc.get_channel_collection(db, user.id, collection_title)
    if not collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=(f"'{collection_title}' collection not present in user account. " 
                "Can't set it as active."
            )
        )
    try:
        await uu.upsert_active_collection(db, user.id, collection_title)
        return {"status": "ok"}
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )


@router.get("/api/active_client_of_user")
async def get_current_active_client_of_user(
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    try:
        return await uu.get_active_client(db, user.id)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )


@router.post("/api/set_active_client_of_user")
async def set_active_client_of_user(
    client_id: str,
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    
    try:
        clients_of_user = await ut.get_user_clients(db, user)
        client_is_registered = any(x["client_id"] == client_id for x in clients_of_user)
        if not client_is_registered:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Client {client_id} not registered. Can't set it as active"
            )
        await uu.upsert_active_client(db, user.id, client_id)
        return {"status": "ok"}
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )


@router.get("/registered_clients")
async def get_registered_clients_of_user(
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    try:
        results = await ut.get_user_clients(db, user)
        return results
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    