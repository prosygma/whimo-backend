from typing import TYPE_CHECKING, Any

from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication as DRFJWTAuthentication
from rest_framework_simplejwt.tokens import Token

from whimo.common.utils import get_user_model
from whimo.db.models import Gadget

if TYPE_CHECKING:  # pragma: no cover
    from rest_framework.views import APIView

User = get_user_model()


class JWTAuthentication(DRFJWTAuthentication):
    def authenticate(self, request: Request) -> tuple[User, Token] | None:  # type: ignore
        if not (auth := super().authenticate(request)):
            return None

        user, validated_token = auth
        if user.is_deleted:  # type: ignore
            return None

        return user, validated_token


class GadgetsModelBackend(ModelBackend):
    def authenticate(  # type: ignore
        self,
        _: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **__: Any,
    ) -> User | None:  # type: ignore
        try:
            gadget = Gadget.objects.select_related("user").get(identifier=username)
        except Gadget.DoesNotExist:
            return None

        user = gadget.user
        if user.is_deleted or not password or not user.check_password(password):
            return None

        return user


class HasVerifiedGadgetPermission(permissions.IsAuthenticated):
    message = _("At least one verified gadget is required")

    def has_permission(self, request: Request, view: "APIView") -> bool:
        if not super().has_permission(request, view):
            return False

        return request.user.gadgets.filter(is_verified=True).exists()  # type: ignore
