#!/usr/bin/env python3
"""Generate STEP 3D models for SkySweep32 Pro Rev B module envelopes."""
from __future__ import annotations

import sys
from pathlib import Path

SYSPATH = r"C:\Users\kiril\AppData\Local\Programs\FreeCAD 1.1\bin"
if SYSPATH not in sys.path:
    sys.path.append(SYSPATH)

import FreeCAD
import Part

MODEL_DIR = Path(__file__).resolve().parent / "3dmodels"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def make_box(dx: float, dy: float, dz: float, x0: float = 0.0, y0: float = 0.0, z0: float = 0.0) -> Part.Shape:
    return Part.makeBox(dx, dy, dz, FreeCAD.Vector(x0, y0, z0))


def make_cylinder(r: float, h: float, x0: float = 0.0, y0: float = 0.0, z0: float = 0.0,
                  dir_v: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> Part.Shape:
    return Part.makeCylinder(r, h, FreeCAD.Vector(x0, y0, z0), FreeCAD.Vector(*dir_v))


def export_step(shape: Part.Shape, name: str) -> Path:
    out_path = MODEL_DIR / f"{name}.step"
    shape.exportStep(str(out_path))
    print(f"[OK] Exported STEP: {out_path} ({out_path.stat().st_size} bytes)")
    return out_path


def build_models() -> None:
    # 1. Ebyte E01-ML01DP5: 18 x 33.4 mm PCB, SMA connector envelope at top
    pcb = make_box(18.0, 33.4, 1.6, -9.0, -16.7, 0.0)
    pa = make_box(10.0, 12.0, 3.0, -5.0, -4.0, 1.6)
    sma = make_cylinder(3.1, 13.0, 0.0, 16.7, 3.5, dir_v=(0.0, 1.0, 0.0))
    e01 = pcb.fuse(pa).fuse(sma)
    export_step(e01, "Ebyte_E01_ML01DP5")

    # 2. Ebyte E07-900M10S: 14 x 20 x 2.4 mm SMD module
    pcb = make_box(14.0, 20.0, 1.0, -7.0, -10.0, 0.0)
    shield = make_box(12.0, 14.0, 1.4, -6.0, -7.0, 1.0)
    ipex = make_cylinder(1.5, 1.0, -4.0, 7.0, 1.0)
    e07 = pcb.fuse(shield).fuse(ipex)
    export_step(e07, "Ebyte_E07_900M10S")

    # 3. Adafruit RFM95W PID 3072: 29 x 25 mm breakout PCB with U.FL connector
    pcb = make_box(29.0, 25.0, 1.6, -14.5, -12.5, 0.0)
    rfm = make_box(16.0, 16.0, 2.0, -8.0, -8.0, 1.6)
    ufl = make_cylinder(1.5, 1.0, 10.0, 0.0, 1.6)
    rfm95 = pcb.fuse(rfm).fuse(ufl)
    export_step(rfm95, "Adafruit_RFM95W_PID3072")

    # 4. RX5808 2012 Qualified Reference Envelope: 28 x 23 x 5 mm RF shield
    rx_shield = make_box(28.0, 23.0, 5.0, -14.0, -11.5, 0.0)
    export_step(rx_shield, "RX5808_2012_REFERENCE_ENVELOPE")

    # 5. Adafruit GPS PID 746: 35 x 25.5 x 6.5 mm PCB with integrated ceramic patch
    pcb = make_box(35.0, 25.5, 1.6, -17.5, -12.75, 0.0)
    patch = make_box(15.0, 15.0, 4.0, -7.5, -7.5, 1.6)
    gps = pcb.fuse(patch)
    export_step(gps, "Adafruit_GPS_PID746")

    # 6. Adafruit MicroSD PID 254: 31.85 x 25.4 x 3.75 mm breakout PCB with push-push socket
    pcb = make_box(31.85, 25.4, 1.6, -15.925, -12.7, 0.0)
    socket = make_box(14.0, 15.0, 2.15, -7.0, -10.0, 1.6)
    sd = pcb.fuse(socket)
    export_step(sd, "Adafruit_MicroSD_PID254")

    # 7. CUI CMT-1203-SMT-TR: 12 x 12 x 3.0 mm magnetic transducer
    buzzer = make_box(12.0, 12.0, 3.0, -6.0, -6.0, 0.0)
    export_step(buzzer, "CUI_CMT_1203_SMT_TR")


if __name__ == "__main__":
    build_models()
