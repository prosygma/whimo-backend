from whimo.common.schemas.base import BaseRequest


class OAuthIdTokenRequest(BaseRequest):
    id_token: str
    nonce: str | None = None
