import io
from collections import defaultdict
import pandas as pd
import numpy as np
import fastapi
import sqlalchemy as sa
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.db import models, db_setup
from teledash.utils.users import active_user
from teledash.utils.db import user as uu
from teledash.utils import telegram
from teledash.utils.db import channel as uc
from teledash.utils import channels as util_channels
from teledash import schemas
import asyncio
from asyncio import current_task
from sqlalchemy.ext.asyncio import async_scoped_session


collection_router = fastapi.APIRouter()
CHAT_UPDATE_TASKS = defaultdict(lambda: defaultdict(dict))


@collection_router.post("/item/{title}")
async def add_collection_of_channels_to_user_account(
    request: fastapi.Request,
    title: str,
    file: fastapi.UploadFile,
    db: Session = fastapi.Depends(get_async_session),
    user: models.User =  fastapi.Depends(active_user)
):
    content = await file.read()
    file_channels = []
    try:
        # Try parsing as CSV
        df = pd.read_csv(
            io.BytesIO(content), 
            sep=None, 
            engine="python",
            encoding="ISO-8859-1"
            
        )
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="File could not be parsed. Try to use .xls, .xlsx, .csv, .tsv"
            )
    # TODO: check if columns don't match schema
    if len(df) == 0:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=f"List of channels for the collection '{title}' is empty"
        )
    try:
        df.columns = df.columns.str.lower()
        df = df.replace({np.nan: None})
        if "url" in df.columns:
            df.rename(columns={"url": "channel_url"}, inplace=True)
        df = df.drop_duplicates("channel_url")
        for row in df.to_dict("records"):
            row_d = schemas.ChannelCustomCreate(**dict(row)).model_dump()
            file_channels.append(row_d)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    
    client_id = await uu.get_active_client(db, user.id)
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        tg_client = await telegram.get_authenticated_client(db, client_id)
        request.app.state.clients[client_id] = tg_client
    collection_in_db = await uc.get_channel_collection(
        db, user.id, title)
    if collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=f"Title '{title}' already present in your collections"
        )
    try:
        for channel in file_channels:
            channel_url = channel["channel_url"]
            channel_common_in_db = await uc.get_channel_by_url(
                db, channel_url
            )
            if not channel_common_in_db:
                channel_common = schemas.ChannelCommon(url=channel_url.lower())
                await uc.insert_channel_common(db, channel_common)
            
            channel_custom = schemas.ChannelCustom(**dict(channel), user_id=user.id)
            await uc.upsert_channel_custom(db, channel_custom)
        await uc.insert_channel_collection(
            db, 
            title, user.id, 
            [schemas.ChannelCreate(url=x["channel_url"]) for x in file_channels]
        )
        record = await uc.get_channel_collection(db, user.id, title)
        response = {
            "status": "ok",
            "data": record
        }
        return response
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e))


@collection_router.delete("/item/{title}")
async def delete_collection_item_for_user(
    title: str,
    db: Session = fastapi.Depends(get_async_session),
    user: models.User = fastapi.Depends(active_user)
):
    collection_in_db = await uc.get_channel_collection(db, user.id, title)
    if not collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=f"Title '{title}' is not present in your collections")
    try:
        await uc.delete_collection_for_user(db, title, user.id)
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e))
    return {
        "status": "ok",
        "data": collection_in_db
    }


@collection_router.get("/item/{title}")
async def get_channels_of_a_given_collection_title(
    title: str,
    db: Session = fastapi.Depends(get_async_session),
    user = fastapi.Depends(active_user)
):
    try:
        response = await uc.get_channel_collection(db, user.id, title)
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e))
    return {
        "status": "ok",
        "data": response
    }


@collection_router.get("/all")
async def get_collections_registered_by_an_user(
    db: Session = fastapi.Depends(get_async_session),
    user = fastapi.Depends(active_user)
):
    try:
        response = await uc.get_channel_collection_titles_of_user(db, user.id)
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e))
    return {
        "status": "ok",
        "data": response
    }


@collection_router.get("/active")
async def get_current_active_collection_of_user(
    user: models.User = fastapi.Depends(active_user),
    db: Session = fastapi.Depends(get_async_session)
):
    try:        
        response = await uu.get_active_collection(db, user.id)
        return response
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400,
            detail=str(e)
        )
    

@collection_router.post("/set_active")
async def set_active_collection_of_user(
    collection_title: str,
    user=fastapi.Depends(active_user),
    db: Session=fastapi.Depends(get_async_session)
):
    collection_in_db = await uc.get_channel_collection(db, user.id, collection_title)
    if not collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=(f"'{collection_title}' collection not present in user account. " 
                "Can't set it as active."
            )
        )
    try:
        await uu.upsert_active_collection(db, user.id, collection_title)
        return {"status": "ok"}
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    

@collection_router.patch("/item/{title}")
async def update_metadata_of_collections_channel(
    request: fastapi.Request,
    title: str,
    db: Session=fastapi.Depends(get_async_session), 
    user=fastapi.Depends(active_user)
):
    
    client_id = await uu.get_active_client(db, user.id)
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        print(f"client of {user.username} is None")
        
        tg_client = await telegram.get_authenticated_client(db, client_id)
        if tg_client is None:
            raise fastapi.HTTPException(
                status_code=400, detail=f"client {client_id} is no usable")
        request.app.state.clients[client_id] = tg_client
    
    collection_in_db = await uc.get_channel_collection(
        db, user.id, title)
    if not collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=f"Title '{title}' not present in your collections"
        )
    
    user_tasks = request.app.state.background_tasks.get(user.id, {})
    same_task = user_tasks.get("update_collections", {}).get(title)
    if same_task:
        user_tasks["update_collections"][title].cancel()
        user_tasks["update_collections"].pop(title)
        # we should do nothing is same_task already running (or not?)

    
    channel_urls = [x["url"] for x in collection_in_db]

    stmt = sa.select(
        models.ChannelCommon.url)\
        .where(models.ChannelCommon.url.in_(channel_urls))\
        .order_by(models.ChannelCommon.updated_at.desc())
    stmt_result = await db.execute(stmt)
    await db.commit()
    sorted_channel_urls = [r[0] for r in stmt_result.fetchall()]

    if not channel_urls:
        return {
            "status": "fail",
            "detail": "no channels present in user account or no registered collection"
        }
    scoped_session =  async_scoped_session(
        db_setup.async_session_maker, scopefunc=current_task)
    
    new_task = asyncio.create_task(util_channels.update_chats_metadata(
                scoped_session, tg_client, sorted_channel_urls))
        # background_tasks.add_task(util_channels.update_chats_metadata, db,
    #                           tg_client, channel_urls
    #                           )
    request.app.state.background_tasks[user.id]["update_collections"][title] = new_task
    return {
        "status": "ok"
        # "data": CHAT_UPDATE_TASKS.keys()
        }


@collection_router.post("/uploadfile")
async def upload_entities(file: fastapi.UploadFile):
    
    content = await file.read()
    error = None
    data = []
    try:
        # Try parsing as CSV
        df = pd.read_csv(
            io.BytesIO(content), 
            sep=None, 
            engine="python",
            encoding="ISO-8859-1"
            
        )
    
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="File could not be parsed. Try to use .xls, .xlsx, .csv, .tsv"
            )
    try:
        df.columns = df.columns.str.lower()
        df = df.replace({np.nan: None})
        for row in df.to_dict("records"):
            row = schemas.ChannelUpload(**row).model_dump()
            data.append(row)
        return {
            "message": "File ok",
            "error": error,
            "rows": data
        }
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    