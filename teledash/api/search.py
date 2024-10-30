import fastapi
from fastapi import HTTPException, APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.utils.channel_messages import search_all_channels, \
    search_all_channels_generator, download_all_channels_media, sample_from_all_channels
import base64
from typing import Union
from teledash import schemas as schemas
from teledash.db import models
from typing import List
import io
import pandas as pd
from dateutil.parser import parse
import json
import io
import csv
from teledash.utils import telegram
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.utils.db import channel as uc
from teledash.utils.db import user as uu
from teledash.utils.users import active_user
from typing_extensions import Annotated
from pydantic import AfterValidator
import zipfile
from stat import S_IFREG
from stream_zip import ZIP_32, async_stream_zip
import datetime as dt
from teledash.utils.admin import enc_key_from_cookies


MAX_MSG_CHUNK_SIZE = 1000
search_router = APIRouter()


def validate_date(v):
    if not v or (v == "null"):
        return None
    return parse(v)


def validate_format(v):
    if not v:
        v = "tsv"  # default
    v = v.strip().lower()
    valid_formats = ["json", "tsv", "zip"]
    if v not in valid_formats:
        raise ValueError(f"{v} format is not supported.")
    return v


StrictDate = Annotated[
    str | None,
    AfterValidator(lambda x: validate_date(x))
]


OutFormat = Annotated[
    str | None,
    AfterValidator(lambda x: validate_format(x))
]


@search_router.get("/search")
async def read_search_channel(
    request: fastapi.Request,
    search: str | None,
    collection_title: str = None,
    channel_urls: List[str]=Query(default=[]),
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    db: Session=Depends(get_async_session),
    user: models.User = Depends(active_user),
    client_id: str | None=None,
    reverse: bool = False
):
    if limit > 100:
        limit = 100
    # collection_title overrides channel_urls
    if collection_title is not None:
        collection_in_db = await uc.get_channel_collection(db, user.id, collection_title)
        if not collection_in_db:
            raise fastapi.HTTPException(
                status_code=400, 
                detail=(f"'{collection_title}' collection not present in user account. "
                        "Create it or chose another collection"
                )
            )
        channel_urls = [x["channel_url"] for x in collection_in_db]
    if not client_id:
        client_id = await uu.get_active_client(db, user.id)
    if client_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} has not registered Telegram clients"
        )
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:  # I believe we should test if tg_client works 
        enc_key = enc_key_from_cookies(request)
        tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
        request.app.state.clients[client_id] = tg_client
    if not channel_urls:
        raise HTTPException(
            status_code=400,
            detail=f"Please set channels to search, set or create a collection"
        )
    try:
        response = await search_all_channels(
            db=db,
            client=tg_client, 
            search=search,
            channel_urls=channel_urls,
            start_date=start_date,
            end_date=end_date,
            chat_type=chat_type,
            limit=limit,
            offset_channel=offset_channel,
            offset_id=offset_id,
            user_id=user.id,
            reverse=reverse
        )
        return JSONResponse(content=jsonable_encoder(
            response, custom_encoder={
            bytes: lambda v: base64.b64encode(v).decode('utf-8')})
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        )


