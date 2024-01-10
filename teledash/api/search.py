import fastapi
from fastapi import HTTPException, APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse, \
    FileResponse
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.channel_messages import search_all_channels, \
    search_all_channels_generator, download_all_channels_media
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
from teledash.utils.db import user as uu


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
    if not client_id:
        client_id = uu.get_active_client(db, user.id)
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
            offset_id=offset_id,
            user_id=user.id
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
    user = Depends(config.settings.MANAGER),
    client_id = None
):
    if not client_id:
        client_id = uu.get_active_client(db, user.id)
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
    headers = {}
    if (out_format == "tsv") or (out_format == "json"):
        fext = ".tsv" if out_format == "tsv" else ".json"
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
            offset_id=offset_id,
            user_id=user.id
        )
    
    async def _encoded_results():
        fieldnames = models.Message.__fields__.keys()
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
        if out_format == "tsv":
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
        media_type='application/octet-stream',
        headers=headers
    )


@search_router.get("/api/stream_search_with_media")
async def search_and_export_messages_and_media_to_zip_file(
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
    user = Depends(config.settings.MANAGER),
    client_id = None,
    media: bool=False
):
    import zipfile
    

    if not client_id:
        client_id = uu.get_active_client(db, user.id)
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
    
    if media:
        headers = {
            'Access-Control-Expose-Headers': 'Content-Disposition',
            'Content-Disposition': f'attachment; filename="export.zip"'
        }
        results = download_all_channels_media(
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
            offset_id=offset_id,
            with_media=True,
            user_id=user.id
        )
        async def _encoded_results():
            zip_buffer = io.BytesIO()
            seek_pos = 0
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as z:
                async for item in results:
                    if item["type"] == "media":
                        with z.open(f'media/{item["filename"]}', mode='w') as mediafile:
                            mediafile.write(item["data"])
                
                        zip_buffer.seek(seek_pos)
                        buffer_chunk = zip_buffer.read()
                        seek_pos = zip_buffer.tell()
                        yield buffer_chunk
            zip_buffer.seek(seek_pos)
            yield zip_buffer.read()


        return StreamingResponse(
            content=_encoded_results(),
            media_type="application/x-zip-compressed",
            headers=headers
        )
    else:
        headers = {}
        if (out_format == "tsv") or (out_format == "json"):
            fext = ".tsv" if out_format == "tsv" else ".json"
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
            offset_id=offset_id,
            user_id=user.id
        )
    
        async def _encoded_results():
            fieldnames = models.Message.__fields__.keys()
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t")
            if out_format == "tsv":
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
            media_type='application/octet-stream',
            headers=headers
        )
