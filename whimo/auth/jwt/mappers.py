from dataclasses import dataclass

from rest_framework_simplejwt.tokens import RefreshToken

from whimo.auth.jwt.schemas.dto import AccessRefreshTokenDTO


@dataclass(slots=True)
class AccessRefreshTokenMapper:
    @staticmethod
    def to_dto(entity: RefreshToken) -> AccessRefreshTokenDTO:
        return AccessRefreshTokenDTO(
            access=str(entity.access_token),
            refresh=str(entity),
        )
