"""Health probe — Náttúrufræðistofnun habitat map (vistgerðakort).

Contract: the habitat class `scripts/natt.py` extracts still exists, is still
served, and still carries the same numeric code — `DN=95` = L14.2 Tún og
akurlendi, the cultivated-land class behind `scripts/agricultural_land_map.py`.

**Rewritten 2026-08-18, from WFS to WCS.** This probe used to assert that the
WFS feature type `LMI_vektor:vistgerd` was present, and it had been failing
since 2026-07-17 because that layer was withdrawn. The conclusion drawn at the
time — that the habitat data had been reorganised into `vistgerdir:v_vg25v_*`
and lost the `DN` codes — was wrong in a way worth recording, because the
mistake was in the question, not the answer.

The map was never withdrawn. It is published as a **raster**, and a raster is
not a feature type, so it can never appear in WFS capabilities no matter how
carefully you read them. The `v_vg25v_*` vector layers that look like a
replacement are a separate small product (freshwater and shores); the land
habitats live in the coverage:

    vistgerdir__ni_vg25r_3utg_lzw    5 m, EPSG:3057, 102,928 x 72,798

Three cheap assertions, none of which transfers the country:

  1. DescribeCoverage — the coverage exists under that id
  2. GetStyles — DN 95 still means L14.2, read from the publisher's own SLD
     rather than from a table copied into this repo
  3. GetCoverage on one 1 km tile — it actually serves pixels

Licence: CC BY 4.0, Náttúrufræðistofnun.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from scripts.natt import COVERAGE, CRS, STYLE_LAYER, WCS, WMS

CULTIVATED_DN = 95
CULTIVATED_CLASS = "L14.2"


def test_coverage_is_published(http):
    """A withdrawal or rename is the documented failure mode — catch it by id."""
    r = http.get(WCS, params={
        "service": "WCS", "version": "2.0.1", "request": "DescribeCoverage",
        "coverageId": COVERAGE,
    })
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}: {r.text[:200]}"
    assert COVERAGE in r.text, (
        f"{COVERAGE} absent from DescribeCoverage — renamed or withdrawn. "
        f"Check WMS GetCapabilities for a new edition before assuming it is gone: "
        f"the 3rd edition replaced a WFS vector layer and looked withdrawn for a month."
    )
    assert "3057" in r.text, "coverage is no longer advertised in EPSG:3057"


def test_legend_still_binds_dn_95_to_cultivated_land(http):
    """The whole agricultural-land map rests on this one number meaning this one
    class. If NÍ renumber in a future edition, the map silently changes subject
    unless something asserts the binding."""
    r = http.get(WMS, params={
        "service": "WMS", "version": "1.1.1", "request": "GetStyles",
        "layers": STYLE_LAYER,
    })
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"

    entries = {
        int(float(e.get("quantity"))): e.get("label")
        for e in ET.fromstring(r.text).iter()
        if e.tag.endswith("ColorMapEntry") and e.get("quantity") and e.get("label")
    }
    assert entries, "no ColorMapEntry rows in the style — GetStyles changed shape"
    assert CULTIVATED_DN in entries, (
        f"DN {CULTIVATED_DN} is gone from the legend; classes present: "
        f"{sorted(entries)[:20]}…"
    )
    assert entries[CULTIVATED_DN].startswith(CULTIVATED_CLASS), (
        f"DN {CULTIVATED_DN} now means {entries[CULTIVATED_DN]!r}, not "
        f"{CULTIVATED_CLASS} — the agricultural-land map would change subject"
    )


def test_coverage_serves_pixels(http):
    """One 1 km tile. Proves the service answers with data rather than a service
    exception, without pulling any real volume — the full grid is ~15 GB."""
    r = http.get(WCS, params=[
        ("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
        ("coverageId", COVERAGE), ("format", "image/tiff"),
        ("compression", "Deflate"),
        ("subset", "X(420000,421000)"), ("subset", "Y(400000,401000)"),
    ])
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}: {r.text[:200]}"
    assert r.content.startswith((b"II", b"MM")), (
        f"not a TIFF — service exception? {r.content[:200]!r}"
    )
    assert len(r.content) > 1000, f"suspiciously small TIFF: {len(r.content)} bytes"
    assert CRS == "EPSG:3057"
