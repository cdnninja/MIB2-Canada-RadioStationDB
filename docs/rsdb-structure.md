# Radio station logo DB (RSDB) — structure reference

Analysed file: `VW_STL_DB.sqlite` from `MH2p_EU_RSDB_01.20.20_20200506` (210 MB, SQLite 3, UTF-8).
`DatabaseVersion` row: `1 | 20 | 20 | 2020-06-05 | Europe`.

Everything below was measured directly from the file unless marked **(inferred)** or **(forum reports)**.

---

## 1. Tables at a glance

| Table | Rows | Role | Needed for Canada? |
|---|---|---|---|
| `Stations` | 11,910 (9,524 FM, 2,386 DAB) | One row per station identity (PI / DAB service) → points at a logo | **Yes — core** |
| `StationLogos` | 7,207 | The PNG images (≈199 MB, 95% of the file) | **Yes — core** |
| `CountryRegionData` | 53 | Country/region list + PI-prefix → country map | **Yes** (Canada row, maybe USA) |
| `CountryRegionTranslationData` | 2,014 (53 × 38 GUI languages) | Names shown in the country/region menu | Yes, for any new region |
| `SdsStationPhoneme` | 54,425 (for 9,392 stations) | Voice-control pronunciations of station names | Optional (2,518 EU stations have none) |
| `SdsPhonemeSets` | 17 | Phoneme language list (includes en-US, fr-CA, es-MX) | Keep as is |
| `DatabaseVersion` | 1 | Version / date / region label | Yes (update date, maybe region) |

Indexes: `Stations(country)`, `Stations(ecc)`, `Stations(frequency)`, `Stations(piSid)`, `Stations(type)`, `SdsStationPhoneme(stationId)`.

Relationships:
- `Stations.country` → `CountryRegionData.countryId`
- `Stations.logoId` → `StationLogos.logoId` (many stations can share one logo; no dangling references)
- `SdsStationPhoneme.stationId` → `Stations.stationId`; `SdsStationPhoneme.phonemeSet` → `SdsPhonemeSets.phonemeSetsId`
- `CountryRegionTranslationData.countryId` → `CountryRegionData.countryId`
- `CountryRegionData.macroRegionId` → another `countryId` (69 = Europe; Russian cities point to 28 = Russia)

---

## 2. `Stations` — column reference

| Column | Meaning | Observed values | For a Canadian row |
|---|---|---|---|
| `stationId` | PK | Allocated in per-country blocks (DE 10xxx, CH 13xxx, AT 14xxx, DK 15xxx, FR 16–17xxx, BE 20xxx, IT 21–23xxx, UK 24–26xxx, ES 30–32xxx, RU cities 71–72xxx, NL 88xxx…) | New unused block, e.g. 90000+ |
| `country` | `CountryRegionData.countryId` | 2–55 | The Canada region id (see §5 — unknown for NAR software) |
| `ecc` | Extended Country Code, **decimal** | 224–228 (= 0xE0–0xE4); **0** = PI known, ECC unknown (1,156 FM rows); **-1** = no PI (always paired with `piSid = -1`) | 161 (= 0xA1, Canada) or 0 |
| `piSid` | FM: RDS PI code. DAB: Service ID. 16-bit, stored as decimal | 0–65535, or -1 = none | The PI the station **actually transmits** |
| `linkedPi` | — | always -1 | -1 |
| `ensembleId` | DAB ensemble ID (EId) | FM: -1; DAB: EId (231 DAB rows have -1) | -1 |
| `scidi`, `subChannelId` | — | always -1 | -1 |
| `frequency` | FM frequency in **kHz** | 73580–108000 (e.g. 102200 = 102.2 MHz); DAB = -1; 246 FM rows = -1 (PI-only match) | e.g. 103900 |
| `longName` | Only used for Russian stations (Latin transliteration, ≤ 8 chars) | '' for 11,404 rows | '' (or call sign) |
| `shortName` | 8-char name = RDS PS / DAB short label. Always filled. | 2–8 chars, no padding | Station's static PS / brand, ≤ 8 chars |
| `type` | Band | only `'FM'` and `'DAB'` | `'FM'` |
| `logoId` | FK → `StationLogos` | 10000–88361 | The logo id |
| `regionalScope`, `networkStatus`, `gpsPosition`, `power`, `height`, `radiationMode`, `descriptor` | Unused | always NULL | NULL |
| `textToSpeech`, `asr`, `language` | Unused | always '' | '' |

