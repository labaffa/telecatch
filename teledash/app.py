from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, \
    FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from teledash.channel_messages import search_all_channels, \
    count_peer_messages, get_channel_or_megagroup, \
    build_chat_info, search_all_channels_generator, \
    load_default_channels_in_db, update_message_counts, \
    update_participant_counts, join_channel, leave_channel
import base64
from teledash.config import DEFAULT_CHANNELS
from typing import Union
from teledash import models
from teledash import config
from teledash.config import tg_client
import datetime as dt
from telethon import functions
from telethon.errors import SessionPasswordNeededError
from typing import List
import io
import pandas as pd
from dateutil.parser import parse
import json
import asyncio
import io
import csv
from tinydb import Query


APP_DATA= {}

BASE_TEMPLATE = '''
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset='UTF-8'>
            <title>Telethon + Quart</title>
        </head>
        <body>{{ content | safe }}</body>
    </html>
'''

PHONE_FORM = '''
    <form action='/login' method='post'>
        Phone (international format): <input name='phone' type='text' placeholder='+34600000000'>
        <input type='submit'>
    </form>
'''

CODE_FORM = '''
    <form action='/login' method='post'>
        Telegram code: <input name='code' type='text' placeholder='70707'>
        <input type='submit'>
    </form>
'''

PASSWORD_FORM = '''
    <form action='/login' method='post'>
        Telegram password: <input name='password' type='text' placeholder='your password'>
        <input type='submit'>
    </form>
'''


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

Channel = Query()


@app.on_event("startup")
async def startup_event():
    await tg_client.connect()
    if await tg_client.is_user_authorized():
        APP_DATA["is_logged_in"] = True
        # await tg_client.start()
        await load_default_channels_in_db(tg_client)
        asyncio.create_task(update_message_counts(tg_client))
        asyncio.create_task(update_participant_counts(tg_client))
    else:
        APP_DATA["is_logged_in"] = False
        APP_DATA["phone"] = None
    

