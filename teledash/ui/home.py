from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from teledash import config
from tinydb import Query


home_router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@home_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(
    request: Request, 
    user=Depends(config.settings.MANAGER)
):
    
    is_logged_in = config.db.table("telegram").search(
        Query().session == "default"
    )[0]["is_logged_in"]
    if not is_logged_in:
        return RedirectResponse("/tglogin")
    
    channels = config.db.table("channels").all()
    ch_meta = {
        "channel_count": sum(1 for c in channels if c["type"] == "channel"),
        "group_count": sum(1 for c in channels if c["type"] != "channel"),
        "participant_count": sum(c["participants_counts"] for c in channels),
    }
    client_ids = [
        x["client_id"] 
        for x in config.db.table("users_clients").search(
            Query().user_id == user.user_id)
        ]
    clients = config.db.table("tg_clients").search(
        Query().client_id.one_of(client_ids)
    )
    active_client = next((x["client_id"] for x in clients), None)
    data = {
        "request": request, 
        "all_channels": config.DEFAULT_CHANNELS,
        "channels_info": {"meta": ch_meta, "data": channels},
        "user": user,
        "clients": clients,
        "active_client": active_client
    }
    return templates.TemplateResponse(
        "index.html",
        data
    )
   
        