### How rows are keyed (evidence)
- **One row per distinct PI**, not per transmitter. A network with many local PIs gets many rows pointing at one logo: Cadena SER = 51 rows → logo 30085; NRK P1 regional services = 42 rows → logo 27033; NDR 1 MV = 6 FM PIs + 1 DAB SId → logo 10000. 2,048 logos are shared by more than one row.
- **PI is not unique on its own.** 837 `(country, type, piSid)` groups have multiple rows and 836 of them point at different logos. They differ by `frequency` (FM) or `ensembleId` (DAB) and `shortName`. Example: five Belgian stations all transmit PI 6000 (PANACH 101.8, BINGO 107.2, CENTRAAL 106.7, VAN WAAS 105.9, ZOE FM 104.9); junk PIs like 0000, 1234, FFFF appear the same way.
- **Stations with no usable PI** (1,186 FM rows in 39 countries) have `piSid = -1`, `ecc = -1`, and always a `frequency` + `shortName`. Where one frequency is reused (e.g. Spain, 87.5: "Vertical" and "Ponent"), the PS name is what separates them.
- **Russia** has no stations under the country itself (id 28). All Russian stations sit in five city sub-regions (51 Moscow, 52 Saint Petersburg, 53 Novosibirsk, 54 Yekaterinburg, 55 Nizhny Novgorod; `macroRegionId = 28`), and ~340 of them have no PI — frequency + name within a city. This is the template for a country where much of FM has no reliable RDS.

### Lookup model **(inferred from the data design — not confirmed on a car)**
1. Car determines the current country/region: menu choice (`AUTO` = id 1, or a named region) or automatically (navigation position and/or RDS ECC).
2. For a received FM station: take the PI's first hex digit, map it through that region's `countryNeighborPi0…F` to a `countryId`, then look up `Stations` by `(country, piSid)`; use `frequency` / `shortName` to break ties.
3. No PI (or PI unknown): look up by `frequency` (+ `shortName`) within the region.
4. DAB: `(country, piSid = SId, ensembleId)`.
5. Show `StationLogos.stationLogo` for the row's `logoId`.

---

## 3. `StationLogos`

| Column | Observed | Notes |
|---|---|---|
| `logoId` | PK, 100 and 10000–88361 | Same numbering blocks as `stationId` |
| `country` | always -1 | unused |
| `isOnPreset` | always NULL | unused |
| `fileName` | always '-1' | unused |
| `stationLogo` | PNG blob | see below |

Image format:
- **PNG only.** 4,183 at **320×240**, 3,024 at **160×120** (both 4:3). Mixed within the same country, so both sizes are accepted.
- 8-bit **RGBA** (7,205 of 7,207); artwork centred on a transparent 4:3 canvas.
- Size 2.2 KB – 193 KB, average 27.6 KB.
- `logoId 100` is a generic grey radio icon referenced by no station — likely the default/placeholder.

Recommendation for new logos: 320×240 RGBA PNG, logo centred with transparent padding, optimised (e.g. `pngquant`/`oxipng`) to keep the DB small.

---

## 4. `CountryRegionData`

53 rows: `1 = AUTO` (the "Automatic" menu entry), `69 = Europe` (macro region), countries 2–55 (ids 19, 29, 40 unused), and the five Russian cities 51–55.

