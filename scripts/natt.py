"""Náttúrufræðistofnun open-data fetcher — habitat types (vistgerðir).

Extracts a single habitat class from the 1:25.000 3rd-edition habitat map and
writes it as polygons, which is what ``agricultural_land_map.py`` consumes.

**Source changed 2026-08-18.** This used to read the WFS feature type
``LMI_vektor:vistgerd`` and filter it with ``CQL_FILTER=DN=95``. That layer was
withdrawn around 2026-07-17 and there is no vector successor for land habitats:
the current vector product (``ni_vg25v``) covers only freshwater and shores.

The map itself was never withdrawn. It is published as a **raster coverage**,
which is why no amount of WFS querying could find it:

    WCS   https://gis.natt.is/geoserver/wcs
    id    vistgerdir__ni_vg25r_3utg_lzw      ("Vistgerðarkort", 5 m, EPSG:3057)

The pixel values are the same ``DN`` codes the old vector layer carried — the
polygons were a derivative of this raster — so ``DN=95`` still means
``L14.2 Tún og akurlendi``. That is not inferred: the layer's own SLD says so,
and ``legend()`` below reads it rather than hardcoding a table.

Licence: CC BY 4.0, Náttúrufræðistofnun. Cite as
``Vistgerðakort 2024 by Náttúrufræðistofnun is licensed under CC BY 4.0``.

CLI:

    # download one habitat class as polygons (default: L14.2 = DN 95)
    uv run python scripts/natt.py habitat --dn 95
    uv run python scripts/natt.py habitat --code L14.2

    # the DN -> class table, straight from the published style
    uv run python scripts/natt.py inventory

Output:
    data/raw/natt/vistgerdir/<L-code>__<slug>.geojson   (EPSG:3057)
    data/raw/natt/vistgerdir/legend.csv                 (DN -> class)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import numpy as np
import rasterio
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from rasterio.features import shapes as raster_shapes
from rasterio.io import MemoryFile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

GEOSERVER = "https://gis.natt.is/geoserver"
WCS = f"{GEOSERVER}/wcs"
WMS = f"{GEOSERVER}/wms"
COVERAGE = "vistgerdir__ni_vg25r_3utg_lzw"
STYLE_LAYER = "vistgerdir:ni_vg25r_3utg_lzw"
CRS = "EPSG:3057"

# Coverage envelope and native resolution, from DescribeCoverage.
X_MIN, Y_MIN = 244069.5, 311026.7
X_MAX, Y_MAX = 758709.5, 675016.7
NATIVE_M = 5.0

# Two passes, because the full grid is 102,928 x 72,798 — 7.5 Gpx, ~15 GB
# uncompressed. Pass 1 samples the country at RECON_M to find which tiles carry
# the class at all; pass 2 fetches only those at full resolution. Farmland is a
# low single-digit percentage of Iceland, so this turns ~15 GB into ~100 MB.
RECON_M = 50.0
RECON_CHUNK_M = 100_000.0
TILE_M = 10_000.0

RAW = Path("data/raw/natt/vistgerdir")


# A full harvest is hundreds of requests over the better part of an hour against
# someone else's public server, so a transient 5xx is a certainty, not a risk.
# The first version of this had no retry and died on a 502 at tile 240 of 582.
RETRIES = 5
BACKOFF = (2, 5, 15, 45)
PAUSE_S = 0.3


def _tiff(params: list[tuple[str, str]], *, timeout: float) -> bytes:
    """GetCoverage as GeoTIFF. Deflate because a categorical raster compresses
    ~18x (measured: an 8.4 MB tile becomes 0.47 MB), and the transfer is the
    whole cost here."""
    q = [
        ("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
        ("coverageId", COVERAGE), ("format", "image/tiff"),
        ("compression", "Deflate"), *params,
    ]
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            r = httpx.get(WCS, params=q, timeout=timeout, follow_redirects=True)
            if r.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"{r.status_code} from WCS", request=r.request, response=r)
            r.raise_for_status()
            if not r.content.startswith((b"II", b"MM")):
                raise RuntimeError(f"WCS did not return a TIFF: {r.content[:200]!r}")
            return r.content
        except (httpx.HTTPStatusError, httpx.TransportError) as e:
            last = e
            if attempt == RETRIES - 1:
                break
            wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            print(f"    {type(e).__name__} — retrying in {wait}s "
                  f"({attempt + 1}/{RETRIES - 1})", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"WCS failed after {RETRIES} attempts: {last}") from last


def _read(blob: bytes) -> tuple[np.ndarray, rasterio.Affine]:
    """Band 1 is the habitat code; band 2 is GeoServer's alpha/validity mask."""
    with MemoryFile(blob) as mem, mem.open() as src:
        return src.read(1), src.transform


