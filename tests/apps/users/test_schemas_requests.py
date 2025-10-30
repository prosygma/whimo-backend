from unittest.mock import patch

import pytest

from whimo.users.schemas.errors import ExactlyOneIdentifierRequiredError
from whimo.users.schemas.requests import GadgetCreateRequest

pytestmark = [pytest.mark.django_db]


class TestGadgetCreateRequest:
    def test_identifier_property_defensive_error(self) -> None:
        # Arrange
        with patch.object(GadgetCreateRequest, "model_validate"):
            request = GadgetCreateRequest.model_construct(email=None, phone=None)

            # Act & Assert
            with pytest.raises(ExactlyOneIdentifierRequiredError):
                _ = request.identifier
