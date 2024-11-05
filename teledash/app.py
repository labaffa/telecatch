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
from contextlib import asynccontextmanager
from teledash.db.db_setup import a_engine
import subprocess


logger = logging.getLogger('uvicorn.error')


async def run_migrations():
    """
    slightly modified https://github.com/sqlalchemy/alembic/discussions/1483
    problem with command.upgrade in our case is: 
    /usr/local/lib/python3.10/site-packages/uvicorn/lifespan/on.py:93: RuntimeWarning: coroutine 'run_async_migrations' was never awaited
    return

    It is supposed to be a warning, so not sure how uvicorn exits.
    TODO: fix it and do not use subprocess
    """
   
    try:
        logger.info("Starting database migrations")

        # Run the Alembic upgrade command using subprocess
        result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Alembic upgrade failed: {result.stderr}")
            raise RuntimeError(f"Alembic upgrade failed: {result.stderr}")
        
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        # Ensure the engine is disposed
        await a_engine.dispose()
        logger.info("Disposed of the engine to close all connections.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clients = {}
    app.state.background_tasks = defaultdict(lambda: defaultdict(dict))
    logger.info("Starting up...")
    logger.info("run alembic upgrade head...")
    await run_migrations()

    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="TeleCatch",
    description="Extract useful info from Telegram channels and groups",
    version="0.0.1",
    # contact={
    #     "name": "Giosue",
    #     "email": "giosue.ruscica@gmail.com",
    # },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
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
