from django.db import migrations

RENAMES = {
    "0201": {
        "Viande de bovins": "Viande de bovins, fraîche ou réfrigérée",
        "Carne de bovino": "Carne de bovino, fresca o refrigerada",
    },
    "0202": {
        "Viande de bovins": "Viande de bovins, congelée",
        "Carne de bovino": "Carne de bovino, congelada",
    },
    "020610": {
        "Abats comestibles de bovins": "Abats comestibles de bovins, frais ou réfrigérés",
        "Despojos comestibles de bovino": "Despojos comestibles de bovino, frescos o refrigerados",
    },
    "020629": {
        "Abats comestibles de bovins": "Abats comestibles de bovins, congelés",
        "Despojos comestibles de bovino": "Despojos comestibles de bovino, congelados",
    },
    "230660": {
        "Oilcake and other solid residues": "Palm nut or kernel oilcake and other solid residues",
        "Tourteaux et autres résidus solides": "Tourteaux et autres résidus solides de noix ou d'amandes de palme",
        "Tortas y demás residuos sólidos": "Tortas y demás residuos sólidos de nuez o almendra de palma",
    },
    "2304": {
        "Oilcake and other solid residues": "Soya-bean oilcake and other solid residues",
        "Tourteaux et autres résidus solides": "Tourteaux et autres résidus solides de soja",
        "Tortas y demás residuos sólidos": "Tortas y demás residuos sólidos de soja",
    },
}


def distinguish_commodity_names(apps, schema_editor) -> None:
    Commodity = apps.get_model("db", "Commodity")

    for commodity in Commodity.objects.filter(code__in=RENAMES):
        renames = RENAMES[commodity.code]
        commodity.name = renames.get(commodity.name, commodity.name)
        commodity.name_variants = {key: renames.get(value, value) for key, value in commodity.name_variants.items()}
        commodity.save(update_fields=["name", "name_variants"])


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0014_drop_test_mode_cross_schema_foreign_keys"),
    ]

    operations = [
        migrations.RunPython(distinguish_commodity_names, migrations.RunPython.noop),
    ]
