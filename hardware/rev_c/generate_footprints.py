#!/usr/bin/env python3
"""Generate reviewed custom footprints for exact Rev C modules."""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE / "SkySweep32RevC.pretty"


def header(name: str, description: str, attr: str) -> list[str]:
    return [
        f'(footprint "{name}"',
        '  (version 20260206)',
        '  (generator "pcbnew")',
        '  (generator_version "10.0")',
        '  (layer "F.Cu")',
        f'  (descr "{description}")',
        f'  (attr {attr})',
        '  (property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS")',
        '    (effects (font (size 1 1) (thickness 0.15))))',
        '  (property "Value" "" (at 0 3 0) (layer "F.Fab") hide',
        '    (effects (font (size 1 1) (thickness 0.15))))',
    ]


def rect(layer: str, x1: float, y1: float, x2: float, y2: float, width: float, fill: str = "none") -> str:
    return (
        f'  (fp_rect (start {x1:g} {y1:g}) (end {x2:g} {y2:g}) '
        f'(stroke (width {width:g}) (type default)) (fill {fill}) (layer "{layer}"))'
    )


def model(filename: str) -> list[str]:
    return [
        f'  (model "${{KIPRJMOD}}/3dmodels/{filename}"',
        '    (offset (xyz 0 0 0))',
        '    (scale (xyz 1 1 1))',
        '    (rotate (xyz 0 0 0)))',
    ]


def write(name: str, rows: list[str]) -> None:
    (LIB / f"{name}.kicad_mod").write_text("\n".join(rows + [")", ""]), encoding="utf-8")


