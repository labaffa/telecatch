import os
from inspect import getsourcefile
from tinydb import TinyDB
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from pydantic import BaseSettings
from decouple import config
from fastapi_login import LoginManager


load_dotenv()


this_path = os.path.abspath(getsourcefile(lambda:0))
this_folder = os.path.dirname(this_path)
repo_folder = os.path.dirname(os.path.dirname(this_folder))
SOURCE_FOLDER = os.path.dirname(this_folder)
SESSIONS_FOLDER =  os.path.join(SOURCE_FOLDER, "sessions")


DEFAULT_CHANNELS = [
     x.strip(" \n") for x in open(os.path.join(SOURCE_FOLDER, "channels.txt"), "r").readlines() if x.strip(" \n")
]

db = TinyDB(
    os.path.join(SESSIONS_FOLDER, 'db.json')
)
channels_table = db.table("channels")


# Setting configuration values
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
USERNAME = os.getenv("USERNAME")
tg_client = TelegramClient(f'{SESSIONS_FOLDER}/{USERNAME}', API_ID, API_HASH)


async def create_client():
    # Create the client and connect
    client = TelegramClient(f'{SESSIONS_FOLDER}/{USERNAME}', API_ID, API_HASH)

    await client.start()
    print("Client created")
    if await client.is_user_authorized() == False:
        await client.send_code_request(PHONE)
        try:
            await client.sign_in(PHONE, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))
    return client


class NotAuthenticatedException(Exception):
    pass


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", cast=str)
    JWT_REFRESH_SECRET_KEY: str = config(
        "JWT_REFRESH_SECRET_KEY", cast=str)
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = (60 * 24 * 365) * 10  # 10 years
    REFRESH_TOKEN_EXPIRE_MINUTES: int = (60 * 24 * 365) * 10 
    # BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
    #     "http://localhost:3000"
    # ]
    PROJECT_NAME: str = "TELEDASH"
    MANAGER = LoginManager(
        config("JWT_SECRET_KEY", cast=str),
        '/login', 
        use_cookie=True, 
        custom_exception=NotAuthenticatedException
    )
    
    
    # Database
    # MONGO_CONNECTION_STRING: str = config("MONGO_CONNECTION_STRING", cast=str)
    
    class Config:
        case_sensitive = True
        


settings = Settings()
    
