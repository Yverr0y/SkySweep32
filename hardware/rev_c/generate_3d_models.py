#!/usr/bin/env python3
"""Generate explicitly conservative Rev C mechanical-envelope STEP models.

These are not cosmetic manufacturer models. Their dimensions come from the
part drawings recorded in hardware_manifest.json and intentionally bound all
material relevant to enclosure clearance.
"""

from __future__ import annotations

import json
from pathlib import Path

import FreeCAD
import Part

HERE = Path(__file__).resolve().parent
MODELS = HERE / "3dmodels"
MANIFEST = json.loads((HERE / "hardware_manifest.json").read_text(encoding="utf-8"))


def box(dx: float, dy: float, dz: float, x: float, y: float, z: float = 0.0) -> Part.Shape:
    return Part.makeBox(dx, dy, dz, FreeCAD.Vector(x, y, z))


def export(name: str, shape: Part.Shape) -> None:
    path = MODELS / name
    document = FreeCAD.newDocument(f"Envelope_{path.stem}")
    feature = document.addObject("PartDesign::Feature", path.stem)
    feature.Label = path.stem
    feature.Shape = shape
    Part.export([feature], str(path))
    FreeCAD.closeDocument(document.Name)
    print(f"[OK] {path.relative_to(HERE)} {shape.BoundBox.XLength:.2f} x "
          f"{shape.BoundBox.YLength:.2f} x {shape.BoundBox.ZLength:.2f} mm")


def generate() -> None:
    MODELS.mkdir(parents=True, exist_ok=True)

    # E01 carrier PCB plus a bounding body for its shield and edge SMA jack.
    # The resulting 22 x 33.4 x 9 mm solid matches the reviewed maximum extent.
    e01 = box(18.0, 33.4, 1.6, -9.0, -16.7)
    e01 = e01.fuse(box(13.0, 22.0, 4.0, -5.0, -11.0, 1.6))
    e01 = e01.fuse(box(8.0, 14.0, 7.4, 5.0, -7.0, 1.6))
    export("Ebyte_E01_ML01DP5_ENVELOPE.step", e01)

    # E07 drawing: castellated 14 x 20 mm module, bounded to 2.4 mm high.
    export("Ebyte_E07_900M10S_ENVELOPE.step", box(14.0, 20.0, 2.4, -7.0, -10.0))

    # SAM-M10Q-00B: 15.9 mm square antenna module, 6.3 mm maximum height.
    export("UBlox_SAM_M10Q_ENVELOPE.step", box(15.9, 15.9, 6.3, -7.95, -7.95))

    # CUI CMT-1203-SMT-TR bounding cylinder, including the 3.0 mm body height.
    export("CUI_CMT_1203_SMT_TR_ENVELOPE.step", Part.makeCylinder(6.0, 3.0))

    # Lid-mounted Adafruit PID 326. The board and display body are separated so
    # the enclosure can check the complete 29.2 x 26.7 x 6.2 mm envelope.
    oled = box(29.2, 26.7, 1.6, -14.6, -13.35)
    oled = oled.fuse(box(26.0, 15.2, 4.6, -13.0, -4.6, 1.6))
    export("Adafruit_OLED_PID326_ENVELOPE.step", oled)
    # Molex 104031-0811 maximum connector body plus a fully inserted microSD.
    # Body dimensions follow SD-104031-001; the card is an explicit service
    # envelope and extends from local y=-9.7 mm to y=+5.3 mm.
    microsd = box(12.0, 11.4, 1.42, -6.0, -5.7)
    microsd = microsd.fuse(box(11.0, 15.0, 1.0, -5.5, -9.7, 0.2))
    export("Molex_104031_0811_WITH_CARD_ENVELOPE.step", microsd)

    # Bourns MF-MSMF200-2 datasheet maximum 4.73 x 3.41 x 0.85 mm.
    export("Bourns_MF_MSMF200_2_ENVELOPE.step", box(4.73, 3.41, 0.85, -2.365, -1.705))

    # Bourns SRN6028 tolerance maximum 6.3 x 6.3 mm, 2.8 mm seated height.
    export("Bourns_SRN6028_3R9M_ENVELOPE.step", box(6.3, 6.3, 2.8, -3.15, -3.15))


if __name__ == "__main__":
    generate()
