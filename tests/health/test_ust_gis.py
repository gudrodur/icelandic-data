"""Health probe — Environment Agency contaminated-land WFS layer."""
from __future__ import annotations

from scripts.ust_gis import CONTAMINATED_LAND, WFS


def test_contaminated_land_is_geojson_with_category(http):
    r = http.get(WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": CONTAMINATED_LAND, "outputFormat": "application/json", "count": 3, "srsName": "EPSG:4326"})
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}: {r.text[:200]}"
    features = r.json().get("features") or []
    assert features, "contaminated-land layer returned no features"
    props = features[0].get("properties") or {}
    assert {"heiti", "teg_mengunar"} <= set(props), f"unexpected properties: {sorted(props)}"
