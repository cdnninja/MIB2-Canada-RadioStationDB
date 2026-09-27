#!/usr/bin/env python3
"""Replay the head unit's station-logo lookup against a built VW_STL_DB.sqlite.

Mirrors the Audi MIB2 HMI code (de.audi.tuner.app.rsdb.*, decompiled from the car's lsd.jxe):
  CountryRegionMngr.listChanged  -> does the logo database start at all?
  LogoDatabase.requestAmFmData   -> station list (country detection) and current station
  StrategyOne/Two/Five           -> the per-region lookup
  LogoDatabase.createLogoRequest -> which row wins, and whether it has a logo

The one part it cannot run is the unit's native `radiodata` service, which answers the queries. It is
modelled as "return every Stations row matching all the fields the request sets", which is what the
request structure (use* flags) describes.

Usage: python3 tools/simulate_hmi.py DB.sqlite [--region 1] [--stations FREQ_KHZ:PIHEX:NAME ...]
       with no --stations, the Calgary list received by a car in Sep 2026 is used.
"""
import argparse
import sqlite3
import sys

# (frequency kHz, PI, received PS) as logged by the car (esotrace, 2026-09-27)
CAR_LIST = [
    (88100, 0xCB9C, "CJWE-FM"), (88900, 0xCB34, ""), (89700, 0xB205, "ICI"), (90300, 0xCD59, ""),
    (90900, 0xCB42, "CJSW"), (92100, 0xC95C, "JAY 92"), (92900, 0xC185, ""), (93700, 0xCE23, ""),
    (95300, 0xCE5C, ""), (95900, 0xC456, ""), (96900, 0xC954, ""), (97700, 0xC5EF, ""),
    (98500, 0xC6A8, "Virgin"), (99700, 0xC37F, ""), (100900, 0xCE38, ""), (101500, 0xCC3F, ""),
    (102100, 0xB203, "CBCMUSIC"), (103100, 0xC37C, ""), (103900, 0xB204, "Premiere"), (105100, 0xCDE9, ""),
    (107300, 0xC1B4, ""),
]

NEIGHBOR_COLS = [f"countryNeighborPi{d:X}" for d in range(16)]


class Service:
    """Stand-in for the native radiodata DSI service."""

    def __init__(self, con):
        self.con = con

    def query(self, req):
        where, args = [], []
        for field, col in (("stationId", "stationId"), ("country", "country"), ("piSid", "piSid"),
                           ("frequency", "frequency"), ("stationType", "type"), ("logoId", "logoId")):
            if req.get("use_" + field):
                where.append(f"{col}=?")
                args.append(req[field])
        sql = "SELECT stationId, country, piSid, frequency, shortName, longName, logoId FROM Stations"
        if where:
            sql += " WHERE " + " AND ".join(where)
        return [dict(zip(("stationId", "country", "piSid", "frequency", "shortName", "longName", "logoId"), r))
                for r in self.con.execute(sql, args)]

    def logo(self, station_id, logo_id):
        return self.con.execute("SELECT length(stationLogo) FROM StationLogos WHERE logoId=?", (logo_id,)).fetchone()


class Regions:
    def __init__(self, con):
        cols = [c[1] for c in con.execute("PRAGMA table_info(CountryRegionData)")]
        self.rows = {r[cols.index("countryId")]: dict(zip(cols, r)) for r in con.execute("SELECT * FROM CountryRegionData")}

    def check_start(self, database_region):
        """CountryRegionMngr.listChanged: returns (ok, message)."""
        n = [c for c in self.rows if c == database_region]
        if len(n) != 1:
            return False, f"found {len(n)} region rows with countryId {database_region} (needs exactly 1)"
        row = self.rows[database_region]
        for _ in range(3):
            if row["countryId"] == row["macroRegionId"]:
                break
            row = self.rows.get(row["macroRegionId"], row)
        if row["countryId"] != row["macroRegionId"]:
            return False, "no root element found"
        menu = [r for r in self.rows.values()
                if r["countryId"] != r["macroRegionId"] and r["macroRegionId"] == row["countryId"] and r["countryId"] != 1]
        return True, f"root region {row['countryId']} ({row['countryNameInternational']}), {len(menu)} regions in the list"

    def strategy(self, country):
        return self.rows.get(country, {}).get("requestStrategy", -1)

    def neighbors(self, country):
        r = self.rows.get(country)
        return [r[c] for c in NEIGHBOR_COLS] if r else [0] * 16

    def home(self, country, cc):
        return self.neighbors(country)[cc] if 0 <= cc < 16 else 0


