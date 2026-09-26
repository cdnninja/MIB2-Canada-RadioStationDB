#!/usr/bin/env python3
"""Make the slim base database in base/ from a full MIB2 (1.10.x) VW_STL_DB.sqlite.

Keeps the schema, DatabaseVersion, the VW region list (CountryRegionData + its menu translations),
the phoneme-set list and the default logo (logoId 100). Removes every station, every station logo
and every voice-control phoneme, plus regions that were not in VW's database (e.g. the community
"Australia" region, countryId 61). The Canadian data is then added by tools/build_db.py.

Usage: python3 tools/make_base.py FULL.sqlite base/VW_STL_DB.base.sqlite
"""
import shutil
import sqlite3
import sys
from pathlib import Path

KEEP_LOGOS = (100,)          # VW's generic radio icon, not referenced by any station
DROP_REGIONS = (61,)         # community-added regions that are not part of VW's database


def main(src: str, dst: str) -> None:
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    con = sqlite3.connect(dst)
    cur = con.cursor()
    cur.execute("DELETE FROM Stations")
    cur.execute("DELETE FROM SdsStationPhoneme")
    cur.execute(f"DELETE FROM StationLogos WHERE logoId NOT IN ({','.join('?' * len(KEEP_LOGOS))})", KEEP_LOGOS)
    marks = ",".join("?" * len(DROP_REGIONS))
    cur.execute(f"DELETE FROM CountryRegionData WHERE countryId IN ({marks})", DROP_REGIONS)
    cur.execute(f"DELETE FROM CountryRegionTranslationData WHERE countryId IN ({marks})", DROP_REGIONS)
    major, minor, rev = cur.execute("SELECT versionMajor, versionMinor, versionRevision FROM DatabaseVersion").fetchone()
    cur.execute("UPDATE DatabaseVersion SET creationDate=?", (f"base {major}.{minor}.{rev} no stations",))
    con.commit()
    con.execute("VACUUM")
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    con.close()
    print(f"wrote {dst} ({Path(dst).stat().st_size / 1024:.0f} KB): {counts}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
