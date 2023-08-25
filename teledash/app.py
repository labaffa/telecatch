from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from teledash.channel_messages import load_default_channels_in_db, \
    update_message_counts, update_participant_counts
from teledash import config
from teledash.config import tg_client
import asyncio
from tinydb import Query
from fastapi.middleware.cors import CORSMiddleware
from teledash.utils.login import auth_exception_handler
from teledash.api.channels import channel_router
from teledash.api.login import api_login_router
from teledash.api.search import search_router
from teledash.ui.login import ui_login_router
from teledash.ui.home import home_router
from teledash.api.admin import admin_router
from teledash.utils.telegram import get_authenticated_client
from teledash.ui import clients

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
    TgStatus = Query()

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

    app.state.clients = {}
    for client_item in config.db.table("tg_clients").all():
        try:
            idx = client_item["client_id"]
            client = await get_authenticated_client(idx)
            app.state.clients[idx] = client
        except Exception:
            pass
        # APP_DATA["is_logged_in"] = False
        # APP_DATA["phone"] = None
    



# app.include_router(
#     router, 
#     prefix=settings.API_V1_STR
#     )
app.include_router(ui_login_router)
app.include_router(channel_router)
app.include_router(search_router)
app.include_router(home_router)
app.include_router(api_login_router)
app.include_router(admin_router)
app.include_router(clients.router)

app.add_exception_handler(
    config.NotAuthenticatedException, auth_exception_handler
)