@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    """
    Inspired from telethon example:
    https://github.com/LonamiWebs/Telethon/blob/v1/telethon_examples/quart_login.py
    
    """
    
    form = await request.form()
    if 'phone' in form:
        APP_DATA["phone"] = form['phone']
        await tg_client.send_code_request(APP_DATA["phone"])
    if 'code' in form:
        try:
            await tg_client.sign_in(code=form['code'])
        except SessionPasswordNeededError:
            
            return templates.TemplateResponse(
                "login_base.html",
                {"request": request, "content": PASSWORD_FORM}
            )
    if 'password' in form:
        await tg_client.sign_in(password=form['password'])
    
    if await tg_client.is_user_authorized():
        APP_DATA["is_logged_in"] = True
        await load_default_channels_in_db(tg_client)
        asyncio.create_task(update_message_counts(tg_client))
        asyncio.create_task(update_participant_counts(tg_client))
        return RedirectResponse("/", status_code=302)

    if APP_DATA["phone"] is None:
        return templates.TemplateResponse(
            "login_base.html",
            {"request": request, "content": PHONE_FORM}
        )
    return templates.TemplateResponse(
        "login_base.html",
        {"request": request, "content": CODE_FORM}
        )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    if not APP_DATA["is_logged_in"]:
        return RedirectResponse("/login")
    
    channels = config.db.table("channels").all()
    ch_meta = {
        "channel_count": sum(1 for c in channels if c["type"] == "channel"),
        "group_count": sum(1 for c in channels if c["type"] != "channel"),
        "participant_count": sum(c["participants_counts"] for c in channels),
    }
    data = {
        "request": request, 
        "all_channels": config.DEFAULT_CHANNELS,
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
   

@app.get("/api/channels_info")
async def info_of_channels_and_groups(
    is_joined: Union[bool, None]=True):
    if is_joined is None:
        channels = config.db.table("channels").all()
    else:
        channels = config.db.table("channels").search(
            Channel.is_joined == is_joined
        )
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


@app.get("/api/stream_search")
async def search_and_export_messages_to_csv(
    search, 
    start_date: StrictDate=None,
    end_date: StrictDate=None,
    chat_type: Union[str, None]=None,
    country: Union[str, None]=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    out_format: Union[str, None]=None
):
    headers = {}
    if (out_format == "csv") or (out_format == "json"):
        fext = ".csv" if out_format == "csv" else ".json"
        headers = {
            'Access-Control-Expose-Headers': 'Content-Disposition',
            'Content-Disposition': f'attachment; filename="export{fext}"'
    }
    results = search_all_channels_generator(
            tg_client, 
            search,
            start_date,
            end_date,
            chat_type,
            country,
            limit,
            offset_channel,
            offset_id
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


@app.post("/api/channel", response_model=models.Channel)
async def add_channel(channel: models.ChannelCreate):
    
    channels = config.db.table("channels")
    Ch = Query()
    channel_in_db = channels.search(
        Ch.identifier == channel.identifier
    )
    if channel_in_db:
        channel_in_db = channel_in_db[0]
    record = None
    if channel_in_db and channel_in_db["is_joined"]:
        raise HTTPException(
            status_code=400, detail="Channel is registered"
        )
    elif channel_in_db and not channel_in_db["is_joined"]:
        record = dict(channel_in_db)
            
    try:
        if not channel_in_db:
            record = await build_chat_info(
                tg_client, channel.identifier
            )
            channels.insert(record)
        input_entity_info = {
            "id": int(record["id"]),
            "access_hash": record["access_hash"]
        }
        await join_channel(tg_client, input_entity_info)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    joined_channel = channels.search(
        Ch.identifier == channel.identifier
    )[0]
    return models.Channel(**(joined_channel))


@app.delete("/api/channel", response_model=models.Channel)
async def delete_channel_from_db(channel: models.ChannelCreate):

    channels = config.db.table("channels")
    Ch = Query()
    
    channel_in_db = channels.search(
        Ch.identifier == channel.identifier
    )
    if channel_in_db:
        channel_in_db = channel_in_db[0]
    if (not channel_in_db) or (not channel_in_db["is_joined"]):
        raise HTTPException(
            status_code=400, detail="Channel is not registered"
        )
    input_entity_info = {
        "id": int(channel_in_db["id"]),
        "access_hash": channel_in_db["access_hash"]
    }
    await leave_channel(tg_client, input_entity_info)
    left_channel = channels.search(
        Ch.identifier == channel.identifier
    )[0]
    return models.Channel(**(left_channel))


@app.put("/api/chat_message_count")
async def update_number_of_messages_in_chat(
    chat: models.ChannelCreate
):
    channels = config.db.table("channels")
    Channel = Query()
    channel_in_db = channels.search(
        Channel.identifier == chat.identifier
    )
    if channel_in_db:
        channel_in_db = channel_in_db[0]
    if not channel_in_db or not channel_in_db["is_joined"]:
        raise HTTPException(
            status_code=400, detail="Channel is not registered"
        )
    input_entity_info = {
        "id": channel_in_db["id"],
        "access_hash": channel_in_db["access_hash"]
    }
    msg_count = await count_peer_messages(
        tg_client, input_entity_info
    )
    config.db.table("channels").update(
        {"count": msg_count["msg_count"]}, 
        Channel.identifier == chat.identifier
    )
    response = config.db.table("channels").search(
        Channel.identifier == chat.identifier
    )[0]
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')})
    )


@app.put("/api/chat_participant_count")
async def update_number_of_participants_in_chat(
    chat: models.ChannelCreate
):
    channels = config.db.table("channels")
    Channel = Query()
    channel_in_db = channels.search(
        Channel.identifier == chat.identifier
    )
    if channel_in_db:
        channel_in_db = channel_in_db[0]
    if not channel_in_db or not channel_in_db["is_joined"]:
        raise HTTPException(
            status_code=400, detail="Channel is not registered"
        )
    input_entity_info = {
        "id": int(channel_in_db["id"]),
        "access_hash": channel_in_db["access_hash"]
    }
    info = await get_channel_or_megagroup(
        tg_client, input_entity_info
    )
    pts_count = info["full_chat"]["participants_count"]
    config.db.table("channels").update(
        {"participants_counts": pts_count}, 
        Channel.identifier == chat.identifier
    )
    response = config.db.table("channels").search(
        Channel.identifier == chat.identifier
    )[0]
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')})
    )


@app.put("/api/update_chat")
async def update_dynamic_variables_of_a_chat(
    chat: models.ChannelCreate
):
    channels = config.db.table("channels")
    Channel = Query()
    channel_in_db = channels.search(
        Channel.identifier == chat.identifier
    )
    if channel_in_db:
        channel_in_db = channel_in_db[0]
    if not channel_in_db or not channel_in_db["is_joined"]:
        raise HTTPException(
            status_code=400, detail="Channel is not registered"
        )
    input_entity_info = {
        "id": int(channel_in_db["id"]),
        "access_hash": channel_in_db["access_hash"]
    }
    chat_info = await get_channel_or_megagroup(
        tg_client, input_entity_info
    )
    msg_count = await count_peer_messages(
        tg_client, input_entity_info
    )
    pts_count = chat_info["full_chat"]["participants_count"]
    config.db.table("channels").update(
        {
            "participants_counts": pts_count,
            "count": msg_count["msg_count"]
        }, 
        Channel.identifier == chat.identifier
    )
    response = config.db.table("channels").search(
        Channel.identifier == chat.identifier
    )[0]
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')})
    )