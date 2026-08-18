---
name: natt
description: Náttúrufræðistofnun habitat types, species and geology via GeoServer WFS/WMS/WCS. The vistgerðir 1:25k habitat map is a 5 m RASTER served over WCS, not the WFS vector layer it used to be — that one was withdrawn in 2026-07. CC BY 4.0, attribution required.
---

# Náttúrufræðistofnun (NÍ) — Open data

Náttúrufræðistofnun Íslands (Icelandic Institute of Natural History) publishes
habitat-type, species-distribution, and geological data as open data.

- Public download portal: https://www.natt.is/is/midlun/opin-gogn/nidurhal-gagna
- Habitat-map viewer: http://vistgerdakort.ni.is/
- Map browser: https://kort.gis.is/mapview/
- Reference monograph (Fjölrit 54, 2018): http://utgafa.ni.is/fjolrit/Fjolrit_54.pdf
- Change-log between 1st and 3rd edition: http://utgafa.ni.is/kort/lysigogn/vg25r_3utg_breytingar.pdf
- Licence: **CC BY 4.0** — open, but attribution is required. natt.is gives the
  form: `[dataset] by Náttúrufræðistofnun is licensed under CC BY 4.0`. An
  earlier version of this skill said "no use restrictions", which is wrong:
  BY is a restriction, and maps built from this data must carry the credit.

## OGC services

NÍ runs a GeoServer at `https://gis.natt.is/geoserver/`. It hosts both NÍ's own
layers and several layers federated from LMI / Hagstofan / Skógræktin.

- WFS GetCapabilities: `https://gis.natt.is/geoserver/wfs?service=WFS&version=2.0.0&request=GetCapabilities`
- WMS GetCapabilities: `https://gis.natt.is/geoserver/wms?service=WMS&version=1.3.0&request=GetCapabilities`
- All layers are published in **EPSG:3057** (ISN93 / LCC Iceland).
- WFS supports `outputFormat=application/json` (GeoJSON) and CQL filters via
  `CQL_FILTER=…`.
- **WCS** serves the rasters: `https://gis.natt.is/geoserver/wcs`. This is where
  the habitat map lives, and it is invisible to WFS — a coverage is not a feature
  type, so no amount of reading WFS capabilities will find it.
- A raster's legend is machine-readable via WMS `GetStyles`, which returns the
  SLD with one `ColorMapEntry` per class (`quantity` = the DN code, `label` =
  the habitat class). Prefer that over copying the table below by hand.

## Vistgerðir á Íslandi (3. útgáfa, 1:25.000) — habitat types

Habitat types ("vistgerðir") are NÍ's national EUNIS-aligned classification.
There are 64 land-, 17 freshwater-, and 24 coastal-shore habitat types,
documented in Fjölrit 54.

**The vector layer is gone (2026-07).** `LMI_vektor:vistgerd` — the polygonised
version, ~24M rows with `DN`/`htxt` — was withdrawn from gis.natt.is, gis.lmi.is
and ogc.gis.is alike; all three answer `InvalidParameterValue: Feature type
LMI_vektor:vistgerd unknown`. Every recipe below that used it has been rewritten.

Do not mistake `vistgerdir:v_vg25v_*` for the replacement. Those are the separate
freshwater-and-shores product (`ni_vg25v`): the land layer holds 360 features,
all of them L12.x Hverasvæði, against the old layer's ~24M.

The land habitats are published **as a raster**, and only as a raster:

| | |
|---|---|
| WCS coverage id | `vistgerdir__ni_vg25r_3utg_lzw` |
| WMS layer | `vistgerdir:ni_vg25r_3utg_lzw` ("Vistgerðarkort") |
| grid | 102,928 × 72,798 at 5 m, EPSG:3057 |
| envelope | X 244,069.5–758,709.5, Y 311,026.7–675,016.7 |
| pixel value | the same `DN` code the vector layer carried |

That last row is the useful part: the codes did not change with the format, so
`DN=95` still means L14.2. Verified against the layer's own SLD, not assumed.

### `DN` → habitat-type mapping (subset of interest)

Codes and labels are sampled from the WFS attributes; spelling matches the
service exactly (Icelandic special chars come back as cp1252 mojibake when
GeoServer is asked for plain text — request `outputFormat=application/json`
to get correct UTF-8).

