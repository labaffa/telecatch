import fastapi
from fastapi import HTTPException, APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse, \
    FileResponse
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.channel_messages import search_all_channels, \
    search_all_channels_generator
import base64
from teledash.config import DEFAULT_CHANNELS
from typing import Union
from teledash import models
from teledash import config
import datetime as dt
from telethon import types
from typing import List
import io
import pandas as pd
from dateutil.parser import parse
import json
import io
import csv
from teledash.utils import telegram
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_db
from teledash.utils.db import tg_client as ut
from teledash.utils.db import channel as uc


search_router = APIRouter()


def validate_date(v):
    if not v or (v == "null"):
        return None
    return parse(v)


class StrictDate(dt.datetime):
    @classmethod
    def __get_validators__(cls):
        yield validate_date


@search_router.get("/api/search_channels")
async def read_search_channel(
    request: fastapi.Request,
    search,
    channel_urls: List[str]=Query(default=[]),
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    country: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    db: Session=Depends(get_db),
    user = Depends(config.settings.MANAGER),
    client_id=None
):
    # TODO: the client_id should be replaced by an 'active client' set by user
    if not client_id:
        client_ids = ut.get_user_clients(db=db, user_id=int(user.id))
        print("[/search_channels]", client_ids)
        client_id = client_ids[0]["client_id"] if client_ids else None
    if client_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} has not registered Telegram clients"
        )
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        tg_client = await telegram.get_authenticated_client(db, client_id)
        request.app.state.clients[client_id] = tg_client
    if not channel_urls:
        collection_titles = uc.get_channel_collection_titles_of_user(db, int(user.id))
        title = collection_titles[0] if collection_titles else None
        if title is None:
            raise HTTPException(
            status_code=400,
            detail=f"Please set channels to search or create a collection"
        )
        # TODO: this should be replaced so that 'search_all_channels' does not query the db
        channel_urls = [   
            x["channel_url"] 
            for x in uc.get_channel_collection(db, user.id, title)
        ]
    print(channel_urls)
    try:
        response = await search_all_channels(
            db=db,
            client=tg_client, 
            search=search,
            channel_urls=channel_urls,
            start_date=start_date,
            end_date=end_date,
            chat_type=chat_type,
            country=country,
            limit=limit,
            offset_channel=offset_channel,
            offset_id=offset_id
        )
        return JSONResponse(content=jsonable_encoder(
            response, custom_encoder={
            bytes: lambda v: base64.b64encode(v).decode('utf-8')})
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        )


@search_router.get("/api/stream_search")
async def search_and_export_messages_to_csv(
    request: fastapi.Request,
    search: str,
    channel_urls: List[str]=Query(default=[]),
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    country: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    out_format: Union[str, None]=None,
    db: Session=Depends(get_db),
    user = Depends(config.settings.MANAGER)
):
    # TODO: the client_id should be replaced by an 'active client' set by user
    client_ids = ut.get_user_clients(db=db, user_id=int(user.id))
    client_id = client_ids[0]["client_id"] if client_ids else None
    if client_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} has not registered Telegram clients"
        )
    
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        tg_client = await telegram.get_authenticated_client(client_id)
        request.app.state.clients[client_id] = tg_client
    if not channel_urls:
        collection_titles = uc.get_channel_collection_titles_of_user(db, int(user.id))
        title = collection_titles[0] if collection_titles else None
        if title is None:
            raise HTTPException(
            status_code=400,
            detail=f"Please set channels to search or create a collection"
        )
        # TODO: this should be replaced so that 'search_all_channels' does not query the db
        channel_urls = [   
            x["channel_url"] 
            for x in uc.get_channel_collection(db, user.id, title)
        ]
    headers = {}
    if (out_format == "csv") or (out_format == "json"):
        fext = ".csv" if out_format == "csv" else ".json"
        headers = {
            'Access-Control-Expose-Headers': 'Content-Disposition',
            'Content-Disposition': f'attachment; filename="export{fext}"'
    }
    results = search_all_channels_generator(
            db=db,
            client=tg_client, 
            search=search,
            channel_urls=channel_urls,
            start_date=start_date,
            end_date=end_date,
            chat_type=chat_type,
            country=country,
            limit=limit,
            offset_channel=offset_channel,
            offset_id=offset_id
        )
    
    async def _encoded_results():
        fieldnames = models.Message.__fields__.keys()
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        if out_format == "csv":
            writer.writeheader()
            yield stream.getvalue()
            async for item in results:
                stream.truncate(0)
                stream.seek(0)
                writer.writerow(item)
                yield stream.getvalue()
        elif out_format =="json":
            idx = 0
            yield "["
            async for item in results:
                if idx > 0:
                    yield ","
                yield json.dumps(
                    jsonable_encoder(models.Message(**item).dict())
                )
                idx += 1
            yield "]"
    return StreamingResponse(
        content=_encoded_results(),
        media_type='text/event-stream',
        headers=headers
    )


@search_router.get("/api/get_messages")
async def get_messages_from_channel_by_id(
    request: fastapi.Request,
    channel_id: Union[str, int], 
    message_ids: List[int]=fastapi.Query(default=[]),
    client_id: Union[str, None]=None
):
    if client_id is not None:
        tg_client = request.app.state.clients.get(client_id)
        if tg_client is None:
            tg_client = await telegram.get_authenticated_client(client_id)
            request.app.state.clients[client_id] = tg_client
    try:
        channel_id = int(channel_id)
    except Exception:
        pass
    if isinstance(channel_id, str):
        channel_info = config.db.table("channels").search(
            Channel.identifier == channel_id
        )
    if isinstance(channel_id, int):
        channel_info = config.db.table("channels").search(
            Channel.id == channel_id
        )
    if channel_info:
        channel_info = channel_info[0]
    if not channel_info or not channel_info["is_joined"]:
        raise HTTPException(
            status_code=400, detail="Channel is not registered"
        )
    entity = types.InputPeerChannel(
        channel_id=int(channel_info["id"]),
        access_hash=channel_info["access_hash"]
    )
    response = []
    async for message in tg_client.iter_messages(
        entity, ids=message_ids
    ):
        message = message.to_dict()
        message["peer_id"]["channel_url"] = channel_info["identifier"]
        message["chat_type"] = channel_info["type"]
        message["country"] = channel_info.get("country")
        response.append(message)
    
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')})
    )


@search_router.post("/api/export_to_csv")
async def get_csv(
    messages: List[models.Message]
    ):
    import os
    
    rows = [dict(m) for m in messages]
    stream = io.StringIO()
    in_path = "./test_csv"
    df = pd.DataFrame(
        columns=models.Message.__fields__.keys())
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(in_path, index=False)
    out_path = os.getcwd() + "/export.csv"
    headers = {'Access-Control-Expose-Headers': 'Content-Disposition'}
    # response.headers["Content-Disposition"] = f"attachment; filename={out_path}"
    """ response = StreamingResponse(
        iter([stream.getvalue()]), media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={out_path}" """
    
    df.to_csv(out_path, index=False)
    return FileResponse(
        path=out_path, 
        media_type="application/octet-stream", 
        filename="export.csv",
        headers=headers
    )