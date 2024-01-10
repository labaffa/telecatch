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
from teledash.utils.db import channel as uc
from sqlalchemy.orm import Session
from teledash.utils import telegram as ut


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
        "channel_id": message["peer_id"]["channel_id"],
        "message": message["message"].replace("\r", "").replace("\t", ""),
        "timestamp": message["date"].isoformat(),
        "type": message["chat_type"],
        "country": message.get("country"),
        "views": message.get("views", 0),
        "language": message.get("language"),
        "category": message.get("category")
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
    channel_info: dict, 
    search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    limit: int=100, 
    offset_id: int=0
):
    all_messages = []
    entity = await ut.get_input_entity(client, channel_info)
    async for message in client.iter_messages(
        entity, 
        search=search, 
        limit=limit, 
        offset_id=offset_id,
        offset_date=end_date
    ):
        
        message_d = message.to_dict()
        if message_d["_"] != "Message":
            continue
        if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
            break
        message_d["peer_id"]["channel_url"] = channel_info["url"]
        message_d["chat_type"] = channel_info["type"]
        message_d["country"] = channel_info.get("country")
        message_d["category"] = channel_info.get("category")
        message_d["language"] = channel_info.get("language")
        record = parse_raw_message(message_d)
        # record.update(**media_metadata)
        all_messages.append(
            record
            )
    return all_messages


async def parse_message_media(message_media):
    media_map = config.TELEGRAM_MEDIA_MAP
    media_type = media_map.get(message_media.to_dict()["_"])
    if media_type == "webpage":
        if message_media.to_dict()["webpage"].get("type", "") != "photo":
            media_type = None
    # title = message_media.to_dict().get(media_type, {}).get("title")
    description = message_media.to_dict().get(media_type, {}).get("description")
    return {
        "media_description": description,
        "media_type": media_type
    }


