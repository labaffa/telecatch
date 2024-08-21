from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Enum, Text, \
    UnicodeText, Unicode, DateTime, Float, Index, MetaData, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
import fastapi_users_db_sqlalchemy


Base = declarative_base()


class MyBase(Base):
    __abstract__ = True

    def to_dict(self):
        return {field.name:getattr(self, field.name) for field in self.__table__.c}


# class User(MyBase):
#     __tablename__ = "user"
#     __table_args__ = (
#        UniqueConstraint("username", name="user_username"),
#        UniqueConstraint("email", name="user_email")
#     )

#     id = Column(Integer, primary_key=True)
#     username = Column(Text, nullable=False)
#     email = Column(Text, nullable=False)
#     hashed_password = Column(Text, nullable=False)
#     displayname = Column(Text, nullable=True, default="")
#     first_name = Column(Text, nullable=True, default="")
#     last_name = Column(Text, nullable=True, default="")
#     disabled = Column(Boolean, default=False)


class User(SQLAlchemyBaseUserTableUUID, MyBase):
    __tablename__ = "user"
    __table_args__ = (
       # UniqueConstraint("username", name="user_username"),
       UniqueConstraint("email", name="user_email"),
    )
    username = Column(Text, nullable=False)
    displayname = Column(Text, nullable=True, default="")
    first_name = Column(Text, nullable=True, default="")
    last_name = Column(Text, nullable=True, default="")
    

class ChannelCommon(MyBase):
    __tablename__ = "channel_common"
    __table_args__ = (
       UniqueConstraint("id", name="channel_id"),
    )

    id = Column(Integer, nullable=True)
    url = Column(Text, primary_key=True, nullable=False, autoincrement=False)
    username = Column(Text, nullable=True)
    type = Column(Text, nullable=False)
    access_hash = Column(Integer, nullable=True)
    messages_count = Column(Integer, nullable=True)
    participants_count = Column(Integer, nullable=True)
    about = Column(Text, default="")
    title = Column(Text, default="")
    inserted_at = Column(DateTime)
    updated_at = Column(DateTime)


class ChannelCustom(MyBase):
    __tablename__ = "channel_custom"

    channel_url = Column(Text, primary_key=True)
    user_id = Column(fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True)
    language = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    category = Column(Text, nullable=True)
    is_joined = Column(Boolean, default=False)



class TgClient(MyBase):
    __tablename__ = "tg_client"

    id = Column(Text, primary_key=True, autoincrement=False)
    phone = Column(Text, nullable=False)
    authenticated = Column(Boolean, default=False)
    api_id = Column(Integer, nullable=True)
    api_hash = Column(Text, nullable=True)
    # api_id_last_2 = Column(Text, nullable=True)
    # api_hash_last_2 = Column(Text, nullable=True)


class UserClient(MyBase):
    __tablename__ = "user_client"

    user_id = Column(fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True)
    client_id = Column(Text, primary_key=True)


class ChannelCollection(MyBase):
    __tablename__ = "channel_collection"

    collection_title = Column(Text, primary_key=True)
    user_id = Column(fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True)
    channel_url = Column(Text, primary_key=True)
    language = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    category = Column(Text, nullable=True)


class CollectionJob(MyBase):
    __tablename__ = "collection_job"

    uid = Column(Text, primary_key=True, autoincrement=False)
    user_id = Column(fastapi_users_db_sqlalchemy.generics.GUID())
    collection_title = Column(Text)
    status = Column(Text, default="in_progress")
    processed_channels = Column(Text, default="[]")


class ActiveCollection(MyBase):
    __tablename__ = "active_collection"

    # I think the primary key should be just user_id, because just one for user should be there
    user_id = Column(fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True, autoincrement=False)
    collection_title = Column(Text, primary_key=True)


class ActiveClient(MyBase):
    __tablename__ = "active_client"

    user_id = Column(fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True, autoincrement=False)
    client_id = Column(Text)


class Entity(MyBase):
    __tablename__ = "entity"

    id = Column(Integer, primary_key=True, nullable=False)
    entity_type = Column(Integer, primary_key=True, nullable=False)
    username = Column(Text, nullable=True)
    name = Column(Text, nullable=True)
    phone = Column(Integer, nullable=True)



