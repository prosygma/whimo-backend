from django.db import migrations


def populate_name_variants(apps, schema_editor):
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    Commodity = apps.get_model("db", "Commodity")

    group_translations = {
        "Cattle": [
            "Bovin",
            "Ganado bovino",
        ],
        "Cocoa": [
            "Cacao",
            "Cacao",
        ],
        "Coffee": [
            "Café",
            "Café",
        ],
        "Palm Oil": [
            "Huile de palme",
            "Aceite de palma",
        ],
        "Rubber": [
            "Caoutchouc",
            "Caucho",
        ],
        "Soy": [
            "Soja",
            "Soja",
        ],
    }

    commodity_translations = {
        "Pure-bred cattle for breeding": [
            "Bovins de race pure pour l'élevage",
            "Ganado bovino de raza pura para cría",
        ],
        "Live cattle": [
            "Bovins vivants",
            "Ganado bovino vivo",
        ],
        "Meat of bovine animals, fresh or chilled": [
            "Viande de bovins",
            "Carne de bovino",
        ],
        "Meat of bovine animals, frozen": [
            "Viande de bovins",
            "Carne de bovino",
        ],
        "Fresh or chilled edible offal of bovine animals": [
            "Abats comestibles de bovins",
            "Despojos comestibles de bovino",
        ],
        "Frozen edible bovine livers": [
            "Foies de bovins comestibles",
            "Hígados de bovino comestibles",
        ],
        "Frozen edible bovine offal": [
            "Abats comestibles de bovins",
            "Despojos comestibles de bovino",
        ],
        "Prepared or preserved meat or offal of bovine animals": [
            "Viandes ou abats de bovins préparés ou conservés",
            "Carne o despojos de bovino preparados o conservados",
        ],
        "Raw hides and skins of bovine or equine animals": [
            "Peaux brutes de bovins ou d'équidés",
            "Pieles y cueros en bruto de bovino o equino",
        ],
        "Tanned or crust hides and skins of bovine or equine animals": [
            "Peaux de bovins ou d'équidés, tannées ou en crust",
            "Pieles y cueros curtidos o en crust de bovino o equino",
        ],
        "Leather further prepared after tanning or crusting, of bovine": [
            "Cuir de bovin, ouvré après tannage ou crust",
            "Cuero de bovino trabajado tras el curtido o crust",
        ],
        "Cocoa beans": [
            "Fèves de cacao",
            "Granos de cacao",
        ],
        "Cocoa shells and other cocoa waste": [
            "Coques et autres déchets de cacao",
            "Cáscaras y otros residuos de cacao",
        ],
        "Cocoa paste": [
            "Pâte de cacao",
            "Pasta de cacao",
        ],
        "Cocoa butter, fat and oil": [
            "Beurre, graisse et huile de cacao",
            "Manteca, grasa y aceite de cacao",
        ],
        "Cocoa powder": [
            "Cacao en poudre",
            "Cacao en polvo",
        ],
        "Chocolate and other preparations containing cocoa": [
            "Chocolat et autres préparations contenant du cacao",
            "Chocolate y demás preparaciones con cacao",
        ],
        "Coffee, whether or not roasted or decaffeinated; coffee husks and skins; coffee substitutes": [
            "Café, torréfié ou non, décaféiné ou non; coques et pellicules de café; succédanés du café",
            "Café, tostado o no, descafeinado o no; cáscaras y cascarillas de café; sucedáneos del café",
        ],
        "Palm nuts and kernels": [
            "Noix et amandes de palme",
            "Nueces y almendras de palma",
        ],
        "Palm oil and its fractions": [
            "Huile de palme et ses fractions",
            "Aceite de palma y sus fracciones",
        ],
        "Crude palm kernel and babassu oil": [
            "Huile brute de palmiste et de babassu",
            "Aceite crudo de palmiste y babasú",
        ],
        "Palm kernel and babassu oil and their fractions": [
            "Huile de palmiste et de babassu et leurs fractions",
            "Aceite de palmiste y babasú y sus fracciones",
        ],
        "Oilcake and other solid residues": [
            "Tourteaux et autres résidus solides",
            "Tortas y demás residuos sólidos",
        ],
        "Glycerol": [
            "Glycérol",
            "Glicerol",
        ],
        "Palmitic acid, stearic acid, their salts and esters": [
            "Acide palmitique, acide stéarique, leurs sels et esters",
            "Ácido palmítico, ácido esteárico, sus sales y ésteres",
        ],
        "Saturated acyclic monocarboxylic acids": [
            "Acides monocarboxyliques acycliques saturés",
            "Ácidos monocarboxílicos acíclicos saturados",
        ],
        "Stearic acid": [
            "Acide stéarique",
            "Ácido esteárico",
        ],
        "Oleic acid": [
            "Acide oléique",
            "Ácido oleico",
        ],
        "Fatty acids, industrial, monocarboxylic": [
            "Acides gras industriels monocarboxyliques",
            "Ácidos grasos industriales monocarboxílicos",
        ],
        "Fatty alcohols": [
            "Alcools gras",
            "Alcoholes grasos",
        ],
        "Natural rubber and similar natural gums": [
            "Caoutchouc naturel et gommes naturelles similaires",
            "Caucho natural y gomas naturales similares",
        ],
        "Compounded rubber, unvulcanised": [
            "Caoutchouc composé, non vulcanisé",
            "Caucho compuesto, sin vulcanizar",
        ],
        "Unvulcanised rubber forms": [
            "Formes de caoutchouc non vulcanisé",
            "Formas de caucho sin vulcanizar",
        ],
        "Vulcanised rubber thread and cord": [
            "Fil et corde en caoutchouc vulcanisé",
            "Hilo y cordón de caucho vulcanizado",
        ],
        "Vulcanised rubber plates, sheets, strips and profiles": [
            "Plaques, feuilles, bandes et profilés en caoutchouc vulcanisé",
            "Placas, hojas, tiras y perfiles de caucho vulcanizado",
        ],
        "Conveyor or transmission belts of vulcanised rubber": [
            "Courroies transporteuses ou de transmission en caoutchouc vulcanisé",
            "Bandas transportadoras o de transmisión de caucho vulcanizado",
        ],
        "New pneumatic tyres": [
            "Pneus neufs",
            "Neumáticos nuevos",
        ],
        "Retreaded or used tyres; solid or cushion tyres": [
            "Pneus rechapés ou usagés; pneus pleins ou à bandage",
            "Neumáticos recauchutados o usados; macizos o de goma",
        ],
        "Inner tubes of rubber": [
            "Chambres à air en caoutchouc",
            "Cámaras de caucho",
        ],
        "Rubber apparel and clothing accessories": [
            "Vêtements et accessoires en caoutchouc",
            "Prendas y accesorios de vestir de caucho",
        ],
        "Articles of vulcanised rubber, n.e.s.": [
            "Ouvrages en caoutchouc vulcanisé, n.c.a.",
            "Artículos de caucho vulcanizado, n.e.p.",
        ],
        "Hard rubber and articles, n.e.s.": [
            "Caoutchouc dur et ouvrages, n.c.a.",
            "Ebonita y artículos, n.e.p.",
        ],
        "Soya beans": [
            "Graines de soja",
            "Soja en grano",
        ],
        "Soya bean flour and meal": [
            "Farine et tourteau de soja",
            "Harina y torta de soja",
        ],
        "Soya-bean oil and its fractions": [
            "Huile de soja et ses fractions",
            "Aceite de soja y sus fracciones",
        ],
    }

    for group in CommodityGroup.objects.all():
        if group.name in group_translations:
            group.name_variants = group_translations[group.name]
            group.save(update_fields=["name_variants"])

    for commodity in Commodity.objects.all():
        if commodity.name in commodity_translations:
            commodity.name_variants = commodity_translations[commodity.name]
            commodity.save(update_fields=["name_variants"])


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0025_commodity_name_variants"),
    ]

    operations = [
        migrations.RunPython(populate_name_variants),
    ]
