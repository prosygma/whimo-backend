import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import requests

from whimo.db.models import WhatsAppSettings

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/{version}/{phone_number_id}/messages"
TIMEOUT_SECONDS = 10


class WhatsAppError(Exception):
    """The request was rejected (bad token, template or number): retrying will not help."""


class WhatsAppTemporaryError(Exception):
    """Network error or Meta-side failure: worth retrying."""


@dataclass(slots=True)
class WhatsAppClient:
    config: WhatsAppSettings

    def send_otp(self, recipient: str, code: str, language: str | None = None) -> str:
        """Sends `code` with the authentication template; returns the WhatsApp message id."""
        url = GRAPH_API_URL.format(version=self.config.api_version, phone_number_id=self.config.phone_number_id)
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient.strip().lstrip("+"),
            "type": "template",
            "template": {
                "name": self.config.template_name,
                "language": {"code": self.config.template_language(language)},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": code}]},
                    # Authentication templates carry a copy-code (url) button that needs the code too.
                    {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": code}]},
                ],
            },
        }
        headers = {"Authorization": f"Bearer {self.config.access_token}"}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise WhatsAppTemporaryError(f"WhatsApp request failed: {exc}") from exc

        body = self._json(response)
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            raise WhatsAppTemporaryError(f"WhatsApp error {response.status_code}: {self._error(body)}")
        if response.status_code >= HTTPStatus.BAD_REQUEST:
            raise WhatsAppError(f"WhatsApp error {response.status_code}: {self._error(body)}")

        messages = body.get("messages") or [{}]
        return str(messages[0].get("id", ""))

    @staticmethod
    def _json(response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _error(body: dict[str, Any]) -> str:
        error = body.get("error") or {}
        return str(error.get("message") or body or "no details")
