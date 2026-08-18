"""Health probe — Náttúrufræðistofnun GeoServer WFS (gis.natt.is).

Contract: the habitat-type layer `scripts/natt.py` LAYER points at still exists
and still serves the `DN` / `htxt` attribute pair that every CQL filter in that
script is built from (`DN=95` = L14.2 Tún og akurlendi, the cultivated-land
polygons behind `scripts/agricultural_land_map.py`).

**This probe is expected to fail as of 2026-07-17** — that is the point, not a
bug in the test. `LMI_vektor:vistgerd` has been withdrawn from gis.natt.is,
gis.lmi.is and ogc.gis.is alike; all three answer
`InvalidParameterValue: Feature type LMI_vektor:vistgerd unknown`.

NÍ have reorganised the habitat data into a `vistgerdir:` workspace, and this
docstring used to call those layers a non-drop-in replacement needing a mapping
decision. Measured against the live WFS on 2026-08-18, that was too generous:
there is nothing here to map to.

    vistgerdir:v_vg25v_fl_land          360 features, vg3 ∈ {L12.1 … L12.4},
                                        every one of them Hverasvæði
    vistgerdir:v_vg25v_fl_vatn       54,093
    vistgerdir:v_vg25v_fl_fjorur     19,519
    ni:vistgerdir_punktar             7,984

~82k features against the old layer's ~24M polygons. The schema is a `vg1…vg5`
hierarchy where `vg3` carries the L-code, so `L14.2 Tún og akurlendi` should be
`vg3='L14.2'` — and `resultType=hits` for that filter returns
`numberMatched="0"`, as do `L14.1` and `L14.3`. The land layer simply does not
carry the cultivated-land class.

So `DN=95` has no successor on this endpoint, and neither `scripts/natt.py` nor
`agricultural_land_map.py` can be migrated to it. The open question is not which
new code to pick; it is where the full-resolution vistgerðakort is published now,
if not on gis.natt.is. Tracked separately — the probe stays red on purpose, and
guessing a layer here would quietly change what the agricultural-land map means.

Payload discipline: the layer is ~24M polygons (the polygonised 5 m raster), so
neither request here transfers geometry — capabilities proves the name,
`resultType=hits` proves non-emptiness, and the attribute check uses
`propertyName=DN,htxt` with `count=5`.
"""
from __future__ import annotations

import re

from scripts.natt import LAYER, WFS


def test_capabilities_lists_the_habitat_layer(http):
    """A rename is the documented failure mode — catch it by name."""
    r = http.get(
        WFS,
        params={"service": "WFS", "version": "2.0.0", "request": "GetCapabilities"},
    )
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"
    assert f"<Name>{LAYER}</Name>" in r.text, (
        f"{r.request.url} -> {r.status_code}: {LAYER} absent from WFS "
        f"capabilities — renamed or withdrawn; see the natt skill"
    )


def test_habitat_layer_serves_dn_and_htxt(http):
    """`DN` + `htxt` are the only two attributes natt.py reads.

    Bounded with count=5 and propertyName so no geometry crosses the wire.
    """
    r = http.get(
        WFS,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": LAYER,
            "propertyName": "DN,htxt",
            "outputFormat": "application/json",
            "count": 5,
        },
    )
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}: {r.text[:200]}"

    payload = r.json()
    assert payload.get("type") == "FeatureCollection", (
        f"unexpected payload type {payload.get('type')!r}"
    )
    features = payload.get("features") or []
    assert features, f"{LAYER} returned zero features"

    props = features[0].get("properties") or {}
    assert "DN" in props and "htxt" in props, (
        f"{LAYER} no longer exposes DN/htxt; got {sorted(props)}"
    )
    assert isinstance(props["DN"], int), (
        f"DN is {type(props['DN']).__name__}, expected int — CQL filters like "
        f"DN=95 assume an integer column"
    )


def test_cultivated_land_filter_still_matches(http):
    """DN=95 (L14.2 Tún og akurlendi) — the filter the agricultural-land map runs.

    `hits` only: the real fetch is ~16.6k polygons and belongs in a fetch run.
    """
    r = http.get(
        WFS,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": LAYER,
            "resultType": "hits",
            "CQL_FILTER": "DN=95",
        },
    )
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}: {r.text[:200]}"

    match = re.search(r'numberMatched="(\d+)"', r.text)
    assert match, f"{r.request.url} -> {r.status_code}: no numberMatched in {r.text[:200]}"
    # Non-emptiness, not a count — the polygon total shifts between editions.
    assert int(match.group(1)) > 0, "DN=95 (L14.2) matched zero polygons"
