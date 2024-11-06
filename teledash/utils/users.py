from fastapi import Depends, Request, BackgroundTasks, Response
from typing import Coroutine, Optional
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
from bcrypt import gensalt
from fastapi_users import exceptions, models, schemas
from teledash.utils.overrides.fastapi_users import FastAPIUsersOverride
from fastapi_users.jwt import SecretType, decode_jwt, generate_jwt
from teledash.config import settings, AUTH_EXPIRATION_TIME
from teledash.utils.admin import derive_key_from_password, encrypt_data
import logging


logger = logging.getLogger('uvicorn.error')


class UserManager(UUIDIDMixin, BaseUserManager):
    reset_password_token_secret = settings.JWT_SECRET_KEY
    verification_token_secret = settings.JWT_SECRET_KEY

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> models.UP:
        """
        This overrides the fastapi_users method in order to add the salt. The salt
        is used to create a key derived from password to encrypt data, and not for 
        passwords.

        Create a user in database.

        Triggers the on_after_register handler on success.

        :param user_create: The UserCreate model to create.
        :param safe: If True, sensitive values like is_superuser or is_verified
        will be ignored during the creation, defaults to False.
        :param request: Optional FastAPI request that
        triggered the operation, defaults to None.
        :raises UserAlreadyExists: A user already exists with the same e-mail.
        :return: A new user.
        """
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        user_dict["salt"] = gensalt().decode()

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user
    
    async def on_after_request_verify(
        self, user: User, token: str, 
        request: Optional[Request] = None
    ):
        logger.info(f"Verification requested for user {user.id}. Verification token: {token}")

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
    
    async def on_after_login(
        self, user: User, 
        credentials, request: Request | None = None, response: Response | None = None, 
    ) -> None:
        key = derive_key_from_password(credentials.password, user.salt.encode())
        enc_key = encrypt_data(settings.DATA_SECRET_KEY.encode(), key.hex())
        data = {"sub": enc_key.hex()}
        expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=AUTH_EXPIRATION_TIME)
        data["exp"] = expire
        cookie = generate_jwt(data, settings.JWT_SECRET_KEY, lifetime_seconds=AUTH_EXPIRATION_TIME)
        r = {
            "httponly": False,
        }
        try:
            ff = dict(response.raw_headers)['set-cookie'.encode()].decode().split(";")
            for f in ff:
                a = f.strip().split("=")
                if len(a) == 1:
                    if a[0].lower() == 'httponly':
                        r["httponly"] = True
                else:
                    match a[0].lower():
                        case "max-age":
                            r["max_age"] = a[1]
                        case "path":
                            r["path"] = a[1]
                        case "samesite":
                            r["samesite"] = a[1]
        except KeyError:  # not a cookie tranport login, e.g. a bearer transport
            r["httponly"] = True
            r["max_age"] = AUTH_EXPIRATION_TIME
            r["path"] = "/"
            r["samesite"] = "lax"
        response.set_cookie(
            'key_hash',
            cookie,
            max_age=r.get("max_age"),
            path=r.get("path"),
            httponly=r.get("httponly"),
            samesite=r.get("samesite"),
        )



async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/api/v1/auth/login")

# COOKIE AUTH
cookie_transport = CookieTransport(
     cookie_max_age=AUTH_EXPIRATION_TIME, cookie_secure=False
)


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


fastapi_users = FastAPIUsersOverride(get_user_manager, [auth_backend, cookie_auth_backend])

active_user = fastapi_users.current_user(active=True)