| Column | Observed | Meaning |
|---|---|---|
| `countryId` | 1–55, 69 | Region id used by `Stations.country` |
| `macroRegionId` | 69 for everything except the Russian cities (28) | Parent region |
| `countryNameInternational` | English name (e.g. 'Germany', 'AUTO', 'Moscow') | Internal label |
| `countryNeighborPi0` … `countryNeighborPiF` | 16 countryIds | **"When I'm in this country, a PI starting with hex digit N belongs to country X."** Germany: 1→DE, 2→CZ, 3→PL, 4→CH, 5→IT, 6→BE, 7→LU, 8→NL, 9→DK, A→AT, B→HU, C→UK, D→DE, E→SE, F→FR. Matches the RDS country-code table. |
| `requestStrategy` | 2 everywhere; **5** for Russia and its cities | Lookup mode **(inferred)**: 5 appears only where stations are frequency-matched |
| `useDatabaseNameInHmi` | 15 everywhere | Unknown (possibly a bitmask for showing the DB name instead of the received PS) |
| `nativeLanguage` | '' except 'ru_RU' for Russia/cities | |
| `extraInt1` | 1 everywhere | Unknown |
| `crId`, `ioc`, `countryNameOriginal`, `iocCountryNameInternational`, `countryEcc`, `countryPi`, `gpsMode`, `gpsp1–4`, `flagId`, `amSupport`, `fmSupport`, `dabSupport`, `speechSupport`, `nurGenehmigteLogos` ("only approved logos"), `extraString1–5`, `extraInt2–5` | all -1 / '-1' / 0 | Unused in this build |

Because `ioc`/`countryEcc` are unused, the link between the car's idea of "Germany" and `countryId = 7` must be hard-coded in the head-unit software. **Which id the NAR software would use for Canada is unknown.**

`CountryRegionTranslationData`: `(countryId, guiLanguageId = -1, guiLanguage, countryRegionTranslation, guiListItemPosition)` — one row per region per GUI language (38 languages, including `en_US`, `fr_CA`, `es_MX`). `guiListItemPosition` is the menu order (AUTO and Europe = 1; countries alphabetical per language; cities ordered within Russia).

---

## 5. Building a Canadian version — what each table needs

**DatabaseVersion** — keep the version family that matches the head unit (**(forum reports)** 1.10.x = MIB2 / MHI2 / MHI2Q, 1.20.x = MIB2+ / MH2p, 1.30.x = MIB3); bump revision/date; `regionCode` value for NAR unknown.

**CountryRegionData** — a Canada row (and probably a USA row for border markets like Windsor, Vancouver, Niagara). Suggested PI-prefix map for Canada: `1–9, A, D, E → USA`, `C → Canada`, `B → Canada` (CBC network codes; B is shared with some US network codes), `0, F → 0`. Open question: the countryId values.

**Stations (FM)** — per station: `country`, `ecc = 161` (0xA1) or `0`, `piSid` = observed PI, `frequency` in kHz (Canadian FM is 88.1–107.9 on odd tenths → 88100…107900), `shortName` ≤ 8 chars, `type = 'FM'`, `logoId`. Network brands (CBC Radio One, CBC Music, ICI Première, ICI Musique, and commercial chains) → many rows, one logo.

**StationLogos** — 320×240 RGBA PNGs.

**CountryRegionTranslationData** — one row per new region × 38 languages.

**SdsStationPhoneme** — can be left empty for Canadian stations.

### Canada-specific data issues
- **PI codes.** ISED's scheme gives Canadian stations PIs in **C000–CFFF** derived from the call sign (ISED publishes a CBC-built calculator spreadsheet), with **B_0x** codes reserved for CBC networks. In practice many Canadian stations transmit a US-formula PI (call sign with C→W) or an encoder default. The DB must hold the PI each station **actually sends** — from DX logs (FMLIST, WTFDA) or by logging it yourself (RTL-SDR + RDS Spy/SDR#), not computed from the call sign.
- **No RDS / scrolling PS.** Stations without RDS need frequency matching; scrolling PS text defeats PS matching (PI still works). Canada reuses frequencies across cities, so country-wide frequency matching will mismatch — use metro sub-regions like Russia (Edmonton, Calgary, Toronto, Montréal, Vancouver…) or skip non-RDS stations.
- **AM and HD2/HD3** have no place in this schema as shipped (`type` is only FM/DAB; no HD subchannel field). AM support untested.

---

