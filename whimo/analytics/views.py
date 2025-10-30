from typing import Any

from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.analytics.services import AnalyticsService
from whimo.common.schemas.base import DataResponse


class AnalyticsView(views.APIView):
    def get(self, _: Request, *__: Any, **___: Any) -> Response:
        analytics_data = AnalyticsService.get_analytics_data()
        return DataResponse(data=analytics_data).as_response()


class UserAnalyticsView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        user_analytics = AnalyticsService.get_user_analytics_data(user_id=request.user.id)
        return DataResponse(data=user_analytics).as_response()
