import fastapi
from teledash import schemas as schemas
from teledash import config
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_db, get_async_session
from teledash.utils.db import user as uu
from teledash.utils.db import channel as uc
from teledash.channel_messages import update_chats_periodically
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
    
# @router.put("/api/set_chat_update_task")
# async def set_chat_update_task_for_user_and_active_client(
#     request: fastapi.Request,
#     # collection: str,
#     client_id: str, period: int=60*60,
#     db: Session=fastapi.Depends(get_db), 
#     user=fastapi.Depends(config.settings.MANAGER)
# ):
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         print(f"client of {user.username} is None")
#         tg_client = await telegram.get_authenticated_client(client_id)
#         if tg_client is None:
#             raise fastapi.HTTPException(
#                 status_code=400, detail=f"client {client_id} is no usable")
#         request.app.state.clients[client_id] = tg_client
#     user_task = CHAT_UPDATE_TASKS.get(user.id)
#     if user_task:
#         CHAT_UPDATE_TASKS[user.id].cancel()
#         CHAT_UPDATE_TASKS.pop(user.id) 
#     channel_urls = [x["url"] for x in uu.get_all_channel_urls(db, user.id)]
#     if not channel_urls:
#         return {
#             "status": "fail",
#             "detail": "no channels present in user account or no registered collection"
#         }
#     new_task = asyncio.create_task(update_chats_periodically(
#         db, tg_client, channel_urls, period))
#     CHAT_UPDATE_TASKS[user.id] = new_task
#     return {
#         "status": "ok"
#         # "data": CHAT_UPDATE_TASKS.keys()
#         }



