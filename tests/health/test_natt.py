"""Health probe — Náttúrufræðistofnun habitat map (gis.natt.is GeoServer).

Contract: RETIRED source. The 1:25.000 3rd-edition habitat raster
`vistgerdir__ni_vg25r_3utg_lzw` that `scripts/natt.py` read was withdrawn from
gis.natt.is in 2026-11 (the Source health run 43685708055 caught it), after the
polygon edition `LMI_vektor:vistgerd` went in 2026-08. No successor is listed
in the WCS, WMS or WFS capabilities, or on gis.lmi.is / ogc.gis.is.

This probe therefore asserts the *absence* and fails only when a habitat raster
is published again — the cue to revive `scripts/natt.py` (set `RETIRED = False`
and point `COVERAGE` / `WMS_LAYER` at the new name). The
`vistgerdir:v_vg25v_fl_*` vector layers are NOT a replacement: they carry only
geothermal, freshwater and littoral habitats. See `.agents/skills/natt/SKILL.md`.
"""
from __future__ import annotations

from scripts.natt import WCS, habitat_raster_ids, wcs_coverage_ids


def test_habitat_raster_still_withdrawn_or_republished(http):
    r = http.get(
        WCS,
        params={"service": "WCS", "version": "2.0.1", "request": "GetCapabilities"},
    )
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"
    ids = wcs_coverage_ids(r.text)
    assert len(ids) >= 5, f"capabilities parsed to {len(ids)} coverages — probe blind"
    found = habitat_raster_ids(ids)
    assert not found, (
        f"{r.request.url} -> habitat raster republished as {found}: revive "
        f"scripts/natt.py (RETIRED = False, new COVERAGE/WMS_LAYER) and restore "
        f"the legend and GetCoverage probes from git history"
    )
