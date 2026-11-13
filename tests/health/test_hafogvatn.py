"""Health probe — MFRI current cod assessment embedded JSON."""
from __future__ import annotations

from bs4 import BeautifulSoup

from scripts.hafogvatn import tables_url


def test_cod_assessment_table_is_embedded_json(http):
    r = http.get(tables_url("cod", 2026))
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"
    soup = BeautifulSoup(r.text, "html.parser")
    heading = soup.find("h3", string="Assessment summary")
    assert heading, "Assessment summary section is absent"
    widget = heading.find_next("div", class_="datatables")
    assert widget, "Assessment summary has no DataTables widget"
    script = widget.find_next_sibling("script")
    assert script and script.get("type") == "application/json", "widget has no embedded JSON"
    assert '"Year"' in script.string and '"SSB"' in script.string and '"F"' in script.string
