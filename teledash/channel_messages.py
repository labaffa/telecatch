import json
from datetime import date, datetime
from telethon import functions
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
        "username": message["peer_id"]["channel_url"],
        "message": message["message"],
        "timestamp": message["date"].isoformat(),
        "type": message["chat_type"],
        "country": message.get("country"),
        "views": message.get("views", 0)
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
    client, channel, search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    limit: int=100, 
    offset_id: int=0
):
    all_messages = []
    try:
        channel_info = config.db.table("channels").search(
            Channel.identifier == channel)[0]
    except IndexError:
        channel_info = await build_chat_info(
            client, channel)
        config.db.table("channels").insert(channel_info)
    async with client:
        async for message in client.iter_messages(
            channel, 
            search=search, 
            limit=limit, 
            offset_id=offset_id,
            offset_date=end_date
            ):
            message = message.to_dict()
            if start_date and message["date"] < start_date.replace(tzinfo=pytz.UTC):
                break
            message["peer_id"]["channel_url"] = channel
            message["chat_type"] = channel_info["type"]
            message["country"] = channel_info.get("country")
            all_messages.append(message)
    return all_messages


async def search_all_channels(
    client, search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, country: str=None, 
    limit: int=100, 
    offset_channel: int=0, offset_id: int=0
):
    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    all_msg = []
    total_msg_count = 0
    channel_limit = limit
    all_channels_id = [
        channel["identifier"]

        for channel in config.db.table("channels").all()
    ]
    for channel in all_channels_id[offset_channel:]:
        try:
            channel_info = config.db.table("channels").search(
            Channel.identifier == channel)[0]
        except IndexError:
            channel_info = await build_chat_info(
            client, channel)
            config.db.table("channels").insert(channel_info)
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        channel_msg = await search_single_channel_batch(
            client, channel, search, 
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
    client, search, 
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
    all_channels_id = [
        channel["identifier"]

        for channel in config.db.table("channels").all()
    ]
    for channel in all_channels_id[offset_channel:]:
        try:
            channel_info = config.db.table("channels").search(
            Channel.identifier == channel)[0]
        except IndexError:
            channel_info = await build_chat_info(
            client, channel)
            config.db.table("channels").insert(channel_info)
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        async with client:
            async for message in client.iter_messages(
                channel, 
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
                message["peer_id"]["channel_url"] = channel
                message["chat_type"] = channel_info["type"]
                message["country"] = channel_info.get("country")
                yield parse_raw_message(message)
            

async def get_channel_or_megagroup(client, channel):
    async with client:
        ch = await client.get_input_entity(channel)
        cha = await client(functions.channels.GetFullChannelRequest(
        channel=ch
    ))
    return cha.to_dict()


async def count_peer_messages(client, peer):
    async with client:
        ch = await client.get_input_entity(peer)
        cha = await client(functions.messages.GetHistoryRequest(
            peer=ch, limit=1,
            offset_id=0, 
            offset_date=None, 
            add_offset=0, 
            max_id=0, 
            min_id=0,
            hash=0
        ))
    msg_count = cha.to_dict()["count"]
    config.db.table("channels").update(
        {"count": msg_count}, Channel.identifier == peer
    )
    return config.db.table("channels").search(
        Channel.identifier == peer
    )


async def build_chat_info(tg_client, channel):
    full_channel = await get_channel_or_megagroup(
        tg_client, channel
    )
    async with config.tg_client:
        await config.tg_client(
            functions.channels.JoinChannelRequest(channel))
    chat = full_channel["chats"][0]
    ts = str(dt.datetime.utcnow())
    ch_type = "group" if (
        chat["megagroup"] or chat["gigagroup"]) else "channel"
    record = {
        "identifier": channel,
        "id": full_channel["full_chat"]["id"],
        "about": full_channel["full_chat"]["about"],
        "title": chat["title"],
        "participants_counts": full_channel["full_chat"][
            "participants_count"
        ],
        "type": ch_type,
        "inserted_at": ts,
        "updated_at": ts
    }
    return record


async def load_default_channels_in_db(
    client, channel_id_list=config.DEFAULT_CHANNELS
):
    for channel in channel_id_list:
        try:
            channel_info = config.db.table("channels").search(
            Channel.identifier == channel)[0]
            print(f"{channel} already present in db")
        except IndexError:
            channel_info = await build_chat_info(
                client, channel)
            config.db.table("channels").insert(channel_info)
            print(f'{channel} inserted in db')
            await asyncio.sleep(0.5)


TIME_INTERVAL_IN_SEC = 60*60


async def count_messages(
    client
):
    while True:
        all_channels = config.db.table("channels").all()
        for channel in all_channels:
            await count_peer_messages(
                client, channel
            )
            print(channel)
            await asyncio.sleep(0.3)
            # async GET requests
            # async update DB
        await asyncio.sleep(TIME_INTERVAL_IN_SEC)