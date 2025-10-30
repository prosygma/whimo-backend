from typing import Any
from uuid import UUID

from rest_framework import views
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.common.schemas.base import DataResponse, PaginatedDataResponse
from whimo.notifications.mappers.notifications import NotificationsMapper
from whimo.notifications.mappers.notifications_push import NotificationsPushMapper
from whimo.notifications.mappers.notifications_settings import NotificationsSettingsMapper
from whimo.notifications.schemas.requests import (
    DeviceAddRequest,
    NotificationListRequest,
    NotificationSettingsUpdateRequest,
    NotificationStatusUpdateRequest,
)
from whimo.notifications.schemas.responses import (
    DeviceAddedResponse,
    NotificationSettingsUpdatedResponse,
    NotificationStatusUpdatedResponse,
)
from whimo.notifications.services.notifications import NotificationsService
from whimo.notifications.services.notifications_push import NotificationsPushService
from whimo.notifications.services.notifications_settings import NotificationsSettingsService


class NotificationsListView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = NotificationListRequest.parse(request, from_query_params=True)
        items, pagination = NotificationsService.list_notifications(user_id=request.user.id, request=payload)

        response = NotificationsMapper.to_dto_list(notifications=items)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()


class NotificationDetailView(views.APIView):
    def get(self, request: Request, notification_id: UUID, *_: Any, **__: Any) -> Response:
        notification = NotificationsService.get(user_id=request.user.id, notification_id=notification_id)

        response = NotificationsMapper.to_dto(notification=notification)
        return DataResponse(data=response).as_response()


class NotificationStatusUpdateView(views.APIView):
    def patch(self, request: Request, notification_id: UUID, *_: Any, **__: Any) -> Response:
        payload = NotificationStatusUpdateRequest.parse(request)
        NotificationsService.update_status(user_id=request.user.id, notification_id=notification_id, request=payload)
        return NotificationStatusUpdatedResponse().as_response()


class NotificationSettingsView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        settings = NotificationsSettingsService.list_notification_settings(user_id=request.user.id)
        response = NotificationsSettingsMapper.to_dto_list(settings=settings)
        return DataResponse(data=response).as_response()

    def put(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = NotificationSettingsUpdateRequest.parse(request)
        NotificationsSettingsService.update_notification_settings(user_id=request.user.id, request=payload)
        return NotificationSettingsUpdatedResponse().as_response()


class NotificationDevicesView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        devices = NotificationsPushService.list_devices(user_id=request.user.id)
        response = NotificationsPushMapper.to_dto_list(devices=devices)
        return DataResponse(data=response).as_response()

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = DeviceAddRequest.parse(request)
        NotificationsPushService.add_device(user_id=request.user.id, request=payload)
        return DeviceAddedResponse().as_response()
