from django.db import migrations


def seed_commodities(apps, schema_editor):
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    Commodity = apps.get_model("db", "Commodity")

    # Each entry: (code, name, unit)
    data = {
        "Cattle": [
            ("010221", "Pure-bred cattle for breeding", "head"),
            ("010229", "Live cattle", "head"),
            ("0201", "Meat of bovine animals, fresh or chilled", "kg"),
            ("0202", "Meat of bovine animals, frozen", "kg"),
            ("020610", "Fresh or chilled edible offal of bovine animals", "kg"),
            ("020622", "Frozen edible bovine livers", "kg"),
            ("020629", "Frozen edible bovine offal", "kg"),
            ("160250", "Prepared or preserved meat or offal of bovine animals", "kg"),
            ("4101", "Raw hides and skins of bovine or equine animals", "m2"),
            ("4104", "Tanned or crust hides and skins of bovine or equine animals", "m2"),
            ("4107", "Leather further prepared after tanning or crusting, of bovine", "m2"),
        ],
        "Cocoa": [
            ("1801", "Cocoa beans", "kg"),
            ("1802", "Cocoa shells and other cocoa waste", "kg"),
            ("1803", "Cocoa paste", "kg"),
            ("1804", "Cocoa butter, fat and oil", "kg"),
            ("1805", "Cocoa powder", "kg"),
            ("1806", "Chocolate and other preparations containing cocoa", "kg"),
        ],
        "Coffee": [
            (
                "0901",
                "Coffee, whether or not roasted or decaffeinated; coffee husks and skins; coffee substitutes",
                "kg",
            ),
        ],
        "Palm Oil": [
            ("120710", "Palm nuts and kernels", "kg"),
            ("1511", "Palm oil and its fractions", "kg"),
            ("151321", "Crude palm kernel and babassu oil", "kg"),
            ("151329", "Palm kernel and babassu oil and their fractions", "kg"),
            ("230660", "Oilcake and other solid residues", "kg"),
            ("290545", "Glycerol", "kg"),
            ("291570", "Palmitic acid, stearic acid, their salts and esters", "kg"),
            ("291590", "Saturated acyclic monocarboxylic acids", "kg"),
            ("382311", "Stearic acid", "kg"),
            ("382312", "Oleic acid", "kg"),
            ("382319", "Fatty acids, industrial, monocarboxylic", "kg"),
            ("382370", "Fatty alcohols", "kg"),
        ],
        "Rubber": [
            ("4001", "Natural rubber and similar natural gums", "kg"),
            ("4005", "Compounded rubber, unvulcanised", "kg"),
            ("4006", "Unvulcanised rubber forms", "kg"),
            ("4007", "Vulcanised rubber thread and cord", "m"),
            ("4008", "Vulcanised rubber plates, sheets, strips and profiles", "m2"),
            ("4010", "Conveyor or transmission belts of vulcanised rubber", "m"),
            ("4011", "New pneumatic tyres", "pcs"),
            ("4012", "Retreaded or used tyres; solid or cushion tyres", "pcs"),
            ("4013", "Inner tubes of rubber", "pcs"),
            ("4015", "Rubber apparel and clothing accessories", "pcs"),
            ("4016", "Articles of vulcanised rubber, n.e.s.", "kg"),
            ("4017", "Hard rubber and articles, n.e.s.", "kg"),
        ],
        "Soy": [
            ("1201", "Soya beans", "kg"),
            ("120810", "Soya bean flour and meal", "kg"),
            ("1507", "Soya-bean oil and its fractions", "kg"),
            ("2304", "Oilcake and other solid residues", "kg"),
        ],
    }

    groups_cache = {}
    for group_name, items in data.items():
        group, _ = CommodityGroup.objects.get_or_create(name=group_name)
        groups_cache[group_name] = group

        for code, name, unit in items:
            Commodity.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "unit": unit,
                    "group": group,
                },
            )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0022_historicaltransaction_farm_latitude_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_commodities),
    ]
