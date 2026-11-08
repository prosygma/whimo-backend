from typing import Any

from rest_framework.response import Response

from whimo.camertrace import services
from whimo.common.schemas.base import DataResponse
from whimo.languages.views import PublicView


class AppOptionsView(PublicView):
    """Geodata choices the mobile apps offer, set in the admin (Settings > Options)."""

    def get(self, *_: Any, **__: Any) -> Response:
        options = services.get_options()
        data = {
            "ask_on_plot": options.ask_on_plot,
            "allow_gps_point": options.allow_gps_point,
            "allow_cicc_qr": options.allow_cicc_qr,
        }
        return DataResponse(data=data).as_response()
