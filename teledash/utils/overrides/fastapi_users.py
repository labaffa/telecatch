from fastapi_users import FastAPIUsers
from teledash.utils.overrides.auth import get_auth_router
from fastapi_users.authentication import AuthenticationBackend
from fastapi import APIRouter


class FastAPIUsersOverride(FastAPIUsers):
    def get_auth_router(
        self, backend: AuthenticationBackend, requires_verification: bool = False
    ) -> APIRouter:
        """
        Return an auth router for a given authentication backend.

        :param backend: The authentication backend instance.
        :param requires_verification: Whether the authentication
        require the user to be verified or not. Defaults to False.
        """
        return get_auth_router(
            backend,
            self.get_user_manager,
            self.authenticator,
            requires_verification,
        )