## 6. Getting it into the car **(forum reports — verify for your unit)**
- On MHI2 / MHI2Q the DB lives at `/net/mmx/mnt/boardbook/RSDB/VW_STL_DB.sqlite`.
- Official SD packages ship the DB renamed as `stl.1vw` (folder `Common`) plus `metainfo2.txt` (release name, vendor e.g. `MIB2_HIGH_Harman`, device release e.g. `011040`, SHA-1 checksums per 512 KB block, variant patterns like `FM2-*-*-EU-*-*`, region `Europe` / `RoW`). Modified packages need the checksums fixed or `skipMetaChecksum = "true"`; `metainfo3` signature errors are reported.
- The M.I.B. toolbox can import `VW_STL_DB.sqlite` (dropped into M.I.B.'s `mod/RSDB/` folder, exact filename required) on MHI2 / MHI2Q. M.I.B. runs only on MHIG / MHI2 / MHI2Q — **not** MH2p.
- Coding: `Station_Logo_DB_Mode = 1` in the infotainment unit (5F); RDS must be on.
- Reported results: editing logos of existing stations works; adding brand-new stations was hit-or-miss.

---

## 7. Open questions / suggested test order
1. Which head unit and firmware (e.g. `MHI2_US_…`, `MHI2Q_US_…`, `MH2p_US_…`)? Decides the DB version family and install route.
2. Does the NAR firmware expose station-logo DB support (coding channel present)?
3. Smallest possible test before building the whole country: add 2–3 Edmonton stations with known PIs + logos, install, check whether they show. Try both a new Canada region and a manual region selection.
4. Then build the full Canadian table from a station list (ISED/CRTC) + observed PIs + logos.

---

## 8. The target car: `MHI2Q_US_AUG22_P5087` (MU1316)

- Harman MIB2 High "Q" unit, US region, Audi A4/A5/Q5/Q7 family (per M.I.B. compatibility table, which lists `MHI2Q_US_AUG22_P5087_MU1316` as supported).
- EU twin `MHI2Q_ER_AUG22_P5092_MU1329` is reported to show RSDB logos when configured → the radio code is very likely present on the US build too.
- Official DB family for MHI2Q is 1.10.x (variant `FMQ`), but the 1.20.20 file (MIB Solution download) has been loaded onto an MHI2Q AUG22 unit via M.I.B. (discussion #62). Display not confirmed there.

### What M.I.B. actually does (from its source, v3.7.3)
- `esd/scripts/rsdb.sh` ("Copy RSDB to unit"): if `/net/mmx/mnt/boardbook/RSDB/VW_STL_DB.sqlite` exists it wipes `RSDB/*.*`; otherwise prints "No VW_STL_DB.sqlite found on unit — Check if FW is compatible with RSDB". Then copies `SD1:/mod/RSDB/VW_STL_DB.sqlite` → `/net/mmx/mnt/boardbook/RSDB/` (`cp -rc`, creates the folder). No validation of the file. Reboot to apply.
- Backup `-RSDB` copies `VW_STL_DB.sqlite` → `backup/…/RadioStationDB/data/0/default/stl.1vw` and `Update.txt` → `RadioStationDB/InfoFile/0/default/update.txt`. `Update.txt` holds `version.default=`; `allversions` prints "Radiodata DB: <name> <version>".
- **"RSDB region"** = persistence `0 / 3221356628` (0xC0020054; M.I.B.'s backup script labels this dataset `Vehicle_Configuration`, saved in `<MU>-datasets.csv`), byte 6 (bits 6.0–6.7). The value list is only what M.I.B. knows — a NAR value may exist undocumented; read byte 6 from your own backup first. Values: `0 none`, `1 EU`, `72 China`, `102 Hong Kong`, `103 Macao`, `205 Korea`, `234 Taiwan`. **No North America value.** A US unit is expected to be `0` → logo DB off.
- Related: FM band setting (persistence `4101`, bits 9.0–9.3) `2 = NAR`; SDS region flag `2 = NAR`.
- `patches/EL/ExceptionList_RSDB.txt` = signature exception for `/net/mmx/mnt/boardbook/RSDB` (for SWDL-style installs of unsigned RSDB packages).

### Plan
1. Install M.I.B. (SD1, red engineering menu → Update → "FREE for all – M.I.B. Launcher"; external power; at own risk).
2. Run M.I.B. backup incl. RSDB + "all versions": does the US unit already have an RSDB folder/DB? If yes, its `CountryRegionData` may reveal NAR region ids.
3. Log Edmonton FM PI codes + PS names (RTL-SDR + RDS decoder) — no public list found.
4. Build test DB: this EU DB + a Canada region (new id, 38 translation rows, neighbor map → Canada) + Edmonton stations, with obvious test logos (frequency + which key matched: PI vs frequency).
5. M.I.B.: set RSDB region = EU → copy DB → reboot → drive; check radio settings for a station-logo country list (Automatic vs manual Canada).

## 9. Precedent: Australian RSDB (ViktorFr/MIB2-Australia-RadioStationDB, v1.0, Aug 2026)

Release DB analysed (`VW_MIB2_Harman_Australia_RSDB_v1.0.zip`, sha256 `17db3838…d1`). Tested on a VW MIB2.5 High (MHI2Q) Discover Pro, **ER/RoW firmware** (media codec `CLU8_MMX2_VW_ER_G13`), in Melbourne. Installed with M.I.B. "Copy RSDB to unit".

- **Schema identical** to the 1.20.20 file. Base is `1.10.66` (MIB2 family); `DatabaseVersion` = `1 | 10 | 66 | '2026-08-16 AU-MELB-v0.8-…' | 'Europe'` (regionCode left as Europe).
- **Logos are 160×120 in the whole 1.10.x DB (8,427 of 8,427)** → MIB2/MHI2Q size. Their new logos are opaque RGB PNGs (no alpha) — works.
- **New region**: `countryId 61` (Australia's phone code — apparently a free choice), `macroRegionId 69`, `requestStrategy 2`, `useDatabaseNameInHmi 15`, `nativeLanguage 'en_AU'`, `extraInt1 1`, everything else -1. **Neighbor-PI map copied verbatim from Germany** (so 3xxx PIs "map" to Poland) — yet Melbourne matched. So with the region chosen manually, the unit apparently searches that region's rows directly; the neighbor map was not needed.
- Translations: 38 rows, all `'Australia'`, positions slotted into each language's list.
- **Station rows**: `country 61`, `ecc 240` (0xF0, Australia's real ECC), observed PI, `frequency` kHz, `shortName`/`longName`/`textToSpeech` = full name (up to 15 chars — 8-char limit not required), `language 'en'`, `ensembleId -1` for FM. New ids 1,425,267+ (stations) and 89,534+ / 90,716+ (logos). 18 FM + 76 DAB rows (DAB rows also have `ensembleId -1`).
- No `SdsStationPhoneme` rows for the new stations.
- Car settings that worked: FM tuner region EU/RDW, AM tuner Australia, **RSDB region EU**, **station-logo region "Australia / country 61"**, automatic/autostore station logos enabled. MMI still displayed the RDS PS text (e.g. "KIIS1011") with the DB logo.
- Their PIs came from the air (manifest: e.g. Fox 101.9 = 3101, triple j 107.5 = 2D5F).

**Implications for Canada:** base the Canadian build on a 1.10.x DB (this release works as a base — keep Australia, add Canada), 160×120 logos, new countryId (not 1 = AUTO), `ecc 161`, observed PIs. Open risk not covered by the precedent: US (NAR) firmware + NAR FM tuner setting.

## 10. Station data source: WTFDA FM database

- https://db.wtfda.org — North American FM database (DXer-maintained) with **PI Code, PS Info, Radiotext** columns, Canadian stations included, no login.
- No GET search; workable route is the city-sorted listing `https://db.wtfda.org/comm_city/up/<page>` (25 rows/page, ~1,277 pages). Calgary ≈ pages 146–147 (or `comm_city/down/1130–1131`). Row order within one city changes between requests, so read several pages/directions and merge.
- Calgary result: `claude/calgary-fm-stations.csv` (30 rows, 24 with real PIs, all in C000–CFFF plus CBC network codes B202/B203/B204). Calgary private stations follow a consistent call-sign → PI scheme (e.g. CJAQ C954 → CJAY C95C: Q→Y = +8; CFEX→CFGQ spacing = 27 per 3rd-letter step).
- CKUA relays use the parent's PI (CKUA-FM-1 Calgary = CE23).

## 11. Canada build v0.1 (2026-09-26)

- Base: Australian v1.0 release DB (1.10.66). Output sha256 `e723b386…78a4`, 115 MB, integrity ok; all base rows/logos untouched.
- Added: CountryRegionData `countryId 124` "Canada" (macro 69, neighbor PI B/C → 124, others 0, requestStrategy 2, useDatabaseNameInHmi 15, nativeLanguage en_CA), 38 translations (localized), 25 logos (`logoId 124001–124025`, 160×120 opaque RGB PNG), 50 Stations rows (`stationId 1240001–1240050`: each station twice, `ecc 161` and `ecc 0`), `descriptor` = "CA Calgary <call>; PI <status> (WTFDA)". `DatabaseVersion.creationDate` = "2026-09-26 CA-CALGARY".
- Logos pulled from each station's Wikipedia infobox via the built-in browser (Wikimedia is blocked from the shell). CKMP uses a dark tile (white text in logo).
- Repo: `cdnninja/MIB2-Canada-RadioStationDB` (layout: `data/stations.csv`, `data/logo_sources.csv`, `data/logos/{source,160x120}`, `tools/build_db.py`, `docs/`). DB itself >100 MB → GitHub release asset, not a commit.
- Tip from the AU build's `descriptor` values: their PIs were verified from the unit's **RCC backup "live frequency list"** — the M.I.B. backup of the car likely contains received stations with PIs.

## Appendix — exact schema

```sql
CREATE TABLE DatabaseVersion (versionMajor INTEGER NOT NULL, versionMinor INTEGER NOT NULL, versionRevision INTEGER NOT NULL, creationDate TEXT, regionCode TEXT);
CREATE TABLE CountryRegionData (crId INTEGER, ioc TEXT NOT NULL, countryId INTEGER NOT NULL, macroRegionId INTEGER NOT NULL, countryNameInternational TEXT NOT NULL, countryNameOriginal Text NOT NULL, iocCountryNameInternational TEXT NOT NULL, countryEcc INTEGER NOT NULL, countryPi INTEGER NOT NULL, countryNeighborPi0 INTEGER NOT NULL, countryNeighborPi1 INTEGER NOT NULL, countryNeighborPi2 INTEGER NOT NULL, countryNeighborPi3 INTEGER NOT NULL, countryNeighborPi4 INTEGER NOT NULL, countryNeighborPi5 INTEGER NOT NULL, countryNeighborPi6 INTEGER NOT NULL, countryNeighborPi7 INTEGER NOT NULL, countryNeighborPi8 INTEGER NOT NULL, countryNeighborPi9 INTEGER NOT NULL, countryNeighborPiA INTEGER NOT NULL, countryNeighborPiB INTEGER NOT NULL, countryNeighborPiC INTEGER NOT NULL, countryNeighborPiD INTEGER NOT NULL, countryNeighborPiE INTEGER NOT NULL, countryNeighborPiF INTEGER NOT NULL, gpsMode TEXT NOT NULL, gpsp1 TEXT NOT NULL, gpsp2 TEXT NOT NULL, gpsp3 TEXT NOT NULL, gpsp4 TEXT NOT NULL, flagId INTEGER NOT NULL, amSupport INTEGER NOT NULL, fmSupport INTEGER NOT NULL, dabSupport INTEGER NOT NULL, speechSupport INTEGER NOT NULL, nurGenehmigteLogos INTEGER NOT NULL, requestStrategy INTEGER NOT NULL, useDatabaseNameInHmi INTEGER NOT NULL, nativeLanguage TEXT NOT NULL, extraString1 TEXT NOT NULL, extraString2 TEXT NOT NULL, extraString3 TEXT NOT NULL, extraString4 TEXT NOT NULL, extraString5 TEXT NOT NULL, extraInt1 INTEGER NOT NULL, extraInt2 INTEGER NOT NULL, extraInt3 INTEGER NOT NULL, extraInt4 INTEGER NOT NULL, extraInt5 INTEGER NOT NULL);
CREATE TABLE CountryRegionTranslationData (countryId INTEGER NOT NULL, guiLanguageId INTEGER NOT NULL, guiLanguage TEXT NOT NULL, countryRegionTranslation TEXT NOT NULL, guiListItemPosition INTEGER NOT NULL);
CREATE TABLE SdsPhonemeSets (phonemeSetsId INTEGER NOT NULL, language TEXT NOT NULL, CLClanguage TEXT NOT NULL, phonemeSetsversionMajor INTEGER NOT NULL, phonemeSetsversionMinor INTEGER NOT NULL, phonemeSetsversionRevision INTEGER NOT NULL);
CREATE TABLE SdsStationPhoneme (sdsId INTEGER, stationId INTEGER NOT NULL, stationPiSid INTEGER NOT NULL, countryId INTEGER NOT NULL, stationType TEXT NOT NULL, orthography TEXT NOT NULL, ttsMode INTEGER NOT NULL, transcription TEXT NOT NULL, phonemeSet INTEGER NOT NULL);
CREATE TABLE StationLogos (logoId INTEGER PRIMARY KEY NOT NULL, country INTEGER, isOnPreset INTEGER, fileName TEXT, stationLogo BLOB);
CREATE TABLE Stations (stationId INTEGER PRIMARY KEY NOT NULL, country INTEGER NOT NULL, ecc INTEGER NOT NULL, piSid INTEGER NOT NULL, linkedPi INTEGER NOT NULL, ensembleId INTEGER NOT NULL, scidi INTEGER NOT NULL, subChannelId INTEGER NOT NULL, frequency INTEGER NOT NULL, longName TEXT, shortName TEXT NOT NULL, type TEXT NOT NULL, logoId INTEGER NOT NULL, regionalScope TEXT, networkStatus TEXT, gpsPosition TEXT, power INTEGER, height INTEGER, radiationMode TEXT, descriptor TEXT, textToSpeech TEXT, asr TEXT, language TEXT);
CREATE INDEX index_SDSstationID ON SdsStationPhoneme (stationId);
CREATE INDEX index_StaCountry ON Stations (country);
CREATE INDEX index_StaEcc ON Stations (ecc);
CREATE INDEX index_StaFrequency ON Stations (frequency);
CREATE INDEX index_StaPiSid ON Stations (piSid);
CREATE INDEX index_StaType ON Stations (type);
```

`SdsStationPhoneme` detail: `orthography` = hex(stationId) + '.' + variant (station 10003 → '2713.1', '2713.2', …); `ttsMode` 1 = primary pronunciation, 0 = alternates; `sdsId` NULL and `stationPiSid`/`countryId`/`stationType` = -1 in every row.

## Sources
- ISED — Program information codes for radio broadcasting stations: https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/licences-and-certificates/radio-authorizations/broadcasting-certification/program-information-codes-radio-broadcasting-stations
- NRSC-4-A annexes (CBC B_0x codes, C000–CFFF): https://www.nrscstandards.org/standards-and-guidelines/documents/archive/nrsc-4-a-annexes-2005.pdf
- RadioDNS country code table (Canada ECC A1; PI prefixes): https://github.com/radiodns/java-CountryCodeResolver
- WTFDA PI converter (Canadian stations using US-style PIs): https://db.wtfda.org/rds1.html
- Australian RSDB project: https://github.com/ViktorFr/MIB2-Australia-RadioStationDB
- M.I.B. source (rsdb.sh, backupplus, Launcher-sda0.esd, patch compatibility table): https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash
- M.I.B. discussion — import VW_STL_DB.sqlite on MHI2Q: https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/discussions/62
- M.I.B. discussion — RSDB problems on MHI2: https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/discussions/644
- Digital Eliteboard RadioStationDB thread (paths, metainfo, versions, coding):
  - https://digital-eliteboard.com/threads/audi-vw-mib2-mhi2-radiostationdb-senderlogos.498865/page-2
  - https://digital-eliteboard.com/threads/audi-vw-mib2-mhi2-radiostationdb-senderlogos.498865/page-8
  - https://digital-eliteboard.com/threads/audi-vw-mib2-mhi2-radiostationdb-senderlogos.498865/page-9
  - https://digital-eliteboard.com/threads/audi-vw-mib2-mhi2-radiostationdb-senderlogos.498865/page-11
  - https://www.digital-eliteboard.com/threads/audi-vw-mib-radiostationdb-senderlogos.498865/page-15
