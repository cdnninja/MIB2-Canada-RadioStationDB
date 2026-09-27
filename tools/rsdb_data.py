"""Load and validate the data tables in data/. Shared by build_db.py and validate.py."""
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGO_DIR = DATA / "logos"

STATION_COLUMNS = ["id", "include", "region", "market", "frequency_mhz", "callsign", "name", "pi", "pi_status",
                   "logo", "language", "source", "notes"]
LOGO_COLUMNS = ["logo_id", "file", "background", "source_url", "notes"]
REGION_COLUMNS = ["region", "country_id", "name", "macro_region_id", "ecc", "pi_prefixes", "native_language",
                  "request_strategy", "use_database_name_in_hmi"]
REGION_NAME_COLUMNS = ["region", "gui_language", "name"]

PI_STATUSES = {"verified", "logged", "guess"}


@dataclass
class Data:
    regions: list = field(default_factory=list)
    region_names: list = field(default_factory=list)
    stations: list = field(default_factory=list)
    logos: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _read(name, columns, errors):
    path = DATA / name
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            errors.append(f"{name}: header must be exactly {','.join(columns)} (got {','.join(reader.fieldnames or [])})")
            return []
        rows = []
        for line, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                errors.append(f"{name}:{line}: wrong number of columns")
                continue
            row = {k: v.strip() for k, v in row.items()}
            row["_where"] = f"{name}:{line}"
            rows.append(row)
        return rows


def station_id(country_id: int, row_id: int) -> int:
    """Stations.stationId for a stations.csv row. Keeps ids stable across builds.

    Exactly one Stations row per station: the head unit looks FM stations up by PI (+ country), never by ECC,
    so a second row with a different ecc is an exact duplicate match and the unit then shows no logo at all.
    """
    return country_id * 10_000 + row_id  # Canada (124) -> 1_240_001 ... 1_249_999


def load() -> Data:
    d = Data()
    e, w = d.errors, d.warnings
    d.regions = _read("regions.csv", REGION_COLUMNS, e)
    d.region_names = _read("region_names.csv", REGION_NAME_COLUMNS, e)
    d.stations = _read("stations.csv", STATION_COLUMNS, e)
    d.logos = _read("logos.csv", LOGO_COLUMNS, e)
    if e:
        return d

    # regions
    region_keys = set()
    for r in d.regions:
        where = r["_where"]
        if r["region"] in region_keys:
            e.append(f"{where}: duplicate region {r['region']}")
        region_keys.add(r["region"])
        for col in ("country_id", "macro_region_id", "request_strategy", "use_database_name_in_hmi"):
            if not r[col].isdigit():
                e.append(f"{where}: {col} must be a number")
        if not re.fullmatch(r"[0-9A-F]{2}", r["ecc"]):
            e.append(f"{where}: ecc must be 2 hex digits (e.g. A1)")
        for p in r["pi_prefixes"].split():
            if not re.fullmatch(r"[0-9A-F]", p):
                e.append(f"{where}: pi_prefixes must be single hex digits separated by spaces")
        if r["country_id"].isdigit() and int(r["country_id"]) in (1, 69):
            e.append(f"{where}: country_id 1 (AUTO) and 69 (Europe) are reserved")

    seen = set()
    for r in d.region_names:
        if r["region"] not in region_keys:
            e.append(f"{r['_where']}: unknown region {r['region']}")
        key = (r["region"], r["gui_language"])
        if key in seen:
            e.append(f"{r['_where']}: duplicate translation {key}")
        seen.add(key)
        if not r["name"]:
            e.append(f"{r['_where']}: name is empty")

    # logos
    logo_files, logo_ids = {}, set()
    for r in d.logos:
        where = r["_where"]
        if not r["logo_id"].isdigit():
            e.append(f"{where}: logo_id must be a number")
        elif r["logo_id"] in logo_ids:
            e.append(f"{where}: duplicate logo_id {r['logo_id']}")
        logo_ids.add(r["logo_id"])
        if r["file"] in logo_files:
            e.append(f"{where}: duplicate file {r['file']}")
        logo_files[r["file"]] = r
        if not (LOGO_DIR / r["file"]).is_file():
            e.append(f"{where}: data/logos/{r['file']} does not exist")
        if not re.fullmatch(r"[0-9A-Fa-f]{6}", r["background"]):
            e.append(f"{where}: background must be a 6-digit hex colour (e.g. FFFFFF)")
        if not r["source_url"]:
            w.append(f"{where}: no source_url for {r['file']}")
    for p in sorted(LOGO_DIR.glob("*")):
        if p.name not in logo_files and p.name != ".gitkeep":
            w.append(f"data/logos/{p.name} is not listed in logos.csv")

    # stations
    ids, keys, used_logos = set(), {}, set()
    for r in d.stations:
        where = r["_where"]
        if not r["id"].isdigit() or int(r["id"]) < 1 or int(r["id"]) > 4999:
            e.append(f"{where}: id must be a number 1-4999")
        elif r["id"] in ids:
            e.append(f"{where}: duplicate id {r['id']} (ids are permanent - use the next unused number)")
        ids.add(r["id"])
        if r["include"] not in ("0", "1"):
            e.append(f"{where}: include must be 0 or 1")
        if r["region"] not in region_keys:
            e.append(f"{where}: unknown region {r['region']}")
        try:
            mhz = float(r["frequency_mhz"])
            khz = round(mhz * 1000)
            if not (87500 <= khz <= 108000) or khz % 100:
                raise ValueError
            r["frequency_khz"] = khz
            if r["region"] == "CA" and (khz // 100) % 2 == 0:
                w.append(f"{where}: {r['frequency_mhz']} MHz is not a standard North American channel (odd tenths)")
        except ValueError:
            e.append(f"{where}: frequency_mhz must be an FM frequency like 92.1")
        if r["include"] != "1":
            continue
        if not re.fullmatch(r"[0-9A-F]{4}", r["pi"]):
            e.append(f"{where}: pi must be 4 upper-case hex digits (e.g. C95C)")
        elif r["pi"] in ("0000", "FFFF"):
            e.append(f"{where}: PI {r['pi']} is an encoder default, not a real station code - set include=0")
        if r["pi_status"] not in PI_STATUSES:
            e.append(f"{where}: pi_status must be one of {', '.join(sorted(PI_STATUSES))}")
        if not r["name"]:
            e.append(f"{where}: name is empty")
        if r["logo"] not in logo_files:
            e.append(f"{where}: logo {r['logo']!r} is not listed in logos.csv")
        used_logos.add(r["logo"])
        if not re.fullmatch(r"[a-z]{2}", r["language"]):
            e.append(f"{where}: language must be a 2-letter code (en, fr, ...)")
        key = (r["region"], r["pi"], r.get("frequency_khz"))
        if key in keys:
            e.append(f"{where}: same region, PI and frequency as {keys[key]}")
        keys[key] = where
    for f_ in logo_files:
        if f_ not in used_logos:
            w.append(f"logos.csv: {f_} is not used by any included station")
    return d
