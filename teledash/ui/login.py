from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import fastapi
from teledash import config
from fastapi.templating import Jinja2Templates
from jose import jwt
from urllib.parse import urljoin
# from teledash.api.login import create_user


ui_login_router = APIRouter()
templates = Jinja2Templates(directory="teledash/templates")



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
        raise ValueError('Form must have email and password')
        # form_action = "signup" 
        # create_user(
        #     schemas.UserAuth(
        #         **{
        #             "username": form["username"],
        #             "password": form["password"],
        #             "email": form["email"]
        #         }
        #     ))

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