def base_request(freq, pi, rds=True):
    return {"piSid": pi, "use_piSid": True, "frequency": freq, "use_frequency": not rds,
            "stationType": "FM", "use_stationType": True}


def strategy_requests(regions, country, req):
    """StrategyOne/Two/Five.createStationDetectRequest for one station."""
    s = regions.strategy(country)
    if s == 2:
        if req["use_piSid"] and not req["use_frequency"]:
            home = regions.home(country, (req["piSid"] & 0xF000) >> 12)
            if home <= 0:
                return [dict(req)]
            if home == country:
                return [dict(req, country=home, use_country=True)]
            return [dict(req, country=country, use_country=True), dict(req, country=home, use_country=True)]
        return []
    if s in (1, 5):
        out = []
        for c in [country] + regions.neighbors(country):
            if c == 0:
                continue
            if s == 5 and req["piSid"] != -1:
                out.append(dict(req, use_frequency=False, use_piSid=True, country=c, use_country=True))
            out.append(dict(req, use_piSid=(s == 5 and False), use_frequency=True, country=c, use_country=True))
        return out
    return None  # unsupported strategy -> nothing


def pick(results, name, freq):
    """LogoDatabase.createLogoRequest tie-break."""
    if len(results) == 1:
        return results[0], "unique"
    if len(results) > 1:
        by_name = [r for r in results if name and r["shortName"].lower() == name.lower()]
        by_freq = [r for r in results if r["frequency"] == freq]
        if len(by_name) == 1:
            return by_name[0], "name match"
        if len(by_freq) == 1:
            return by_freq[0], "frequency match"
        return None, f"{len(results)} rows, no unique name/frequency match"
    return None, "no row"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--region", type=int, default=1, help="RSDB region adaptation (car: 1 = AUTO)")
    ap.add_argument("--stations", nargs="*", help="FREQ_KHZ:PIHEX[:NAME]")
    a = ap.parse_args()
    stations = CAR_LIST if not a.stations else [
        (int(s.split(":")[0]), int(s.split(":")[1], 16), (s.split(":") + [""])[2]) for s in a.stations]

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    svc, regions = Service(con), Regions(con)

    ok, msg = regions.check_start(a.region)
    print(f"1. Logo database start (region list, databaseRegion={a.region}): {'OK' if ok else 'FAIL'} - {msg}")
    if not ok:
        sys.exit(1)

    # 2. station list: country detection (settingsRegion = AUTO, list >= 2 -> database request only)
    votes = {}
    for f, pi, name in stations:
        res = svc.query(base_request(f, pi))
        if len(res) == 1:
            votes[res[0]["country"]] = votes.get(res[0]["country"], 0) + 1
    best = max(votes.items(), key=lambda kv: kv[1]) if votes else (1, 0)
    detected = best[0] if best[1] > 1 else 1
    print(f"2. Country detection from the station list: votes {votes or '{}'} -> country {detected}"
          f" ({regions.rows.get(detected, {}).get('countryNameInternational', '?')}), strategy {regions.strategy(detected)}")

    # 3. per-station lookup with the detected country's strategy, then logo
    print("3. Station lookups (frequency, PI, result):")
    hits = 0
    for f, pi, name in stations:
        reqs = strategy_requests(regions, detected, base_request(f, pi))
        if reqs is None:
            print(f"   {f/1000:6.1f} {pi:04X}  unsupported strategy")
            continue
        chosen, why = None, "no request sent"
        for r in reqs:
            chosen, why = pick(svc.query(r), name, f)
            if chosen:
                break
        if chosen and chosen["logoId"] != -1 and svc.logo(chosen["stationId"], chosen["logoId"]):
            hits += 1
            print(f"   {f/1000:6.1f} {pi:04X}  LOGO  {chosen['shortName']!r} logoId {chosen['logoId']} ({why})")
        elif chosen:
            print(f"   {f/1000:6.1f} {pi:04X}  row {chosen['stationId']} but no logo")
        else:
            print(f"   {f/1000:6.1f} {pi:04X}  none ({why})")
    print(f"=> {hits} of {len(stations)} received stations would show a logo")


if __name__ == "__main__":
    main()
