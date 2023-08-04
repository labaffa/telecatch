import json
from datetime import date, datetime
from telethon import functions, types
from telethon.tl.functions.messages import (
    GetHistoryRequest, SearchRequest)
from telethon.tl.types import (
    PeerChannel, InputMessagesFilterEmpty
)
import os
from teledash import config, models
from tinydb import Query
import datetime as dt
import pytz
import asyncio
from typing import Union


Channel = Query()


# some functions to parse json date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        return json.JSONEncoder.default(self, o)


def parse_raw_message(message):
    return {
        "id": message["id"],
        "username": message["peer_id"]["channel_url"],
        "message": message["message"],
        "timestamp": message["date"].isoformat(),
        "type": message["chat_type"],
        "country": message.get("country"),
        "views": message.get("views", 0),
        # "media": 
    }


async def search_channel_raw(client, channel, search):
    offset_id = 0
    limit = 100
    all_messages = []
    total_messages = 0
    total_count_limit = 0
    while True:
        print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
        history = await client(SearchRequest(
            peer=channel,
            q=search,
            filter=InputMessagesFilterEmpty(),
            offset_id=offset_id,
            add_offset=0,
            limit=limit,
            min_date=None,
            max_date=None,
            max_id=0,
            min_id=0,
            hash=0
        ))
        if not history.messages:
            break
        messages = history.messages
        for message in messages:
            message = message.to_dict()
            all_messages.append(message)
        offset_id = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break
    return all_messages


async def search_single_channel_batch(
    client, 
    channel: dict, 
    search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    limit: int=100, 
    offset_id: int=0
):
    all_messages = []
    channel_info = config.db.table("channels").search(
            Channel.id == int(channel["id"]))[0]
   
    entity = types.InputPeerChannel(
        channel_id=int(channel["id"]),
        access_hash=channel["access_hash"]
    )
    async for message in client.iter_messages(
        entity, 
        search=search, 
        limit=limit, 
        offset_id=offset_id,
        offset_date=end_date
    ):
        message = message.to_dict()
        if message["_"] != "Message":
            continue
        if start_date and message["date"] < start_date.replace(tzinfo=pytz.UTC):
            break
        message["peer_id"]["channel_url"] = channel_info["identifier"]
        message["chat_type"] = channel_info["type"]
        message["country"] = channel_info.get("country")
        all_messages.append(parse_raw_message(message))
    return all_messages


async def search_all_channels(
    client, 
    search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, 
    country: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0
):
    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    all_msg = []
    total_msg_count = 0
    channel_limit = limit
    all_channels = config.db.table("channels").all()
    for channel_info in all_channels[offset_channel:]:
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        channel_msg = await search_single_channel_batch(
            client, 
            channel_info, 
            search, 
            start_date, end_date,
            channel_limit, 
            offset_id)
        total_msg_count += len(channel_msg)
        offset_id = 0
        all_msg.extend(channel_msg)
        if (limit is not None):
            channel_limit = limit - total_msg_count
            if (total_msg_count >= limit):
                break
    return all_msg


async def search_all_channels_generator(
    client, 
    search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, country: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0
):  
    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    all_channels = config.db.table("channels").all()
    for channel_info in all_channels[offset_channel:]:
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        entity = types.InputPeerChannel(
            channel_id=int(channel_info["id"]),
            access_hash=channel_info["access_hash"]
        )
        async for message in client.iter_messages(
            entity, 
            search=search, 
            limit=limit, 
            offset_id=offset_id,
            offset_date=end_date
        ):
            message = message.to_dict()
            if message["_"] != "Message":
                continue
            if start_date and message["date"] < start_date.replace(tzinfo=pytz.UTC):
                break
            message["peer_id"]["channel_url"] = channel_info["identifier"]
            message["chat_type"] = channel_info["type"]
            message["country"] = channel_info.get("country")
            yield parse_raw_message(message)
            

async def get_channel_or_megagroup(
        client, channel: Union[str, dict, int]):
    try:
        channel = int(channel)
    except Exception:
        pass
    try:
        channel = types.InputPeerChannel(
            channel_id=int(channel["id"]),
            access_hash=channel["access_hash"]
        )
    except Exception:
        pass

    cha = await client(
        functions.channels.GetFullChannelRequest(
            channel=channel
        ))
    return cha.to_dict()


