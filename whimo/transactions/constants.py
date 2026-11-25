LOCATION_S3_PREFIX = "locations"
CHAIN_TIER_FIELD = "_chain_tier"
LOCATION_FILE_SIGNATURES = (
    (b"\xd0\xcf\x11\xe0", ".xls"),
    (b"%PDF", ".pdf"),
    (b"\x89PNG", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"{", ".geojson"),
    (b"<?xml", ".kml"),
    (b"<kml", ".kml"),
)
