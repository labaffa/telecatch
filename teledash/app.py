from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from teledash.ui.login import ui_login_router
from teledash.api.search import search_router
from teledash.ui.home import home_router as ui_home_router
from teledash.ui.clients import router as ui_clients_router
from teledash.api.collections import collection_router
from teledash.api.telegram_clients import clients_router
from teledash.api.channels import channel_router
from teledash.ui.channels import router as ui_channels_router
from teledash.api.admin import admin_router
from teledash.utils.users import auth_backend, fastapi_users, cookie_auth_backend
from teledash.schemas import UserCreateFU, UserReadFU, UserUpdateFU
from collections import defaultdict
import logging


logger = logging.getLogger('uvicorn.error')


app = FastAPI(
    title="TeleDash",
    description="Extract useful info from Telegram channels and groups",
    version="0.0.1",
    contact={
        "name": "Giosue",
        "email": "giosue.ruscica@gmail.com",
    },
    license_info={
        "name": "MIT",
    },
    default_response_class=ORJSONResponse
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="teledash/static"), name="static")

    
@app.on_event("startup")
async def startup_event():
    app.state.clients = {}
    app.state.background_tasks = defaultdict(lambda: defaultdict(dict))
    
    
app.include_router(ui_home_router, include_in_schema=False)
app.include_router(ui_clients_router, include_in_schema=False)
app.include_router(ui_channels_router, include_in_schema=False)
app.include_router(channel_router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(ui_login_router, include_in_schema=False)
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(collection_router, prefix="/api/v1/collections", tags=["collections"])
app.include_router(clients_router, prefix="/api/v1/clients", tags=["telegram clients"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/api/v1/auth",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_auth_router(cookie_auth_backend),
    prefix="/api/v1/cookie",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserReadFU, UserCreateFU),
    prefix="/api/v1/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(), 
    prefix="/api/v1/auth",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_verify_router(UserReadFU),
    prefix="/api/v1/auth",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserReadFU, UserUpdateFU), 
    prefix="/api/v1/users",
    tags=["users"]
)


def auth_exception_handler(request, exc):
    """
    https://stackoverflow.com/questions/73630653

    Redirect the user to the login page if not logged in
    """
    from fastapi.encoders import jsonable_encoder

    if not request.url.path.startswith("/api/"):
        return RedirectResponse(
            url='/app_login?next=' + str(request.url)
        )
    else:
        return ORJSONResponse(
            status_code=401, content=jsonable_encoder({"detail": "unauthorized"}))
    

app.add_exception_handler(
   401, auth_exception_handler
)
