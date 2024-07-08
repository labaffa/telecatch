import json
from datetime import date, datetime
from telethon import functions, types
from telethon.tl.functions.messages import (
    GetHistoryRequest, SearchRequest)
from telethon.tl.types import (
    PeerChannel, InputMessagesFilterEmpty
)
from tinydb import Query
from teledash import config, schemas
import datetime as dt
import pytz
import asyncio
from teledash.utils.db import channel as uc
from sqlalchemy.orm import Session
from teledash.utils import telegram as ut
from teledash.utils import channels as util_channels
from typing import Iterable
from async_timeout import timeout
import math


Channel = Query()


# some functions to parse json date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        return json.JSONEncoder.default(self, o)


def get_author(message):
    if not isinstance(message, dict):
        message = message.to_dict()
    author_type = "channel"  # we assume channel as default value
    if message["from_id"]:
        if message["from_id"]["_"] == "PeerUser":
            author_type = "user"
        author_id = next(
            int(v) for k, v in message["from_id"].items() if k.endswith("_id")
        )
    else:
        try:
            author_id = message["peer_id"]["channel_id"]
        except Exception as e:
            print("Problem getting author from message: ")
            print(message)
            author_type = None
            author_id = None
    return {
        "author_type": author_type,
        "author_id": author_id
    }

        
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
        "category": message.get("category"),
        "author_type": message.get("author", {}).get("author_type"),
        "author_id": message.get("author", {}).get("author_id"),
        "reply_to_author_type": message.get(
            "reply_to_msg_author", {}).get("author_type"),
        "reply_to_author_id": message.get(
            "reply_to_msg_author", {}).get("author_id"),
        "fwd_from_author_type": message.get(
            "fwd_from_author", {}).get("author_type"),
        "fwd_from_author_id": message.get(
            "fwd_from_author", {}).get("author_id"),
        "media_type": message.get("media_type"),
        "media_filename": message.get("media_filename")
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
    db: Session,
    client, 
    channel_info: dict, 
    search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    limit: int=100, 
    offset_id: int=0,
    reverse: bool=False,
    enrich_messages: bool=True
):
    all_messages = []
    batch_messages = []
    entity = await util_channels.get_input_entity(client, channel_info)
    # this is added because telegram api don't seem to work with offset_date and reverse
    # but it's not optimal at all, when reverse and start_date. we could do:
    # 1. ask in non reverse mode with offset_date = start_date (+ something) for just 
    # one message to get the message id, and than pass the min/max_id in actual query
    offset_date = None if reverse else end_date
    
    async for message in client.iter_messages(
        entity, 
        search=search,
        limit=None, 
        offset_id=offset_id,
        offset_date=offset_date,
        reverse=reverse
    ):
        
        message_d = message.to_dict()
        if message_d["_"] != "Message":
            continue
        if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
            if reverse:
                continue
            else:
                break
        if reverse and end_date and message_d["date"] > end_date.replace(tzinfo=pytz.UTC):
            break
        limit -= 1
        if limit < 0:
            break
        
        message_d["peer_id"]["channel_url"] = channel_info["url"]
        message_d["chat_type"] = channel_info["type"]
        message_d["country"] = channel_info.get("country")
        message_d["category"] = channel_info.get("category")
        message_d["language"] = channel_info.get("language")
        message_d["author"] = get_author(message_d)
        if message_d["author"]["author_type"] is None:  # message not valid
            print("Unable to get author, message might be broken. Skipping: ")
            print(message_d)
            continue
        if message_d["fwd_from"]:
            fwd_author = get_author(message_d["fwd_from"])
            if fwd_author["author_type"] is None:
                print("FORWARDED MESSAGE MISSING AUTHOR:")
                print(message_d)
                fwd_author["author_id"] = 0
            message_d["fwd_from_author"] = fwd_author
        batch_messages.append(message_d)
        if len(batch_messages) >= 200:
            print("Enriching")
            batch_records = await enrich_and_parse_messages(
                db, client, entity, batch_messages, enrich=enrich_messages
            )
            
            all_messages.extend(batch_records)
            batch_messages = []
    print("Enriching remaining messages")
    batch_records = await enrich_and_parse_messages(
        db, client, entity, batch_messages, enrich=enrich_messages
    )
    
    all_messages.extend(batch_records)
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
    user_id, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    reverse: bool=False
):
    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    all_msg = []
    total_msg_count = 0
    channel_limit = limit
    channel_urls = [x.strip().lower() for x in channel_urls]
    all_channels = await uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    all_channels = sorted(
        all_channels, key=lambda x: channel_urls.index(x["url"].strip().lower())
    )
    for channel_info in all_channels[offset_channel:]:
        channel_info = dict(channel_info)
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retrieving entity info from Telegram')
            try:
                common_channel_info = await util_channels.build_chat_info(
                    client, channel_info["url"]
                )
                channel_info.update(**common_channel_info)
                print('Inserting entity info and metadata in db')
                await uc.upsert_channel_common(db, schemas.ChannelCommon(**channel_info))
            except Exception as e:
                # IMPORTANT: should we skip here?
                print("Not able to get and save chat info because of error: " + str(e))
        try: 
            print("[search_all_channels]: ", channel_info)
            channel_msg = await search_single_channel_batch(
                db,
                client, 
                channel_info, 
                search, 
                start_date, 
                end_date,
                channel_limit, 
                offset_id,
                reverse
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


async def enrich_with_author_of_replies(client, entity, messages):
    reply_ids = list(set([
        m["reply_to"]["reply_to_msg_id"]
        for m in messages if m["reply_to"]
    ]))
    print("getting replied")
    replied_messages = await client.get_messages(entity, ids=reply_ids)
    print("received")
    replied_messages_by_id = {
        m.id: m.to_dict() for m in replied_messages if m is not None
    }
    enriched = []
    for bm in messages:
        if bm["reply_to"]:
            replied_msg = replied_messages_by_id.get(bm["reply_to"]["reply_to_msg_id"])
            if replied_msg:
                bm["reply_to_msg_author"] = get_author(replied_msg)
        enriched.append(bm)
    return enriched


async def enrich_and_parse_messages(db, client, entity, messages, enrich=True):
    timeout_seconds = 10 if enrich else 0
    try:
        async with timeout(timeout_seconds):
            messages = await enrich_with_author_of_replies(client, entity, messages)
        parsed_batch = [parse_raw_message(m) for m in messages]
        enriched_entities = await enrich_entities_of_messages(
            db, parsed_batch, client
        )
        enriched_messages = enrich_messages_with_entities(parsed_batch, enriched_entities)
    except Exception as e:
        print("error in enrichment:", str(e))
        parsed_batch = [parse_raw_message(m) for m in messages]
        enriched_messages = list(parsed_batch)
    return enriched_messages


async def search_all_channels_generator(
    db: Session,
    client,
    search, 
    channel_urls,
    user_id: int,
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None,
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    reverse: bool=False,
    enrich_messages: bool=True
):  
    if not chat_type:
        chat_type = None
    if limit < 0:
        limit = None
    channel_urls = [x.strip().lower() for x in channel_urls]
    all_channels = await uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    all_channels = sorted(
        all_channels, key=lambda x: channel_urls.index(x["url"].strip().lower())
    )
    total_msg_count = 0
    channel_limit = limit
    batch_messages = []
    # this is added because telegram api don't seem to work with offset_date and reverse
    # but it's not optimal at all, when reverse and start_date. we could do:
    # 1. ask in non reverse mode with offset_date = start_date (+ something) for just 
    # one message to get the message id, and than pass the min/max_id in actual query
    offset_date = None if reverse else end_date
    for channel_info in all_channels[offset_channel:]:
        channel_info = dict(channel_info)

        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retrieving entity info from Telegram')
            try:
                common_channel_info = await util_channels.build_chat_info(
                    client, channel_info["url"]
                )
                channel_info.update(**common_channel_info)
                print('Inserting entity info and metadata in db')
                await uc.upsert_channel_common(db, schemas.ChannelCommon(**channel_info))
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
        try:

            
            entity = await util_channels.get_input_entity(client, channel_info)
            async for message in client.iter_messages(
                entity, 
                search=search, 
                limit=None,  # we use channel_limit counter 
                offset_id=offset_id,
                offset_date=offset_date,
                reverse=reverse
            ):
                message_d = message.to_dict()
                if message_d["_"] != "Message":
                    continue
                if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
                    if reverse:
                        continue
                    else:
                        break
                if reverse and end_date and message_d["date"] > end_date.replace(tzinfo=pytz.UTC):
                    break
                if channel_limit is not None:
                    channel_limit -= 1
                    if channel_limit <= 0:
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
                            fname = f'{message_d["date"].strftime("%Y-%m")}/{message_d["peer_id"]["channel_id"]}_{message_d["id"]}.png'
                            media_metadata["media_filename"] = fname
                    except Exception:
                        media_metadata["media_filename"] = None
                message_d["author"] = get_author(message_d)
                if message_d["fwd_from"]:
                    message_d["fwd_from_author"] = get_author(message_d["fwd_from"])
                message_d.update(**media_metadata)
                batch_messages.append(message_d)
                if len(batch_messages) >= 200:  # move to config, it is taken from Telethon get_entity
                    print("Enriching")
                    enriched_messages = await enrich_and_parse_messages(
                        db, client, entity, batch_messages, enrich=enrich_messages
                    )
                    batch_messages = []
                    for msg in enriched_messages:
                        yield msg
            # # enrich and yield remaining messages
            # print("Enriching remaining messages")
            # enriched_messages = await enrich_and_parse_messages(
            #     db, client, entity, batch_messages
            # )
            # for msg in enriched_messages:
            #     yield msg
        except Exception as e:
            print(f'Problem getting messages from channel {channel_info["url"]} due to: {str(e)}')
        offset_id = 0
        if (limit is not None):
            channel_limit = limit - total_msg_count
            if (total_msg_count >= limit):
                break
    try:
        print("Enriching remaining messages")
        enriched_messages = await enrich_and_parse_messages(
            db, client, entity, batch_messages, enrich=enrich_messages
        )
        for msg in enriched_messages:
            yield msg
    except Exception as e:
        print(f'Problem enriching and yielding last chunk of messages from channel {channel_info["url"]} due to: {str(e)}')


async def download_all_channels_media(
    db: Session,
    client,
    search, 
    channel_urls,
    user_id: int,
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    with_media: bool=True,
    messages_chunk_size: int=1000,
    reverse: bool=False,
    enrich_messages: bool=True
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

    channel_urls = [x.strip().lower() for x in channel_urls]
    all_channels = await uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    all_channels = sorted(
        all_channels, key=lambda x: channel_urls.index(x["url"].strip().lower())
    )
    total_msg_count = 0
    channel_limit = limit
    messages_chunk = []
    messages_to_enrich = []
    chunks_count = 0

    for channel_info in all_channels[offset_channel:]:
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retriving entity info from Telegram')
            try:
                common_channel_info = await util_channels.build_chat_info(
                    client, channel_info["url"]
                )
                print('Inserting entity info and metadata in db')
                await uc.upsert_channel_common(db, schemas.ChannelCommon(**channel_info))
                channel_info.update(**common_channel_info)
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
        try:
            entity = await util_channels.get_input_entity(client, channel_info)
            # this is added because telegram api don't seem to work with offset_date and reverse
            # but it's not optimal at all, when reverse and start_date. we could do:
            # 1. ask in non reverse mode with offset_date = start_date (+ something) for just 
            # one message to get the message id, and than pass the min/max_id in actual query
            offset_date = None if reverse else end_date
            async for message in client.iter_messages(
                entity, 
                search=search, 
                limit=None,  # I dont remember why, but we use counter channel_limit
                offset_id=offset_id,
                offset_date=offset_date,
                reverse=reverse
            ):
                message_d = message.to_dict()
                if message_d["_"] != "Message":
                    continue
                if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
                    if reverse:
                        continue
                    else:
                        break
                if reverse and end_date and message_d["date"] > end_date.replace(tzinfo=pytz.UTC):
                    break
                if channel_limit is not None:
                    channel_limit -= 1
                    if channel_limit <= 0:
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
                            fname = f'{message_d["date"].strftime("%Y-%m")}/{message_d["peer_id"]["channel_id"]}_{message_d["id"]}.png'
                            media_metadata["media_filename"] = fname
                            print(f"[search_single_batch]: downloading {media_metadata['media_type']} media of {channel_info['url']}: {message_d['id']}")
                            async with timeout(5):
                                await message.download_media(media_buffer)
                            yield {
                                "type": "media", 
                                "data": media_buffer.getvalue(), 
                                "filename": media_metadata["media_filename"]
                            }
                        except Exception as e:
                            print(e)
                            media_metadata["media_filename"] = None
                message_d["author"] = get_author(message_d)
                if message_d["fwd_from"]:
                    message_d["fwd_from_author"] = get_author(message_d["fwd_from"])
                message_d.update(**media_metadata)
                # messages_chunk.append(parse_raw_message(message_d))
                total_msg_count += 1
                chunk_full = (total_msg_count % messages_chunk_size) == 0
                messages_to_enrich.append(message_d)
                if (len(messages_to_enrich) >= 200) or chunk_full:  # move to config, it is taken from Telethon get_entity
                    print("Enriching")
                    enriched_messages = await enrich_and_parse_messages(
                        db, client, entity, messages_to_enrich, enrich=enrich_messages
                    )
                    messages_chunk.extend(enriched_messages)
                    messages_to_enrich = []
                if chunk_full:
                    chunks_count += 1
                    yield {
                        "type": "messages",
                        "data": messages_chunk,
                        "filename": f"{chunks_count}.tsv"
                    }
                    messages_chunk = []
        except Exception as e:
            print(f'Problem getting messages from channel {channel_info["url"]} due to: {str(e)}')
        offset_id = 0
        if (limit is not None):
            channel_limit = limit - total_msg_count
            if (total_msg_count >= limit):
                break
    try:
        print("Enriching remaining messages")
        enriched_messages = await enrich_and_parse_messages(
            db, client, entity, messages_to_enrich, enrich=enrich_messages
        )
        messages_chunk.extend(enriched_messages)
        chunks_count += 1
        yield {
            "type": "messages",
            "data": messages_chunk,
            "filename": f"{chunks_count}.tsv"
        }
    except Exception as e:
        print(f'Problem enriching and yielding last chunk of messages from channel {channel_info["url"]} due to: {str(e)}')
        

async def join_channel(tg_client, channel: dict):
    """
    channel must be a dict with, at least, id and access_hash
    keys of a channel

    """
    entity = await util_channels.get_input_entity(tg_client, channel)
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
    entity = await util_channels.get_input_entity(tg_client, channel)
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
            channel_info = await util_channels.build_chat_info(
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
                        channel = await util_channels.build_chat_info(client, url)
                        print('Inserting entity info and metadata in db')
                        uc.upsert_channel_common(db, schemas.ChannelCommon(**channel))
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
            count = await util_channels.count_peer_messages(
                client, input_entity_info
            )
            info = await util_channels.get_channel_or_megagroup(
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
            count = await util_channels.count_peer_messages(
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
            info = await util_channels.get_channel_or_megagroup(
                client, input_entity_info
                )
            pts_count = info["full_chat"]["participants_count"]
            config.db.table("channels").update(
                {"participants_counts": pts_count}, 
                Channel.id == int(channel["id"])
            )
            await asyncio.sleep(1)
        await asyncio.sleep(TIME_INTERVAL_IN_SEC)


def parse_entity(entity_dict):
    entity_type_str = entity_dict["_"].lower()
    entity_type = config.EntityType[entity_type_str].value
    name = None
    if config.EntityType.user.name == entity_type_str:
        name = " ".join(
            x for x in [entity_dict.get("first_name", ""), entity_dict.get("last_name", "")]
            if x
        )
        name = name if name else None
    elif config.EntityType.channel.name == entity_type_str:
        name = entity_dict.get("title")
    return {
        "id": entity_dict["id"],
        "entity_type": entity_type,
        "username": entity_dict.get("username"),
        "name": name,
        "phone": entity_dict.get("phone")
    }


def enrich_key(k, entity):
    if k.startswith("author"):
        k_user = "author_username"
        k_name = "author_name"
    elif k.startswith("reply"):
        k_user = "reply_to_author_username"
        k_name = "reply_to_author_name"
    elif k.startswith("fwd"):
        k_user = "fwd_from_author_username"
        k_name = "fwd_from_author_name"
    else:
        return
    return {k_user: entity["username"], k_name: entity["name"]}
    

async def enrich_entities_of_messages(
    db: Session,
    messages: Iterable[schemas.Message],
    client
):
    authors, replies, forwards = [], [], []
    for msg in messages:
        authors.append(
            {"entity_type": msg["author_type"], "id": msg["author_id"]}
        )
        replies.append(
            {
                "entity_type": msg["reply_to_author_type"], 
                "id": msg["reply_to_author_id"]
            })
        forwards.append({
                "entity_type": msg["fwd_from_author_type"], 
                "id": msg["fwd_from_author_id"]
            })
    all_entities = authors + replies + forwards

    # TODO: consider working just with ID when finding entitites to search on Telegram
    # print(all_entities)
    # print(entities_to_find)
    entities_to_find = list(
        map(dict, set(tuple(sorted(sub.items())) 
        for sub in all_entities if all(v is not None for v in sub.values())))
    )
    entities_in_db = await uc.get_entities_in_list(db=db, entities=entities_to_find)
    entity_keys_in_db = [
        {"id": e["id"], "entity_type": config.EntityType(e["entity_type"]).name} 
        for e in entities_in_db
    ]
    
    entities_to_find_not_in_db = [e for e in entities_to_find if e not in entity_keys_in_db]
    # group by entity type (telethon get_entity does the same )
    users_to_find, channels_to_find, chats_to_find = [], [], []
    e_groups = {
        config.EntityType.user.name: [],
        config.EntityType.channel.name: [],
        config.EntityType.chat.name: []
    }
    for e in entities_to_find_not_in_db:
        t = e["entity_type"]
        if t not in e_groups:
            print("Unknown entity type: ", t)
            continue
        e_groups[t].append(e)
    entities_from_telegram = []
    for t, group in e_groups.items():
        try:
            group_from_telegram = await client.get_entity([e["id"] for e in group])
            entities_from_telegram.extend([
                parse_entity(x.to_dict()) for x in group_from_telegram
            ])
        except Exception as e:
            print("Problems getting entities of type: ", t)
            ids = [e["id"] for e in group]
            print("One of the following id is giving problem: ", ids)
    await uc.insert_entities(db, entities_from_telegram)
    return entities_in_db + entities_from_telegram


def enrich_messages_with_entities(messages, entities):
    all_full_entities_by_id = {x["id"]: x for x in entities}
    enriched_messages = []
    for msg in messages:
        enriched_keys = {}
        for k, v in msg.items():
            if k.endswith("_id") and (v is not None):
                entity = all_full_entities_by_id.get(v)
                if not entity:  # issues getting entity info
                    continue
                to_update = enrich_key(k, entity)
                if to_update:
                    enriched_keys.update(**to_update)
        msg.update(**enriched_keys)
        enriched_messages.append(msg)
    return enriched_messages


async def search_single_channel_batch_trycatch(
    db: Session,
    client, 
    channel_info: dict, 
    search, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    limit: int=100, 
    offset_id: int=0,
    reverse: bool=False
):
    try:
        all_messages = []
        batch_messages = []
        try:
            entity = await util_channels.get_input_entity(client, channel_info)
        except Exception as e:
            print(f'{channel_info["url"]} might be not present on Telegram anymore. Skipping')
            return []
        # this is added because telegram api don't seem to work with offset_date and reverse
        # but it's not optimal at all, when reverse and start_date. we could do:
        # 1. ask in non reverse mode with offset_date = start_date (+ something) for just 
        # one message to get the message id, and than pass the min/max_id in actual query
        offset_date = None if reverse else end_date
        
        async for message in client.iter_messages(
            entity, 
            search=search,
            limit=None, 
            offset_id=offset_id,
            offset_date=offset_date,
            reverse=reverse
        ):
            
            message_d = message.to_dict()
            if message_d["_"] != "Message":
                continue
            if start_date and message_d["date"] < start_date.replace(tzinfo=pytz.UTC):
                if reverse:
                    continue
                else:
                    break
            if reverse and end_date and message_d["date"] > end_date.replace(tzinfo=pytz.UTC):
                break
            limit -= 1
            if limit < 0:
                break
            
            message_d["peer_id"]["channel_url"] = channel_info["url"]
            message_d["chat_type"] = channel_info["type"]
            message_d["country"] = channel_info.get("country")
            message_d["category"] = channel_info.get("category")
            message_d["language"] = channel_info.get("language")
            message_d["author"] = get_author(message_d)
            if message_d["author"]["author_type"] is None:  # message not valid
                print("Unable to get author, message might be broken. Skipping: ")
                print(message_d)
                continue
            if message_d["fwd_from"]:
                fwd_author = get_author(message_d["fwd_from"])
                if fwd_author["author_type"] is None:
                    print("FORWARDED MESSAGE MISSING AUTHOR:")
                    print(message_d)
                    fwd_author["author_id"] = 0
                message_d["fwd_from_author"] = fwd_author
            batch_messages.append(message_d)
            if len(batch_messages) >= 200:
                # print("Enriching")
                # batch_records = await enrich_and_parse_messages(
                #     db, client, entity, batch_messages
                # )
                batch_records = [parse_raw_message(m) for m in batch_messages]
                all_messages.extend(batch_records)
                batch_messages = []
        # print("Enriching remaining messages")
        # batch_records = await enrich_and_parse_messages(
        #     db, client, entity, batch_messages
        # )

        # batch_records = batch_messages
        batch_records = [parse_raw_message(m) for m in batch_messages]
        all_messages.extend(batch_records)
    except Exception as e:
        print(f'Problem getting messages from channel {channel_info["url"]} due to: {str(e)}')
        all_messages = []
    return all_messages


async def sample_from_all_channels(
    db: Session,
    client, 
    search,
    channel_urls,
    user_id, 
    start_date: dt.datetime=None, 
    end_date: dt.datetime=None,
    chat_type: str=None, 
    limit: int=100, 
    offset_channel: int=0, 
    offset_id: int=0,
    reverse: bool=False
):
    
    if not chat_type:
        chat_type = None
    if limit < 0:
        return []
    if limit > 200:
        limit = 200
    all_msg = []
    total_msg_count = 0
    channel_urls = [x.strip().lower() for x in channel_urls]
    all_channels = await uc.get_channels_from_list_of_urls(db, channel_urls, user_id)
    all_channels = sorted(
        all_channels, key=lambda x: channel_urls.index(x["url"].strip().lower())
    )
    

    channel_limit = math.ceil(limit/len(channel_urls))
    coros = []
    for channel_info in all_channels[offset_channel:]:
        
        channel_info = dict(channel_info)
        if (chat_type is not None) and (channel_info["type"] != chat_type):
            continue
        if not channel_info["id"]:
            print(f'{channel_info["url"]} has not id and access_hash yet. Retrieving entity info from Telegram')
            try:
                common_channel_info = await util_channels.build_chat_info(
                    client, channel_info["url"]
                )
                channel_info.update(**common_channel_info)
                print('Inserting entity info and metadata in db')
                await uc.upsert_channel_common(db, schemas.ChannelCommon(**channel_info))
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
         
        coros.append(search_single_channel_batch_trycatch(
            db,
            client, 
            channel_info, 
            search, 
            start_date, 
            end_date,
            channel_limit, 
            offset_id,
            reverse
            ))
    
    coros_responses = await asyncio.gather(*coros, return_exceptions=True)
    all_msg = []
    for coro in coros_responses:
        if isinstance(coro, list):
            all_msg.extend(coro)
    all_msg = sorted(all_msg, key= lambda x: x["timestamp"], reverse=True)
    return all_msg