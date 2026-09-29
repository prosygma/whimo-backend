from typing import Any

from django.db.models import Model

from whimo.common.test_mode import is_test_mode

# Models that get their own tables in the test_mode schema. In test mode every query
# runs on the test_mode alias (search_path=test_mode,public), so these resolve to the
# test_mode copies while everything else - User, Commodity, HarvestSeason, ... -
# falls through to public, including inside joins and subqueries. Their tables must
# NOT exist in the test_mode schema: a foreign key created there would bind to an
# empty test_mode copy instead of the real, populated public one (Postgres resolves
# an unqualified table name in a constraint at CREATE TIME via search_path, not
# per-query).
TEST_MODE_MODEL_NAMES = {
    "transaction",
    "historicaltransaction",
    "balance",
    "historicalbalance",
    "notification",
    "historicalnotification",
    "notificationsettings",
    "historicalnotificationsettings",
}

# Additionally allowed only for allow_migrate: legacy models that Transaction and
# HistoricalTransaction used to have a foreign key to, removed in
# 0011_retire_legacy_seasons. Replaying migration history against a fresh test_mode
# alias still passes through the migration that first added that FK, so the
# referenced table has to exist transiently - then 0011 drops it again under
# test_mode too, same as it already did under default.
_LEGACY_MIGRATION_ONLY_MODEL_NAMES = {
    "season",
    "historicalseason",
    "seasoncommodity",
    "historicalseasoncommodity",
}


class TestModeRouter:
    def db_for_read(self, _model: type[Model], **_hints: Any) -> str | None:
        return self._route()

    def db_for_write(self, _model: type[Model], **_hints: Any) -> str | None:
        return self._route()

    def allow_relation(self, _obj1: Any, _obj2: Any, **_hints: Any) -> bool:
        # default and test_mode are the same physical database (same host, port and
        # name; only search_path differs), so a Transaction row routed to test_mode
        # and a User row routed to default are always a valid relation.
        return True

    def allow_migrate(
        self, db: str, _app_label: str, model_name: str | None = None, **hints: Any
    ) -> bool | None:
        if db == "default":
            return True
        if db != "test_mode":
            return None
        if hints.get("always_migrate"):
            return True
        # Data migrations (RunPython/RunSQL) carry no model_name and write through
        # this same router like any other ORM code, not through whichever alias is
        # being migrated - replaying them here would write into "default" a second
        # time. Only replay operations that shape a specific model's table.
        return model_name in TEST_MODE_MODEL_NAMES or model_name in _LEGACY_MIGRATION_ONLY_MODEL_NAMES

    @staticmethod
    def _route() -> str | None:
        return "test_mode" if is_test_mode() else None
