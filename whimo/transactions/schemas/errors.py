from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import BadRequest, Conflict, InternalServerError, NotFound


class CommodityGroupRequiredError(BadRequest):
    message = _("Commodity group is required")


class OnlyAcceptedStatusAllowedError(BadRequest):
    message = _("Only accepted status is allowed")


class PartialLocationError(BadRequest):
    message = _("Location must be complete or must be empty")


class LocationFileMustBeProvidedError(BadRequest):
    message = _("Location file must be provided for this location type")


class LocationFileNotSupportedError(BadRequest):
    message = _("Location file is not supported for this location type")


class LocationFileInvalidSyntaxError(BadRequest):
    message = _("Location file syntax is invalid")


class InvalidStatusUpdateError(BadRequest):
    message = _("Transaction can only be accepted or rejected")


class RecipientConflictError(Conflict):
    message = _("Transaction recipient cannot be the same as the user")


class RecipientIsNotSpecifiedError(NotFound):
    message = _("Transaction recipient is not specified")


class LocationFileUploadError(InternalServerError):
    message = _("Location file upload error")


class LocationFileDownloadError(InternalServerError):
    message = _("Location file download error")


class RecipientInvalidError(BadRequest):
    message = _("Transaction recipient data must contain only one identifier at a time")


class InvalidLatitudeError(BadRequest):
    message = _("Latitude must be between -90 and 90 degrees")


class InvalidLongitudeError(BadRequest):
    message = _("Longitude must be between -180 and 180 degrees")