def tile(x0: float, y0: float, x1: float, y1: float, *,
         scale: float | None = None, timeout: float = 300.0):
    p = [("subset", f"X({x0},{x1})"), ("subset", f"Y({y0},{y1})")]
    if scale is not None:
        p.append(("scaleFactor", str(scale)))
    return _read(_tiff(p, timeout=timeout))


def legend() -> dict[int, str]:
    """DN -> habitat class, read from the layer's published SLD.

    The alternative was to hardcode 73 rows copied out of Fjölrit nr. 54. This
    way a re-classification upstream shows up as a changed label rather than as
    a silently wrong map.
    """
    r = httpx.get(WMS, params={
        "service": "WMS", "version": "1.1.1", "request": "GetStyles",
        "layers": STYLE_LAYER,
    }, timeout=60.0, follow_redirects=True)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    out: dict[int, str] = {}
    for e in root.iter():
        if not e.tag.endswith("ColorMapEntry"):
            continue
        q, label = e.get("quantity"), e.get("label")
        if q is None or not label:
            continue
        try:
            out[int(float(q))] = label
        except ValueError:
            continue
    if not out:
        raise RuntimeError("no ColorMapEntry rows in the style — did GetStyles change?")
    return dict(sorted(out.items()))


def _recon(dn: int) -> list[tuple[float, float]]:
    """Pass 1 — which TILE_M tiles contain this class at all.

    Sampled at RECON_M with nearest-neighbour, so a class that exists only in
    patches much smaller than RECON_M could in principle be missed. At 50 m
    against fields that are hectares, that does not happen; `--no-recon` skips
    this pass for a class where it would matter.
    """
    hits: set[tuple[float, float]] = set()
    chunks = [
        (x, y)
        for x in np.arange(X_MIN, X_MAX, RECON_CHUNK_M)
        for y in np.arange(Y_MIN, Y_MAX, RECON_CHUNK_M)
    ]
    for i, (cx, cy) in enumerate(chunks, 1):
        x1 = min(cx + RECON_CHUNK_M, X_MAX)
        y1 = min(cy + RECON_CHUNK_M, Y_MAX)
        arr, tr = tile(cx, cy, x1, y1, scale=NATIVE_M / RECON_M, timeout=300.0)
        rows, cols = np.nonzero(arr == dn)
        for r_, c_ in zip(rows, cols):
            wx, wy = tr * (c_ + 0.5, r_ + 0.5)
            hits.add((np.floor(wx / TILE_M) * TILE_M, np.floor(wy / TILE_M) * TILE_M))
        print(f"  recon {i:>2}/{len(chunks)}  {int(cx):>7},{int(cy):>7}  "
              f"{len(rows):>7,} px  → {len(hits)} tiles so far", file=sys.stderr)
    return sorted(hits)


def _all_tiles() -> list[tuple[float, float]]:
    return [
        (float(x), float(y))
        for x in np.arange(X_MIN, X_MAX, TILE_M)
        for y in np.arange(Y_MIN, Y_MAX, TILE_M)
    ]


