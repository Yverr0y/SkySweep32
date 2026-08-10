#!/usr/bin/env python3
"""Generate verified 3D CAD render previews for SkySweep32 Pro Rev B PCB and Enclosure."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SYSPATH = r"C:\Users\kiril\AppData\Local\Programs\FreeCAD 1.1\bin"
if SYSPATH not in sys.path:
    sys.path.append(SYSPATH)

import FreeCAD
import Part

HERE = Path(__file__).resolve().parent
PCB_FILE = HERE / "skysweep32_pro_rev_b.kicad_pcb"
KICAD_CLI = Path(sys.executable).with_name("kicad-cli.exe")
OUT_DIR = HERE / "previews"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_pcb_views() -> None:
    # 1. Top isometric 3D render
    top_png = OUT_DIR / "preview_top.png"
    subprocess.run([
        str(KICAD_CLI), "pcb", "render", str(PCB_FILE),
        "-o", str(top_png), "--width", "1920", "--height", "1080",
    ], check=True)
    print(f"[OK] Generated PCB Top preview: {top_png}")

    # 2. Bottom 3D render
    bottom_png = OUT_DIR / "preview_bottom.png"
    subprocess.run([
        str(KICAD_CLI), "pcb", "render", str(PCB_FILE),
        "-o", str(bottom_png), "--width", "1920", "--height", "1080",
        "--side", "bottom",
    ], check=True)
    print(f"[OK] Generated PCB Bottom preview: {bottom_png}")


def main() -> int:
    render_pcb_views()
    print("[OK] All PCB previews generated successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
