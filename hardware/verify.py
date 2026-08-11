#!/usr/bin/env python3
"""Rebuild Rev C evidence from the canonical KiCad sources and firmware contract."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "hardware" / "rev_c"
sys.path.insert(0, str(REV))
from tool_discovery import (  # noqa: E402
    discover_freecad_runner,
    discover_kicad_cli,
)

SCHEMATIC = REV / "skysweep32_rev_c.kicad_sch"
BOARD = REV / "skysweep32_rev_c.kicad_pcb"
VALIDATION = REV / "validation"
PREVIEWS = REV / "previews"
TOOLCHAIN = json.loads((ROOT / "hardware" / "toolchain.json").read_text(encoding="utf-8"))



def command(args: list[str], *, cwd: Path = ROOT) -> None:
    print("+", subprocess.list2cmdline(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def output(args: list[str], *, cwd: Path = ROOT) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+)+", value)
    if not match:
        raise RuntimeError(f"cannot parse tool version from {value!r}")
    return tuple(int(part) for part in match.group(0).split("."))


def assert_reports() -> dict[str, object]:
    erc = (VALIDATION / "erc.rpt").read_text(encoding="utf-8")
    drc = (VALIDATION / "drc.rpt").read_text(encoding="utf-8")
    mechanical = json.loads((REV / "enclosure" / "mechanical_validation.json").read_text(encoding="utf-8"))
    if not re.search(r"ERC messages:\s*0\s+Errors\s+0\s+Warnings", erc):
        raise RuntimeError("ERC report is not zero-error/zero-warning")
    if "Found 0 DRC violations" not in drc or "Found 0 unconnected pads" not in drc:
        raise RuntimeError("DRC report is not zero-violation/zero-unconnected")
    if mechanical.get("status") != "PASS" or mechanical.get("failures"):
        raise RuntimeError("mechanical validation did not pass")
    return mechanical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-firmware", action="store_true", help="skip the PlatformIO build")
    parser.add_argument("--skip-renders", action="store_true", help="skip PNG regeneration")
    args = parser.parse_args()
    source_revision = output(["git", "rev-parse", "HEAD"])
    source_tree_dirty = bool(output(["git", "status", "--porcelain"]))


    python_minimum = version_tuple(TOOLCHAIN["python"]["minimum_version"])
    if sys.version_info[: len(python_minimum)] < python_minimum:
        raise RuntimeError(f"Python {TOOLCHAIN['python']['minimum_version']} or newer is required")

    kicad = discover_kicad_cli()
    freecad = discover_freecad_runner()
    kicad_version = output([str(kicad), "--version"])
    required_kicad_major = int(TOOLCHAIN["kicad"]["required_major"])
    if version_tuple(kicad_version)[0] != required_kicad_major:
        raise RuntimeError(f"KiCad major {required_kicad_major} required, found {kicad_version}")
    sch_api_version = importlib.metadata.version("kicad-sch-api")
    required_sch_api = TOOLCHAIN["python"]["packages"]["kicad-sch-api"]
    if sch_api_version != required_sch_api:
        raise RuntimeError(f"kicad-sch-api {required_sch_api} required, found {sch_api_version}")

    pio = shutil.which("pio")
    if not args.skip_firmware and not pio:
        raise FileNotFoundError("PlatformIO pio not found on PATH")
    if not SCHEMATIC.is_file() or not BOARD.is_file():
        raise FileNotFoundError("Rev C canonical schematic/PCB is missing")

    VALIDATION.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    summary_path = VALIDATION / "verification_summary.json"
    summary_path.unlink(missing_ok=True)

    command([sys.executable, str(ROOT / "scripts" / "generate_rev_c_pinmap.py"), "--check"])
    command([
        str(kicad), "sch", "erc", "--severity-all", "--exit-code-violations",
        "--output", str(VALIDATION / "erc.rpt"), str(SCHEMATIC),
    ])
    command([
        str(kicad), "pcb", "drc", "--refill-zones", "--severity-all",
        "--exit-code-violations", "--output", str(VALIDATION / "drc.rpt"), str(BOARD),
    ])
    command([str(freecad), str(REV / "generate_3d_models.py")], cwd=REV)
    command([
        str(kicad), "pcb", "export", "step", "--force", "--output",
        str(REV / "skysweep32_rev_c_pcba.step"), str(BOARD),
    ])
    command([str(freecad), str(REV / "generate_enclosure.py")], cwd=REV)
    command([sys.executable, str(REV / "generate_mechanical_drawing.py")], cwd=REV)

    if not args.skip_renders:
        command([
            str(kicad), "pcb", "render", "--quality", "high", "--floor", "--perspective",
            "--rotate", "35,0,-35", "--width", "1800", "--height", "1200",
            "--background", "opaque", "--output", str(PREVIEWS / "pcb_iso.png"), str(BOARD),
        ])
        command([
            str(kicad), "pcb", "render", "--quality", "high", "--floor", "--perspective",
            "--rotate", "35,0,-35", "--side", "bottom", "--width", "1800", "--height", "1200",
            "--background", "opaque", "--output", str(PREVIEWS / "pcb_bottom.png"), str(BOARD),
        ])
        command([
            str(kicad), "pcb", "render", "--quality", "high", "--floor", "--width", "1800",
            "--height", "1200", "--background", "opaque", "--output",
            str(PREVIEWS / "pcb_top.png"), str(BOARD),
        ])
        command([str(freecad), str(REV / "render_enclosure.py")], cwd=REV)

    command([sys.executable, str(REV / "export_manufacturing.py")], cwd=REV)
    if not args.skip_firmware:
        command([str(pio), "run", "-e", "esp32s3_rev_c_passive"])

    mechanical = assert_reports()
    required_freecad = version_tuple(TOOLCHAIN["freecad"]["minimum_version"])
    if version_tuple(str(mechanical["freecad_version"])) < required_freecad:
        raise RuntimeError(
            f"FreeCAD {TOOLCHAIN['freecad']['minimum_version']} or newer required, "
            f"found {mechanical['freecad_version']}"
        )

    summary = {
        "design": "SkySweep32 Rev C Passive Monitor",
        "maturity": "READY_FOR_FIRST_PROTOTYPE",
        "production_validated": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_revision,
        "source_tree_dirty": source_tree_dirty,
        "tools": {
            "kicad": kicad_version,
            "kicad_sch_api": sch_api_version,
            "freecad": mechanical["freecad_version"],
            "freecad_runner": str(freecad),
            "platformio": output([str(pio), "--version"]) if pio else "skipped",
            "python": sys.version.split()[0],
        },
        "commands": {
            "pin_contract": "python scripts/generate_rev_c_pinmap.py --check",
            "erc": "kicad-cli sch erc --severity-all --exit-code-violations",
            "drc": "kicad-cli pcb drc --refill-zones --severity-all --exit-code-violations",
            "pcba": "kicad-cli pcb export step --force",
            "mechanical": "FreeCAD generate_3d_models.py && FreeCAD generate_enclosure.py",
            "fabrication": "python hardware/rev_c/export_manufacturing.py",
            "firmware": "pio run -e esp32s3_rev_c_passive",
        },
        "gates": {
            "pin_contract": "PASS",
            "erc_zero_errors_warnings": "PASS",
            "drc_zero_violations_unconnected": "PASS",
            "mechanical_interference_and_service": mechanical["status"],
            "exact_bom_and_fabrication_exports": "PASS",
            "firmware_build": "SKIPPED" if args.skip_firmware else "PASS",
            "renders": "SKIPPED" if args.skip_renders else "PASS",
        },
        "evidence": {
            "erc": "validation/erc.rpt",
            "drc": "validation/drc.rpt",
            "mechanical": "enclosure/mechanical_validation.json",
            "fabrication": "manufacturing/fabrication_manifest.json",
            "mechanical_drawing": "enclosure/rev_c_mechanical_drawing.svg",
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] Rev C verification complete: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
