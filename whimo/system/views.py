from typing import Any

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from whimo.system.schemas.responses import HealthcheckResponse


class HealthcheckView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, *_: Any, **__: Any) -> Response:
        return HealthcheckResponse().as_response()
