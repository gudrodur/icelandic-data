"""Render per-source status lights into the README's source tables.

The badge at the top of the README is the headline: one light, 7-day bar, for a
stranger deciding whether to trust the repo. This is the detail view — a light
per source, showing the *current* verdict, for someone deciding whether the one
source they care about is worth cloning for.

Deliberately edits only the light. The Source and Description prose in those
tables is hand-written and stays hand-owned; this script adds or refreshes a
leading status cell and touches nothing else. Generating the prose too would
mean the README slowly becomes a worse copy of the skill descriptions.

    uv run python scripts/health_panel.py --history health/history.jsonl
    uv run python scripts/health_panel.py --history h.jsonl --check   # CI: no writes

Sources with no probe render as ○ rather than a false green — see
tests/health/README.md for why some skills have nothing upstream to probe.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from scripts.health_verdict import judge_all, load  # noqa: E402

# README display name -> probe name (the tests/health/test_<name>.py stem).
# Kept here rather than derived: the README says "Umferð (Vegagerðin)" for
# humans and the probe says "umferd" for machines, and both are correct.
DISPLAY_TO_PROBE = {
    "Hagstofa Íslands": "hagstofan",
    "Seðlabanki": "sedlabanki",
    "Tekjusagan": "tekjusagan",
    "Velsældarvísar": "velsaeldarvisar",
    "Heimsmarkmið": "heimsmarkmid",
    "Ríkisreikningur": "rikisreikningur",
    "Landlæknir": "landlaeknir",
    "Vinnumálastofnun": "vinnumalastofnun",
    "Farsæld barna": "farsaeld_barna",
    "Mælaborð landbúnaðarins": "maelabord_landbunadarins",
    "Ferðamálastofa": "ferdamalastofa",
    "Umferð (Vegagerðin)": "umferd",
    "Byggðastofnun": "byggdastofnun",
    "Vernd (Ríkislögreglustjóri)": "vernd",
    "Skatturinn": "skatturinn",
    "Nasdaq Iceland": "nasdaq",
    "Fuel": "fuel",
    "Maskína": "maskina",
    "Opnir reikningar": "opnirreikningar",
    "Tenders": "tenders",
    "HMS": "hms",
    "Skipulagsmál (Planitor)": "skipulagsmal",
    "Samgöngustofa": "samgongustofa",
    "car (island.is)": "car",
    "Veður": "vedur",
    "Loftgæði": "loftgaedi",
    "CO2 (co2.is)": "co2",
    "LMI": "lmi",
    "Laun (payday.is)": "laun",
    "Gengi (Borgun)": "gengi",
    "Dómstólar": "domstolar",
    "Reykjavíkurborg": "reykjavik",
}

# Rows with no upstream of their own. Rendered ○, never green — a green light
# on something that cannot break is a lie that looks like coverage.
NO_UPSTREAM = {
    "Financials": "analysis over skatturinn PDFs",
    "Insurance": "analysis over skatturinn PDFs",
    "iceaddr": "local library, bundled SQLite",
    "Kortagerð": "renders from cached LMI data",
}

LIGHT = {
    "healthy": "🟢",
    "flaky": "🟡",
    "dead": "🔴",
    "broken": "🔴",
    "unknown": "⚪",
}
NONE_LIGHT = "○"

START = "<!-- health:start -->"
END = "<!-- health:end -->"

_ROW = re.compile(r"^\|(?P<cells>.+)\|\s*$")


def lights(history: pathlib.Path, window_days: int = 30) -> dict[str, str]:
    """probe name -> light emoji."""
    verdicts = judge_all(load(history, window_days))
    return {v.source: LIGHT.get(v.verdict, "⚪") for v in verdicts}


def _light_for(display: str, by_probe: dict[str, str]) -> str:
    if display in NO_UPSTREAM:
        return NONE_LIGHT
    probe = DISPLAY_TO_PROBE.get(display)
    if probe is None:
        return "⚪"
    return by_probe.get(probe, "⚪")


def render(readme: str, by_probe: dict[str, str]) -> str:
    """Add/refresh the leading status cell in every source table row."""
    out, in_panel = [], False
    for line in readme.splitlines():
        if line.strip() == START:
            in_panel = True
            out.append(line)
            continue
        if line.strip() == END:
            in_panel = False
            out.append(line)
            continue
        if not in_panel:
            out.append(line)
            continue

        m = _ROW.match(line)
        if not m:
            out.append(line)
            continue

        cells = [c.strip() for c in m.group("cells").split("|")]

        # Header + separator: widen once, idempotently.
        if cells[:2] == ["Source", "Description"]:
            out.append("| | Source | Description |")
            continue
        if cells[:1] == ["", "Source", "Description"][:1] and cells[1:3] == ["Source", "Description"]:
            out.append("| | Source | Description |")
            continue
        if all(set(c) <= {"-", ":"} and c for c in cells):
            out.append("|" + "|".join(["---"] * max(len(cells), 3)) + "|")
            continue

        # Data row: drop any existing light cell, then re-add.
        if cells and (cells[0] in LIGHT.values() or cells[0] == NONE_LIGHT or cells[0] == ""):
            cells = cells[1:]
        if len(cells) < 2:
            out.append(line)
            continue
        display, desc = cells[0], cells[1]
        out.append(f"| {_light_for(display, by_probe)} | {display} | {desc} |")

    return "\n".join(out) + ("\n" if readme.endswith("\n") else "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history", type=pathlib.Path, required=True)
    ap.add_argument("--readme", type=pathlib.Path, default=pathlib.Path("README.md"))
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--check", action="store_true", help="exit 1 if the panel is stale; write nothing")
    args = ap.parse_args(argv)

    src = args.readme.read_text(encoding="utf-8")
    if START not in src or END not in src:
        print(f"{args.readme} has no {START} / {END} markers", file=sys.stderr)
        return 2

    out = render(src, lights(args.history, args.window_days))
    if out == src:
        print("panel up to date")
        return 0
    if args.check:
        print("panel is stale", file=sys.stderr)
        return 1
    args.readme.write_text(out, encoding="utf-8")
    print(f"panel refreshed -> {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
