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
from typing import List
from pydantic import BaseModel
from telethon.utils import parse_username
from teledash.utils.admin import enc_key_from_cookies
import logging


logger = logging.getLogger('uvicorn.error')


collection_router = fastapi.APIRouter()
CHAT_UPDATE_TASKS = defaultdict(lambda: defaultdict(dict))


class CollectionChannels(BaseModel):
    title: str
    channels: List[schemas.ChannelCustomCreate]


async def file_to_list_of_channel_creators(input_file: fastapi.UploadFile):
    content = await input_file.read()
    file_channels = []
    try:
        # Try parsing as CSV
        reader = pd.read_csv(io.BytesIO(content), sep = None, engine='python', iterator = True)
        inferred_sep = reader._engine.data.dialect.delimiter
        df = pd.read_csv(io.BytesIO(content), sep=inferred_sep)

    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="File could not be parsed. Try to use .xls, .xlsx, .csv, .tsv"
        )
    if len(df) == 0:
        out = {
            "data": [],
            "ok": False,
            "detail": "File does not contain valid channels"
        }
    invalid_channels = []
    try:
        df.columns = df.columns.str.lower().str.strip()

        df = df.replace({np.nan: None})
        if "url" in df.columns:
            df.rename(columns={"url": "channel_url"}, inplace=True)
        if "channel_url" not in df.columns:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="No 'url' or 'channel_url' column found in the file. It is required"
            )
        df = df.replace({np.nan: None})
        df = df.dropna(how="all")        
        df = df.drop_duplicates("channel_url")
        for row in df.to_dict("records"):
            channel_url = row.get("channel_url")
            row['channel_url'] = parse_username(channel_url)[0]  # try to tranform to lower username
            if row['channel_url'] is None:
                invalid_channels.append(channel_url)
                continue
            row_d = schemas.ChannelCustomCreate(**dict(row)).model_dump()
            file_channels.append(row_d)
        out = {"data": file_channels, "ok": True, "detail": None, "invalid_channels": invalid_channels}
    except Exception as e:
        out = {"data": None, "ok": False, "detail": str(e)}
    return out


async def add_collection(db: Session, user: models.User, channels, title):
    invalid_channels = []
    if not channels:
        raise ValueError(f'Collection {title} is empty. Insert at least one channel ')
    for channel in channels:
        channel_url = channel["channel_url"]
        channel["channel_url"] = parse_username(channel["channel_url"])[0]
        if channel["channel_url"] is None:

            invalid_channels.append(channel_url)
            continue
        channel_common_in_db = await uc.get_channel_by_url(
            db, channel["channel_url"]
        )
        if not channel_common_in_db:
            channel_common = schemas.ChannelCommon(url=channel["channel_url"].lower())
            await uc.insert_channel_common(db, channel_common)
        
        # channel_custom = schemas.ChannelCustom(**dict(channel), user_id=user.id)
        # await uc.upsert_channel_custom(db, channel_custom)
    await uc.insert_channel_collection(
        db, 
        title, 
        user.id, 
        [
            schemas.ChannelCustom(**dict(x), user_id=user.id) 
            for x in channels if x["channel_url"] is not None
        ]
    )
    record = await uc.get_channel_collection(db, user.id, title)
    response = {
        "status": "ok",
        "data": record,
        "invalid_channels": invalid_channels
    }
    return response


@collection_router.post("/item/{title}")
async def add_collection_of_channels_to_user_account(
    request: fastapi.Request,
    collection_body: CollectionChannels,
    db: Session = fastapi.Depends(get_async_session),
    user: models.User =  fastapi.Depends(active_user)
):  
    title = collection_body.title
    channels = [dict(c) for c in collection_body.channels]
    # remove duplicates 
    channels = list({x["channel_url"].strip().lower(): x for x in channels}.values())
    client_id = await uu.get_active_client(db, user.id)
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        enc_key = enc_key_from_cookies(request)
        tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
        request.app.state.clients[client_id] = tg_client
    collection_in_db = await uc.get_channel_collection(
        db, user.id, title)
    if collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=f"Title '{title}' already present in your collections"
        )
    try:
        response = await add_collection(db, user, channels, title)
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e))
    
    return response


@collection_router.post("/item/{title}/from_file")
async def add_collection_of_channels_to_user_account_from_file(
    request: fastapi.Request,
    title: str,
    file: fastapi.UploadFile,
    db: Session = fastapi.Depends(get_async_session),
    user: models.User =  fastapi.Depends(active_user)
):
    
    file_parsing = await file_to_list_of_channel_creators(file)
    if not file_parsing["ok"]:
        raise fastapi.HTTPException(
            status_code=400, detail=file_parsing["detail"]
        )
    channels = file_parsing["data"]
    
    client_id = await uu.get_active_client(db, user.id)
    if not client_id:
        raise fastapi.HTTPException(
            status_code=400, detail="No Telegram client registered"
        )
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        try:
            enc_key = enc_key_from_cookies(request)
            tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
        except Exception:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f'Authentication problems for client: {client_id}'
            )
        request.app.state.clients[client_id] = tg_client
    collection_in_db = await uc.get_channel_collection(
        db, user.id, title)
    if collection_in_db:
        raise fastapi.HTTPException(
            status_code=400, 
            detail=f"Title '{title}' already present in your collections"
        )
    try:
        response = await add_collection(db, user, channels, title)
    except Exception as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e))
    
    return response


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
        logger.info(f"client of {user.username} is None")
        enc_key = enc_key_from_cookies(request)
        tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
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
        .order_by(models.ChannelCommon.updated_at.asc())
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
    invalid_rows = []
    try:
        # Try parsing as CSV
        reader = pd.read_csv(io.BytesIO(content), sep = None, engine='python', iterator = True)
        inferred_sep = reader._engine.data.dialect.delimiter
        df = pd.read_csv(io.BytesIO(content), sep=inferred_sep)

    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="File could not be parsed. Try to use .xls, .xlsx, .csv, .tsv"
            )
    try:
        df.columns = df.columns.str.strip().str.lower()
        if "url" not in df.columns:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="No 'url' column found in the file. It is required"
            )
        df = df.replace({np.nan: None})
        df = df.dropna(how="all")
        # remove rows where url is None or empty
        invalid_rows.extend(df[df["url"].isna()].to_dict("records"))
        df = df[~df["url"].isna()]
        for row in df.to_dict("records"):
            channel_url = parse_username(row["url"])[0]
            if channel_url is None:
                invalid_rows.append(row)
                continue
            row["url"] = channel_url
            try:
                row = schemas.ChannelUpload(**row).model_dump()
                data.append(row)
            except Exception as e:
                invalid_rows.append(row)
        return {
            "message": "File ok",
            "error": error,
            "rows": data,
            "invalid_rows": invalid_rows
        }
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    