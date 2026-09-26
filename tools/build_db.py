#!/usr/bin/env python3
"""Build the Canadian VW_STL_DB.sqlite for Harman MIB2 High / MHI2Q units.

Starts from a MIB2 (1.10.x) RadioStationDB (see base.json) and adds everything in data/:
  regions.csv       -> CountryRegionData            (one row per region)
  region_names.csv  -> CountryRegionTranslationData (region name per GUI language)
  logos.csv + logos/ -> StationLogos                (rendered to 160x120 opaque PNG)
  stations.csv      -> Stations                     (include=1 rows; two rows each: ecc=region ECC and ecc=0)

Usage:
  python3 tools/build_db.py --out dist/mod/RSDB/VW_STL_DB.sqlite [--base BASE.sqlite] [--version v0.2.0]
                            [--preview dist/logo-preview.png] [--logo-dir dist/logos]

Without --base the base database is downloaded from base.json (and cached in .cache/base).
Running it again on an output file is safe: all rows for the regions in regions.csv are replaced.
"""
import argparse
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from rsdb_data import LOGO_DIR, ROOT, load, station_ids

LOGO_SIZE = (160, 120)   # every logo in the 1.10.x (MIB2) database is 160x120
MARGIN = 8
CACHE = ROOT / ".cache" / "base"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_base() -> Path:
    cfg = json.loads((ROOT / "base.json").read_text())
    db = CACHE / "VW_STL_DB.base.sqlite"
    if db.is_file() and sha256(db) == cfg["sqlite_sha256"]:
        return db
    CACHE.mkdir(parents=True, exist_ok=True)
    zpath = CACHE / "base.zip"
    if not (zpath.is_file() and sha256(zpath) == cfg["zip_sha256"]):
        print(f"downloading base database: {cfg['url']}")
        urllib.request.urlretrieve(cfg["url"], zpath)
        if sha256(zpath) != cfg["zip_sha256"]:
            sys.exit("base zip checksum mismatch - check base.json")
    with zipfile.ZipFile(zpath) as z, z.open(cfg["member"]) as src, open(db, "wb") as dst:
        shutil.copyfileobj(src, dst)
    if sha256(db) != cfg["sqlite_sha256"]:
        sys.exit("base sqlite checksum mismatch - check base.json")
    return db


