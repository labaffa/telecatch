from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from teledash import config
from teledash.utils.db import user as uu
from teledash.utils.db import tg_client as ut
from teledash.utils.db import channel as uc
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.utils.users import active_user
from teledash.db import models
from teledash.utils.admin import decrypt_data, enc_key_from_cookies
import logging


logger = logging.getLogger('uvicorn.error')


home_router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@home_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(
    request: Request, 
    user: models.User = Depends(active_user),
    db: Session = Depends(get_async_session)
):
    enc_key = enc_key_from_cookies(request)

    user_collections = await uc.get_channel_collection_titles_of_user(db, user.id)
    user_clients = await ut.get_user_clients(db, user)

    active_collection = await uu.get_active_collection(db, user.id)
    if active_collection not in user_collections:  # if collection deleted
        active_collection = None 
    if active_collection:
        channels = await uc.get_channel_collection(db, user.id, active_collection)
    else:
        channels = []
    
    channel_urls = [c["url"] for c in channels]
    # user_clients_meta = await ut.get_user_clients(db, user.id)
    
    clients = [
        x for x in user_clients
        if request.app.state.clients.get(x["client_id"])
    ]
    clients = [dict(x) for x in clients]

    for i in range(1):
        try:
            clients[i]["phone"] = decrypt_data(enc_key, bytes.fromhex(clients[i]["phone"]))
            a = 1/0
        except Exception as e:
            logging.info(str(e))
            pass
    active_client = next((x["client_id"] for x in clients), None)
    active_client_id = await uu.get_active_client(db, user.id)
    active_client = next((x for x in user_clients if x["client_id"] == active_client_id), None)
    if active_client is None:
        active_client = {"client_id": None, "phone": None, "authenticated": None}
    else:
        active_client = dict(active_client)
        active_client["phone"] = decrypt_data(enc_key, bytes.fromhex(active_client["phone"]))
    data = {
        "request": request, 
        "user": user,
        "clients": clients,
        "active_client": active_client,
        "collections": user_collections,
        "active_collection": active_collection,
        "channel_urls": channel_urls
    }
    return templates.TemplateResponse(
        "index.html",
        data
    )
   
        