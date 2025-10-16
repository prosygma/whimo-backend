from whimo.common.schemas.base import BaseRequest


class OAuthIdTokenRequest(BaseRequest):
    id_token: str
    nonce: str | None = None


class OAuthCodeRequest(BaseRequest):
    code: str
    redirect_uri: str
    state: str | None = None
    nonce: str | None = None
