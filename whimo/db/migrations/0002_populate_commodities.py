from dataclasses import dataclass, asdict

from django.db import migrations


@dataclass
class CommodityDTO:
    code: str
    unit: str
    name: str
    name_variants: list[str]


@dataclass
class CommodityGroupDTO:
    name: str
    name_variants: list[str]
    commodities: list[CommodityDTO]


groups = [
    CommodityGroupDTO(
        name="Cattle",
        name_variants=[
            "Bovin",
            "Ganado bovino",
        ],
        commodities=[
            CommodityDTO(
                code="010221",
                unit="head",
                name="Pure-bred cattle for breeding",
                name_variants=[
                    "Bovins de race pure pour l'élevage",
                    "Ganado bovino de raza pura para cría",
                ],
            ),
            CommodityDTO(
                code="010229",
                unit="head",
                name="Live cattle",
                name_variants=[
                    "Bovins vivants",
                    "Ganado bovino vivo",
                ],
            ),
            CommodityDTO(
                code="0201",
                unit="kg",
                name="Meat of bovine animals, fresh or chilled",
                name_variants=[
                    "Viande de bovins",
                    "Carne de bovino",
                ],
            ),
            CommodityDTO(
                code="0202",
                unit="kg",
                name="Meat of bovine animals, frozen",
                name_variants=[
                    "Viande de bovins",
                    "Carne de bovino",
                ],
            ),
            CommodityDTO(
                code="020610",
                unit="kg",
                name="Fresh or chilled edible offal of bovine animals",
                name_variants=[
                    "Abats comestibles de bovins",
                    "Despojos comestibles de bovino",
                ],
            ),
            CommodityDTO(
                code="020622",
                unit="kg",
                name="Frozen edible bovine livers",
                name_variants=[
                    "Foies de bovins comestibles",
                    "Hígados de bovino comestibles",
                ],
            ),
            CommodityDTO(
                code="020629",
                unit="kg",
                name="Frozen edible bovine offal",
                name_variants=[
                    "Abats comestibles de bovins",
                    "Despojos comestibles de bovino",
                ],
            ),
            CommodityDTO(
                code="160250",
                unit="kg",
                name="Prepared or preserved meat or offal of bovine animals",
                name_variants=[
                    "Viandes ou abats de bovins préparés ou conservés",
                    "Carne o despojos de bovino preparados o conservados",
                ],
            ),
            CommodityDTO(
                code="4101",
                unit="m2",
                name="Raw hides and skins of bovine or equine animals",
                name_variants=[
                    "Peaux brutes de bovins ou d'équidés",
                    "Pieles y cueros en bruto de bovino o equino",
                ],
            ),
            CommodityDTO(
                code="4104",
                unit="m2",
                name="Tanned or crust hides and skins of bovine or equine animals",
                name_variants=[
                    "Peaux de bovins ou d'équidés, tannées ou en crust",
                    "Pieles y cueros curtidos o en crust de bovino o equino",
                ],
            ),
            CommodityDTO(
                code="4107",
                unit="m2",
                name="Leather further prepared after tanning or crusting, of bovine",
                name_variants=[
                    "Cuir de bovin, ouvré après tannage ou crust",
                    "Cuero de bovino trabajado tras el curtido o crust",
                ],
            ),
        ],
    ),
    CommodityGroupDTO(
        name="Cocoa",
        name_variants=[
            "Cacao",
            "Cacao",
        ],
        commodities=[
            CommodityDTO(
                code="1801",
                unit="kg",
                name="Cocoa beans",
                name_variants=[
                    "Fèves de cacao",
                    "Granos de cacao",
                ],
            ),
            CommodityDTO(
                code="1802",
                unit="kg",
                name="Cocoa shells and other cocoa waste",
                name_variants=[
                    "Coques et autres déchets de cacao",
                    "Cáscaras y otros residuos de cacao",
                ],
            ),
            CommodityDTO(
                code="1803",
                unit="kg",
                name="Cocoa paste",
                name_variants=[
                    "Pâte de cacao",
                    "Pasta de cacao",
                ],
            ),
            CommodityDTO(
                code="1804",
                unit="kg",
                name="Cocoa butter, fat and oil",
                name_variants=[
                    "Beurre, graisse et huile de cacao",
                    "Manteca, grasa y aceite de cacao",
                ],
            ),
            CommodityDTO(
                code="1805",
                unit="kg",
                name="Cocoa powder",
                name_variants=[
                    "Cacao en poudre",
                    "Cacao en polvo",
                ],
            ),
            CommodityDTO(
                code="1806",
                unit="kg",
                name="Chocolate and other preparations containing cocoa",
                name_variants=[
                    "Chocolat et autres préparations contenant du cacao",
                    "Chocolate y demás preparaciones con cacao",
                ],
            ),
        ],
    ),
    CommodityGroupDTO(
        name="Coffee",
        name_variants=[
            "Café",
            "Café",
        ],
        commodities=[
            CommodityDTO(
                code="0901",
                unit="kg",
                name="Coffee, whether or not roasted or decaffeinated; coffee husks and skins; coffee substitutes",
                name_variants=[
                    "Café, torréfié ou non, décaféiné ou non; coques et pellicules de café; succédanés du café",
                    "Café, tostado o no, descafeinado o no; cáscaras y cascarillas de café; sucedáneos del café",
                ],
            )
        ],
    ),
    CommodityGroupDTO(
        name="Palm Oil",
        name_variants=[
            "Huile de palme",
            "Aceite de palma",
        ],
        commodities=[
            CommodityDTO(
                code="120710",
                unit="kg",
                name="Palm nuts and kernels",
                name_variants=[
                    "Noix et amandes de palme",
                    "Nueces y almendras de palma",
                ],
            ),
            CommodityDTO(
                code="1511",
                unit="kg",
                name="Palm oil and its fractions",
                name_variants=[
                    "Huile de palme et ses fractions",
                    "Aceite de palma y sus fracciones",
                ],
            ),
            CommodityDTO(
                code="151321",
                unit="kg",
                name="Crude palm kernel and babassu oil",
                name_variants=[
                    "Huile brute de palmiste et de babassu",
                    "Aceite crudo de palmiste y babasú",
                ],
            ),
            CommodityDTO(
                code="151329",
                unit="kg",
                name="Palm kernel and babassu oil and their fractions",
                name_variants=[
                    "Huile de palmiste et de babassu et leurs fractions",
                    "Aceite de palmiste y babasú y sus fracciones",
                ],
            ),
            CommodityDTO(
                code="230660",
                unit="kg",
                name="Oilcake and other solid residues",
                name_variants=[
                    "Tourteaux et autres résidus solides",
                    "Tortas y demás residuos sólidos",
                ],
            ),
            CommodityDTO(
                code="290545",
                unit="kg",
                name="Glycerol",
                name_variants=[
                    "Glycérol",
                    "Glicerol",
                ],
            ),
            CommodityDTO(
                code="291570",
                unit="kg",
                name="Palmitic acid, stearic acid, their salts and esters",
                name_variants=[
                    "Acide palmitique, acide stéarique, leurs sels et esters",
                    "Ácido palmítico, ácido esteárico, sus sales y ésteres",
                ],
            ),
            CommodityDTO(
                code="291590",
                unit="kg",
                name="Saturated acyclic monocarboxylic acids",
                name_variants=[
                    "Acides monocarboxyliques acycliques saturés",
                    "Ácidos monocarboxílicos acíclicos saturados",
                ],
            ),
            CommodityDTO(
                code="382311",
                unit="kg",
                name="Stearic acid",
                name_variants=[
                    "Acide stéarique",
                    "Ácido esteárico",
                ],
            ),
            CommodityDTO(
                code="382312",
                unit="kg",
                name="Oleic acid",
                name_variants=[
                    "Acide oléique",
                    "Ácido oleico",
                ],
            ),
            CommodityDTO(
                code="382319",
                unit="kg",
                name="Fatty acids, industrial, monocarboxylic",
                name_variants=[
                    "Acides gras industriels monocarboxyliques",
                    "Ácidos grasos industriales monocarboxílicos",
                ],
            ),
            CommodityDTO(
                code="382370",
                unit="kg",
                name="Fatty alcohols",
                name_variants=[
                    "Alcools gras",
                    "Alcoholes grasos",
                ],
            ),
        ],
    ),
    CommodityGroupDTO(
        name="Rubber",
        name_variants=[
            "Caoutchouc",
            "Caucho",
        ],
        commodities=[
            CommodityDTO(
                code="4001",
                unit="kg",
                name="Natural rubber and similar natural gums",
                name_variants=[
                    "Caoutchouc naturel et gommes naturelles similaires",
                    "Caucho natural y gomas naturales similares",
                ],
            ),
            CommodityDTO(
                code="4005",
                unit="kg",
                name="Compounded rubber, unvulcanised",
                name_variants=[
                    "Caoutchouc composé, non vulcanisé",
                    "Caucho compuesto, sin vulcanizar",
                ],
            ),
            CommodityDTO(
                code="4006",
                unit="kg",
                name="Unvulcanised rubber forms",
                name_variants=[
                    "Formes de caoutchouc non vulcanisé",
                    "Formas de caucho sin vulcanizar",
                ],
            ),
            CommodityDTO(
                code="4007",
                unit="m",
                name="Vulcanised rubber thread and cord",
                name_variants=[
                    "Fil et corde en caoutchouc vulcanisé",
                    "Hilo y cordón de caucho vulcanizado",
                ],
            ),
            CommodityDTO(
                code="4008",
                unit="m2",
                name="Vulcanised rubber plates, sheets, strips and profiles",
                name_variants=[
                    "Plaques, feuilles, bandes et profilés en caoutchouc vulcanisé",
                    "Placas, hojas, tiras y perfiles de caucho vulcanizado",
                ],
            ),
            CommodityDTO(
                code="4010",
                unit="m",
                name="Conveyor or transmission belts of vulcanised rubber",
                name_variants=[
                    "Courroies transporteuses ou de transmission en caoutchouc vulcanisé",
                    "Bandas transportadoras o de transmisión de caucho vulcanizado",
                ],
            ),
            CommodityDTO(
                code="4011",
                unit="pcs",
                name="New pneumatic tyres",
                name_variants=[
                    "Pneus neufs",
                    "Neumáticos nuevos",
                ],
            ),
            CommodityDTO(
                code="4012",
                unit="pcs",
                name="Retreaded or used tyres; solid or cushion tyres",
                name_variants=[
                    "Pneus rechapés ou usagés; pneus pleins ou à bandage",
                    "Neumáticos recauchutados o usados; macizos o de goma",
                ],
            ),
            CommodityDTO(
                code="4013",
                unit="pcs",
                name="Inner tubes of rubber",
                name_variants=[
                    "Chambres à air en caoutchouc",
                    "Cámaras de caucho",
                ],
            ),
            CommodityDTO(
                code="4015",
                unit="pcs",
                name="Rubber apparel and clothing accessories",
                name_variants=[
                    "Vêtements et accessoires en caoutchouc",
                    "Prendas y accesorios de vestir de caucho",
                ],
            ),
            CommodityDTO(
                code="4016",
                unit="kg",
                name="Articles of vulcanised rubber, n.e.s.",
                name_variants=[
                    "Ouvrages en caoutchouc vulcanisé, n.c.a.",
                    "Artículos de caucho vulcanizado, n.e.p.",
                ],
            ),
            CommodityDTO(
                code="4017",
                unit="kg",
                name="Hard rubber and articles, n.e.s.",
                name_variants=[
                    "Caoutchouc dur et ouvrages, n.c.a.",
                    "Ebonita y artículos, n.e.p.",
                ],
            ),
        ],
    ),
    CommodityGroupDTO(
        name="Soy",
        name_variants=[
            "Soja",
            "Soja",
        ],
        commodities=[
            CommodityDTO(
                code="1201",
                unit="kg",
                name="Soya beans",
                name_variants=[
                    "Graines de soja",
                    "Soja en grano",
                ],
            ),
            CommodityDTO(
                code="120810",
                unit="kg",
                name="Soya bean flour and meal",
                name_variants=[
                    "Farine et tourteau de soja",
                    "Harina y torta de soja",
                ],
            ),
            CommodityDTO(
                code="1507",
                unit="kg",
                name="Soya-bean oil and its fractions",
                name_variants=[
                    "Huile de soja et ses fractions",
                    "Aceite de soja y sus fracciones",
                ],
            ),
            CommodityDTO(
                code="2304",
                unit="kg",
                name="Oilcake and other solid residues",
                name_variants=[
                    "Tourteaux et autres résidus solides",
                    "Tortas y demás residuos sólidos",
                ],
            ),
        ],
    ),
]


def populate_commodities(apps, schema_editor):
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    Commodity = apps.get_model("db", "Commodity")

    for group_dto in groups:
        group, _ = CommodityGroup.objects.get_or_create(
            name=group_dto.name,
            name_variants=group_dto.name_variants,
        )

        for commodity_dto in group_dto.commodities:
            defaults = asdict(commodity_dto)
            defaults["group"] = group
            name = defaults.pop("name")

            Commodity.objects.get_or_create(name=name, defaults=defaults)


def remove_commodities(apps, schema_editor):
    CommodityGroup = apps.get_model("db", "CommodityGroup")

    for group_dto in groups:
        group, _ = CommodityGroup.objects.delete(name=group_dto.name)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0001_create_models"),
    ]

    operations = [
        migrations.RunPython(
            code=populate_commodities,
            reverse_code=remove_commodities,
        ),
    ]
