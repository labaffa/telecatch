from pydantic import BaseModel, Field, EmailStr
from typing import Union, Optional, List
from uuid import UUID, uuid4


def validate_int(v):
    if not v:
        return 0
    return int(v)


class StringInt(str):
    @classmethod
    def __get_validators__(cls):
        yield validate_int


class ChannelCreate(BaseModel):
    identifier: Union[str, int]


class Channel(ChannelCreate):
    id: int
    about: str
    title: str
    participants_counts: int
    type: str
    inserted_at: str
    updated_at: str
    count: Union[int, None] = None
    access_hash: Union[int, None] = None
    username: Union[str, None] = None
    is_joined: bool = False


class Message(BaseModel):
    id: int
    username: str
    message: str
    timestamp: str
    type: str
    country: Union[str, None]
    views: Union[StringInt, None]
    # media: Union[str, None]


# login

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None


class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None


class UserAuth(BaseModel):
    email: EmailStr = Field(..., description="user email")
    username: str = Field(..., min_length=5, max_length=50, description="user username")
    password: str = Field(..., min_length=5, max_length=24, description="user password")
    

class TelegramClient(BaseModel):
    phone: Union[str, None] = None
    api_id: Union[str, None] = None
    api_hash: Union[str, None] = None
    client_id: str  # this is session_path (phone + id + hash)
    authenticated: bool = False


class User(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    displayname: Union[str, None] = None
    first_name: Union[str, None] = None
    last_name: Union[str, None] = None
    disabled: Optional[bool] = False
    
    
class UserTelegramRelation(BaseModel):
    user_id: str
    client_id: str


class UserInDB(User):
    hashed_password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None




