from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from teledash import config
from tinydb import Query


router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@router.get("/clients", include_in_schema=False)
@router.post("/clients", include_in_schema=False)
async def page_to_manage_user_clients(
    request: Request,
    user=Depends(config.settings.MANAGER)
):
    client_ids = [
        x["client_id"] 
        for x in config.db.table("users_clients").search(
            Query().user_id == user.user_id)
    ]
    clients = config.db.table("tg_clients").search(
        Query().client_id.one_of(client_ids)
    )
    data = {
        "request": request,
        "clients": clients,
        "user": user
    }
    return templates.TemplateResponse(
        "user_clients.html",
        data
    )
