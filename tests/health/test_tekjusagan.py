"""Health probe — Tekjusagan (Forsætisráðuneytið).

History: until 2026-10-15 the SPA embedded a token-gated Power BI report and
this probe checked the token endpoint (GET /api/report/<id> -> {id, embedToken}).
The SPA was rebuilt without Power BI; that URL now returns the SPA index
(text/html) and the bundles carry no token code. The data is served by an open
JSON backend instead (found in the lazy chunks, 2026-10-19):

    POST https://tekjusagan.is/api/sqldata/<procedure>   flat JSON filters
    POST https://tekjusagan.is/api/sqlseries/<queryId>

The contract probed here is the smallest of those calls
(scripts.tekjusagan.PROBE_ENDPOINT): JSON in, JSON with a non-empty `items`
list out. The SPA routes themselves are deliberately *not* probed: it is an
Angular app, so every route — including ones that no longer exist — returns the
same 200 index.html, and a probe over them would be green by construction.
"""
from __future__ import annotations

import pytest

from scripts.tekjusagan import API_URL, PROBE_ENDPOINT, PROBE_PAYLOAD


@pytest.fixture(scope="module")
def answer(http):
    r = http.post(PROBE_ENDPOINT, json=PROBE_PAYLOAD)
    assert r.status_code == 200, (
        f"{PROBE_ENDPOINT} -> {r.status_code}: {r.text[:200]} "
        f"(the SPA was rebuilt once already on 2026-10-15 — re-derive the route "
        f"from the lazy chunks listed in index.html)"
    )
    assert r.headers["content-type"].startswith("application/json"), (
        f"{PROBE_ENDPOINT} -> {r.headers['content-type']}, not JSON — the API "
        f"route moved and the SPA index is answering instead"
    )
    return r.json()


def test_data_api_answers_json(answer):
    assert answer.get("success") is True, f"success flag not set; got {str(answer)[:200]}"
    assert isinstance(answer.get("items"), list), f"no items list; got {sorted(answer)}"


def test_data_api_returns_a_headcount(answer):
    """A value, not just a 200 — an empty items list means the procedure's
    parameter names or filter vocabulary changed and every query returns 0 rows."""
    items = answer["items"]
    assert items, "items is empty for IncomeGroup=3, Year=1991 — filter vocabulary changed?"
    assert items[0].get("Heildarfjöldi", 0) > 1000, f"implausible headcount: {items[0]}"


@pytest.mark.degraded_ok
def test_backend_rejects_missing_parameters(http):
    """Guards against the probe above passing by construction: the backend must
    still validate its inputs (an SQL procedure missing a parameter -> 400). If
    it starts answering 200 to an empty body, a 200 above proves less.
    degraded_ok — this tests the API's manners, not whether our data is reachable."""
    r = http.post(f"{API_URL}GenderEducationGroups", json={})
    assert r.status_code != 200, f"empty body accepted -> 200: {r.text[:200]}"