def harvest(dn: int, *, recon: bool = True) -> list[dict]:
    """Pass 2 — polygonise the class, tile by tile, at native resolution.

    Each tile's polygons are cached on disk as they are produced, so an
    interrupted run resumes instead of starting over. Learned the hard way: a
    502 at tile 240 of 582 threw away forty minutes of someone else's bandwidth
    as well as ours.
    """
    tiles = _recon(dn) if recon else _all_tiles()
    cache = RAW / ".tiles"
    cache.mkdir(parents=True, exist_ok=True)
    done = sum(1 for tx, ty in tiles
               if (cache / f"dn{dn}_{int(tx)}_{int(ty)}.json").exists())
    print(f"  {len(tiles)} tiles to read at {NATIVE_M:.0f} m"
          f"{f' ({done} already cached)' if done else ''}", file=sys.stderr)

    feats: list[dict] = []
    for i, (tx, ty) in enumerate(tiles, 1):
        hit = cache / f"dn{dn}_{int(tx)}_{int(ty)}.json"
        if hit.exists():
            feats.extend(json.loads(hit.read_text(encoding="utf-8")))
        else:
            x1, y1 = min(tx + TILE_M, X_MAX), min(ty + TILE_M, Y_MAX)
            arr, tr = tile(tx, ty, x1, y1, timeout=300.0)
            mask = arr == dn
            local = [g for g, _ in raster_shapes(
                mask.astype(np.uint8), mask=mask, transform=tr)] if mask.any() else []
            hit.write_text(json.dumps(local), encoding="utf-8")
            feats.extend(local)
            time.sleep(PAUSE_S)
        if i % 10 == 0 or i == len(tiles):
            print(f"  tile {i:>4}/{len(tiles)}  {len(feats):,} polygons",
                  file=sys.stderr)
    return feats


def _slug(s: str) -> str:
    s = s.lower()
    for k, v in {"á": "a", "ð": "d", "é": "e", "í": "i", "ó": "o", "ú": "u",
                 "ý": "y", "þ": "th", "æ": "ae", "ö": "o"}.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def cmd_habitat(args: argparse.Namespace) -> None:
    table = legend()
    if args.code:
        matches = [dn for dn, lab in table.items() if lab.startswith(args.code)]
        if not matches:
            raise SystemExit(f"no class starting with {args.code!r} in the legend")
        dn = matches[0]
    else:
        dn = args.dn
    label = table.get(dn)
    if label is None:
        raise SystemExit(f"DN {dn} is not in the legend — run: natt.py inventory")
    print(f"DN {dn} = {label}", file=sys.stderr)

    geoms = harvest(dn, recon=not args.no_recon)
    if not geoms:
        raise SystemExit(f"no pixels matched DN {dn}")

    # Stitch across tile seams. Polygonising tile by tile splits every patch
    # that crosses a tile edge into two, and the map prints the polygon count
    # to readers as "reitir" — so without this the headline number is an
    # artefact of TILE_M rather than a fact about Iceland. Areas are unaffected
    # either way; the count is not.
    before = len(geoms)
    merged = unary_union([shape(g) for g in geoms])
    parts = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    geoms = [mapping(g) for g in parts]
    print(f"  {before:,} tile-local polygons → {len(geoms):,} after merging seams",
          file=sys.stderr)

    code = label.split()[0]
    rest = label[len(code):].strip()
    fc = {
        "type": "FeatureCollection",
        "name": f"{COVERAGE} DN={dn}",
        "crs": {"type": "name", "properties": {"name": f"urn:ogc:def:crs:{CRS}"}},
        "features": [
            {"type": "Feature", "properties": {"DN": dn, "htxt": label},
             "geometry": g}
            for g in geoms
        ],
    }
    out = RAW / f"{code}__{_slug(rest)}.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(geoms):,} polygons ({label}) to {out}", file=sys.stderr)


def cmd_inventory(_: argparse.Namespace) -> None:
    table = legend()
    out = RAW / "legend.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["DN", "htxt"])
        w.writerows(table.items())
    print(f"Wrote {len(table)} DN→class rows to {out}", file=sys.stderr)
    for dn, lab in table.items():
        print(f"  DN={dn:>4}  {lab}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    h = sp.add_parser("habitat", help="extract one habitat class as polygons")
    g = h.add_mutually_exclusive_group(required=True)
    g.add_argument("--dn", type=int, help="raster code, e.g. 95 = L14.2")
    g.add_argument("--code", help="L-code prefix, e.g. L14.2")
    h.add_argument("--no-recon", action="store_true",
                   help="skip the sampling pass and read every tile")
    h.set_defaults(fn=cmd_habitat)

    inv = sp.add_parser("inventory", help="dump the DN→class legend")
    inv.set_defaults(fn=cmd_inventory)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
