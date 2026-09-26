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
cp dist/logo-preview.png dist/package/logo-preview.png
python tools/release_notes.py --version "$VERSION" --stations-csv dist/package/STATIONS.csv > dist/RELEASE_NOTES.md
(cd dist/package && sha256sum mod/RSDB/VW_STL_DB.sqlite > SHA256SUMS.txt)
(cd dist/package && zip -r -q "../MIB2-Canada-RSDB-${VERSION}.zip" .)
ls -la dist
