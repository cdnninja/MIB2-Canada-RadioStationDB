#!/usr/bin/env bash
# Validate the data, build VW_STL_DB.sqlite and package it into dist/MIB2-Canada-RSDB-<version>.zip
# Usage: tools/package.sh <version>
set -euo pipefail
VERSION="${1:?usage: tools/package.sh <version>}"
cd "$(dirname "$0")/.."
rm -rf dist
python tools/validate.py
python tools/build_db.py \
  --out dist/package/mod/RSDB/VW_STL_DB.sqlite \
  --version "$VERSION" \
  --preview dist/logo-preview.png \
  --logo-dir dist/logos
cp release/INSTALL.txt dist/package/INSTALL.txt
# HMI startup fix (MU1316 only): kept in its own folder so it is never copied to the card by accident
FIX=dist/package/hmi_startup_fix_MU1316_only
mkdir -p "$FIX"
cp -R hmi_startup_fix/sdcard "$FIX/sdcard"
cp hmi_startup_fix/Launcher-sda0.esd.snippet hmi_startup_fix/README.md "$FIX/"
cp dist/logo-preview.png dist/package/logo-preview.png
python tools/release_notes.py --version "$VERSION" --stations-csv dist/package/STATIONS.csv > dist/RELEASE_NOTES.md
(cd dist/package && sha256sum mod/RSDB/VW_STL_DB.sqlite $(find hmi_startup_fix_MU1316_only -type f | sort) > SHA256SUMS.txt)
(cd dist/package && zip -r -q "../MIB2-Canada-RSDB-${VERSION}.zip" .)
ls -la dist
