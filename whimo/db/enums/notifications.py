from enum import StrEnum


class NotificationStatus(StrEnum):
    PENDING = "pending"
    READ = "read"


class NotificationType(StrEnum):
    TRANSACTION_PENDING = "transaction_pending"
    TRANSACTION_ACCEPTED = "transaction_accepted"
    TRANSACTION_REJECTED = "transaction_rejected"
    TRANSACTION_EXPIRED = "transaction_expired"

    GEODATA_MISSING = "geodata_missing"
    GEODATA_UPDATED = "geodata_updated"


class NotificationDeviceType(StrEnum):
    FCM = "fcm"
    APNS = "apns"
