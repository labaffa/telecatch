import os
from inspect import getsourcefile
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from decouple import config
from enum import Enum
from fastapi_mail import ConnectionConfig


load_dotenv()


this_path = os.path.abspath(getsourcefile(lambda:0))
this_folder = os.path.dirname(this_path)
repo_folder = os.path.dirname(os.path.dirname(this_folder))
SOURCE_FOLDER = os.path.dirname(this_folder)
SESSIONS_FOLDER =  os.path.join(SOURCE_FOLDER, "sessions")
DATA_FOLDER = os.path.join(SOURCE_FOLDER, "data")

SQLALCHEMY_DATABASE_URL = (
    'sqlite+aiosqlite:///' + 
    f'{os.path.join(SESSIONS_FOLDER, "teledash.db")}'
)

DEFAULT_CHANNELS = [
     x.strip(" \n") for x in open(os.path.join(SOURCE_FOLDER, "channels.txt"), "r").readlines() if x.strip(" \n")
]


AUTH_EXPIRATION_TIME = int(os.getenv("AUTH_EXPIRATION_TIME", 999999999))



class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", cast=str)
    JWT_REFRESH_SECRET_KEY: str = config(
        "JWT_REFRESH_SECRET_KEY", cast=str)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = (60 * 24 * 365) * 10  # 10 years
    REFRESH_TOKEN_EXPIRE_MINUTES: int = (60 * 24 * 365) * 10 
    DATA_SECRET_KEY: str = config("DATA_SECRET_KEY", cast=str)
    # BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
    #     "http://localhost:3000"
    # ]
    PROJECT_NAME: str = "TeleCatch"
    # Database
    # MONGO_CONNECTION_STRING: str = config("MONGO_CONNECTION_STRING", cast=str)
    
    class Config:
        case_sensitive = True
        


settings = Settings()
    
TELEGRAM_MEDIA_MAP = {
    "MessageMediaWebPage": "webpage",
    # "MessageMediaDocument": "document",
    "MessageMediaPhoto": "photo"
}


class EntityType(Enum):
    user = 1
    channel = 2
    chat = 3


mail_connection_config = ConnectionConfig(
    MAIL_USERNAME = "telecatch.api@gmail.com",
    MAIL_PASSWORD = "sztf wsgs sfbd vnpn",
    MAIL_FROM = "telecatch.api@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="TeleCatch",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    # VALIDATE_CERTS = False
)