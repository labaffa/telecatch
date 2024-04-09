from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from teledash import config
from teledash.utils.db import tg_client as ut
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.utils.db import user as uu
from teledash.utils.db import channel as uc
from teledash.utils.users import active_user
from teledash.db import models


router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@router.get("/channels", include_in_schema=False)
@router.post("/channels", include_in_schema=False)
async def page_to_manage_user_clients(
    request: Request,
    user: models.User = Depends(active_user),
    db: Session = Depends(get_async_session)
):
    user_collections = await uc.get_channel_collection_titles_of_user(db, user.id)
    active_collection = await uu.get_active_collection(db, user.id)
    if active_collection not in user_collections:  # if collection deleted
        active_collection = None
    user_clients_meta = await ut.get_user_clients(db, user)
    # active_client = next((x["client_id"] for x in clients), None)
    active_client_id = await uu.get_active_client(db, user.id)
    active_client = next(
        (x for x in user_clients_meta if x["client_id"] == active_client_id), None
    )
    if active_client is None:
        active_client = {"client_id": None, "phone": None, "authenticated": None}
    data = {
        "request": request,
        "user": user,
        "active_client": dict(active_client),
        "active_collection": active_collection
    }
    return templates.TemplateResponse(
        "user_channels.html",
        data
    )
