#!/usr/bin/env python3
"""Generate and validate the Rev C enclosure around the exported PCBA STEP.

The KiCad assembly is the mechanical reference. Enclosure coordinates use the
KiCad STEP convention: board x=0..120 mm, y=-85..0 mm, board bottom z=0.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import FreeCAD
import Part

HERE = Path(__file__).resolve().parent
OUT = HERE / "enclosure"
MANIFEST = HERE / "hardware_manifest.json"
PCBA_STEP = HERE / "skysweep32_rev_c_pcba.step"
OLED_STEP = HERE / "3dmodels" / "Adafruit_OLED_PID326_ENVELOPE.step"

HOLES = ((5.0, -5.0), (115.0, -5.0), (115.0, -80.0), (5.0, -80.0))
BUTTONS = ((82.0, -80.0), (93.0, -80.0), (104.0, -80.0))


def box(dx: float, dy: float, dz: float, x: float, y: float, z: float) -> Part.Shape:
    return Part.makeBox(dx, dy, dz, FreeCAD.Vector(x, y, z))


def cylinder(radius: float, height: float, x: float, y: float, z: float) -> Part.Shape:
    return Part.makeCylinder(radius, height, FreeCAD.Vector(x, y, z))


def rounded_prism(
    x: float,
    y: float,
    width: float,
    depth: float,
    radius: float,
    z: float,
    height: float,
) -> Part.Shape:
    if radius <= 0 or radius * 2 >= min(width, depth):
        raise ValueError("invalid rounded-prism radius")
    shape = box(width - 2 * radius, depth, height, x + radius, y, z)
    shape = shape.fuse(box(width, depth - 2 * radius, height, x, y + radius, z))
    for cx, cy in (
        (x + radius, y + radius),
        (x + width - radius, y + radius),
        (x + width - radius, y + depth - radius),
        (x + radius, y + depth - radius),
    ):
        shape = shape.fuse(cylinder(radius, height, cx, cy, z))
    return shape


def hex_prism(across_flats: float, height: float, x: float, y: float, z: float) -> Part.Shape:
    radius = across_flats / math.sqrt(3.0)
    points = [
        FreeCAD.Vector(
            x + radius * math.cos(math.radians(30 + 60 * index)),
            y + radius * math.sin(math.radians(30 + 60 * index)),
            z,
        )
        for index in range(6)
    ]
    points.append(points[0])
    return Part.Face(Part.makePolygon(points)).extrude(FreeCAD.Vector(0, 0, height))


def build_base() -> Part.Shape:
    # 2.5 mm floor and walls, 1.5 mm nominal PCB edge clearance.
    outer = rounded_prism(-4.0, -89.0, 128.0, 93.0, 6.0, -6.5, 13.5)
    cavity = rounded_prism(-1.5, -86.5, 123.0, 88.0, 3.5, -4.0, 12.0)
    base = outer.cut(cavity)

    # Wall openings: USB-C, microSD, E01 SMA access, and J5 edge-launch SMA.
    for opening in (
        box(13.0, 6.0, 7.5, 13.5, -90.0, -3.0),
        box(6.0, 16.0, 5.0, 121.0, -67.0, -0.5),
        box(6.0, 18.0, 11.5, 121.0, -37.0, 0.0),
        box(6.0, 14.0, 11.5, -5.0, -51.0, -4.0),
    ):
        base = base.cut(opening)

    # PCB supports, through screws, DIN 934 M3 nut traps, and protective feet.
    for x, y in HOLES:
        base = base.fuse(cylinder(4.2, 4.0, x, y, -4.0))
        base = base.fuse(cylinder(5.0, 1.5, x, y, -8.0))
        base = base.cut(cylinder(1.7, 9.5, x, y, -8.0))
        base = base.cut(hex_prism(5.8, 2.8, x, y, -6.6))
    return base.removeSplitter()


def build_lid() -> Part.Shape:
    # Outside skirt fits over the base with 0.30 mm radial assembly clearance.
    top = rounded_prism(-6.2, -91.2, 132.4, 97.4, 8.2, 12.5, 3.0)
    skirt_outer = rounded_prism(-6.2, -91.2, 132.4, 97.4, 8.2, 6.8, 5.7)
    skirt_inner = rounded_prism(-4.3, -89.3, 128.6, 93.6, 6.3, 6.5, 6.3)
    lid = top.fuse(skirt_outer.cut(skirt_inner))

    # Upper halves of the two RF connector openings cross the lid skirt.
    lid = lid.cut(box(4.0, 18.0, 5.5, 123.0, -37.0, 6.5))
    lid = lid.cut(box(4.0, 14.0, 2.5, -7.0, -51.0, 6.5))

    # M3 compression posts clamp the PCB between lid and base without bending.
    for x, y in HOLES:
        lid = lid.fuse(cylinder(4.0, 10.9, x, y, 1.6))
        lid = lid.cut(cylinder(1.7, 14.5, x, y, 1.0))
        lid = lid.cut(cylinder(3.1, 3.1, x, y, 12.5))

    # OLED snap cradle. The board envelope is 45.4..74.6 x -68.35..-41.65
    # at z=9.3..10.9. Side walls retain 0.20 mm lateral clearance; bottom
    # shelves and top snap lips bound it with 0.10 mm vertical clearance.
    for rail in (
        box(0.8, 25.5, 3.5, 44.4, -67.75, 9.0),
        box(0.8, 25.5, 3.5, 74.8, -67.75, 9.0),
        box(28.4, 0.6, 3.5, 45.8, -69.15, 9.0),
        box(28.4, 0.6, 3.5, 45.8, -41.45, 9.0),
        box(1.2, 22.0, 0.2, 45.2, -66.0, 9.0),
        box(1.2, 22.0, 0.2, 73.6, -66.0, 9.0),
        box(0.6, 16.0, 0.3, 45.2, -63.0, 11.0),
        box(0.6, 16.0, 0.3, 74.2, -63.0, 11.0),
    ):
        lid = lid.fuse(rail)
    lid = lid.cut(box(26.4, 16.0, 4.0, 46.8, -60.0, 12.0))

    # Three independent plungers operate RESET, BOOT and USER; LED remains
    # visible through a dedicated 3.4 mm aperture at D3.
    for x, y in BUTTONS:
        lid = lid.cut(cylinder(2.6, 4.0, x, y, 12.0))
    lid = lid.cut(cylinder(1.7, 4.0, 71.0, -76.0, 12.0))
    return lid.removeSplitter()


def build_button() -> Part.Shape:
    stem = cylinder(1.2, 9.7, 0.0, 0.0, 2.8)
    flange = cylinder(3.0, 0.8, 0.0, 0.0, 11.7)
    cap = cylinder(2.3, 3.7, 0.0, 0.0, 12.5)
    return stem.fuse(flange).fuse(cap).removeSplitter()



def build_m3_socket_screw() -> Part.Shape:
    # DIN 912 M3 x 20: 3.0 mm head height, 5.5 mm nominal head diameter.
    shank = cylinder(1.5, 20.0, 0.0, 0.0, -7.5)
    head = cylinder(2.75, 3.0, 0.0, 0.0, 12.5)
    return shank.fuse(head).removeSplitter()


def build_m3_nut() -> Part.Shape:
    # DIN 934 M3: 5.5 mm across flats, 2.4 mm nominal thickness.
    return hex_prism(5.5, 2.4, 0.0, 0.0, -6.4)

def placed(shape: Part.Shape, x: float, y: float, z: float) -> Part.Shape:
    copy = shape.copy()
    copy.translate(FreeCAD.Vector(x, y, z))
    return copy


def export_step(name: str, shapes: list[tuple[str, Part.Shape]]) -> Path:
    path = OUT / name
    document = FreeCAD.newDocument(f"Export_{path.stem}")
    objects = []
    for label, shape in shapes:
        obj = document.addObject("PartDesign::Feature", label)
        obj.Label = label
        obj.Shape = shape
        objects.append(obj)
    Part.export(objects, str(path))
    FreeCAD.closeDocument(document.Name)
    return path


def export_stl(name: str, shape: Part.Shape) -> Path:
    path = OUT / name
    shape.exportStl(str(path))
    return path


def intersection_volume(first: Part.Shape, second: Part.Shape) -> float:
    return first.common(second).Volume


def generate() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    if not PCBA_STEP.is_file():
        raise FileNotFoundError(f"PCBA STEP missing: {PCBA_STEP}")
    pcba = Part.read(str(PCBA_STEP))
    oled = placed(Part.read(str(OLED_STEP)), 60.0, -55.0, 9.3)
    base = build_base()
    lid = build_lid()
    button_source = build_button()
    buttons = [placed(button_source, x, y, 0.0) for x, y in BUTTONS]
    pressed_buttons = [placed(button_source, x, y, -0.65) for x, y in BUTTONS]
    screw_source = build_m3_socket_screw()
    nut_source = build_m3_nut()
    screws = [placed(screw_source, x, y, 0.0) for x, y in HOLES]
    nuts = [placed(nut_source, x, y, 0.0) for x, y in HOLES]

    service_envelopes = {
        "usb_cable": box(13.0, 12.0, 7.5, 13.5, -96.0, -3.0),
        "microsd_card": box(22.0, 16.0, 5.0, 110.0, -67.0, -0.5),
        "e01_sma_plug": box(20.0, 18.0, 11.5, 116.0, -37.0, 0.0),
        "e07_sma_body": box(17.0, 14.0, 12.0, -14.0, -51.0, -4.0),
    }

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    freecad_version = ".".join(FreeCAD.Version()[:3])

    checks = {
        "design": manifest["design"],
        "freecad_version": freecad_version,
        "input_sha256": {
            "pcba_step": hashlib.sha256(PCBA_STEP.read_bytes()).hexdigest(),
            "oled_step": hashlib.sha256(OLED_STEP.read_bytes()).hexdigest(),
        },
        "base_bbox_mm": [
            base.BoundBox.XMin, base.BoundBox.XMax,
            base.BoundBox.YMin, base.BoundBox.YMax,
            base.BoundBox.ZMin, base.BoundBox.ZMax,
        ],
        "lid_bbox_mm": [
            lid.BoundBox.XMin, lid.BoundBox.XMax,
            lid.BoundBox.YMin, lid.BoundBox.YMax,
            lid.BoundBox.ZMin, lid.BoundBox.ZMax,
        ],
        "base_valid": base.isValid() and not base.isNull(),
        "lid_valid": lid.isValid() and not lid.isNull(),
        "button_valid": button_source.isValid() and not button_source.isNull(),
        "screw_valid": screw_source.isValid() and not screw_source.isNull(),
        "nut_valid": nut_source.isValid() and not nut_source.isNull(),
        "pcba_base_collision_mm3": intersection_volume(pcba, base),
        "pcba_lid_collision_mm3": intersection_volume(pcba, lid),
        "pcba_oled_collision_mm3": intersection_volume(pcba, oled),
        "oled_lid_collision_mm3": intersection_volume(oled, lid),
        "pcba_button_collision_mm3": sum(intersection_volume(pcba, item) for item in buttons),
        "pressed_button_switch_contact_mm3": [
            intersection_volume(pcba, item) for item in pressed_buttons
        ],
        "pressed_button_lid_collision_mm3": sum(
            intersection_volume(lid, item) for item in pressed_buttons
        ),
        "base_lid_collision_mm3": intersection_volume(base, lid),
        "fastener_case_collision_mm3": sum(
            intersection_volume(screw, base) + intersection_volume(screw, lid)
            + intersection_volume(nut, base) + intersection_volume(nut, lid)
            for screw, nut in zip(screws, nuts)
        ),
        "fastener_pcba_collision_mm3": sum(
            intersection_volume(screw, pcba) + intersection_volume(nut, pcba)
            for screw, nut in zip(screws, nuts)
        ),
        "service_envelope_collision_mm3": {
            name: intersection_volume(envelope, base) + intersection_volume(envelope, lid)
            for name, envelope in service_envelopes.items()
        },
        "pcba_bbox_mm": [
            pcba.BoundBox.XMin,
            pcba.BoundBox.XMax,
            pcba.BoundBox.YMin,
            pcba.BoundBox.YMax,
            pcba.BoundBox.ZMin,
            pcba.BoundBox.ZMax,
        ],
        "lid_ceiling_clearance_mm": 12.5 - pcba.BoundBox.ZMax,
        "board_edge_clearance_mm": 1.5,
        "base_lid_fit_clearance_mm": 0.3,
        "oled_lateral_clearance_mm": 0.2,
        "oled_vertical_clearance_mm": 0.1,
        "button_press_to_switch_mm": 0.65,
        "fastener_specification": {
            "screw": "DIN 912 M3 x 20",
            "screw_head_clearance_mm": 0.35,
            "nut": "DIN 934 M3",
            "nut_across_flats_clearance_mm": 0.3,
        },
    }

    tolerance = 1e-4
    failures = []
    for key in ("base_valid", "lid_valid", "button_valid", "screw_valid", "nut_valid"):
        if not checks[key]:
            failures.append(key)
    for key in (
        "pcba_base_collision_mm3",
        "pcba_lid_collision_mm3",
        "pcba_oled_collision_mm3",
        "oled_lid_collision_mm3",
        "pcba_button_collision_mm3",
        "pressed_button_lid_collision_mm3",
        "base_lid_collision_mm3",
        "fastener_case_collision_mm3",
        "fastener_pcba_collision_mm3",
    ):
        if float(checks[key]) > tolerance:
            failures.append(key)
    for key, volume in checks["service_envelope_collision_mm3"].items():
        if float(volume) > tolerance:
            failures.append(f"service:{key}")
    if any(float(volume) <= tolerance for volume in checks["pressed_button_switch_contact_mm3"]):
        failures.append("pressed_button_switch_contact_mm3")
    if float(checks["lid_ceiling_clearance_mm"]) < 1.5:
        failures.append("lid_ceiling_clearance_mm")
    checks["status"] = "PASS" if not failures else "FAIL"
    checks["failures"] = failures

    export_step("skysweep32_rev_c_base.step", [("Base", base)])
    export_step("skysweep32_rev_c_lid.step", [("Lid", lid)])
    export_step("skysweep32_rev_c_button.step", [("Button", button_source)])
    export_stl("skysweep32_rev_c_base.stl", base)
    export_stl("skysweep32_rev_c_lid.stl", lid)
    export_stl("skysweep32_rev_c_button.stl", button_source)

    closed = [("Base", base), ("PCBA", pcba), ("OLED", oled), ("Lid", lid)]
    closed += [(f"Button_{index}", shape) for index, shape in enumerate(buttons, 1)]
    closed += [(f"Screw_{index}", shape) for index, shape in enumerate(screws, 1)]
    closed += [(f"Nut_{index}", shape) for index, shape in enumerate(nuts, 1)]
    export_step("skysweep32_rev_c_closed_assembly.step", closed)

    open_lid = placed(lid, 0.0, 0.0, 30.0)
    open_oled = placed(oled, 0.0, 0.0, 30.0)
    open_buttons = [placed(shape, 0.0, 0.0, 30.0) for shape in buttons]
    opened = [("Base", base), ("PCBA", pcba), ("OLED_in_lid", open_oled), ("Lid", open_lid)]
    opened += [(f"Button_{index}", shape) for index, shape in enumerate(open_buttons, 1)]
    opened += [(f"Nut_{index}", shape) for index, shape in enumerate(nuts, 1)]
    export_step("skysweep32_rev_c_open_assembly.step", opened)

    exploded_pcba = placed(pcba, 0.0, 0.0, 12.0)
    exploded_oled = placed(oled, 0.0, 0.0, 42.0)
    exploded_lid = placed(lid, 0.0, 0.0, 58.0)
    exploded_buttons = [placed(shape, 0.0, 0.0, 76.0) for shape in buttons]
    exploded = [("Base", base), ("PCBA", exploded_pcba), ("OLED", exploded_oled), ("Lid", exploded_lid)]
    exploded += [(f"Button_{index}", shape) for index, shape in enumerate(exploded_buttons, 1)]
    exploded_screws = [placed(shape, 0.0, 0.0, 90.0) for shape in screws]
    exploded_nuts = [placed(shape, 0.0, 0.0, -10.0) for shape in nuts]
    exploded += [(f"Screw_{index}", shape) for index, shape in enumerate(exploded_screws, 1)]
    exploded += [(f"Nut_{index}", shape) for index, shape in enumerate(exploded_nuts, 1)]
    export_step("skysweep32_rev_c_exploded.step", exploded)

    cut_tool = box(140.0, 50.0, 100.0, -10.0, -40.0, -10.0)
    cutaway = [
        ("Base_section", base.cut(cut_tool)),
        ("PCBA_section", pcba.cut(cut_tool)),
        ("OLED_section", oled.cut(cut_tool)),
        ("Lid_section", lid.cut(cut_tool)),
    ]
    export_step("skysweep32_rev_c_cutaway.step", cutaway)

    report = OUT / "mechanical_validation.json"
    report.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))
    if failures:
        raise SystemExit(f"mechanical validation failed: {', '.join(failures)}")
    return checks


if __name__ == "__main__":
    generate()
