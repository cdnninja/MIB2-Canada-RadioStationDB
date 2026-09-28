# HMI startup fix (MU1316 only)

> **Risk: read this first.** This places a file on the head unit's app partition that changes which
> services the HMI starts at boot. It is only for **MU1316 (`MHI2Q_US_AUG22_P5087`)** and has been used
> on one car (a 2017 Audi A4 B9). If the HMI misbehaved after installing it, you would need GEM and
> M.I.B. to remove it again. Use at your own risk, on external power.

## Why it is needed

On North American firmware the head unit never starts its radio station database service
(`radiodata`), so no station logos can show, whatever database is installed. The HMI's built-in startup
settings (`MIB2_Evo_HighQC_NAR_G22`) define a `RadioStationDB` component, the one that starts that
service, but nothing references it.

The HMI reads `/eso/hmi/lsd/hmi_startup.json` before its built-in copy (and falls back to the built-in
copy if that file is missing or unreadable). `hmi_startup.json` here is the built-in file with one entry
added to `LastmodeOrder`:

```diff
         {
+          "name": "RadioStationDB"
+                                        },
+        {
           "name": "Ecall"
```

`RadioStationDB` then starts the same way as `Exlap` (its neighbour in that list): a background start of
one service that nothing waits for.

## Files

Every release zip includes these files in the folder `hmi_startup_fix_MU1316_only/`; you don't need to download them from here.

| File | Goes on the M.I.B. SD card at |
|---|---|
| `sdcard/mod/RSDB/hmi_startup.json` | `/mod/RSDB/hmi_startup.json` |
| `sdcard/esd/scripts/rsdb_hmi_install.sh` | `/esd/scripts/rsdb_hmi_install.sh` |
| `sdcard/esd/scripts/rsdb_hmi_remove.sh` | `/esd/scripts/rsdb_hmi_remove.sh` |
| `Launcher-sda0.esd.snippet` | pasted into `/esd/Launcher-sda0.esd` (the two buttons) |

Copy the contents of `sdcard/` to the root of the card. Then open `/esd/Launcher-sda0.esd` in a text
editor, find the **Copy RSDB to unit** entry and paste the snippet right after it:

```
script
    value   sys 1 0x0100 "/net/mmx/fs/sda0/esd/scripts/rsdb.sh"
    label   "Copy RSDB to unit"
                                  <- paste Launcher-sda0.esd.snippet here
```

M.I.B.'s own `rsdb.sh` ("Copy RSDB to unit") is not changed.

## Buttons

GEM > m.i.b. > multimedia_system > radio > radiostation_db

- **Canada RSDB: place HMI startup file (MU1316 only)**
  - Reads the unit's MU number (the same way M.I.B. does). If it is not `MU1316`, it stops and changes nothing.
  - If the unit already has `/eso/hmi/lsd/hmi_startup.json`, it stops, changes nothing, and saves a copy
    of the unit's file to the card as `/backup/hmi_startup.json.from_unit`.
  - Otherwise it copies the file to the unit. Reboot to apply.
- **Canada RSDB: remove HMI startup file**
  - Saves a copy to the card as `/backup/hmi_startup.json.removed`, deletes the file from the unit.
    Reboot to apply. The HMI then uses its built-in startup settings again.

A firmware update also removes the file.

## Where the file comes from

| | SHA-1 |
|---|---|
| Built-in `resources/hmi_startup.json` in the MU1316 HMI image (`lsd.jxe`), identical to `/eso/hmi/lsd/hmi_startup.json.example` in the `MHI2Q_US_AUG22_P5087` firmware | `e049fdc91c7b849ab8873eed2beee53f32474f40` |
| `sdcard/mod/RSDB/hmi_startup.json` (the above plus the one entry; everything else byte-identical, CRLF line endings kept) | `9573fc94d1a316fabb69f3696a03570035a72fc0` |

The file was checked with the HMI's own startup-config loader (from the decompiled `lsd.jxe`): 54
components load, as with the built-in file, and `RadioStationDB` becomes referenced with the same domain
start settings as `Exlap` (domain 36 `RadioDataServer`, state 0x4, asynchronous).

Other firmware versions have their own built-in file. Do not use this one on them.
