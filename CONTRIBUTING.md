# Contributing stations

Every station is a row in [`data/stations.csv`](data/stations.csv), with a logo listed in [`data/logos.csv`](data/logos.csv). Edit those files (the GitHub web editor is fine) and open a pull request. The build checks your change and attaches a preview of the logos to the run.

## Add or fix a station

1. **Find the station's RDS PI code.** It's a 4-digit hex code such as `C95C`, and the logo match depends on it, so it must be what the station actually transmits. Good sources, best first:
   - Your car's own M.I.B. backup, which keeps a live frequency list with PI codes.
   - An RDS scanner, RTL-SDR (with SDR#, SDR++ or RDS Spy) or a radio that shows PI.
   - The [WTFDA FM database](https://db.wtfda.org), where DXers log the PI codes they hear.

   Canadian private stations usually use `C000`–`CFFF`. CBC networks use shared codes: Radio One `B202`, CBC Music `B203`, ICI Première `B204`.

2. **Add a row to `data/stations.csv`.** Use the next unused `id`. Ids are permanent: never renumber or reuse one; set `include` to `0` to drop a station instead.

   | Column | Example | Notes |
   |---|---|---|
   | `id` | `31` | Next unused number, never reused. |
   | `include` | `1` | `0` keeps the row but leaves it out of the build. |
   | `region` | `CA` | From `data/regions.csv`. |
   | `market` | `Edmonton` | The city the station is heard in. |
   | `frequency_mhz` | `92.1` | |
   | `callsign` | `CJAY-FM` | |
   | `name` | `CJAY 92` | Station branding. |
   | `pi` | `C95C` | Upper-case hex. `0000` and `FFFF` are encoder defaults and can't be used. |
   | `pi_status` | `logged` | `verified` (seen in your car or on a scanner), `logged` (from a database), or `guess`. |
   | `logo` | `CJAY_FM.png` | File name in `data/logos/`. |
   | `language` | `en` | `en` or `fr`. |
   | `source` | `WTFDA` | Where the PI came from. |
   | `notes` | | Anything useful. |

3. **Add the logo, if it's new.**
   - Put a PNG in `data/logos/`. Any size works; around 300 px wide or more looks best, and a transparent background is fine.
   - Add a row to `data/logos.csv` with the next unused `logo_id` (1240xx), the file name, the tile `background` (`FFFFFF`, or a dark colour for logos with white lettering) and the `source_url`.
   - Stations on the same network can share one logo row.

4. **Check it locally** (optional; the PR build does the same):

   ```sh
   pip install pillow
   python tools/validate.py
   python tools/build_db.py --out dist/mod/RSDB/VW_STL_DB.sqlite --preview dist/logo-preview.png
   ```

5. **Open the pull request.** Say which city it covers and whether you've tested it in a car.

## Test reports

Even without changing data, please open an issue with your car, unit and firmware (for example `MHI2Q_US_AUG22_P5087`), city, and which stations did or didn't get a logo.
