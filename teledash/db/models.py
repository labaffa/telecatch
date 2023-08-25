from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Enum, Text, \
    UnicodeText, Unicode, DateTime, Float, Index, MetaData, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    displayname = Column(Text, nullable=True, default="")
    first_name = Column(Text, nullable=True, default="")
    last_name = Column(Text, nullable=True, default="")
    disabled = Column(Boolean, default=False)
    hashed_password = Column(Text, nullable=True)


class ChannelCommon(Base):
    __tablename__ = "channel_common"
    id = Column(Integer, primary_key=True)
    url = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    access_hash = Column(Text)
    messages_count = Column(Text)
    participants_count = Column(Text)
    about = Column(Text, default="")
    title = Column(Text, default="")
    inserted_at = Column(DateTime)
    updated_at = Column(DateTime)


class Tag(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)


class ChannelCustom(Base):
    __tablename__ = "channel_custom"
    channel_id = Column(Integer, ForeignKey("channel_common.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    language = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    category = Column(Text, nullable=True)


class ChannelTag(Base):
    __tablename__ = "channel_tag"

    channel_id = Column(Integer, ForeignKey("channel_common.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    tag_id = Column(Integer, ForeignKey("tag.id")) 


class TgClient(Base):
    __tablename__ = "tg_client"

    id = Column(Text, primary_key=True)
    phone = Column(Text, nullable=False)
    authenticated = Column(Boolean, default=False)



