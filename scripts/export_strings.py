#!/usr/bin/env python3
"""Build the translation catalogue (whimo/languages/catalog/<code>.json) from the app sources.

Each catalogue file holds every string of one language, one section per platform:

    {"web": {"<namespace>": {"<key>": "..."}}, "android": {...}, "ios": {...}, "api": {...}}

The English file is the template administrators download to add a language, and the list of
keys an uploaded file may contain. Run it again whenever an app adds or renames strings:

    python scripts/export_strings.py \
        --web ../whimo/public/locales \
        --android ../whimo-android/app/src/main/res [--android ../whimo-android/app/src/<flavor>/res] \
        --ios ../whimo-ios/Packages/Resources/Sources/Resources/Localization

The `api` section is read from this repository's locale/ directory. A platform whose source is
not given keeps the section already in the catalogue.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "whimo" / "languages" / "catalog"
LOCALE_DIR = ROOT / "locale"


def base_code(name: str) -> str:
    return re.split(r"[-_]", name)[0].lower()


# Web: public/locales/<code>/<namespace>.json
# ______________________________________________________________________________________________________________________


def read_web(root: Path) -> dict[str, dict]:
    languages: dict[str, dict] = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        languages[base_code(folder.name)] = {
            file.stem: json.loads(file.read_text(encoding="utf-8")) for file in sorted(folder.glob("*.json"))
        }
    return languages


# Android: res/values[-<code>]/strings.xml
# ______________________________________________________________________________________________________________________

ANDROID_ESCAPES = {"n": "\n", "t": "\t", "'": "'", '"': '"', "@": "@", "?": "?", "\\": "\\"}


def android_unescape(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return re.sub(r"\\(.)", lambda m: ANDROID_ESCAPES.get(m.group(1), m.group(1)), text)


def read_android_file(path: Path) -> dict[str, str]:
    strings: dict[str, str] = {}
    for element in ET.parse(path).getroot().iter("string"):
        if element.get("translatable") == "false":
            continue
        strings[element.attrib["name"]] = android_unescape("".join(element.itertext()))
    return strings


def read_android(roots: list[Path]) -> dict[str, dict]:
    # Later roots (a product flavor) override earlier ones (main), as in the Gradle build.
    languages: dict[str, dict] = {}
    for root in roots:
        for folder in sorted(root.glob("values*")):
            strings = folder / "strings.xml"
            if not strings.exists():
                continue
            suffix = folder.name.removeprefix("values").lstrip("-")
            if suffix and not re.fullmatch(r"[a-z]{2,3}(-r[A-Z]{2})?", suffix):
                continue  # values-night, values-v31...
            code = base_code(suffix) if suffix else "en"
            languages.setdefault(code, {}).update(read_android_file(strings))
    return languages


# iOS: <code>.lproj/Localizable.strings
# ______________________________________________________________________________________________________________________

IOS_LINE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', re.MULTILINE)
IOS_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "r": "\r"}


def ios_unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda m: IOS_ESCAPES.get(m.group(1), m.group(1)), text)


def read_ios(root: Path) -> dict[str, dict]:
    languages: dict[str, dict] = {}
    for folder in sorted(root.glob("*.lproj")):
        source = (folder / "Localizable.strings").read_text(encoding="utf-8")
        languages[base_code(folder.stem)] = {
            ios_unescape(key): ios_unescape(value) for key, value in IOS_LINE.findall(source)
        }
    return languages


# API: locale/<code>/LC_MESSAGES/django.po
# ______________________________________________________________________________________________________________________


def po_string(lines: list[str]) -> str:
    return "".join(json.loads(line) for line in lines)


def read_po_file(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    msgid: list[str] = []
    msgstr: list[str] = []
    current: list[str] | None = None
    fuzzy = False

    def flush() -> None:
        nonlocal msgid, msgstr, fuzzy
        key = po_string(msgid)
        if key and not fuzzy:
            entries.append((key, po_string(msgstr)))
        msgid, msgstr, fuzzy = [], [], False

    for raw in [*path.read_text(encoding="utf-8").splitlines(), ""]:
        line = raw.strip()
        if not line:
            flush()
            current = None
        elif line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
        elif line.startswith("#"):
            continue
        elif line.startswith("msgid "):
            current = msgid
            current.append(line[6:])
        elif line.startswith("msgstr "):
            current = msgstr
            current.append(line[7:])
        elif line.startswith('"') and current is not None:
            current.append(line)
    return entries


def read_api(root: Path) -> dict[str, dict]:
    languages: dict[str, dict] = {}
    for po in sorted(root.glob("*/LC_MESSAGES/django.po")):
        code = base_code(po.parent.parent.name)
        entries = read_po_file(po)
        if code == "en":
            languages[code] = {key: value or key for key, value in entries}
        else:
            languages[code] = {key: value for key, value in entries if value}
    # Every message English knows about is a key, even when no .po lists it yet.
    return languages


# Main
# ______________________________________________________________________________________________________________________


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--web", type=Path, help="web app public/locales directory")
    parser.add_argument("--android", type=Path, action="append", help="Android res directory (repeat for a flavor)")
    parser.add_argument("--ios", type=Path, help="iOS Localization directory holding the .lproj folders")
    args = parser.parse_args()

    sections: dict[str, dict[str, dict]] = {"api": read_api(LOCALE_DIR)}
    if args.web:
        sections["web"] = read_web(args.web)
    if args.android:
        sections["android"] = read_android(args.android)
    if args.ios:
        sections["ios"] = read_ios(args.ios)

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    codes = {code for languages in sections.values() for code in languages}
    codes |= {path.stem for path in CATALOG_DIR.glob("*.json")}

    for code in sorted(codes):
        path = CATALOG_DIR / f"{code}.json"
        catalog = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for platform, languages in sections.items():
            if code in languages:
                catalog[platform] = languages[code]
        ordered = {platform: catalog[platform] for platform in ("web", "android", "ios", "api") if platform in catalog}
        path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        counts = ", ".join(f"{platform} {count_strings(ordered[platform])}" for platform in ordered)
        print(f"{path.relative_to(ROOT)}: {counts}")
    return 0


def count_strings(section: dict) -> int:
    return sum(count_strings(value) if isinstance(value, dict) else 1 for value in section.values())


if __name__ == "__main__":
    sys.exit(main())
