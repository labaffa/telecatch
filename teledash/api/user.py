import fastapi
from teledash import models as schemas
from teledash import config
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_db
from teledash.utils.db import user as uu
from teledash.utils.db import channel as uc
from teledash.channel_messages import update_chats_periodically
from teledash.db import models as db_models
import asyncio
from teledash.utils import telegram


router = fastapi.APIRouter()
CHAT_UPDATE_TASKS = {}


@router.get("/users/{user_id}", response_model=schemas.UserInDB)
async def read_user(
    user_id: int, db: Session = fastapi.Depends(get_db)):
    db_user = uu.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise fastapi.HTTPException(
            status_code=404, detail="User not found"
        )
    return db_user


@router.get("/api/active_collection_of_user")
async def get_current_active_collection_of_user(
    user=fastapi.Depends(config.settings.MANAGER),
    db: Session=fastapi.Depends(get_db)
):
    try:
        return uu.get_active_collection(db, user.id)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400,
            detail=str(e)
        )
    

@router.post("/api/set_active_collection_of_user")
async def set_active_collection_of_user(
    collection_title: str,
    user=fastapi.Depends(config.settings.MANAGER),
    db: Session=fastapi.Depends(get_db)
):
    try:
        uu.upsert_active_collection(db, user.id, collection_title)
        return {"status": "ok"}
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )


@router.put("/api/set_chat_update_task")
async def set_chat_update_task_for_user_and_active_client(
    request: fastapi.Request,
    # collection: str,
    client_id: str, period: int=60*60,
    db: Session=fastapi.Depends(get_db), 
    user=fastapi.Depends(config.settings.MANAGER)
):
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        tg_client = await telegram.get_authenticated_client(client_id)
        request.app.state.clients[client_id] = tg_client
    user_task = CHAT_UPDATE_TASKS.get(user.id)
    if user_task:
        CHAT_UPDATE_TASKS[user.id].cancel()
        CHAT_UPDATE_TASKS.pop(user.id)
    channel_urls = [x["url"] for x in uu.get_all_channel_urls(db, user.id)]
    if not channel_urls:
        return {
            "status": "fail",
            "detail": "no channels present in user account or no registered collection"
        }
    new_task = asyncio.create_task(update_chats_periodically(
        db, tg_client, channel_urls, period))
    CHAT_UPDATE_TASKS[user.id] = new_task
    return {
        "status": "ok"
        # "data": CHAT_UPDATE_TASKS.keys()
        }
