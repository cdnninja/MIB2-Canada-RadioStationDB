# Base database

`VW_STL_DB.base.sqlite` is the starting point for every build (`tools/build_db.py`). It is VW's MIB2 RadioStationDB **1.10.66** with everything country-specific removed:

| Kept | Removed |
|---|---|
| Table layout (schema and indexes) | All 16,714 European and Australian stations |
| `DatabaseVersion` (1.10.66) | All station logos except VW's default radio icon (`logoId 100`) |
| VW's region list: 53 `CountryRegionData` rows, including AUTO and Europe | All voice-control pronunciations (`SdsStationPhoneme`) |
| Region names in 38 menu languages (`CountryRegionTranslationData`) | The community-added "Australia" region (countryId 61) |
| Phoneme language list (`SdsPhonemeSets`) | |

The region list stays because the car builds its station-logo region menu from it, and the Canada region hangs under the same "Europe" macro region (69).

## Where it came from

It was cut from the VW 1.10.66 database included in the [Australian RSDB v1.0 release](https://github.com/ViktorFr/MIB2-Australia-RadioStationDB) by ViktorFr. Thanks to that project for the database and for proving the method on MHI2Q units.

To regenerate it, or move to a newer VW database, run:

```sh
python3 tools/make_base.py <full VW_STL_DB.sqlite> base/VW_STL_DB.base.sqlite
```

Then update the checksum in [`base.json`](base.json) and open a `feat:` pull request.
