from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from teledash.templates.login_forms import PHONE_FORM, \
    CODE_FORM, PASSWORD_FORM    
from teledash.config import tg_client
from telethon.errors import SessionPasswordNeededError
import fastapi
from teledash import config
from tinydb import Query
from fastapi.templating import Jinja2Templates
import asyncio
from teledash.utils.channel_messages import load_default_channels_in_db, \
    update_message_counts, update_participant_counts


tg_login_router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@tg_login_router.post(
    "/tglogin", 
    response_class=HTMLResponse, 
    include_in_schema=False)
@tg_login_router.get(
    "/tglogin", 
    response_class=HTMLResponse, 
    include_in_schema=False)
async def form_for_telegram_login(request: fastapi.Request):
    """
    Inspired from telethon example:
    https://github.com/LonamiWebs/Telethon/blob/v1/telethon_examples/quart_login.py
    
    """
    APP_DATA = config.db.table("telegram")
    TgStatus = Query()
    form = await request.form()
    if 'phone' in form:
        phone = form["phone"]
        APP_DATA.update(
            {"phone": phone},
            TgStatus.session == "default"
        )
        # APP_DATA["phone"] = form['phone']
        await tg_client.send_code_request(phone)
    if 'code' in form:
        try:
            await tg_client.sign_in(code=form['code'])
        except SessionPasswordNeededError:
            
            return templates.TemplateResponse(
                "login_base.html",
                {"request": request, "content": PASSWORD_FORM}
            )
    if 'password' in form:
        await tg_client.sign_in(password=form['password'])
    
    if await tg_client.is_user_authorized():
        APP_DATA.update(
            {"is_logged_in": True},
            TgStatus.session == "default"
        )
        # APP_DATA["is_logged_in"] = True
        await load_default_channels_in_db(tg_client)
        asyncio.create_task(update_message_counts(tg_client))
        asyncio.create_task(update_participant_counts(tg_client))
        return RedirectResponse("/", status_code=302)
    default_item = APP_DATA.search(
        TgStatus.session == "default"
    )[0]
    if default_item["phone"] is None:
        return templates.TemplateResponse(
            "login_base.html",
            {"request": request, "content": PHONE_FORM}
        )
    return templates.TemplateResponse(
        "login_base.html",
        {"request": request, "content": CODE_FORM}
        )

