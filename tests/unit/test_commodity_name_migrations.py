import importlib

import pytest
from django.apps import apps
from django.conf import settings

from tests.factories.commodities import CommodityFactory
from whimo.db.models import Commodity

populate_migration = importlib.import_module("whimo.db.migrations.0002_populate_commodities")
variants_migration = importlib.import_module("whimo.db.migrations.0004_name_variants_to_dict")
distinguish_migration = importlib.import_module("whimo.db.migrations.0015_distinguish_commodity_names")

pytestmark = [pytest.mark.django_db]


class TestDistinguishCommodityNamesMigration:
    def test_every_seeded_commodity_has_a_distinct_name_in_each_language(self) -> None:
        # Arrange
        populate_migration.populate_commodities(apps, None)
        variants_migration.list_to_dict(apps, None)

        # Act
        distinguish_migration.distinguish_commodity_names(apps, None)

        # Assert
        commodities = list(Commodity.objects.all())
        for language, _ in settings.LANGUAGES:
            names = [commodity.name_variants.get(language, commodity.name) for commodity in commodities]
            assert len(set(names)) == len(names), language

    def test_names_an_admin_changed_stay_as_they_are(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(
            code="2304",
            name="Soybean meal",
            name_variants={"fr-FR": "Tourteau de soja", "es-ES": "Tortas y demás residuos sólidos"},
        )

        # Act
        distinguish_migration.distinguish_commodity_names(apps, None)

        # Assert
        commodity.refresh_from_db()
        assert commodity.name == "Soybean meal"
        assert commodity.name_variants == {
            "fr-FR": "Tourteau de soja",
            "es-ES": "Tortas y demás residuos sólidos de soja",
        }
