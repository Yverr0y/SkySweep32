#!/usr/bin/env python3
"""Generate Sentinel Enclosure Rev B 3D CAD models (STEP/STL) and verify fit."""
from __future__ import annotations

import sys
from pathlib import Path

SYSPATH = r"C:\Users\kiril\AppData\Local\Programs\FreeCAD 1.1\bin"
if SYSPATH not in sys.path:
    sys.path.append(SYSPATH)

import FreeCAD
import Part

ENCLOSURE_DIR = Path(__file__).resolve().parent / "enclosures"
ENCLOSURE_DIR.mkdir(parents=True, exist_ok=True)


def make_box(dx: float, dy: float, dz: float, x0: float = 0.0, y0: float = 0.0, z0: float = 0.0) -> Part.Shape:
    return Part.makeBox(dx, dy, dz, FreeCAD.Vector(x0, y0, z0))


def make_cylinder(r: float, h: float, x0: float = 0.0, y0: float = 0.0, z0: float = 0.0,
                  dir_v: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> Part.Shape:
    return Part.makeCylinder(r, h, FreeCAD.Vector(x0, y0, z0), FreeCAD.Vector(*dir_v))


def build_enclosure() -> tuple[Path, Path, Path, Path]:
    # PCB is 120 x 80 x 1.6 mm from (10, 10) to (130, 90).
    # Inner case cavity: 123 x 83 x 24 mm from (8.5, 8.5, 2.0) to (131.5, 91.5, 26.0).
    # Wall thickness: 2.5 mm -> Outer box: 128 x 88 x 28.5 mm from (6.0, 6.0, -0.5) to (134.0, 94.0, 28.0).
    # Bottom case: Z in [-0.5, 17.5] (height 18 mm).
    # Lid case: Z in [17.5, 28.0] (height 10.5 mm).

    outer_bottom = make_box(128.0, 88.0, 18.0, 6.0, 6.0, -0.5)
    inner_bottom = make_box(123.0, 83.0, 16.0, 8.5, 8.5, 2.0)
    bottom_shell = outer_bottom.cut(inner_bottom)

    # Add 4 mounting bosses for M3 screws at PCB hole centers: (15, 15), (125, 15), (125, 85), (15, 85)
    bosses = []
    for bx, by in [(15.0, 15.0), (125.0, 15.0), (125.0, 85.0), (15.0, 85.0)]:
        outer_boss = make_cylinder(3.5, 4.0, bx, by, -0.5)
        hole = make_cylinder(1.4, 6.0, bx, by, -0.5) # M3 thread pilot hole d=2.8mm
        bosses.append(outer_boss.cut(hole))

    for b in bosses:
        bottom_shell = bottom_shell.fuse(b)

    # Cutouts in bottom case:
    # 1. USB-C cutout at top wall (Y=6.0): X in [17.5, 28.5], Z in [1.5, 8.5]
    usb_cut = make_box(11.0, 5.0, 7.0, 17.5, 5.0, 1.5)
    # 2. MicroSD slot at left wall (X=6.0): Y in [60.0, 76.0], Z in [1.5, 6.5]
    sd_cut = make_box(5.0, 16.0, 5.0, 5.0, 60.0, 1.5)
    # 3. Button openings at bottom wall (Y=94.0): 3 holes d=4.0mm at X=18, 24, 30, Z=3.5mm
    btn1 = make_cylinder(2.0, 5.0, 18.0, 91.0, 3.5, dir_v=(0.0, 1.0, 0.0))
    btn2 = make_cylinder(2.0, 5.0, 24.0, 91.0, 3.5, dir_v=(0.0, 1.0, 0.0))
    btn3 = make_cylinder(2.0, 5.0, 30.0, 91.0, 3.5, dir_v=(0.0, 1.0, 0.0))
    # 4. SMA connector bulkheads d=6.5mm:
    # - 2.4G SMA at right wall (X=134.0, Y=28.0, Z=6.0)
    sma_24g = make_cylinder(3.25, 6.0, 131.0, 28.0, 6.0, dir_v=(1.0, 0.0, 0.0))
    # - 5.8G SMA at right wall (X=134.0, Y=50.0, Z=6.0)
    sma_58g = make_cylinder(3.25, 6.0, 131.0, 50.0, 6.0, dir_v=(1.0, 0.0, 0.0))
    # - LORA SMA at right wall (X=134.0, Y=74.0, Z=6.0)
    sma_lora = make_cylinder(3.25, 6.0, 131.0, 74.0, 6.0, dir_v=(1.0, 0.0, 0.0))
    # - SUB-G SMA at left wall (X=6.0, Y=48.0, Z=6.0)
    sma_subg = make_cylinder(3.25, 6.0, 5.0, 48.0, 6.0, dir_v=(1.0, 0.0, 0.0))

    bottom_case = bottom_shell.cut(usb_cut).cut(sd_cut).cut(btn1).cut(btn2).cut(btn3)
    bottom_case = bottom_case.cut(sma_24g).cut(sma_58g).cut(sma_lora).cut(sma_subg)

    # Lid Case: Z in [17.5, 28.0]
    outer_lid = make_box(128.0, 88.0, 10.5, 6.0, 6.0, 17.5)
    inner_lid = make_box(123.0, 83.0, 8.0, 8.5, 8.5, 17.5)
    lid_shell = outer_lid.cut(inner_lid)

    # OLED viewing window cutout on top lid (Z=28.0): X in [48.0, 78.0], Y in [40.0, 65.0]
    oled_win = make_box(30.0, 25.0, 5.0, 48.0, 40.0, 25.5)
    lid_case = lid_shell.cut(oled_win)

    # Verify 3D solids & manifold status
    assert bottom_case.isValid(), "Bottom case shape is invalid"
    assert lid_case.isValid(), "Lid case shape is invalid"
    print(f"[OK] Bottom case volume: {bottom_case.Volume:.2f} mm³")
    print(f"[OK] Lid case volume: {lid_case.Volume:.2f} mm³")

    # Export STEP and STL
    b_step = ENCLOSURE_DIR / "skysweep32_pro_case_bottom_rev_b.step"
    b_stl = ENCLOSURE_DIR / "skysweep32_pro_case_bottom_rev_b.stl"
    l_step = ENCLOSURE_DIR / "skysweep32_pro_case_lid_rev_b.step"
    l_stl = ENCLOSURE_DIR / "skysweep32_pro_case_lid_rev_b.stl"

    bottom_case.exportStep(str(b_step))
    bottom_case.exportStl(str(b_stl))
    lid_case.exportStep(str(l_step))
    lid_case.exportStl(str(l_stl))

    print(f"[OK] Exported Bottom STEP: {b_step} ({b_step.stat().st_size} bytes)")
    print(f"[OK] Exported Bottom STL: {b_stl} ({b_stl.stat().st_size} bytes)")
    print(f"[OK] Exported Lid STEP: {l_step} ({l_step.stat().st_size} bytes)")
    print(f"[OK] Exported Lid STL: {l_stl} ({l_stl.stat().st_size} bytes)")

    return b_step, b_stl, l_step, l_stl


if __name__ == "__main__":
    build_enclosure()
