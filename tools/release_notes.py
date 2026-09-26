#!/usr/bin/env python3
"""Print Markdown release notes for a build, and optionally write the included-stations CSV for the package."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from rsdb_data import ROOT, load


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--db", type=Path, default=ROOT / "dist/package/mod/RSDB/VW_STL_DB.sqlite")
    ap.add_argument("--stations-csv", type=Path, help="write the included stations here")
    a = ap.parse_args()

    d = load()
    stations = [s for s in d.stations if s["include"] == "1"]
    stations.sort(key=lambda s: (s["market"], s["frequency_khz"]))
    base = json.loads((ROOT / "base.json").read_text())
    digest = hashlib.sha256(a.db.read_bytes()).hexdigest() if a.db.is_file() else "n/a"

    if a.stations_csv:
        cols = ["market", "frequency_mhz", "callsign", "name", "pi", "pi_status"]
        with open(a.stations_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            for s in stations:
                w.writerow([s[c] for c in cols])

    markets = sorted({s["market"] for s in stations})
    print(f"## Canada RSDB {a.version}\n")
    print(f"{len(stations)} FM stations ({', '.join(markets)}) added to the MIB2 base database "
          f"({base['name']}).\n")
    print("Unzip, copy the `mod` folder to the root of your M.I.B. SD card and follow `INSTALL.txt`.\n")
    print(f"`VW_STL_DB.sqlite` sha256: `{digest}`\n")
    print("| Market | MHz | Call sign | Name | PI |")
    print("|---|---|---|---|---|")
    for s in stations:
        flag = " (guess)" if s["pi_status"] == "guess" else ""
        print(f"| {s['market']} | {s['frequency_mhz']} | {s['callsign']} | {s['name']} | {s['pi']}{flag} |")


if __name__ == "__main__":
    main()
