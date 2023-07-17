from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, \
    FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.channel_messages import search_all_channels, \
    count_peer_messages, get_channel_or_megagroup, \
    build_chat_info
import base64
from teledash.config import ALL_CHANNELS
from typing import Union
from teledash import models
from teledash import config
from teledash.config import tg_client
import datetime as dt
from telethon import functions
from typing import List
import io
import pandas as pd
from dateutil.parser import parse
import json
import unicodedata
import asyncio


def validate_date(v):
    if not v or (v == "null"):
        return None
    return parse(v)


class StrictDate(dt.datetime):
    @classmethod
    def __get_validators__(cls):
        yield validate_date


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
app.mount("/static", StaticFiles(directory="teledash/static"), name="static")
templates = Jinja2Templates(directory="teledash/templates")
tg_client.start()


TIME_INTERVAL_IN_SEC = 60*60*2


async def count_messages():
    while True:
        for channel in ALL_CHANNELS:
            print(channel)
            await count_peer_messages(
                tg_client, channel
            )
            await asyncio.sleep(0.3)
            # async GET requests
            # async update DB
        await asyncio.sleep(TIME_INTERVAL_IN_SEC)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(count_messages())


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):

    channels = config.db.table("channels").all()
    ch_meta = {
        "channel_count": sum(1 for c in channels if c["type"] == "channel"),
        "group_count": sum(1 for c in channels if c["type"] != "channel"),
        "participant_count": sum(c["participants_counts"] for c in channels),
    }
    data = {
        "request": request, 
        "all_channels": ALL_CHANNELS,
        "channels_info": {"meta": ch_meta, "data": channels}
        }
    return templates.TemplateResponse(
        "index.html",
        data
    )


@app.get("/api/search_channels")
async def read_search_channel(
    search, 
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    country: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0
):
    async with tg_client:  
        response = await search_all_channels(
            tg_client, 
            search, 
            start_date, end_date,
            chat_type, country,
            limit,
            offset_channel, offset_id
        )
    
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')}))


@app.get("/api/get_channel")
async def read_get_channel(channel: Union[str, int]):
    response = await get_channel_or_megagroup(tg_client, channel)
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')}))
   

@app.post("/api/channel", response_model=models.Channel)
async def add_channel(channel: models.ChannelCreate):
    from tinydb import Query

    channels = config.db.table("channels")
    Ch = Query()
    async with config.tg_client:
        entity = await config.tg_client.get_input_entity(
            channel.identifier)
    channel_in_db = channels.search(Ch.id == entity.channel_id)
    if channel_in_db:
        raise HTTPException(
            status_code=400, detail="Channel is registered"
        )
    
    record = await build_chat_info(
        tg_client, channel.identifier)
    channels.insert(record)
    return models.Channel(**record)


@app.get("/api/channels_info")
async def info_of_channels_and_groups():
    channels = config.db.table("channels").all()
    meta = {
        "channel_count": sum(1 for c in channels if c["type"] == "channel"),
        "group_count": sum(1 for c in channels if c["type"] != "channel"),
        "participant_count": sum(c["participants_counts"] for c in channels),
        "msg_count": sum(c.get("count", 0) for c in channels)
    }
    data = [models.Channel(**c) for c in channels]
    return {"meta": meta, "data": data}


@app.post("/api/export_to_csv")
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


@app.put("/api/chat_message_count")
async def update_number_of_messages_in_chat(
    chat: str):
    response = await count_peer_messages(
        tg_client, chat
    )
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')})
    )


@app.delete("/api/channel", response_model=models.Channel)
async def delete_channel_from_db(
    channel: models.ChannelCreate
):
    from tinydb import Query

    channels = config.db.table("channels")
    Ch = Query()
    async with config.tg_client:
        entity = await config.tg_client.get_input_entity(
            channel.identifier
        )
    channel_in_db = channels.search(Ch.id == entity.channel_id)
    if not channel_in_db:
        raise HTTPException(
            status_code=400, detail="Channel is not registered"
        )
    async with config.tg_client:
        await config.tg_client(
            functions.channels.LeaveChannelRequest(
                channel.identifier))
    channels.remove(Ch.id == entity.channel_id)
    return models.Channel(**(channel_in_db[0]))