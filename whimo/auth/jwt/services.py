from dataclasses import dataclass

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from whimo.auth.jwt.mappers import AccessRefreshTokenMapper
from whimo.auth.jwt.schemas.dto import AccessRefreshTokenDTO
from whimo.auth.jwt.schemas.errors import (
    AuthenticationFailedError,
    NoVerifiedGadgetError,
    SocialAccountError,
    TokenNotValidError,
)
from whimo.auth.jwt.schemas.requests import TokenObtainPairRequest, TokenRefreshRequest
from whimo.common.utils import get_user_model
from whimo.db.models import Gadget

User = get_user_model()


@dataclass(slots=True)
class JWTService:
    @staticmethod
    def obtain_token_pair(payload: TokenObtainPairRequest) -> AccessRefreshTokenDTO:
        if not (user := authenticate(username=payload.username, password=payload.password)):
            gadget = Gadget.objects.select_related("user").filter(identifier=payload.username).first()
            if gadget and not gadget.user.is_deleted and not gadget.user.has_usable_password():
                raise SocialAccountError
            raise AuthenticationFailedError

        if not user.gadgets.filter(is_verified=True).exists():
            raise NoVerifiedGadgetError

        refresh = RefreshToken.for_user(user)
        return AccessRefreshTokenMapper.to_dto(refresh)

    @staticmethod
    def refresh_token_pair(payload: TokenRefreshRequest) -> AccessRefreshTokenDTO:
        try:
            refresh = RefreshToken(payload.refresh)  # type: ignore
        except Exception as exc:
            raise TokenNotValidError from exc

        return AccessRefreshTokenMapper.to_dto(refresh)
