import json
from datetime import date, datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import (GetHistoryRequest, SearchRequest)
from telethon.tl.types import (
    PeerChannel, InputMessagesFilterEmpty
)
import os
from inspect import getsourcefile

load_dotenv()

this_path = os.path.abspath(getsourcefile(lambda:0))
this_folder = os.path.dirname(this_path)
repo_folder = os.path.dirname(os.path.dirname(this_folder))
SOURCE_FOLDER = os.path.dirname(this_folder)


# some functions to parse json date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        return json.JSONEncoder.default(self, o)




# Setting configuration values
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
USERNAME = os.getenv("USERNAME")
tg_client = TelegramClient(f'{this_folder}/{USERNAME}', API_ID, API_HASH)

ALL_CHANNELS = [
     x.strip(" \n") for x in open("./teledash/channels.txt", "r").readlines() if x.strip(" \n")
]

# Create the client and connect
# client = TelegramClient(username, api_id, api_hash)



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
            all_messages.append(message.to_dict())
        offset_id = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break
    return all_messages


async def create_client():
    # Create the client and connect
    client = TelegramClient(USERNAME, API_ID, API_HASH)

    await client.start()
    print("Client created")
    if await client.is_user_authorized() == False:
        await client.send_code_request(PHONE)
        try:
            await client.sign_in(PHONE, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))
    return client


async def search_single_channel_batch(client, channel, search, limit=100, offset_id=0):
    all_messages = []
    async for message in client.iter_messages(
        channel, search=search, limit=limit, offset_id=offset_id):
        all_messages.append(message.to_dict())
    return all_messages


async def search_all_channels(client, search, limit=100, offset_channel=0, offset_id=0):
    all_msg = []
    total_msg_count = 0
    channel_limit = limit
    for channel in ALL_CHANNELS[offset_channel:]:
        channel_msg = await search_single_channel_batch(
            client, channel, search, channel_limit, offset_id)
        total_msg_count += len(channel_msg)
        channel_limit = limit - total_msg_count
        all_msg.extend(channel_msg)
        if total_msg_count >= limit:
            break
    return all_msg


async def main():
    client = await create_client()
    user_input_search = input('enter search word(string):')
    all_messages = await search_all_channels(client, user_input_search)
    with open('channel_messages.json', 'w') as outfile:
        json.dump(all_messages, outfile, cls=DateTimeEncoder)


if __name__ == "__main__":
    with tg_client:
        tg_client.loop.run_until_complete(main())