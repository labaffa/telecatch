from pydantic import BaseModel, Field, EmailStr, Json, AliasChoices
from typing import Union, Optional, List, Literal, Any
from uuid import UUID, uuid4
from dateutil.parser import parse
import datetime as dt
from fastapi_users import schemas as fu_schemas


def validate_int(v):
    if not v:
        return 0
    return int(v)


def validate_date(v):
    if not v:
        return None
    return parse(v)


class StringInt(str):
    @classmethod
    def __get_validators__(cls):
        yield validate_int


class StrictDate(dt.datetime):
    @classmethod
    def __get_validators__(cls):
        yield validate_date


class ChannelCreate(BaseModel):
    url: Union[str, int]

    def __hash__(self):
        return hash(self.url)


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
    channel_id: int
    username: str
    message: str
    timestamp: str
    type: str
    country: Union[str, None]
    language: Union[str, None]
    category: Union[str, None]
    views: Union[StringInt, None]
    media_type: Union[str, None] = None
    media_description: Union[str, None] = None
    media_filename: Union[str, None] = None
    author_type: Optional[int]
    author_id: Optional[int]
    author_username: Optional[str]
    author_name: Optional[str]
    reply_to_author_type: Optional[int]
    reply_to_author_id: Optional[int]
    reply_to_author_username: Optional[str]
    reply_to_author_name: Optional[str]
    fwd_from_author_type: Optional[int]
    fwd_from_author_id: Optional[int]
    fwd_from_author_username: Optional[str]
    fwd_from_author_name: Optional[str]


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
    username: str = Field(..., min_length=1, max_length=50, description="user username")
    password: str = Field(..., min_length=1, max_length=24, description="user password")
    

class TelegramClient(BaseModel):
    phone: Union[str, None] = None
    api_id: int
    api_hash: str
    client_id: str  # this is session_path (phone + id + hash)
    authenticated: bool = False


class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    displayname: Union[str, None] = None
    first_name: Union[str, None] = None
    last_name: Union[str, None] = None
    disabled: Optional[bool] = False
    
    
class UserTelegramRelation(BaseModel):
    user_id: int
    client_id: str


class UserInDB(User):
    hashed_password: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ChannelUpload(BaseModel):
    url: str
    location: Union[str, None] = None
    language: Union[str, None] = None
    category: Union[str, None] = None
    # username: Union[str, None] = None
    # name: Union[str, None] = None
    # type: Union[str, None] = None


class ChannelCommon(BaseModel):
    id: Union[int, None] = None
    url: str
    username: Union[str, None] = None
    type: Literal["channel", "group", "undefined"] = "undefined"
    access_hash: Union[int, None] = None
    messages_count: Union[int, None] = None
    participants_count: Union[int, None] = None
    about: str = ""
    title: str = Field(validation_alias="name", default="")
    inserted_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)

    class Config:
        from_attributes = True
        populate_by_name = True


class ChannelCustomCreate(BaseModel):
    channel_url: str = Field(..., validation_alias=AliasChoices("url", "channel_url"))
    language: str | None = None
    location: str | None = None
    category: str | None = None


class ChannelCustom(ChannelCustomCreate):
    user_id: int | UUID | str
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ChannelInfo(ChannelCommon):
    language: Optional[str]
    location: Optional[str]
    category: Optional[str]


class ChannelTag(BaseModel):
    user_id: int
    channel_id: int
    tag_id: int = 0  # index for meaningless/default tag


class Tag(BaseModel):
    tag: str
    tag_id: int


class ChannelCollection(BaseModel):
    collection_title: str
    user_id: int
    channel_url: str
    language: str | None = None
    location: str | None = None
    category: str | None = None    


class ChannelCollectionPayload(BaseModel):
    """ user_id is taken from fastapi dependency"""

    collection_title: str
    channel_urls: List[ChannelCreate]


class Job(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    status: str = "in_progress"
    processed_channels: List[str] = Field(default_factory=list)


class CollectionJob(BaseModel):
    uid: str
    user_id: int
    collection_title: str
    status: str = "in_progress"
    processed_channels: Json[Any] = '[]'

    class Config:
        from_attributes = True
        populate_by_name = True


class ActiveCollection(BaseModel):
    user_id: int
    collection_title: str


class ActiveClient(BaseModel):
    user_id: int
    client_id: str
    

class Entity(BaseModel):
    id: int
    entity_type: int
    username: Optional[str]
    name: Optional[str]
    phone: Optional[int]



# fastapi-users

class UserReadFU(fu_schemas.BaseUser):
    username: str


class UserCreateFU(fu_schemas.BaseUserCreate):
    username: str


class UserUpdateFU(fu_schemas.BaseUserUpdate):
    username: str


class EmailSchema(BaseModel):
    email: List[EmailStr]