async def count_peer_messages(client, channel: dict):
    entity = types.InputPeerChannel(
        channel_id=int(channel["id"]),
        access_hash=channel["access_hash"]
    )
    cha = await client(functions.messages.GetHistoryRequest(
        peer=entity, 
        limit=1,
        offset_id=0, 
        offset_date=None, 
        add_offset=0, 
        max_id=0, 
        min_id=0,
        hash=0
    ))
    msg_count = cha.to_dict()["count"]
    return {
        "chat": channel["id"],
        "msg_count": msg_count
    }
    

async def build_chat_info(tg_client, channel: str):
    """
    channel: must be the url of the channel, i.e. this method
        is generally called if a channel has been never seen
    """
    full_channel = await get_channel_or_megagroup(
        tg_client, channel
    )
    channel_id = int(full_channel["full_chat"]["id"])
    chat = full_channel["chats"][0]
    ts = str(dt.datetime.utcnow())
    ch_type = "group" if (
        chat["megagroup"] or chat["gigagroup"]) else "channel"
    record = {
        "identifier": channel,
        "id": channel_id,
        "about": full_channel["full_chat"]["about"],
        "title": chat["title"],
        "participants_counts": full_channel["full_chat"][
            "participants_count"
        ],
        "type": ch_type,
        "inserted_at": ts,
        "updated_at": ts,
        "access_hash": chat["access_hash"],
        "username": chat["username"],
        
    }
    return record


async def join_channel(tg_client, channel: dict):
    """
    channel must be a dict with, at least, id and access_hash
    keys of a channel

    """
    entity = types.InputPeerChannel(
        channel_id=int(channel["id"]),
        access_hash=channel["access_hash"]
    )
    await tg_client(
        functions.channels.JoinChannelRequest(entity)
    )
    config.db.table("channels").update(
        {"is_joined": True}, 
        Channel.id == int(channel["id"])
    )
    return config.db.table("channels").search(
        Channel.id == int(channel["id"]))[0]


async def leave_channel(tg_client, channel: dict):
    entity = types.InputPeerChannel(
        channel_id=int(channel["id"]),
        access_hash=channel["access_hash"]
    )
    await tg_client(
        functions.channels.LeaveChannelRequest(
            entity
    ))
    config.db.table("channels").update(
        {"is_joined": False}, 
        Channel.id == int(channel["id"])
    )
    return config.db.table("channels").search(
        Channel.id == int(channel["id"]))[0]


async def load_default_channels_in_db(
    client, channel_id_list=config.DEFAULT_CHANNELS
):
    """
    TODO: deal with the scenario in which a default channel
    is deleted by an user from the webapp. in this case, since
    the channel is still in the db (but with is_joined == True),
    the channel won't be part of the joined channel at a new 
    startup of the app. DECIDE what to do with this


    """
    for channel in channel_id_list:
        try:
            channel_info = config.db.table("channels").search(
            Channel.identifier == channel)[0]
            print(f"{channel} already present in db")
        except IndexError:
            channel_info = await build_chat_info(
                client, channel)
            config.db.table("channels").insert(channel_info)
            input_entity_info = {
                "id": int(channel_info["id"]),
                "access_hash": channel_info["access_hash"]
            }
            await join_channel(client, input_entity_info)
            print(f'{channel} inserted in db')
            await asyncio.sleep(0.5)


TIME_INTERVAL_IN_SEC = 60*60


async def update_message_counts(client):
    while True:
        all_channels = config.db.table("channels").all()
        
        for channel in all_channels:
            if not channel["is_joined"]:
                continue
            print(f'Updating message count of: {channel}')
            input_entity_info = {
                "id": int(channel["id"]),
                "access_hash": channel["access_hash"]
            }
            count = await count_peer_messages(
                client, input_entity_info
            )
            config.db.table("channels").update(
                {"count": count["msg_count"]}, 
                Channel.id == int(channel["id"])
            )
            await asyncio.sleep(1)
        await asyncio.sleep(TIME_INTERVAL_IN_SEC)


async def update_participant_counts(client):
    while True:
        all_channels = config.db.table("channels").all()
        for channel in all_channels:
            if not channel["is_joined"]:
                continue
            print(f'Updating participants count of: {channel}')
            input_entity_info = {
                "id": int(channel["id"]),
                "access_hash": channel["access_hash"]
            }
            info = await get_channel_or_megagroup(
                client, input_entity_info
                )
            pts_count = info["full_chat"]["participants_count"]
            config.db.table("channels").update(
                {"participants_counts": pts_count}, 
                Channel.id == int(channel["id"])
            )
            await asyncio.sleep(1)
        await asyncio.sleep(TIME_INTERVAL_IN_SEC)
