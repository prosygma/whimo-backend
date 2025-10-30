from dataclasses import dataclass

from authlib.integrations.django_client import OAuth
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from whimo.auth.jwt.mappers import AccessRefreshTokenMapper
from whimo.auth.jwt.schemas.dto import AccessRefreshTokenDTO
from whimo.auth.social.schemas.dto import OAuthProvider, OAuthUserInfo
from whimo.auth.social.schemas.errors import OAuthError
from whimo.auth.social.schemas.requests import OAuthIdTokenRequest
from whimo.db.enums import GadgetType
from whimo.db.models import Gadget, User


@dataclass(slots=True)
class OAuthService:
    @staticmethod
    def authorize_token(request: OAuthIdTokenRequest, provider: OAuthProvider) -> AccessRefreshTokenDTO:
        try:
            data = OAuthService._parse_id_token(request, provider)
        except Exception as err:
            raise OAuthError from err
        user_info = OAuthUserInfo(**data)
        return OAuthService._process_user_info(user_info)

    @staticmethod
    def _process_user_info(userinfo: OAuthUserInfo) -> AccessRefreshTokenDTO:
        try:
            user = OAuthService._fetch_user_with_gadget(userinfo)
        except Gadget.DoesNotExist:
            user = OAuthService._create_user_with_gadget(userinfo)

        refresh = RefreshToken.for_user(user)
        return AccessRefreshTokenMapper.to_dto(refresh)

    @staticmethod
    def _parse_id_token(request: OAuthIdTokenRequest, provider: OAuthProvider) -> dict:
        if provider == OAuthProvider.GOOGLE:
            return OAuthService._parse_google_id_token(request)
        if provider == OAuthProvider.APPLE:
            return OAuthService._parse_apple_id_token(request)
        raise NotImplementedError  # pragma: no cover

    @staticmethod
    def _parse_google_id_token(request: OAuthIdTokenRequest) -> dict:
        oauth = OAuth()
        oauth.register(
            name="google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email"},
        )

        token = {"id_token": request.id_token}
        return oauth.google.parse_id_token(token=token, nonce=request.nonce)

    @staticmethod
    def _parse_apple_id_token(request: OAuthIdTokenRequest) -> dict:
        oauth = OAuth()
        oauth.register(
            name="apple",
            server_metadata_url="https://account.apple.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email"},
        )

        token = {"id_token": request.id_token}
        claims_options = {"iss": {"value": "https://appleid.apple.com"}}
        return oauth.apple.parse_id_token(token=token, nonce=request.nonce, claims_options=claims_options)

    @staticmethod
    def _fetch_user_with_gadget(userinfo: OAuthUserInfo) -> User:  # type: ignore
        gadget = Gadget.objects.select_related("user").get(identifier=userinfo.email, type=GadgetType.EMAIL)
        return gadget.user

    @staticmethod
    def _create_user_with_gadget(userinfo: OAuthUserInfo) -> User:  # type: ignore
        with transaction.atomic():
            user = User.objects.create_custom_user(password=None)
            Gadget.objects.create(
                user=user,
                type=GadgetType.EMAIL,
                identifier=userinfo.email,
                is_verified=userinfo.email_verified,
            )
        return user
