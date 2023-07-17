import os
from inspect import getsourcefile
from tinydb import TinyDB
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


load_dotenv()

this_path = os.path.abspath(getsourcefile(lambda:0))
this_folder = os.path.dirname(this_path)
repo_folder = os.path.dirname(os.path.dirname(this_folder))
SOURCE_FOLDER = os.path.dirname(this_folder)

ALL_CHANNELS = [
     x.strip(" \n") for x in open(os.path.join(this_folder, "channels.txt"), "r").readlines() if x.strip(" \n")
]

db = TinyDB(
    os.path.join(this_folder, 'sessions/db.json')
)
channels_table = db.table("channels")

# Setting configuration values
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
USERNAME = os.getenv("USERNAME")
tg_client = TelegramClient(f'{this_folder}/sessions/{USERNAME}', API_ID, API_HASH)


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