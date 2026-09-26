# MIB2-Canada-RadioStationDB

A Canadian RadioStationDB for MIB2 devices.

This is an attempt at a custom Canadian logo database for Harman **MIB2 High / MIB2.5 High (MHI2 / MHI2Q)** head units, so FM stations show their logo on the radio screen. It starts with just Calgary for testing purposes. Request your city by [opening an issue](../../issues/new/choose).

> **Status: early testing.** The method is confirmed on a European-firmware MHI2Q in Australia ([ViktorFr/MIB2-Australia-RadioStationDB](https://github.com/ViktorFr/MIB2-Australia-RadioStationDB)). North American firmware (for example `MHI2Q_US_AUG22_P5087`) hasn't been tested yet, so please report what you see.

## City support

| City | Province | FM stations | PI codes verified in a car | Logos tested in a car |
|---|---|---|---|---|
| Calgary (incl. Airdrie, Okotoks, High River) | AB | 25 | 23 of 25 | Not yet |

Don't see your city? [Request it](../../issues/new/choose), or add it yourself; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Download and install

Get the latest `MIB2-Canada-RSDB-vX.Y.Z.zip` from **[Releases](../../releases)**. The zip contains:

- `mod/RSDB/VW_STL_DB.sqlite`, the database.
- `INSTALL.txt`, step-by-step instructions using [M.I.B.](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash).
- `STATIONS.csv` and `logo-preview.png`, showing which stations and logos are in this release.

In short:

1. Back up your RSDB with M.I.B.
2. Copy `mod/RSDB/VW_STL_DB.sqlite` to the M.I.B. SD card.
3. Run **Copy RSDB to unit** and reboot.
4. Set **RSDB region = EU**. North American units ship with `none`, which switches the logo database off.
5. Choose **Canada** as the station-logo region in the car's radio settings.

## What's in the data

Everything is in plain files under [`data/`](data), so anyone can send a pull request:

| File | Contents |
|---|---|
| [`data/stations.csv`](data/stations.csv) | One row per FM station: frequency, call sign, name, RDS PI code, logo. |
| [`data/logos.csv`](data/logos.csv) + [`data/logos/`](data/logos) | Logo images (any size; the build renders them to 160×120), with tile background and source. |
| [`data/regions.csv`](data/regions.csv) | The "Canada" region added to the database (countryId 124, RDS ECC A1). |
| [`data/region_names.csv`](data/region_names.csv) | The region's name in each of the unit's 38 menu languages. |
| [`base/VW_STL_DB.base.sqlite`](base) | The empty MIB2 base database (VW's region list, no stations, 132 KB) the Canadian data is added to. |

See [CONTRIBUTING.md](CONTRIBUTING.md) to add or fix a station.

## How it works

The unit's radio station database is a SQLite file. The build starts from the empty base (the VW table layout, region list and menu translations, with every other country's stations and logos removed) and adds:

- a "Canada" row to `CountryRegionData`,
- its menu names to `CountryRegionTranslationData`,
- one `StationLogos` row per logo (160×120 PNG),
- two `Stations` rows per station, keyed by RDS PI code and frequency.

The two station rows are identical except for the extended country code: one uses Canada's `A1` and the other uses `0` (unknown), because North American stations rarely broadcast that code. Both point to the same logo.

[docs/rsdb-structure.md](docs/rsdb-structure.md) has the full table-by-table notes.

## Credits

- [ViktorFr/MIB2-Australia-RadioStationDB](https://github.com/ViktorFr/MIB2-Australia-RadioStationDB): the proven method, and the 1.10.66 database the empty base was cut from.
- [M.I.B. – More Incredible Bash](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash).
- [WTFDA North American FM Station Database](https://db.wtfda.org): logged PI codes.
- Station logos come from the stations' Wikipedia pages (sources in [`data/logos.csv`](data/logos.csv)). Names and logos belong to their owners and are used only to identify the stations.

Not affiliated with Volkswagen, Audi, Harman or any broadcaster. Use at your own risk.