async def search_all_channels(
    db: Session,
    client, 
    search,
    channel_urls, 
    user_id: int,
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
    all_channels = uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    for channel_info in all_channels[offset_channel:]:
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retriving entity info from Telegram')
            try:
                common_channel_info = await build_chat_info(client, channel_info["url"])
                print('Inserting entity info and metadata in db')
                uc.upsert_channel_common(db, models.ChannelCommon(**channel_info))
                channel_info.update(**common_channel_info)
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
        try: 
            print("[search_all_channels]: ", channel_info)
            channel_msg = await search_single_channel_batch(
                client, 
                channel_info, 
                search, 
                start_date, 
                end_date,
                channel_limit, 
                offset_id
                )
        except Exception as e:
            print(f'Problem getting messages from channel {channel_info["url"]} due to: {str(e)}')
            channel_msg = []
        total_msg_count += len(channel_msg)
        offset_id = 0
        all_msg.extend(channel_msg)
        if (limit is not None):
            channel_limit = limit - total_msg_count
            if (total_msg_count >= limit):
                break
    return all_msg


async def search_all_channels_generator(
    db: Session,
    client,
    search, 
    channel_urls,
    user_id: int,
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, 
    country: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
):  
    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    all_channels = uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    for channel_info in all_channels[offset_channel:]:
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retriving entity info from Telegram')
            try:
                common_channel_info = await build_chat_info(client, channel_info["url"])
                print('Inserting entity info and metadata in db')
                uc.upsert_channel_common(db, models.ChannelCommon(**channel_info))
                channel_info.update(**common_channel_info)
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
        try:
            entity = await ut.get_input_entity(client, channel_info)
            async for message in client.iter_messages(
                entity, 
                search=search, 
                limit=limit, 
                offset_id=offset_id,
                offset_date=end_date
            ):
                message_d = message.to_dict()
                if message_d["_"] != "Message":
                    continue
                if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
                    break
                message_d["peer_id"]["channel_url"] = channel_info["url"]
                message_d["chat_type"] = channel_info["type"]
                message_d["country"] = channel_info.get("location")
                message_d["category"] = channel_info.get("category")
                message_d["language"] = channel_info.get("language")
                media_metadata = dict(zip(
                    ["media_type", "media_description", "media_filename"], [None]*3
                ))
                if message.media is not None:
                    try:
                        media_metadata = await parse_message_media(message.media)
                        if media_metadata["media_type"] is not None:
                            fname = f'{message_d["date"].strftime("%Y-%m")}/{message_d["peer_id"]["channel_id"]}_{message_d["id"]}'
                            media_metadata["media_filename"] = fname
                    except Exception:
                        media_metadata["media_filename"] = None
                record = parse_raw_message(message_d)
                record.update(**media_metadata)
                yield record
        except Exception as e:
            print(f'Problem getting messages from channel {channel_info["url"]} due to: {str(e)}')
            

async def download_all_channels_media(
    db: Session,
    client,
    search, 
    channel_urls,
    user_id: int,
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, 
    country: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    with_media: bool=True,
):  
    
    """
    At first, this function was planned to give both messages and, if with_media is True, the media.
    But there are problems (read 'it's impossible') to update a file (i.e. the spreadsheet of the 
    messages) inside a zip file, so workarounds are needed for this. In the meanwhile, the user must
    run two different queries, one for messages (search_all_channels_generator function) and 
    one to download media (this function). The two outputs are connected via the following:
    - spreadsheet (messages) has a column called 'media_filename' (even if you won't download the file)
    - zipped files have the same filename as reported on media_filename spreadsheet

    """
    import io

    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    all_channels = uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    for channel_info in all_channels[offset_channel:]:
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retriving entity info from Telegram')
            try:
                common_channel_info = await build_chat_info(client, channel_info["url"])
                print('Inserting entity info and metadata in db')
                uc.upsert_channel_common(db, models.ChannelCommon(**channel_info))
                channel_info.update(**common_channel_info)
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
        try:
            entity = await ut.get_input_entity(client, channel_info)

            async for message in client.iter_messages(
                entity, 
                search=search, 
                limit=limit, 
                offset_id=offset_id,
                offset_date=end_date
            ):
                message_d = message.to_dict()
                if message_d["_"] != "Message":
                    continue
                if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
                    break
                message_d["peer_id"]["channel_url"] = channel_info["url"]
                message_d["chat_type"] = channel_info["type"]
                message_d["country"] = channel_info.get("location")
                media_metadata = dict(zip(
                    ["media_type", "media_description", "media_filename"], [None]*3
                ))
                if with_media and message.media is not None:
                    media_metadata = await parse_message_media(message.media)
                    if media_metadata["media_type"] is not None:
                        try:
                            media_buffer = io.BytesIO()
                            fname = f'{message_d["date"].strftime("%Y-%m")}/{message_d["peer_id"]["channel_id"]}_{message_d["id"]}'
                            media_metadata["media_filename"] = fname
                            print(f"[search_single_batch]: downloading {media_metadata['media_type']} media of {channel_info['url']}: {message_d['id']}")
                            await message.download_media(media_buffer)
                            yield {
                                "type": "media", 
                                "data": media_buffer.getvalue(), 
                                "filename": media_metadata["media_filename"]
                            }
                        except Exception:
                            media_metadata["media_filename"] = None
                # record = parse_raw_message(message_d)
                # record.update(**media_metadata)
                # yield {"type": "message", "data": record}
        except Exception as e:
            print(f'Problem getting messages from channel {channel_info["url"]} due to: {str(e)}')
            
async def get_channel_or_megagroup(
        client, channel: Union[str, dict, int]):
    try:
        channel = int(channel)
    except Exception:
        pass
    try:
        channel = await ut.get_input_entity(client, channel)
    except Exception:
        pass

    cha = await client(
        functions.channels.GetFullChannelRequest(
            channel=channel
        ))
    return cha.to_dict()


async def count_peer_messages(client, channel: dict):
    entity = await ut.get_input_entity(client, channel)
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
    ts = dt.datetime.utcnow()
    ch_type = "group" if (
        chat["megagroup"] or chat["gigagroup"]) else "channel"
    record = {
        "id": channel_id,
        "url": channel,
        "username": chat["username"],
        "type": ch_type,
        "access_hash": chat["access_hash"],
        "about": full_channel["full_chat"]["about"],
        "title": chat["title"],
        "participants_count": full_channel["full_chat"][
            "participants_count"
        ],
        "inserted_at": ts,
        "updated_at": ts,
        
    }
    return record


async def join_channel(tg_client, channel: dict):
    """
    channel must be a dict with, at least, id and access_hash
    keys of a channel

    """
    entity = await ut.get_input_entity(tg_client, channel)
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
    entity = await ut.get_input_entity(tg_client, channel)
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


async def update_chats_periodically(
    db: Session, client, channel_urls, period=TIME_INTERVAL_IN_SEC, sleep_for_requests=3
):
    while True:
        client_is_usable = await ut.client_is_logged_and_usable(client)
        if not client_is_usable:
            print(f"[update_chats_periodically]: client is not usable")
            await asyncio.sleep(period)
            continue
        for url in channel_urls:
            print(f'Updating: {url}')
            channel = uc.get_channel_by_url(db, url)  # it should return dict or None
            print(f'Channel in db: {channel}')
            if channel:  # this function works just on already initiated channels (url in db)
                print(channel)
                if not channel["id"]:
                    print(f'{url} has not id and access_hash yet. Trying to retrieve entity info from Telegram')
                    try:
                        channel = await build_chat_info(client, url)
                        print('Inserting entity info and metadata in db')
                        uc.upsert_channel_common(db, models.ChannelCommon(**channel))
                    except Exception as e:
                        print("Not able to get and save chat info because of error: " + str(e))
                        print(f'Skipping {url}')
                        await asyncio.sleep(sleep_for_requests)
                        continue  # try next channel in list
            if not channel:  # should never happen this
                continue  
            input_entity_info = {
                "id": int(channel["id"]),
                "access_hash": channel["access_hash"],
                "url": channel["url"]
            }
            count = await count_peer_messages(
                client, input_entity_info
            )
            info = await get_channel_or_megagroup(
                client, input_entity_info
            )
            pts_count = info["full_chat"]["participants_count"]
            # update channel in db. channel["url"] should be ok because they are initiated
            uc.update_channel_common(db, channel["url"], {
                "messages_count": count["msg_count"],
                "participants_count": pts_count
            })
            await asyncio.sleep(sleep_for_requests)
        await asyncio.sleep(period)


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