@search_router.get("/export_search")
async def search_and_export_messages_and_media_to_zip_file(
    request: fastapi.Request,
    search: str,
    collection_title: str | None = None,
    channel_urls: List[str]=Query(default=[]),
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    out_format: OutFormat="tsv",
    db: Session=Depends(get_async_session),
    user: models.User = Depends(active_user),
    client_id = None,
    with_media: bool=True,
    reverse: bool=False,
    messages_chunk_size: int=1000,
    enrich_messages: bool=True,
    ids: List[int]=Query(default=[])
):
    if not len(ids):
        ids = None
    if messages_chunk_size > MAX_MSG_CHUNK_SIZE:
        messages_chunk_size = MAX_MSG_CHUNK_SIZE
    if collection_title is not None:
        collection_in_db = await uc.get_channel_collection(db, user.id, collection_title)
        if not collection_in_db:
            raise fastapi.HTTPException(
                status_code=400, 
                detail=(f"'{collection_title}' collection not present in user account. "
                        "Create it or chose another collection"
                )
            )
        channel_urls = [x["channel_url"] for x in collection_in_db]

    if not client_id:
        client_id = await uu.get_active_client(db, user.id)
    if client_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} has not registered Telegram clients"
        )
    
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        enc_key = enc_key_from_cookies(request)
        tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
        request.app.state.clients[client_id] = tg_client
    if not channel_urls:
        raise HTTPException(
            status_code=400,
            detail=f"Please set channels to search or create a collection"
        )
    if with_media:
        headers = {
            'Access-Control-Expose-Headers': 'Content-Disposition',
            f'Content-Disposition': f'attachment; filename="media_export.zip"'
        }
        results = download_all_channels_media(
            db=db,
            client=tg_client, 
            search=search,
            channel_urls=channel_urls,
            start_date=start_date,
            end_date=end_date,
            chat_type=chat_type,
            limit=limit,
            offset_channel=offset_channel,
            offset_id=offset_id,
            with_media=True,
            user_id=user.id,
            reverse=reverse,
            messages_chunk_size=messages_chunk_size,
            enrich_messages=enrich_messages,
            ids=ids
        )
        
    
        
        tsv_columns = schemas.Message.__fields__.keys()
                    
        async def to_async_data(d):
            yield d

        async def _stream_zip_members():
            
            async for item in results:
                if item["type"] == "media":
                    modified_at = dt.datetime.now()
                    mode = S_IFREG | 0o600
                    yield (f'media/{item["filename"]}', modified_at, mode, ZIP_32, to_async_data(item["data"]))
                elif item["type"] == "messages":
                    df = pd.DataFrame(item["data"], columns=tsv_columns)
                    modified_at = dt.datetime.now()
                    mode = S_IFREG | 0o600
                    yield (f'messages/{item["filename"]}', modified_at, mode, ZIP_32, to_async_data(df.to_csv(sep="\t", index=False).encode()))

        async def stream_results():
            async for chunk in async_stream_zip(_stream_zip_members()):
                yield chunk

        async def _encoded_results():
            tsv_columns = schemas.Message.__fields__.keys()
            c = 0
            zip_buffer = io.BytesIO()
            seek_pos = 0
            z = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
            async for item in results:
                
                c += 1
                if item["type"] == "media":
                    with z.open(f'media/{item["filename"]}', mode='w') as mediafile:
                        mediafile.write(item["data"])
                elif item["type"] == "messages":
                    df = pd.DataFrame(item["data"], columns=tsv_columns)
                    with z.open(f'messages/{item["filename"]}', mode='w') as mediafile:
                        mediafile.write(df.to_csv(sep="\t", index=False).encode())
                zip_buffer.seek(seek_pos)
                buffer_chunk = zip_buffer.read()
                
                seek_pos = zip_buffer.tell()
                yield buffer_chunk

            z.close()
            zip_buffer.seek(seek_pos)
            final_chunk = zip_buffer.read()
            yield final_chunk


        return StreamingResponse(
            content=stream_results(),
            media_type="application/x-zip-compressed",
            headers=headers
        )
    else:
        
        headers = {
            'Access-Control-Expose-Headers': 'Content-Disposition',
            'Content-Disposition': f'attachment; filename="export.{out_format}"'
        }
        results = search_all_channels_generator(
            db=db,
            client=tg_client, 
            search=search,
            channel_urls=channel_urls,
            start_date=start_date,
            end_date=end_date,
            chat_type=chat_type,
            limit=limit,
            offset_channel=offset_channel,
            offset_id=offset_id,
            user_id=user.id,
            reverse=reverse,
            enrich_messages=enrich_messages,
            ids=ids
        )
    
        async def _encoded_results():
            fieldnames = schemas.Message.__fields__.keys()
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
                        jsonable_encoder(schemas.Message(**item).model_dump())
                    )
                    idx += 1
                yield "]"

        return StreamingResponse(
            content=_encoded_results(),
            media_type='application/octet-stream',
            headers=headers
        )


@search_router.get("/sample")
async def read_sample_from_channelsl(
    request: fastapi.Request,
    search: str | None,
    collection_title: str = None,
    channel_urls: List[str]=Query(default=[]),
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    db: Session=Depends(get_async_session),
    user: models.User = Depends(active_user),
    client_id: str | None=None,
    reverse: bool = False
):
    if limit > 100:
        limit = 100
    # collection_title overrides channel_urls
    if collection_title is not None:
        collection_in_db = await uc.get_channel_collection(db, user.id, collection_title)
        if not collection_in_db:
            raise fastapi.HTTPException(
                status_code=400, 
                detail=(f"'{collection_title}' collection not present in user account. "
                        "Create it or chose another collection"
                )
            )
        channel_urls = [x["channel_url"] for x in collection_in_db]
    if not client_id:
        client_id = await uu.get_active_client(db, user.id)
    if client_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} has not registered Telegram clients"
        )
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:  # I believe we should test if tg_client works 
        enc_key = enc_key_from_cookies(request)
        tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
        request.app.state.clients[client_id] = tg_client
    if not channel_urls:
        raise HTTPException(
            status_code=400,
            detail=f"Please set channels to search, set or create a collection"
        )
    try:
        response = await sample_from_all_channels(
            db=db,
            client=tg_client, 
            search=search,
            channel_urls=channel_urls,
            start_date=start_date,
            end_date=end_date,
            chat_type=chat_type,
            limit=limit,
            offset_channel=offset_channel,
            offset_id=offset_id,
            user_id=user.id,
            reverse=reverse
        )
        return JSONResponse(content=jsonable_encoder(
            response, custom_encoder={
            bytes: lambda v: base64.b64encode(v).decode('utf-8')})
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        )    