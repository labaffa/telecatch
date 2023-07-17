from pydantic import BaseModel
from typing import Union


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


class Message(BaseModel):
    username: str
    message: str
    timestamp: str
    type: str
    country: str
    views: StringInt

