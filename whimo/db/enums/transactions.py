from enum import StrEnum
from typing import Any


class TransactionAction(StrEnum):
    BUYING = "buying"
    SELLING = "selling"


class TransactionType(StrEnum):
    PRODUCER = "producer"
    DOWNSTREAM = "downstream"
    CONVERSION = "conversion"


class TransactionLocation(StrEnum):
    QR = "qr"
    MANUAL = "manual"
    FILE = "file"
    GPS = "gps"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NO_RESPONSE = "no_response"


class TransactionTraceability(StrEnum):
    FULL = "full"
    CONDITIONAL = "conditional"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"

    @property
    def _order_map(self) -> dict[str, int]:
        return {
            TransactionTraceability.FULL: 4,
            TransactionTraceability.CONDITIONAL: 3,
            TransactionTraceability.PARTIAL: 2,
            TransactionTraceability.INCOMPLETE: 1,
        }

    def __lt__(self, other: Any) -> bool:
        return self._order_map[self] < self._order_map[other]
