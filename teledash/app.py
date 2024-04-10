from fastapi import FastAPI, Depends
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from tinydb import Query
from fastapi.middleware.cors import CORSMiddleware
from teledash.ui.login import ui_login_router
from teledash.api.login import api_login_router
from teledash.api.channels import channel_router
# from teledash import config
# from teledash.utils.login import auth_exception_handler
from teledash.api.search import search_router
# from teledash.ui.home import home_router
# from teledash.api.admin import admin_router
# from teledash.utils.telegram import get_authenticated_client
# from teledash.ui import clients
from teledash.api.user import router as user_router
from teledash.api.collections import collection_router
from teledash.api.telegram_clients import clients_router
# from teledash.ui.channels import router as channels_router
# from teledash.db.models import Base
# from teledash.db.db_setup import engine, get_db
# from teledash.utils.db import tg_client as ut
from teledash.db.db_setup import create_db_and_tables
from teledash.db.models import User
from teledash.utils.users import auth_backend, active_user, fastapi_users
from teledash.schemas import UserCreateFU, UserReadFU, UserUpdateFU
from collections import defaultdict


# Base.metadata.create_all(bind=engine)


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

    
Channel = Query()


@app.on_event("startup")
async def startup_event():
    """ TgStatus = Query()

    APP_DATA= config.db.table("telegram")
    default_item = APP_DATA.search(
        TgStatus.session == "default"
    )
    if not default_item:
        default_item = {
            "is_logged_in": None,
            "phone": None,
            "session": "default"
        }
        APP_DATA.insert(
            default_item
        )
    else:
        default_item = default_item[0]
    
    await tg_client.connect()
    if await tg_client.is_user_authorized():
        # APP_DATA["is_logged_in"] = True
        APP_DATA.update(
            {"is_logged_in": True},
            TgStatus.session == "default"
        )
        # await tg_client.start()
        await load_default_channels_in_db(tg_client)
        asyncio.create_task(update_message_counts(tg_client))
        asyncio.create_task(update_participant_counts(tg_client))
    else:
        APP_DATA.update(
            {"is_logged_in": False, "phone": None},
            TgStatus.session == "default"
        )
 """
    app.state.clients = {}
    app.state.background_tasks = defaultdict(lambda: defaultdict(dict))
    # db = next(get_async_session())
    async with async_session_maker() as db:
        clients_meta = [
            x[0].to_dict() for x in await ut.get_clients_meta(db)
        ]
    

    # TODO: this should be done when an user logs in, instead
    # of loading all the clients at startup. 
    for client_item in clients_meta:
        try:
            idx = client_item["id"]
            client = await telegram.get_authenticated_client(db, idx)
            if client is not None:
                app.state.clients[idx] = client
        except Exception as e:
            print(f"Error getting client for {client_item['phone']}: ", str(e))
            pass
        # APP_DATA["is_logged_in"] = False
        # APP_DATA["phone"] = None
    await create_db_and_tables()
    pass
    



# app.include_router(
#     router, 
#     prefix=settings.API_V1_STR
#     )

app.include_router(search_router, prefix="/v1", tags=["search"])
# app.include_router(home_router)
# app.include_router(admin_router)
# app.include_router(clients.router)
# app.include_router(user_router)
# app.include_router(channels_router)
# app.include_router(channel_router)
# app.include_router(api_login_router)
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(collection_router, prefix="/api/v1/collections", tags=["collections"])
app.include_router(clients_router, prefix="/api/v1/clients", tags=["telegram clients"])
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
