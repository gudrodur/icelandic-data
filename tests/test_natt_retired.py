"""Offline guard for the withdrawn natt habitat raster.

gis.natt.is dropped coverage ``vistgerdir__ni_vg25r_3utg_lzw`` (and its WMS
layer) in 2026-11. No successor exists on gis.natt.is, gis.lmi.is or
ogc.gis.is, so `scripts/natt.py` is retired and the health probe watches for a
republication instead of demanding the old name.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts import natt

FIXTURE = Path(__file__).parent / "fixtures" / "natt_wcs_capabilities_2026-11-15.xml"
OLD_ID = "vistgerdir__ni_vg25r_3utg_lzw"


def test_fixture_is_a_real_capabilities_listing():
    ids = natt.wcs_coverage_ids(FIXTURE.read_text(encoding="utf-8"))
    assert len(ids) >= 20, ids  # an empty parse must not read as "absent"
    assert "High_Resolution_Layer__Grassland" in ids


def test_old_coverage_is_absent_from_saved_capabilities():
    ids = natt.wcs_coverage_ids(FIXTURE.read_text(encoding="utf-8"))
    assert OLD_ID not in ids
    assert natt.habitat_raster_ids(ids) == []


def test_habitat_raster_ids_spots_a_republished_or_renamed_raster():
    assert natt.habitat_raster_ids(
        ["x__y", "vistgerdir__ni_vg25r_4utg_lzw", OLD_ID]
    ) == ["vistgerdir__ni_vg25r_4utg_lzw", OLD_ID]


@pytest.mark.parametrize("cmd", [natt.cmd_habitat, natt.cmd_inventory])
def test_commands_explain_the_withdrawal_without_network(cmd, monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("retired command touched the network")

    monkeypatch.setattr(natt.httpx, "get", no_network)
    ns = argparse.Namespace(format="geotiff", code=None, dn=95, res=50, tile_px=5000)
    with pytest.raises(SystemExit) as e:
        cmd(ns)
    assert "withdrawn" in str(e.value) and OLD_ID in str(e.value)
