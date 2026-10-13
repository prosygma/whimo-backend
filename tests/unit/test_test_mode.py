import pytest

from whimo.common.test_mode import enable_test_mode, is_test_mode

pytestmark = [pytest.mark.django_db]


class TestTestMode:
    def test_disabled_by_default(self) -> None:
        assert is_test_mode() is False

    def test_enabled_inside_context_manager(self) -> None:
        with enable_test_mode():
            assert is_test_mode() is True

    def test_disabled_after_context_manager_exits(self) -> None:
        with enable_test_mode():
            pass

        assert is_test_mode() is False

    def test_disabled_after_context_manager_raises(self) -> None:
        with pytest.raises(ValueError, match="boom"), enable_test_mode():
            raise ValueError("boom")

        assert is_test_mode() is False