def render_logo(path: Path, bg_hex: str) -> Image.Image:
    bg = tuple(int(bg_hex[i:i + 2], 16) for i in (0, 2, 4))
    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    w, h = LOGO_SIZE
    s = min((w - 2 * MARGIN) / im.width, (h - 2 * MARGIN) / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    tile = Image.new("RGBA", LOGO_SIZE, bg + (255,))
    tile.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return tile.convert("RGB")


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def build(base: Path, out: Path, version: str, preview: Path | None, logo_dir: Path | None) -> None:
    data = load()
    if data.errors:
        sys.exit("data has errors - run tools/validate.py")

    out.parent.mkdir(parents=True, exist_ok=True)
    if base.resolve() != out.resolve():
        shutil.copyfile(base, out)
    con = sqlite3.connect(out)
    cur = con.cursor()
    region_by_key = {r["region"]: r for r in data.regions}

    # remove anything from a previous build of these regions
    for r in data.regions:
        cid = int(r["country_id"])
        lo, hi = station_ids(cid, 1)[0], station_ids(cid, 4999)[1]
        cur.execute("DELETE FROM Stations WHERE country=? OR stationId BETWEEN ? AND ?", (cid, lo, hi))
        cur.execute("DELETE FROM CountryRegionData WHERE countryId=?", (cid,))
        cur.execute("DELETE FROM CountryRegionTranslationData WHERE countryId=?", (cid,))
        if cur.execute("SELECT count(*) FROM Stations WHERE stationId BETWEEN ? AND ?", (lo, hi)).fetchone()[0]:
            sys.exit(f"stationId range {lo}-{hi} clashes with the base database")
    logo_ids = [int(l["logo_id"]) for l in data.logos]
    marks = ",".join("?" * len(logo_ids))
    clash = cur.execute(f"SELECT count(*) FROM Stations WHERE logoId IN ({marks})", logo_ids).fetchone()[0]
    if clash:
        sys.exit(f"{clash} base stations already use logo ids from logos.csv - pick unused logo_id values")
    cur.execute(f"DELETE FROM StationLogos WHERE logoId IN ({','.join('?' * len(logo_ids))})", logo_ids)

    # regions
    ncols = len(cur.execute("PRAGMA table_info(CountryRegionData)").fetchall())
    for r in data.regions:
        cid = int(r["country_id"])
        prefixes = {int(p, 16) for p in r["pi_prefixes"].split()}
        neighbor = [cid if i in prefixes else 0 for i in range(16)]
        row = [-1, "-1", cid, int(r["macro_region_id"]), r["name"], r["name"], r["name"], -1, -1, *neighbor,
               "0", "0", "-1", "-1", "-1",                 # gpsMode, gpsp1-4 (as in every existing row)
               -1, -1, -1, -1, -1, -1,                     # flagId, am/fm/dab/speechSupport, nurGenehmigteLogos
               int(r["request_strategy"]), int(r["use_database_name_in_hmi"]), r["native_language"],
               "-1", "-1", "-1", "-1", "-1", 1, -1, -1, -1, -1]
        assert len(row) == ncols, (len(row), ncols)
        cur.execute(f"INSERT INTO CountryRegionData VALUES ({','.join('?' * ncols)})", row)

    names = {(n["region"], n["gui_language"]): n["name"] for n in data.region_names}
    langs = cur.execute("SELECT DISTINCT guiLanguageId, guiLanguage FROM CountryRegionTranslationData "
                        "WHERE countryId NOT IN (%s)" % ",".join(r["country_id"] for r in data.regions)).fetchall()
    for r in data.regions:
        for lang_id, lang in langs:
            name = names.get((r["region"], lang), r["name"])
            before = cur.execute(
                """SELECT count(*) FROM CountryRegionTranslationData t JOIN CountryRegionData c ON c.countryId=t.countryId
                   WHERE t.guiLanguage=? AND c.macroRegionId=? AND c.countryId NOT IN (1,69,?)
                   AND t.countryRegionTranslation < ?""",
                (lang, int(r["macro_region_id"]), int(r["country_id"]), name)).fetchone()[0]
            cur.execute("INSERT INTO CountryRegionTranslationData VALUES (?,?,?,?,?)",
                        (int(r["country_id"]), lang_id, lang, name, before + 1))

    # logos
    stations = [s for s in data.stations if s["include"] == "1"]
    used = {s["logo"] for s in stations}
    tiles = {}
    for l in data.logos:
        if l["file"] not in used:
            continue
        tile = render_logo(LOGO_DIR / l["file"], l["background"])
        tiles[l["file"]] = (int(l["logo_id"]), tile)
        cur.execute("INSERT INTO StationLogos (logoId, country, isOnPreset, fileName, stationLogo) VALUES (?,?,?,?,?)",
                    (int(l["logo_id"]), -1, None, "-1", png_bytes(tile)))
        if logo_dir:
            logo_dir.mkdir(parents=True, exist_ok=True)
            tile.save(logo_dir / l["file"], "PNG", optimize=True)

    # stations
    for s in stations:
        reg = region_by_key[s["region"]]
        cid = int(reg["country_id"])
        for station_id, ecc in zip(station_ids(cid, int(s["id"])), (int(reg["ecc"], 16), 0)):
            cur.execute(
                """INSERT INTO Stations (stationId, country, ecc, piSid, linkedPi, ensembleId, scidi, subChannelId,
                   frequency, longName, shortName, type, logoId, regionalScope, networkStatus, gpsPosition, power,
                   height, radiationMode, descriptor, textToSpeech, asr, language)
                   VALUES (?,?,?,?,-1,-1,-1,-1,?,?,?,'FM',?,NULL,NULL,NULL,NULL,NULL,NULL,?,?,'',?)""",
                (station_id, cid, ecc, int(s["pi"], 16), s["frequency_khz"], s["name"], s["name"],
                 tiles[s["logo"]][0], f"{s['region']} {s['market']} {s['callsign']}; PI {s['pi_status']} ({s['source']})",
                 s["name"], s["language"]))

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cur.execute("UPDATE DatabaseVersion SET creationDate=?", (f"{stamp} CA {version}".strip(),))
    con.commit()
    if cur.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        sys.exit("integrity check failed")
    dangling = cur.execute("SELECT count(*) FROM Stations s WHERE s.logoId BETWEEN 1 AND 2147483647 AND NOT EXISTS "
                           "(SELECT 1 FROM StationLogos l WHERE l.logoId=s.logoId) AND s.country IN (%s)"
                           % ",".join(r["country_id"] for r in data.regions)).fetchone()[0]
    if dangling:
        sys.exit(f"{dangling} new stations point at a missing logo")
    con.execute("VACUUM")
    con.close()

    if preview:
        by_logo = {}
        for s in stations:
            by_logo.setdefault(s["logo"], []).append(f"{s['frequency_mhz']} {s['pi']}")
        items = sorted(tiles.items(), key=lambda kv: kv[1][0])
        cols, cw, ch = 5, 176, 150
        sheet = Image.new("RGB", (cols * cw, ((len(items) + cols - 1) // cols) * ch), (48, 48, 48))
        draw = ImageDraw.Draw(sheet)
        for i, (fname, (lid, tile)) in enumerate(items):
            x, y = (i % cols) * cw + 8, (i // cols) * ch + 6
            sheet.paste(tile, (x, y))
            draw.text((x, y + 123), ", ".join(by_logo[fname])[:28], fill=(235, 235, 235))
        preview.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(preview)

    print(f"built {out} ({out.stat().st_size / 1e6:.1f} MB, sha256 {sha256(out)})")
    print(f"  {len(data.regions)} region(s), {len(stations)} stations ({2 * len(stations)} rows), {len(tiles)} logos")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--base", type=Path, help="base VW_STL_DB.sqlite (default: download from base.json)")
    ap.add_argument("--version", default="dev")
    ap.add_argument("--preview", type=Path, help="write a PNG contact sheet of the logos")
    ap.add_argument("--logo-dir", type=Path, help="also write the rendered 160x120 logos here")
    a = ap.parse_args()
    build(a.base or fetch_base(), a.out, a.version, a.preview, a.logo_dir)


if __name__ == "__main__":
    main()
