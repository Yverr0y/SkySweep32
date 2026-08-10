#!/usr/bin/env python3
"""Generate the native KiCad 10 SkySweep32 Pro Rev B carrier-board baseline.

Run with the Python bundled with KiCad 10. The script exports the authoritative
schematic netlist, writes the project footprint library, places every component,
and emits a four-layer `.kicad_pcb`. Routing is completed from the emitted DSN
and checked in as the manufacturing source; use `--base-only` to regenerate the
pre-route baseline intentionally.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PROJECT = HERE / "skysweep32_pro_rev_b.kicad_pro"
SCHEMATIC = HERE / "skysweep32_pro_rev_b.kicad_sch"
NETLIST = HERE / "skysweep32_pro_rev_b.xml"
BOARD = HERE / "skysweep32_pro_rev_b.kicad_pcb"
BASE_BOARD = HERE / "skysweep32_pro_rev_b_base.kicad_pcb"
FP_LIB = HERE / "SkySweep32.pretty"
MODEL_DIR = HERE / "3dmodels"
KICAD_ROOT = Path(sys.executable).resolve().parent.parent
KICAD_CLI = Path(sys.executable).with_name("kicad-cli.exe")
SYSTEM_FP = KICAD_ROOT / "share" / "kicad" / "footprints"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def v(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def fp_header(name: str, description: str) -> list[str]:
    return [
        f'(footprint "{name}"',
        '  (version 20240108)',
        '  (generator pcbnew)',
        '  (layer "F.Cu")',
        f'  (descr "{description}")',
        '  (attr through_hole)',
        '  (property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS")',
        '    (effects (font (size 1 1) (thickness 0.15))))',
        '  (property "Value" "" (at 0 3 0) (layer "F.Fab") hide',
        '    (effects (font (size 1 1) (thickness 0.15))))',
    ]


def rect_lines(w: float, h: float, courtyard: float = 0.5) -> list[str]:
    x, y = w / 2, h / 2
    c = courtyard
    return [
        f'  (fp_rect (start {-x:g} {-y:g}) (end {x:g} {y:g})',
        '    (stroke (width 0.25) (type default)) (fill none) (layer "F.SilkS"))',
        f'  (fp_rect (start {-x-c:g} {-y-c:g}) (end {x+c:g} {y+c:g})',
        '    (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
        f'  (fp_rect (start {-x:g} {-y:g}) (end {x:g} {y:g})',
        '    (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
    ]


def tht_pad(number: str, x: float, y: float, pin1: bool = False) -> str:
    shape = "rect" if pin1 else "circle"
    return (f'  (pad "{number}" thru_hole {shape} (at {x:g} {y:g}) '
            '(size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask"))')


def smd_pad(number: str, x: float, y: float, sx: float = 1.8, sy: float = 0.8) -> str:
    return (f'  (pad "{number}" smd roundrect (at {x:g} {y:g}) '
            f'(size {sx:g} {sy:g}) (layers "F.Cu" "F.Paste" "F.Mask") '
            '(roundrect_rratio 0.2))')


def model_line(filename: str, z_offset: float = 0.0) -> list[str]:
    return [
        f'  (model "${{KIPRJMOD}}/3dmodels/{filename}"',
        f'    (offset (xyz 0 0 {z_offset:g}))',
        '    (scale (xyz 1 1 1))',
        '    (rotate (xyz 0 0 0)))',
    ]


def write_footprint(name: str, lines: list[str]) -> None:
    (FP_LIB / f"{name}.kicad_mod").write_text("\n".join(lines + [")", ""]), encoding="utf-8")


def write_custom_footprints() -> None:
    FP_LIB.mkdir(parents=True, exist_ok=True)

    # E01-ML01DP5: official 18 x 33.4 mm module with one 1x8, 2.54 mm row.
    name = "Module_Ebyte_E01_ML01DP5"
    rows = fp_header(name, "Ebyte E01-ML01DP5 nRF24L01P PA/LNA SMA module")
    rows += rect_lines(18, 33.4)
    rows += ['  (fp_rect (start 5 -7) (end 13 7) (stroke (width 0.2) (type default)) (fill none) (layer "F.Fab"))']
    for pin in range(1, 9):
        rows.append(tht_pad(str(pin), -7.25, (pin - 4.5) * 2.54, pin == 1))
    rows += model_line("Ebyte_E01_ML01DP5.step")
    write_footprint(name, rows)

    # E07-900M10S: official 14 x 20 mm, 22 castellated pads at 1.27 mm.
    name = "Module_Ebyte_E07_900M10S"
    rows = fp_header(name, "Ebyte E07-900M10S CC1101 855-925 MHz castellated module")
    rows[5] = '  (attr smd)'
    rows += rect_lines(14, 20)
    ys_right = {1: 9.0, 2: 7.73, 3: 6.46, **{n: 0.09 - (n - 4) * 1.27 for n in range(4, 12)}}
    ys_left = {12: -8.80, **{n: -8.80 + (n - 12) * 1.27 for n in range(13, 20)}, 20: 6.46, 21: 7.73, 22: 9.0}
    for pin, y in ys_right.items():
        rows.append(smd_pad(str(pin), 6.75, y))
    for pin, y in ys_left.items():
        rows.append(smd_pad(str(pin), -6.75, y))
    rows += model_line("Ebyte_E07_900M10S.step")
    write_footprint(name, rows)

    def header_module(name: str, description: str, w: float, h: float,
                      pins: list[tuple[str, float, float]], model: str,
                      holes: list[tuple[float, float, float]] = []) -> None:
        rows = fp_header(name, description) + rect_lines(w, h)
        for number, x, y in pins:
            rows.append(tht_pad(number, x, y, number == "1"))
        for x, y, drill in holes:
            rows.append(f'  (pad "" np_thru_hole circle (at {x:g} {y:g}) (size {drill:g} {drill:g}) (drill {drill:g}) (layers "*.Cu" "*.Mask"))')
        rows += model_line(model)
        write_footprint(name, rows)

    # Adafruit PID 3072 is 29 x 25 mm. Nine used nets occupy the documented
    # header positions; the remaining breakout holes are retained as NC pads.
    rfm_pins = [(str(i + 1), -12.7, -8.89 + i * 2.54) for i in range(8)]
    rfm_pins += [(str(9 + i), 12.7, 8.89 - i * 2.54) for i in range(8)]
    header_module("Module_Adafruit_RFM95W_PID3072", "Adafruit PID 3072 RFM95W breakout",
                  29, 25, rfm_pins, "Adafruit_RFM95W_PID3072.step")

    # RX5808 remains a controlled reference envelope until a purchased lot is
    # qualified. Pin row follows the documented 2012 receiver layout.
    rx_pins = [(str(i + 1), -12.7 + i * 2.54, 9.0) for i in range(8)]
    header_module("Module_RX5808_2012_QUALIFIED", "RX5808 2012 qualified-lot reference envelope",
                  28, 23, rx_pins, "RX5808_2012_REFERENCE_ENVELOPE.step")

    gps_pins = [(str(i + 1), -10.16 + i * 2.54, 10.2) for i in range(9)]
    header_module("Module_Adafruit_GPS_PID746", "Adafruit Ultimate GPS v3 PID 746",
                  35, 25.5, gps_pins, "Adafruit_GPS_PID746.step",
                  [(-15.25, -10.0, 2.5), (15.25, -10.0, 2.5)])

    sd_pins = [(str(i + 1), -7.62 + i * 2.54, 10.5) for i in range(7)]
    header_module("Module_Adafruit_MicroSD_PID254", "Adafruit microSD breakout PID 254",
                  31.85, 25.4, sd_pins, "Adafruit_MicroSD_PID254.step",
                  [(-13.5, -10.0, 2.5), (13.5, -10.0, 2.5)])

    name = "Buzzer_CUI_CMT-1203-SMT-TR"
    rows = fp_header(name, "CUI Devices CMT-1203-SMT-TR magnetic transducer")
    rows[5] = '  (attr smd)'
    rows += rect_lines(12, 12)
    rows += [smd_pad("1", -4.5, 0, 2.2, 3.0), smd_pad("2", 4.5, 0, 2.2, 3.0)]
    rows += model_line("CUI_CMT_1203_SMT_TR.step")
    write_footprint(name, rows)


def export_netlist() -> None:
    if not KICAD_CLI.exists():
        raise FileNotFoundError(f"KiCad CLI not found beside interpreter: {KICAD_CLI}")
    subprocess.run([
        str(KICAD_CLI), "sch", "export", "netlist", str(SCHEMATIC),
        "--format", "kicadxml", "-o", str(NETLIST),
    ], check=True)


def parse_netlist() -> tuple[list[dict[str, str]], list[tuple[str, list[tuple[str, str]]]]]:
    root = ET.parse(NETLIST).getroot()
    components: list[dict[str, str]] = []
    for node in root.find("components"):
        fields = {f.attrib["name"]: (f.text or "") for f in node.findall("./fields/field")}
        components.append({
            "ref": node.attrib["ref"],
            "value": node.findtext("value") or "",
            "footprint": node.findtext("footprint") or "",
            "mpn": fields.get("MPN", ""),
            "manufacturer": fields.get("Manufacturer", ""),
        })
    nets: list[tuple[str, list[tuple[str, str]]]] = []
    for node in root.find("nets"):
        members = [(p.attrib["ref"], p.attrib["pin"]) for p in node.findall("node")]
        nets.append((node.attrib["name"].removeprefix("/"), members))
    return components, nets

def is_unconnected_net(name: str) -> bool:
    return name.startswith("unconnected-(")


def validate_critical_module_nets(
    nets: list[tuple[str, list[tuple[str, str]]]],
) -> None:
    actual: dict[tuple[str, str], str] = {}
    for name, members in nets:
        for member in members:
            if member in actual:
                raise ValueError(f"Pin {member} appears in more than one exported net")
            actual[member] = name
    contracts = {
        "J2": {
            "1": "GND", "2": "3V3_NRF", "3": "NRF24_CE", "4": "NRF24_CSN",
            "5": "RF_SPI_SCK", "6": "RF_SPI_MOSI", "7": "RF_SPI_MISO",
            "8": "NRF24_IRQ_TP",
        },
        "J3": {
            "1": "GND", "2": "GND", "3": "GND", "4": "GND", "5": "GND",
            "6": None, "7": None, "8": None, "9": "3V3_CC", "10": None,
            "11": "GND", "12": "GND", "13": None, "14": "CC1101_GDO2_TP",
            "15": "CC1101_GDO0_TP", "16": "RF_SPI_MISO",
            "17": "RF_SPI_MOSI", "18": "RF_SPI_SCK", "19": "CC1101_CSN",
            "20": "GND", "21": None, "22": "GND",
        },
    }
    for ref, pins in contracts.items():
        for pin, expected in pins.items():
            observed = actual.get((ref, pin))
            valid = is_unconnected_net(observed or "") if expected is None else observed == expected
            if not valid:
                raise ValueError(
                    f"{ref} pad {pin}: exported net {observed!r}, expected {expected!r}"
                )


def assert_board_net_contract(
    board: pcbnew.BOARD,
    member_net_names: dict[tuple[str, str], str],
) -> None:
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for (ref, pin), expected in member_net_names.items():
        fp = footprints.get(ref)
        if fp is None:
            raise ValueError(f"Board is missing netlisted footprint {ref}")
        pads = [pad for pad in fp.Pads() if pad.GetNumber() == pin]
        if not pads:
            raise ValueError(f"{ref} footprint has no pad {pin}")
        for pad in pads:
            if pad.GetNetname() != expected:
                raise ValueError(
                    f"{ref} pad {pin}: saved PCB net {pad.GetNetname()!r}, "
                    f"expected {expected!r}"
                )


def load_footprint(identifier: str) -> pcbnew.FOOTPRINT:
    library, name = identifier.split(":", 1)
    root = FP_LIB if library == "SkySweep32" else SYSTEM_FP / f"{library}.pretty"
    fp = pcbnew.FootprintLoad(str(root), name)
    if fp is None:
        raise FileNotFoundError(f"Footprint {identifier} not found in {root}")
    return fp


def natural_ref(ref: str) -> tuple[str, int]:
    match = re.fullmatch(r"([^0-9]+)([0-9]+)", ref)
    return (match.group(1), int(match.group(2))) if match else (ref, 0)


MAJOR_PLACEMENT: dict[str, tuple[float, float, float]] = {
    "J1": (23, 16, 180),
    "U4": (34, 16, 0),
    "F1": (15, 23, 0),
    "D1": (15, 27, 90),
    "U2": (23, 26, 0),
    "U3": (44, 20, 0),
    "L1": (53, 20, 0),
    "D5": (47, 27, 0),
    "D6": (53, 27, 0),
    "J8": (55, 14, 0),
    "J9": (70, 14, 0),
    "J6": (94, 23, 0),
    "J2": (118, 28, 0),
    "J3": (19.5, 48, 0),
    "U1": (60, 58, 180),
    "J7": (19.5, 68, 0),
    "J10": (13, 65, 90),
    "SW1": (18, 85, 0),
    "SW2": (24, 85, 0),
    "SW3": (30, 85, 0),
    "J4": (100, 74, 0),
    "J5": (116, 50, 0),
    "BZ1": (120, 68, 0),
    "J11": (120, 78, 270),
}


def generated_placement(ref: str) -> tuple[float, float, float]:
    prefix, number = natural_ref(ref)
    if prefix == "C":
        power_caps = {
            1: (15, 34), 2: (20, 34), 3: (18, 30), 4: (24, 30),
            5: (32, 26), 6: (25, 34), 7: (30, 34), 8: (35, 34), 9: (15, 14),
        }
        if number in power_caps:
            x, y = power_caps[number]
            return (x, y, 0)
        local = {
            10: (104, 15), 11: (104, 20), 13: (31, 44), 14: (31, 49),
            16: (94, 62), 17: (94, 64), 19: (94, 45), 20: (94, 50),
            22: (94, 59), 23: (98, 59), 25: (99, 64), 26: (104, 64),
            28: (31, 64), 29: (31, 69), 30: (94, 55), 31: (30, 78),
        }
        x, y = local[number]
        return (x, y, 0)
    if prefix == "FB":
        spots = {1: (40, 18), 2: (48, 18), 3: (104, 25), 4: (31, 54), 5: (94, 38), 6: (109, 64)}
        return (*spots[number], 0)
    if prefix == "R":
        power_res = {
            1: (19, 11), 2: (27, 11), 3: (15, 18), 4: (30, 20), 5: (34, 20),
            6: (21, 28), 7: (28, 28), 8: (31, 34), 9: (34, 28), 10: (37, 28),
            11: (39.8, 41), 12: (43.6, 41), 13: (47.4, 41),
        }
        if number in power_res:
            x, y = power_res[number]
            return (x, y, 0)
        module_res = {
            14: (51.2, 41), 15: (98, 45), 16: (58, 20), 17: (72, 20),
            18: (55.0, 41), 19: (58.8, 41), 20: (62.6, 41), 21: (66.4, 41),
            22: (70.2, 41), 23: (74.0, 41), 24: (24, 42), 25: (94, 86),
            26: (94, 84), 27: (99, 84), 28: (104, 84), 29: (77.8, 41),
            30: (81.6, 41), 31: (85.4, 41), 32: (33, 76), 33: (33, 80),
            34: (30, 84), 35: (120, 62), 36: (120, 65), 37: (120, 73),
            38: (120, 76), 39: (89.2, 41), 40: (93.0, 41),
        }
        x, y = module_res[number]
        return (x, y, 0)
    if prefix in {"Q", "D"}:
        trans = {
            "Q1": (120, 64, 0), "Q2": (120, 74, 0),
            "D2": (37, 27, 0), "D3": (29, 23, 0), "D4": (29, 24, 0),
        }
        return trans[ref]
    if prefix == "TP":
        # Two diagnostic testpoint rows placed in tiers at Y=29 and Y=33, clear of resistors at Y=37 and MCU pins at Y=45.5
        # Two diagnostic testpoint rows placed in tiers at Y=31 and Y=36, clear of all components
        if number <= 12:
            return (36 + (number - 1) * 3.2, 31.0, 0)
        return (36 + (number - 13) * 3.2, 36.0, 0)
def add_outline(board: pcbnew.BOARD) -> None:
    x0, y0, x1, y1, radius = 10.0, 10.0, 130.0, 90.0, 4.0
    segments = [
        ((x0 + radius, y0), (x1 - radius, y0)),
        ((x1, y0 + radius), (x1, y1 - radius)),
        ((x1 - radius, y1), (x0 + radius, y1)),
        ((x0, y1 - radius), (x0, y0 + radius)),
    ]
    for start, end in segments:
        shape = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetStart(v(*start)); shape.SetEnd(v(*end)); shape.SetWidth(mm(0.1))
        board.Add(shape)
    arcs = [
        ((x1 - radius, y0), (x1 - 1.172, y0 + 1.172), (x1, y0 + radius)),
        ((x1, y1 - radius), (x1 - 1.172, y1 - 1.172), (x1 - radius, y1)),
        ((x0 + radius, y1), (x0 + 1.172, y1 - 1.172), (x0, y1 - radius)),
        ((x0, y0 + radius), (x0 + 1.172, y0 + 1.172), (x0 + radius, y0)),
    ]
    for start, mid, end in arcs:
        shape = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetArcGeometry(v(*start), v(*mid), v(*end)); shape.SetWidth(mm(0.1))
        board.Add(shape)


def add_mounting_hole(board: pcbnew.BOARD, ref: str, x: float, y: float) -> None:
    fp = load_footprint("MountingHole:MountingHole_3.2mm_M3")
    fp.SetReference(ref); fp.SetValue("M3 NPTH")
    fp.SetPosition(v(x, y)); board.Add(fp)
def add_board_text(board: pcbnew.BOARD, text: str, x: float, y: float,
                   size: float = 1.2, layer: int = pcbnew.F_SilkS) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text); item.SetPosition(v(x, y)); item.SetLayer(layer)
    item.SetTextSize(v(size, size)); item.SetTextThickness(mm(max(0.15, size * 0.12)))
    board.Add(item)


def configure_netclasses(board: pcbnew.BOARD) -> None:
    settings = board.GetDesignSettings().m_NetSettings
    board.GetDesignSettings().m_MinThroughDrill = mm(0.2)
    default = settings.GetDefaultNetclass()
    default.SetClearance(mm(0.2)); default.SetTrackWidth(mm(0.25))
    default.SetViaDiameter(mm(0.7)); default.SetViaDrill(mm(0.3))
    power = pcbnew.NETCLASS("Power")
    power.SetClearance(mm(0.25)); power.SetTrackWidth(mm(0.8))
    power.SetViaDiameter(mm(0.9)); power.SetViaDrill(mm(0.4))
    settings.SetNetclass("Power", power)
    for pattern in ["VBUS*", "3V3*", "5V_*", "VBAT*"]:
        settings.SetNetclassPatternAssignment(pattern, "Power")
    settings.RecomputeEffectiveNetclasses()


def add_zone(board: pcbnew.BOARD, net_name: str, layer: int,
             points: list[tuple[float, float]], clearance: float = 0.3) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(board.FindNet(net_name))
    zone.SetLocalClearance(mm(clearance))
    zone.SetMinThickness(mm(0.2))
    outline = zone.Outline(); contour = outline.NewOutline()
    for x, y in points:
        outline.Append(v(x, y), contour)
    board.Add(zone)


def generate_board() -> pcbnew.BOARD:
    write_custom_footprints()
    export_netlist()
    components, nets = parse_netlist()
    validate_critical_module_nets(nets)

    board = pcbnew.BOARD()
    board.SetFileName(str(BASE_BOARD))
    board.SetCopperLayerCount(4)
    board.SetLayerName(pcbnew.In1_Cu, "GND_PLANE")
    board.SetLayerName(pcbnew.In2_Cu, "POWER_PLANE")
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_MIXED)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    configure_netclasses(board)
    add_outline(board)

    connected_nets = [(name, members) for name, members in nets if not is_unconnected_net(name)]
    net_objects: dict[str, pcbnew.NETINFO_ITEM] = {}
    for code, (name, _members) in enumerate(connected_nets, 1):
        net = pcbnew.NETINFO_ITEM(board, name, code)
        board.Add(net); net_objects[name] = net

    member_net: dict[tuple[str, str], pcbnew.NETINFO_ITEM] = {}
    member_net_names: dict[tuple[str, str], str] = {}
    for name, members in connected_nets:
        for member in members:
            member_net[member] = net_objects[name]
            member_net_names[member] = name

    footprints: dict[str, pcbnew.FOOTPRINT] = {}
    for component in sorted(components, key=lambda c: natural_ref(c["ref"])):
        ref = component["ref"]
        fp = load_footprint(component["footprint"])
        fp.SetReference(ref); fp.SetValue(component["value"])
        fp.SetFPIDAsString(component["footprint"])
        x, y, angle = MAJOR_PLACEMENT[ref] if ref in MAJOR_PLACEMENT else generated_placement(ref)
        fp.SetPosition(v(x, y)); fp.SetOrientationDegrees(angle)
        prefix, _ = natural_ref(ref)
        if prefix in {"C", "R", "FB"} or ref in {"D2", "D3", "D4"}:
            fp.Reference().SetVisible(False)
        else:
            fp.Reference().SetVisible(True)
            fp.Reference().SetTextSize(v(0.8, 0.8))
            fp.Reference().SetTextThickness(mm(0.12))
        for pad in fp.Pads():
            net = member_net.get((ref, pad.GetNumber()))
            if net is not None:
                pad.SetNet(net)
        board.Add(fp); footprints[ref] = fp

    for index, (x, y) in enumerate([(15, 15), (125, 15), (125, 85), (15, 85)], 1):
        add_mounting_hole(board, f"H{index}", x, y)

    add_board_text(board, "SkySweep32 Pro Rev B", 70, 87, 1.5)
    add_board_text(board, "DESIGN IN PROGRESS - DO NOT ORDER", 70, 12, 1.1)
    add_board_text(board, "SUB-G", 12, 58, 1.0)
    add_board_text(board, "2.4G", 124, 48, 1.0)
    add_board_text(board, "5.8G", 124, 60, 1.0)
    add_board_text(board, "LORA", 104, 88, 1.0)
    add_board_text(board, "GPL-3.0-only | github.com/bobberdolle1/SkySweep32", 70, 88.5, 0.8, pcbnew.B_SilkS)

    # Plane intents are part of the native board: uninterrupted ground on L2,
    # split low-frequency distribution on L3, and ground pours on both exteriors.
    perimeter = [(10.6, 10.6), (129.4, 10.6), (129.4, 89.4), (10.6, 89.4)]
    add_zone(board, "GND", pcbnew.In1_Cu, perimeter)
    add_zone(board, "3V3_MAIN", pcbnew.In2_Cu, [(30, 11), (129, 11), (129, 89), (30, 89)])
    add_zone(board, "VBUS_PROTECTED", pcbnew.In2_Cu, [(11, 11), (29, 11), (29, 89), (11, 89)])
    add_zone(board, "GND", pcbnew.F_Cu, perimeter)
    add_zone(board, "GND", pcbnew.B_Cu, perimeter)

    assert_board_net_contract(board, member_net_names)
    pcbnew.SaveBoard(str(BASE_BOARD), board)
    reloaded = pcbnew.LoadBoard(str(BASE_BOARD))
    assert_board_net_contract(reloaded, member_net_names)
    return board


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-only", action="store_true", help="write only the unrouted board baseline")
    args = parser.parse_args()
    board = generate_board()
    if args.base_only:
        print(f"[OK] Wrote unrouted base: {BASE_BOARD}")
        return 0
    # The generated baseline is copied to the canonical output. A routed SES can
    # then be imported with pcbnew.ImportSpecctraSES and the result saved there.
    pcbnew.SaveBoard(str(BOARD), board)
    print(f"[OK] Wrote native board baseline: {BOARD}")
    print(f"[INFO] Components: {len(board.GetFootprints())}; nets: {board.GetNetCount()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
