# WHIMO Farm QR — Specification

v1.3 · 20 Aug 2026 · for QR generator developers

Each QR encodes **one GeoJSON object as plain UTF-8 text**, minified to a single
line. No wrapper, no compression, no Base64, no URL.

## Rules

1. **Top level** must be `Feature` or `FeatureCollection`. A bare geometry
   (`{"type":"Point","coordinates":[...]}`) is rejected.
2. **Geometry** must be `Point` or `Polygon` — both equally valid, a single point
   is a complete farm location. `LineString`, `MultiPoint`, `MultiPolygon`,
   `MultiLineString` and `GeometryCollection` are rejected and fail the whole scan.
   For several plots use a `FeatureCollection`, one `Feature` each (types may be mixed).
3. **`properties` is mandatory** on every feature. Send `{}` when empty — omitting
   it or sending `null` fails the scan.
4. **Coordinates are `[longitude, latitude]`** — longitude first. Round to 6 decimals
   (~11 cm). Optional third value = altitude in metres.
5. **Close polygon rings** — repeat the first position last, minimum 4 positions.
   Not enforced by the app, but an open ring renders wrong on the map.
6. **Keep the payload under 1200 bytes.** Simplify traced boundaries
   (Douglas–Peucker) before encoding. Quiet zone 4 modules. Error-correction
   level **M** normally; level **H** if a logo is overlaid in the centre, as the
   existing "Share location" codes do — at H the ceiling drops to 1273 bytes.

## Metadata

Custom fields go under `properties` and are **preserved, not discarded** — they
reappear in the supply-chain exports our customers download. Send only agreed
fields, no personal data.

- `TransactionId` — **do not send**, assigned by WHIMO and overwritten.
- `ProducerName`, `ProducerCountry`, `ProductionPlace` — reserved.
- Any other key is free. Keys are case-sensitive.
- Values are stored verbatim, whitespace included — trim them in the generator.
- Dates are **not parsed** by WHIMO — any string is stored and exported verbatim,
  so the current `"date":"20260710 19:05"` is accepted as is and needs no change.
  ISO 8601 UTC (`"2026-07-10T19:05:00Z"`) is worth considering when the field list
  is next revised, since the present format carries no timezone. Suggestion, not
  a requirement.

## Examples

Accepted — point with metadata (decoded from a live "Share location" QR, 210 bytes,
EC level H). A `Point` is a complete, valid farm location:

```json
{"type":"Feature","properties":{"name":"Kenema District ","survey":"EUDR Cocoa Farm Mapping (Kenema, Kailahun and Kono)","date":"20260131 18:03"},
 "geometry":{"type":"Point","coordinates":[-11.112771,7.970897]}}
```

Accepted — closed polygon (real generator output, 270 bytes):

```json
{"type":"Feature","properties":{"name":"somewhere_france","survey":"OLAM Colombia encuesta","date":"20260710 19:05"},
 "geometry":{"type":"Polygon","coordinates":[[[4.603431,45.691673],[4.604785,45.692369],
 [4.607276,45.689646],[4.605574,45.688917],[4.603431,45.691673]]]}}
```

Rejected — no `properties`, bare geometry, or unsupported geometry type:

```json
{"type":"Feature","geometry":{"type":"Point","coordinates":[35.102,-6.204]}}
{"type":"Point","coordinates":[35.102,-6.204]}
{"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":[[35.1,-6.2],[35.2,-6.3]]}}
```

## Checklist before printing a batch

- [ ] Top level is `Feature` / `FeatureCollection`, never a bare geometry
- [ ] `properties` present on every feature (`{}` if empty, never `null`)
- [ ] Every `geometry.type` is `Point` or `Polygon`
- [ ] Order is `[longitude, latitude]` — for mainland Tanzania longitude is
      **29.3…40.5**, latitude **−11.8…−0.9**. Negative or single-digit longitude
      means the pair is swapped.
- [ ] Coordinates rounded to 6 decimals
- [ ] Polygon rings closed, ≥ 4 positions
- [ ] JSON minified, UTF-8, no BOM, no trailing newline
- [ ] Payload < 1200 bytes
- [ ] Generated image decodes back to a byte-identical string
- [ ] `TransactionId` absent

Send us a few sample payloads before printing in volume — we will run them
through the same validator. A geometry type you need that is not listed above is
a small change on our side; reprinting cards is not.
