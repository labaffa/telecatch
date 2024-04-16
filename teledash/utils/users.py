from fastapi import Depends, Request, BackgroundTasks
from typing import Optional
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, \
    JWTStrategy, CookieTransport
from fastapi_users.db import SQLAlchemyUserDatabase
from teledash.db.db_setup import get_user_db
from teledash.config import settings, mail_connection_config, AUTH_EXPIRATION_TIME
from teledash.db.models import User
from fastapi_mail import FastMail, MessageSchema, MessageType
from jose import JWTError, jwt
import datetime as dt
from urllib.parse import urljoin


class UserManager(UUIDIDMixin, BaseUserManager):
    reset_password_token_secret = settings.JWT_SECRET_KEY
    verification_token_secret = settings.JWT_SECRET_KEY

    async def on_after_request_verify(
        self, user: User, token: str, 
        request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    async def on_after_forgot_password(
            self, user: User, token: str, request: Optional[Request] = None, 
        ):
            host = urljoin(request.headers.get('referer'), "/")
            href = urljoin(host, f"reset_password?ac={token}")
            html = f"""
                Hello,<br>
                <br>
                You (or someone else) entered this email address when 
                trying to reset the password of a TeleCatch account.<br>

                If you are not a TeleCatch user, please ignore this email. <br>
                <br>
                To initiate the password reset process, click <a href="{href}">here</a>
                """
            timestamp = dt.datetime.strftime(dt.datetime.utcnow(), '%Y-%m-%dT%H%M%S')
            message = MessageSchema(
                subject=f"Password recovery - {timestamp}",
                recipients=[user.email],
                body=html,
                subtype=MessageType.html)
            fm = FastMail(mail_connection_config)
            pay = jwt.decode(
                 token,
                 settings.JWT_SECRET_KEY, 
                 algorithms=[settings.ALGORITHM],
                 audience='fastapi-users:reset'
                 )
            await fm.send_message(message)
            

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/v1/auth/login")

# COOKIE AUTH
cookie_transport = CookieTransport(cookie_max_age=AUTH_EXPIRATION_TIME)


def get_jwt_strategy():
    return JWTStrategy(
         secret=settings.JWT_SECRET_KEY, lifetime_seconds=AUTH_EXPIRATION_TIME)


auth_backend = AuthenticationBackend(
    name="jwt", 
    transport=bearer_transport, 
    get_strategy=get_jwt_strategy                                     
)


cookie_auth_backend = AuthenticationBackend(
  name="cookie",  # I changed the name
  transport=cookie_transport,
  get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers(get_user_manager, [auth_backend, cookie_auth_backend])

active_user = fastapi_users.current_user(active=True)


