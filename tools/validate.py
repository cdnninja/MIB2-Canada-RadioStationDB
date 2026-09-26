#!/usr/bin/env python3
"""Check the data tables in data/ before building. Exits non-zero if anything is wrong.

Also checks that every logo image opens and is large enough to look good at 160x120.
Usage: python3 tools/validate.py
"""
import sys
from collections import Counter

from PIL import Image

from rsdb_data import LOGO_DIR, load


def main() -> int:
    d = load()
    for row in d.logos:
        path = LOGO_DIR / row["file"]
        if not path.is_file():
            continue
        try:
            with Image.open(path) as im:
                im.load()
                if im.width < 120 and im.height < 90:
                    d.warnings.append(f"{row['_where']}: {row['file']} is only {im.width}x{im.height} - it will look blurry")
        except Exception as exc:  # noqa: BLE001
            d.errors.append(f"{row['_where']}: {row['file']} is not a readable image ({exc})")

    included = [s for s in d.stations if s["include"] == "1"]
    by_market = Counter(s["market"] for s in included)
    print(f"regions: {len(d.regions)}  translations: {len(d.region_names)}  logos: {len(d.logos)}  "
          f"stations: {len(d.stations)} ({len(included)} included)")
    for market, n in sorted(by_market.items()):
        print(f"  {market}: {n} stations")
    for msg in d.warnings:
        print(f"warning: {msg}")
    for msg in d.errors:
        print(f"ERROR: {msg}")
    if d.errors:
        print(f"\n{len(d.errors)} error(s) - fix them before building.")
        return 1
    print("\ndata OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
