"""Health probe — Fiskistofa public active-closures WFS."""
from __future__ import annotations

from scripts.fiskistofa import ACTIVE_CLOSURES, WFS


def test_active_closures_are_geojson(http):
    r = http.get(WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": ACTIVE_CLOSURES, "outputFormat": "application/json", "count": 5})
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}: {r.text[:200]}"
    payload = r.json()
    assert payload.get("type") == "FeatureCollection", f"unexpected type {payload.get('type')!r}"
    assert "features" in payload, f"unexpected keys: {sorted(payload)}"
