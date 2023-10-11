from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from teledash import config
from teledash.utils.db import tg_client as ut
from teledash.utils.db import user as uu
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_db


router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@router.get("/clients", include_in_schema=False)
@router.post("/clients", include_in_schema=False)
async def page_to_manage_user_clients(
    request: Request,
    user=Depends(config.settings.MANAGER),
    db: Session = Depends(get_db)
):
    
    active_collection = uu.get_active_collection(db, user.id)
    clients = ut.get_user_clients(db, user_id=user.id)
    active_client_id = uu.get_active_client(db, user.id)
    active_client = next((x for x in clients if x["client_id"] == active_client_id), None)
    data = {
        "request": request,
        "clients": clients,
        "user": user,
        "active_collection": active_collection,
        "active_client": dict(active_client)
    }
    return templates.TemplateResponse(
        "user_clients.html",
        data
    )
