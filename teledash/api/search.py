import fastapi
from fastapi import HTTPException, APIRouter, Depends, Query, Body, Form
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.utils.channel_messages import search_all_channels, \
    search_all_channels_generator, download_all_channels_media, sample_from_all_channels
import base64
from typing import Union, Optional
from teledash import schemas as schemas
from teledash.db import models
from typing import List, Literal
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
from pydantic import AfterValidator, BaseModel, Field
import zipfile
from stat import S_IFREG
from stream_zip import ZIP_32, async_stream_zip
import datetime as dt
from teledash.utils.admin import enc_key_from_cookies
import logging


logger = logging.getLogger('uvicorn.error')

MAX_MSG_CHUNK_SIZE = 1000
search_router = APIRouter()


def validate_date(v):
    if not v or (v == "null"):
        return None
    if isinstance(v, dt.datetime):
        return v
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
    str | dt.datetime | None,
    AfterValidator(lambda x: validate_date(x))
]


OutFormat = Annotated[
    str | None,
    AfterValidator(lambda x: validate_format(x))
]

class SearchParams(BaseModel):
    q: str | None = Field(..., description='Return only messages that contain this string')
    source: str | List[str] = Field (..., description='A collection title or a list of valid channel URL or usernames')
    start_date: StrictDate | None = None
    end_date: StrictDate | None = None
    chat_type: str | None = None
    limit: int = 100
    offset_channel: int = 0
    offset_id: int = 0
    client_id: str | None = None  # should change to phone number
    reverse: bool = False
    source_type: Literal['collection', 'urls'] = 'urls'


# class ExportParams(SearchParams):
#     with_media: bool = True
#     messages_chunk_size: int = 1000
#     enrich_messages: bool = True
#     ids: List[int] = Field(default=[], description='List of message ids to query. If present overrides time filters and offsets')
#     out_format: OutFormat = 'tsv'


class ExportParams:
    def __init__(
        self,
        q: Optional[str] = Form(None),
        source: str = Form(...),
        start_date: Optional[StrictDate] = Form(None),
        end_date: Optional[StrictDate] = Form(None),
        chat_type: Optional[str] = Form(None),
        limit: int = Form(100),
        offset_channel: int = Form(0),
        offset_id: int = Form(0),
        client_id: Optional[str] = Form(None),
        reverse: bool = Form(False),
        source_type: str = Form('urls'),
        with_media: bool = Form(True),
        messages_chunk_size: int = Form(1000),
        enrich_messages: bool = Form(True),
        ids: Optional[str] = Form("[]"),
        out_format: str = Form("tsv"),
    ):
        self.q = q
        self.source = json.loads(source) if source.startswith("[") else source
        self.start_date = start_date
        self.end_date = end_date
        self.chat_type = chat_type
        self.limit = limit
        self.offset_channel = offset_channel
        self.offset_id = offset_id
        self.client_id = client_id
        self.reverse = reverse
        self.source_type = source_type
        self.with_media = with_media
        self.messages_chunk_size = messages_chunk_size
        self.enrich_messages = enrich_messages
        self.ids = json.loads(ids)
        self.out_format = out_format


@search_router.post("/search")
async def read_search_channel(
    request: fastapi.Request,
    search_params: SearchParams,
    db: Session=Depends(get_async_session),
    user: models.User = Depends(active_user),
):
    if search_params.source_type == "collection":
        collection_title = search_params.source[0]
    elif search_params.source_type == "urls":
        collection_title = None
        channel_urls = search_params.source
    limit = search_params.limit
    if limit > 100:
        limit = 100
    client_id = search_params.client_id
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
            search=search_params.q,
            channel_urls=channel_urls,
            start_date=search_params.start_date,
            end_date=search_params.end_date,
            chat_type=search_params.chat_type,
            limit=limit,
            offset_channel=search_params.offset_channel,
            offset_id=search_params.offset_id,
            user_id=user.id,
            reverse=search_params.reverse
        )
        return JSONResponse(content=jsonable_encoder(
            response, custom_encoder={
            bytes: lambda v: base64.b64encode(v).decode('utf-8')})
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        )


@search_router.post("/export_search")
async def search_and_export_messages_and_media_to_zip_file(
    request: fastapi.Request,
    search_params: ExportParams = Depends(),
    db: Session=Depends(get_async_session),
    user: models.User = Depends(active_user)
):
    if search_params.source_type == "collection":
        collection_title = search_params.source[0]
    elif search_params.source_type == "urls":
        collection_title = None
        channel_urls = search_params.source
    ids = search_params.ids  # this has real meaning just if querying a single channel_url, since it applies to all channels
    messages_chunk_size = search_params.messages_chunk_size
    with_media = search_params.with_media
    enrich_messages = search_params.enrich_messages
    out_format = search_params.out_format
    if not len(ids):
        ids = None
    if messages_chunk_size > MAX_MSG_CHUNK_SIZE:
        messages_chunk_size = MAX_MSG_CHUNK_SIZE
    limit = search_params.limit
    client_id = search_params.client_id
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
            search=search_params.q,
            channel_urls=channel_urls,
            start_date=search_params.start_date,
            end_date=search_params.end_date,
            chat_type=search_params.chat_type,
            limit=limit,
            offset_channel=search_params.offset_channel,
            offset_id=search_params.offset_id,
            with_media=True,
            user_id=user.id,
            reverse=search_params.reverse,
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
            search=search_params.q,
            channel_urls=channel_urls,
            start_date=search_params.start_date,
            end_date=search_params.end_date,
            chat_type=search_params.chat_type,
            limit=limit,
            offset_channel=search_params.offset_channel,
            offset_id=search_params.offset_id,
            user_id=user.id,
            reverse=search_params.reverse,
            enrich_messages=enrich_messages,
            ids=ids
        )
    
        async def _encoded_results():
            fieldnames = schemas.Message.__fields__.keys()
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter="\t", extrasaction='ignore')
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


@search_router.post("/sample")
async def read_sample_from_channelsl(
    request: fastapi.Request,
    search_params: SearchParams,
    db: Session=Depends(get_async_session),
    user: models.User = Depends(active_user),
    
):
    if search_params.source_type == "collection":
        collection_title = search_params.source[0]
    elif search_params.source_type == "urls":
        collection_title = None
        channel_urls = search_params.source
    limit = search_params.limit
    if limit > 100:
        limit = 100
    client_id = search_params.client_id
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
            search=search_params.q,
            channel_urls=channel_urls,
            start_date=search_params.start_date,
            end_date=search_params.end_date,
            chat_type=search_params.chat_type,
            limit=limit,
            offset_channel=search_params.offset_channel,
            offset_id=search_params.offset_id,
            user_id=user.id,
            reverse=search_params.reverse
        )
        return JSONResponse(content=jsonable_encoder(
            response, custom_encoder={
            bytes: lambda v: base64.b64encode(v).decode('utf-8')})
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        )    