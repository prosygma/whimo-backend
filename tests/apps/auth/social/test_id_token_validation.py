"""ID tokens sent by the mobile apps are parsed for real here (the other social tests mock parsing).

Tokens are signed with a key generated for the test; only authlib's network calls (provider
metadata and key set) are patched.
"""

import time
from collections.abc import Callable
from http import HTTPStatus
from typing import Any

import jwt
import pytest
from authlib.integrations.django_client import DjangoOAuth2App
from cryptography.hazmat.primitives.asymmetric import rsa
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper
from pytest_mock import MockerFixture

from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_EMAIL

pytestmark = [pytest.mark.django_db]

KEY_ID = "test-key"
GOOGLE_CLIENT_ID = "our-web-client.apps.googleusercontent.com"
APPLE_CLIENT_ID = "org.example.whimo"
OTHER_CLIENT_ID = "some-other-app.apps.googleusercontent.com"
NONCE = "nonce-1"  # both apps send a nonce with the ID token
PROVIDERS = {
    "google": {"url": reverse("google_login"), "issuer": "https://accounts.google.com"},
    "apple": {"url": reverse("apple_login"), "issuer": "https://appleid.apple.com"},
}

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_JWK = {
    **jwt.algorithms.RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True),
    "kid": KEY_ID,
    "alg": "RS256",
    "use": "sig",
}


@pytest.fixture(autouse=True)
def provider_keys(mocker: MockerFixture, settings: SettingsWrapper) -> None:
    settings.OAUTH_GOOGLE_ID_TOKEN_AUDIENCES = [GOOGLE_CLIENT_ID]
    settings.OAUTH_APPLE_ID_TOKEN_AUDIENCES = [APPLE_CLIENT_ID]

    def metadata(app: DjangoOAuth2App) -> dict:
        return {
            "issuer": PROVIDERS[app.name]["issuer"],
            "jwks_uri": "https://keys.invalid/",
            "id_token_signing_alg_values_supported": ["RS256"],
        }

    mocker.patch.object(DjangoOAuth2App, "load_server_metadata", autospec=True, side_effect=metadata)
    mocker.patch.object(DjangoOAuth2App, "fetch_jwk_set", return_value={"keys": [_PUBLIC_JWK]})


@pytest.fixture
def make_token() -> Callable[..., str]:
    def make(provider: str, aud: str | list[str] | None, **claims: Any) -> str:
        now = int(time.time())
        payload = {
            "iss": PROVIDERS[provider]["issuer"],
            "aud": aud,
            "sub": "subject-1",
            "email": USER_EMAIL,
            "email_verified": True,
            "iat": now,
            "exp": now + 600,
            "nonce": NONCE,
            **claims,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256", headers={"kid": KEY_ID})

    return make


def login(client: APIClient, provider: str, token: str) -> int:
    return client.post(path=PROVIDERS[provider]["url"], data={"id_token": token, "nonce": NONCE}).status_code


class TestIdTokenAudience:
    @pytest.mark.parametrize(("provider", "aud"), [("google", GOOGLE_CLIENT_ID), ("apple", APPLE_CLIENT_ID)])
    def test_token_for_our_client_is_accepted(
        self, client: APIClient, make_token: Callable[..., str], provider: str, aud: str
    ) -> None:
        assert login(client, provider, make_token(provider, aud)) == HTTPStatus.OK

    @pytest.mark.parametrize("provider", ["google", "apple"])
    def test_token_for_another_app_is_rejected(
        self, client: APIClient, make_token: Callable[..., str], provider: str
    ) -> None:
        assert login(client, provider, make_token(provider, OTHER_CLIENT_ID)) == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize("provider", ["google", "apple"])
    def test_token_without_audience_is_rejected(
        self, client: APIClient, make_token: Callable[..., str], provider: str
    ) -> None:
        assert login(client, provider, make_token(provider, None)) == HTTPStatus.UNAUTHORIZED

    def test_token_listing_our_client_among_others_is_accepted(
        self, client: APIClient, make_token: Callable[..., str]
    ) -> None:
        token = make_token("google", [OTHER_CLIENT_ID, GOOGLE_CLIENT_ID])
        assert login(client, "google", token) == HTTPStatus.OK

    def test_any_configured_audience_is_accepted(
        self, client: APIClient, make_token: Callable[..., str], settings: SettingsWrapper
    ) -> None:
        settings.OAUTH_GOOGLE_ID_TOKEN_AUDIENCES = [GOOGLE_CLIENT_ID, "ios-client.apps.googleusercontent.com"]
        token = make_token("google", "ios-client.apps.googleusercontent.com")
        assert login(client, "google", token) == HTTPStatus.OK

    @pytest.mark.parametrize("provider", ["google", "apple"])
    def test_no_configured_audience_rejects_every_token(
        self, client: APIClient, make_token: Callable[..., str], settings: SettingsWrapper, provider: str
    ) -> None:
        settings.OAUTH_GOOGLE_ID_TOKEN_AUDIENCES = []
        settings.OAUTH_APPLE_ID_TOKEN_AUDIENCES = []
        aud = GOOGLE_CLIENT_ID if provider == "google" else APPLE_CLIENT_ID
        assert login(client, provider, make_token(provider, aud)) == HTTPStatus.UNAUTHORIZED


class TestIdTokenOtherChecks:
    def test_tampered_signature_is_rejected(self, client: APIClient, make_token: Callable[..., str]) -> None:
        head, body, signature = make_token("google", GOOGLE_CLIENT_ID).split(".")
        forged = f"{head}.{body}.{signature[:-6]}AAAAAA"
        assert login(client, "google", forged) == HTTPStatus.UNAUTHORIZED

    def test_wrong_issuer_is_rejected(self, client: APIClient, make_token: Callable[..., str]) -> None:
        token = make_token("google", GOOGLE_CLIENT_ID, iss="https://issuer.invalid")
        assert login(client, "google", token) == HTTPStatus.UNAUTHORIZED

    def test_expired_token_is_rejected(self, client: APIClient, make_token: Callable[..., str]) -> None:
        now = int(time.time())
        token = make_token("google", GOOGLE_CLIENT_ID, iat=now - 7200, exp=now - 3600)
        assert login(client, "google", token) == HTTPStatus.UNAUTHORIZED