| DN | Code | Label |
|---:|------|-------|
| 1–5 | L1.1–L1.5 | Melavistir (gravel/sand barrens) |
| 6–8 | L3.1–L3.3 | Skriðuvistir (scree) |
| 9–10 | L4.1–L4.2 | Eyrar / aurar (river plains) |
| 11–13 | L5.1–L5.3 | Mosavistir (moss) |
| 15–17 | L6.1, L6.3, L6.4 | Hraunavistir (lava fields) |
| 19–25 | L7.* | Strandvistir (coastal terrestrial) |
| 26–38 | L8.* | Mýrar / flóar (mires / fens) |
| 39–45 | L9.* | Graslendi (grasslands) |
| 46–55 | L10.* | Móar / kjarrlendi (heaths / scrub) |
| 95 | **L14.2** | **Tún og akurlendi** (cultivated hayfield + arable) |
| 98 | V1 | Vötn (lakes) |
| 99 | V2 | Ár (rivers) |
| 108 | L13.1 | Jöklar og urðarjöklar (glaciers / rock glaciers) |
| 150 | L14.1 | Þéttbýli og annað manngert land (urban / man-made) |
| 152 | L11 | Birkiskógur (birch woodland) |
| 153 | L14.3 | Skógrækt (forestry) |
| 160 | L14.4 | Alaskalúpína (Alaska lupine — invasive) |
| 162 | L14.6 | Skógarkerfill ofl. þéttar tegundir (cow-parsley etc.) |
| 175 | F | Fjöruvistir (intertidal) |
| 176 | FX1.1 | Sjávarlón (coastal lagoons) |

### Fetching one habitat type

There is no server-side filter any more — you cannot ask a coverage for "just
class 95". You fetch pixels and threshold them locally, which `scripts/natt.py`
does:

```bash
uv run python scripts/natt.py inventory          # DN → class, from GetStyles
uv run python scripts/natt.py habitat --dn 95    # → GeoJSON polygons, EPSG:3057
```

Two things make that affordable, and both are worth knowing before writing a
fetcher of your own against this coverage:

- **`compression=Deflate` on GetCoverage.** A categorical raster compresses ~18x
  (measured: an 8.4 MB tile → 0.47 MB). Transfer is the entire cost here, so this
  is the difference between ~15 GB and under a gigabyte for the country.
- **Sample before you fetch.** `scaleFactor` gives a cheap low-resolution pass to
  find which tiles contain the class at all; only those are read at 5 m. Farmland
  is a low single-digit percentage of Iceland. Note that scaling is
  nearest-neighbour, so a class occurring only in patches far below the sampling
  step could be missed — `--no-recon` reads every tile for those.

A raw single tile, if you want to see the shape of it:

```bash
curl -sS "https://gis.natt.is/geoserver/wcs?service=WCS&version=2.0.1\
&request=GetCoverage&coverageId=vistgerdir__ni_vg25r_3utg_lzw\
&subset=X(420000,421000)&subset=Y(400000,401000)\
&format=image/tiff&compression=Deflate" -o tile.tif
```

**Baseline for L14.2** from the withdrawn vector layer: ~16,600 polygons,
~1,800 km². Any raster-derived figure should land near the area; the polygon
count is not comparable unless tile seams are dissolved, because polygonising
tile by tile splits every patch that crosses a tile edge.

## Other vector layers in the WFS

The WFS exposes 473 layer names (measured 2026-08-18). The most useful for
nature/agriculture work are:

| Layer | What |
|-------|------|
| `ni:ni_vg25v_fl` | Coastal-shore habitat polygons (24 fjöru-vistir) |
| `ni:ni_vg25v_li` | Running-water lines |
| `ni:ni_vg25v_pt` | Cold/thermal-spring points |
| `ni:vistgerdir_punktar` | Field-survey sample points |
| `ni:Floraisl_dreifing` | Vascular-plant distribution (Flóra Íslands) |
| `ni:Smadyr_dreifing` | Invertebrate distribution |
| `ni:hvitabjorn_a_islandi` | Polar-bear sightings |
| `land_og_skogur:natturulegt_birkilendi` | Natural birch woodland (Skógræktin) |
| `land_og_skogur:raektad_skoglendi` | Cultivated forest (Skógræktin) |
| `land_og_skogur:jardvegsrof` | Soil erosion |
| `CORINE:clc18_is`, `clc12_is`, `clc06_is`, `clc00_is` | CORINE Land Cover for Iceland |

## Caveats

- The text-based GeoServer responses (GML/CSV) come through as **cp1252-mojibake**
  for Icelandic characters. Always request `outputFormat=application/json` for
  clean UTF-8.
- **A missing layer is not a missing dataset.** When `LMI_vektor:vistgerd`
  vanished it looked withdrawn, and a month was spent hunting a vector successor
  among the `vistgerdir:v_vg25v_*` layers that never had the data. The map had
  simply moved from a feature type to a coverage. Check WMS *and* WCS
  capabilities before concluding anything is gone.
- Polygonising the raster produces many tiny polygons, same as the old vector
  layer did. Dissolve across tile seams before counting patches, and simplify
  before rendering at country scale.
- Edition 3 (2023) reshuffled L-codes vs edition 1 — see `vg25r_3utg_breytingar.pdf`
  before mixing data across editions.
- The WFS server can be slow on un-indexed CQL filters; filtering on `DN`
  (integer) is much faster than `htxt LIKE …`.
