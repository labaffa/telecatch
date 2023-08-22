from teledash.channel_messages import search_all_channels, \
    count_peer_messages, get_channel_or_megagroup, \
    build_chat_info, search_all_channels_generator, \
    load_default_channels_in_db, update_message_counts, \
    update_participant_counts, join_channel, leave_channel
from teledash import models
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import base64
from teledash import config
from typing import Union
from tinydb import Query


channel_router = APIRouter()
Channel = Query()


@channel_router.get("/api/get_channel")
async def read_get_channel(channel: Union[str, int]):
    response = await get_channel_or_megagroup(tg_client, channel)
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')}))


@channel_router.get("/api/channels_info")
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


@channel_router.post("/api/channel", response_model=models.Channel)
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


@channel_router.delete(
    "/api/channel", response_model=models.Channel
)
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


@channel_router.put("/api/chat_message_count")
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


@channel_router.put("/api/chat_participant_count")
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


@channel_router.put("/api/update_chat")
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
