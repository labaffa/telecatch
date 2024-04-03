from fastapi import APIRouter, HTTPException
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
from teledash.channel_messages import load_default_channels_in_db, \
    update_message_counts, update_participant_counts
from teledash import schemas
from jose import jwt
from urllib.parse import urljoin
# from teledash.api.login import create_user


ui_login_router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@ui_login_router.post(
    "/tglogin", 
    response_class=HTMLResponse, 
    include_in_schema=False)
@ui_login_router.get(
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


@ui_login_router.post(
    "/app_login",
    response_class=HTMLResponse,
    summary="Form to login or signup if not yet registered",
    include_in_schema=False
)
@ui_login_router.get(
    "/app_login",
    response_class=HTMLResponse,
    summary="Form to login or signup if not yet registered",
    include_in_schema=False
)
async def form_for_app_login(
    request: fastapi.Request
):
    form = await request.form()
    if len(form) == 2:  # user/email and password
        form_action = "login"
    elif len(form) > 2:
        form_action = "signup" 
        create_user(
            schemas.UserAuth(
                **{
                    "username": form["username"],
                    "password": form["password"],
                    "email": form["email"]
                }
            ))

    return templates.TemplateResponse(
        "app_login.html",
        {"request": request}
    )


@ui_login_router.post(
    "/reset_password",
    response_class=HTMLResponse,
    summary="Form to reset password",
    include_in_schema=False
)
@ui_login_router.get(
    "/reset_password",
    response_class=HTMLResponse,
    summary="Form to reset password",
    include_in_schema=False
)
async def form_for_password_reset(
    request: fastapi.Request, ac: str
):
    
    try:
        jwt.decode(
            ac,
            config.settings.JWT_SECRET_KEY, 
            algorithms=[config.settings.ALGORITHM],
            audience='fastapi-users:reset'
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Token not valid"
        )
    form = await request.form()
    if len(form) > 0:
        print(form)
        host = urljoin(request.headers.get('referer'), "/")
        url = urljoin(host, f"/v1/auth/reset-password")
        payload = {
            "token": ac,
            "password": form["password"]
        }
        requests.post(url, data=payload)

    return templates.TemplateResponse(
        "reset_password_form.html",
        {"request": request}
    )