def generate() -> None:
    LIB.mkdir(parents=True, exist_ok=True)

    # E01-ML01DP5: 18.0 x 33.4 mm PCB, single 1x8 2.54 mm row.
    # The courtyard includes the edge SMA body documented by Ebyte.
    name = "Module_Ebyte_E01_ML01DP5"
    rows = header(name, "Ebyte E01-ML01DP5 nRF24L01P PA/LNA module; Ebyte mechanical drawing", "through_hole")
    rows += [
        rect("F.SilkS", -9, -16.7, 9, 16.7, 0.25),
        rect("F.CrtYd", -9.5, -17.2, 13.5, 17.2, 0.05),
        rect("F.Fab", -9, -16.7, 9, 16.7, 0.1),
        rect("F.Fab", 5, -7, 13, 7, 0.1),
        '  (fp_text user "SMA OVERHANG" (at 9 0 90) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
    ]
    for pin in range(1, 9):
        shape = "rect" if pin == 1 else "circle"
        y = (pin - 4.5) * 2.54
        rows.append(
            f'  (pad "{pin}" thru_hole {shape} (at -7.25 {y:g}) (size 1.8 1.8) '
            '(drill 1) (layers "*.Cu" "*.Mask"))'
        )
    rows += model("Ebyte_E01_ML01DP5_ENVELOPE.step")
    write(name, rows)

    # E07-900M10S: 14 x 20 x 3 mm. Pin numbering is transcribed from
    # E07-900M10S manual section 3; this corrects the inverted Rev B land map.
    name = "Module_Ebyte_E07_900M10S"
    rows = header(name, "Ebyte E07-900M10S CC1101 855-925 MHz; manual section 3 land pattern", "smd")
    rows += [
        rect("F.CrtYd", -7.5, -10.5, 7.5, 10.5, 0.05),
        rect("F.Fab", -7, -10, 7, 10, 0.1),
        '  (fp_text user "IPX" (at -4.5 -7.5) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        '  (fp_text user "1" (at 5.6 -8.8) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
    ]
    right = {1: -9.0, 2: -7.73, 3: -6.46, **{n: -0.09 + (n - 4) * 1.27 for n in range(4, 12)}}
    left = {12: 8.80, **{n: 8.80 - (n - 12) * 1.27 for n in range(13, 20)}, 20: -6.46, 21: -7.73, 22: -9.0}
    for pin, y in right.items():
        rows.append(
            f'  (pad "{pin}" smd roundrect (at 6.75 {y:g}) (size 1.8 0.8) '
            '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2))'
        )
    for pin, y in left.items():
        rows.append(
            f'  (pad "{pin}" smd roundrect (at -6.75 {y:g}) (size 1.8 0.8) '
            '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2))'
        )
    rows += model("Ebyte_E07_900M10S_ENVELOPE.step")
    write(name, rows)

    # SAM-M10Q-00B: official 20-pad LGA land pattern. Pad positions and sizes
    # match UBX-22013293 R03 and SparkFun's open reference implementation.
    name = "Module_UBlox_SAM_M10Q"
    rows = header(name, "u-blox SAM-M10Q-00B; UBX-22013293 R03 land pattern", "smd")
    rows += [
        rect("F.CrtYd", -8.25, -8.25, 8.25, 8.25, 0.05),
        rect("F.Fab", -7.75, -7.75, 7.75, 7.75, 0.1),
        '  (fp_circle (center -8.8 4.8) (end -8.4 4.8) (stroke (width 0.2) (type default)) (fill none) (layer "F.Fab"))',
        '  (fp_text user "RF/COPPER KEEPOUT 11x11" (at 0 0 90) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
    ]
    positions = {
        1: (-7.125, 3.8, 0), 2: (-7.125, 1.9, 0), 3: (-7.125, 0, 0),
        4: (-7.125, -1.9, 0), 5: (-7.125, -3.8, 0),
        6: (-3.8, -7.125, 90), 7: (-1.9, -7.125, 90), 8: (0, -7.125, 90),
        9: (1.9, -7.125, 90), 10: (3.8, -7.125, 90),
        11: (7.125, -3.8, 0), 12: (7.125, -1.9, 0), 13: (7.125, 0, 0),
        14: (7.125, 1.9, 0), 15: (7.125, 3.8, 0),
        16: (3.8, 7.125, 90), 17: (1.9, 7.125, 90), 18: (0, 7.125, 90),
        19: (-1.9, 7.125, 90), 20: (-3.8, 7.125, 90),
    }
    for pin, (x, y, rotation) in positions.items():
        shape = "rect" if pin == 1 else "roundrect"
        rr = "" if pin == 1 else " (roundrect_rratio 0.15)"
        rows.append(
            f'  (pad "{pin}" smd {shape} (at {x:g} {y:g} {rotation}) (size 2.75 1.6) '
            f'(layers "F.Cu" "F.Paste" "F.Mask"){rr})'
        )
    rows += model("UBlox_SAM_M10Q_ENVELOPE.step")
    rows += [
        '  (zone (layers "F.Cu" "B.Cu" "In1.Cu" "In2.Cu") (hatch full 0.508)',
        '    (connect_pads (clearance 0)) (min_thickness 0.254)',
        '    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))',
        '    (fill (thermal_gap 0.508) (thermal_bridge_width 0.508))',
        '    (polygon (pts (xy -5.5 -5.5) (xy 5.5 -5.5) (xy 5.5 5.5) (xy -5.5 5.5))))',
        '  )',
    ]
    write(name, rows)

    # M3 hole with a deliberate 10 mm courtyard representing screw head,
    # washer, tool and enclosure-boss clearance rather than only drill copper.
    name = "MountingHole_M3_5mm_Keepout"
    rows = header(name, "M3 NPTH with 5 mm radial fastener and boss keepout", "exclude_from_pos_files exclude_from_bom")
    rows += [
        '  (fp_circle (center 0 0) (end 2.2 0) (stroke (width 0.25) (type default)) (fill none) (layer "F.SilkS"))',
        '  (fp_circle (center 0 0) (end 5 0) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
        '  (fp_circle (center 0 0) (end 1.6 0) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
        '  (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))',
    ]
    write(name, rows)

    name = "Buzzer_CUI_CMT_1203_SMT_TR"
    rows = header(name, "CUI Devices CMT-1203-SMT-TR 12 x 12 mm magnetic transducer", "smd")
    rows += [
        '  (fp_circle (center 0 0) (end 6 0) (stroke (width 0.25) (type default)) (fill none) (layer "F.SilkS"))',
        rect("F.CrtYd", -6.5, -6.5, 6.5, 6.5, 0.05),
        '  (fp_circle (center 0 0) (end 6 0) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
        '  (pad "1" smd rect (at -4.5 0) (size 2.2 3.0) (layers "F.Cu" "F.Paste" "F.Mask"))',
        '  (pad "2" smd roundrect (at 4.5 0) (size 2.2 3.0) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2))',
    ]
    rows += model("CUI_CMT_1203_SMT_TR_ENVELOPE.step")
    write(name, rows)

    print(f"[OK] Wrote custom footprint library: {LIB}")


if __name__ == "__main__":
    generate()
