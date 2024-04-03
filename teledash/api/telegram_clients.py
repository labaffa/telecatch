import fastapi
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.db import models
from teledash.utils.users import active_user
from teledash.utils.db import user as uu
from teledash.utils.db import channel as uc
from teledash.utils.db import tg_client as ut
from teledash.utils import telegram
from teledash import schemas
from typing import Annotated


clients_router = fastapi.APIRouter()


@clients_router.post("/register")
async def add_phone_to_user(
    request: fastapi.Request,
    phone_or_bot_token: Annotated[str, fastapi.Form()],
    api_id: Annotated[int, fastapi.Form()],
    api_hash: Annotated[str, fastapi.Form()],
    code: Annotated[int, fastapi.Form()] = None,
    user: models.User = fastapi.Depends(active_user),
    db: Session = fastapi.Depends(get_async_session),
    phone: bool = True
):
    if phone:
        client_creation_func = telegram.create_client
        phone_or_bot_token = telegram.parse_phone(phone_or_bot_token)
        if not phone_or_bot_token:
            raise fastapi.HTTPException(
                status_code=400, detail="Provided phone has invalid format"
            )
    else:
        client_creation_func = telegram.create_bot_client
    try:
        session_id = telegram.create_session_id(
            phone_or_bot_token, api_id, api_hash, phone=phone)
        client_id = session_id + '.session'
        client_in_db = await ut.get_client_meta(db, client_id)
        client_in_db = client_in_db.to_dict() if client_in_db else {}
        authenticated = client_in_db.get("authenticated", False)
        
        # authenticated = await client_is_logged_and_usable(client_id, api_id, api_hash)
        print("authenticated: ", authenticated)
        try:
            client_used_by_app = request.app.state.clients.get(client_id)
        except Exception:
            client_used_by_app = None
        if client_used_by_app:
            print("[add_tg_phone]: client in app")
            await ut.upsert_user_client_relation(
                db=db, user_id=user.id, client_id=client_id
            )
            is_usable = await telegram.client_is_logged_and_usable(client_used_by_app)
            print("[add_tg_phone] is usable: ", is_usable)
            if is_usable:
                return client_in_db
            else:
                authenticated = False
        else:
            authenticated = False
        print("[register]: creating client")   
        client_dict = await client_creation_func(
            phone_or_bot_token, api_id, api_hash, code, authenticated,
        )
        print("[register]: created")
        print(client_dict)
        tg_client = {
            "id": client_dict["session_file"],
            "phone": phone_or_bot_token,
            "api_id": api_id,
            "api_hash": api_hash
        }
        tg_client["authenticated"] = True if (client_dict["status"] == "ok") else False    
        await ut.upsert_tg_client(db=db, row_dict=tg_client)
        await ut.upsert_user_client_relation(
            db=db, user_id=user.id, client_id=client_id
        )
        print("inserted")
        if tg_client["authenticated"]:
            request.app.state.clients[client_id] = await telegram.get_authenticated_client(
                db, client_id
            )
            print("set")
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=[{"msg": str(e)}]
        )
    print("outing")
    return tg_client


@clients_router.get("/active")
async def get_current_active_client_of_user(
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    try:
        return await uu.get_active_client(db, user.id)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )


@clients_router.post("/set_active")
async def set_active_client_of_user(
    client_id: str,
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    try:
        clients_of_user = await ut.get_user_clients(db, user)
        client_is_registered = any(x["client_id"] == client_id for x in clients_of_user)
        if not client_is_registered:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Client {client_id} not registered. Can't set it as active"
            )
        await uu.upsert_active_client(db, user.id, client_id)
        return {"status": "ok"}
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    

@clients_router.get("/registered")
async def get_registered_clients_of_user(
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    try:
        results = await ut.get_user_clients(db, user)
        return results
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )