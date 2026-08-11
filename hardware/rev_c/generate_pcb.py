#!/usr/bin/env python3
"""Generate the placed four-layer SkySweep32 Rev C PCB from the KiCad netlist."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from tool_discovery import discover_kicad_cli, discover_kicad_root

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

KICAD_ROOT = discover_kicad_root()
KICAD_BIN = KICAD_ROOT / "bin"
if os.name == "nt":
    os.add_dll_directory(str(KICAD_BIN))
sys.path.insert(0, str(KICAD_BIN / "Lib" / "site-packages"))

import pcbnew  # noqa: E402

SCHEMATIC = HERE / "skysweep32_rev_c.kicad_sch"
NETLIST = HERE / "skysweep32_rev_c.net"
BOARD = HERE / "skysweep32_rev_c.kicad_pcb"
BASE_BOARD = HERE / "skysweep32_rev_c_placed.kicad_pcb"
FP_LIB = HERE / "SkySweep32RevC.pretty"
SYSTEM_FP = KICAD_ROOT / "share" / "kicad" / "footprints"
KICAD_CLI = discover_kicad_cli(KICAD_ROOT)
STACKUP = """		(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Green") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "prepreg") (thickness 0.18)
				(material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 2" (type "core") (thickness 1.1)
				(material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 3" (type "prepreg") (thickness 0.18)
				(material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Green") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "ENIG")
			(dielectric_constraints yes)
		)
"""




def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))
def inject_stackup(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "\n\t\t(stackup\n" not in text:
        text = text.replace("\n\t(setup\n", f"\n\t(setup\n{STACKUP}", 1)
        path.write_text(text, encoding="utf-8")




def export_netlist() -> None:
    subprocess.run(
        [str(KICAD_CLI), "sch", "export", "netlist", str(SCHEMATIC), "--format", "kicadxml", "-o", str(NETLIST)],
        cwd=HERE,
        check=True,
    )


def parse_netlist() -> tuple[list[dict[str, str]], list[tuple[str, list[tuple[str, str]]]]]:
    root = ET.parse(NETLIST).getroot()
    components: list[dict[str, str]] = []
    for node in root.find("components"):
        fields = {field.attrib["name"]: (field.text or "") for field in node.findall("./fields/field")}
        components.append(
            {
                "ref": node.attrib["ref"],
                "value": node.findtext("value") or "",
                "footprint": node.findtext("footprint") or "",
                "mpn": fields.get("MPN", ""),
                "manufacturer": fields.get("Manufacturer", ""),
                "dnp": fields.get("DNP", "").lower(),
            }
        )
    nets: list[tuple[str, list[tuple[str, str]]]] = []
    for node in root.find("nets"):
        nets.append(
            (
                node.attrib["name"].removeprefix("/"),
                [(pin.attrib["ref"], pin.attrib["pin"]) for pin in node.findall("node")],
            )
        )
    return components, nets


def load_footprint(identifier: str) -> pcbnew.FOOTPRINT:
    library, name = identifier.split(":", 1)
    root = FP_LIB if library == "SkySweep32RevC" else SYSTEM_FP / f"{library}.pretty"
    footprint = pcbnew.FootprintLoad(str(root), name)
    if footprint is None:
        raise FileNotFoundError(f"Footprint {identifier} not found in {root}")
    return footprint
def replace_3d_model(footprint: pcbnew.FOOTPRINT, filename: str) -> None:
    footprint.Models().clear()
    model = pcbnew.FP_3DMODEL()
    model.m_Filename = f"${{KIPRJMOD}}/3dmodels/{filename}"
    footprint.Add3DModel(model)


MODEL_OVERRIDES = {
    "J2": "Molex_104031_0811_WITH_CARD_ENVELOPE.step",
    "F1": "Bourns_MF_MSMF200_2_ENVELOPE.step",
    "L1": "Bourns_SRN6028_3R9M_ENVELOPE.step",
}




def natural_reference(reference: str) -> tuple[str, int]:
    match = re.fullmatch(r"([^0-9]+)([0-9]+)", reference)
    return (match.group(1), int(match.group(2))) if match else (reference, 0)


# Placement is a reviewed mechanical/electrical input. The board datum is the
# lower-left corner in the top view; pcbnew screen coordinates increase down,
# so the same file coordinates are described as upper-left in plots.
PLACEMENT: dict[str, tuple[float, float, float]] = {
    # Mechanically constrained external/service interfaces.
    "J1": (20.0, 81.325, 0),       # USB-C mouth at bottom board edge
    "J2": (113.0, 59.0, 90),      # microSD insertion through right wall
    "J5": (2.55, 44.27, 180),     # 2.54 mm footprint edge + 0.01 mm fab margin
    "J3": (63.0, 79.0, 0),        # keyed STEMMA QT lid harness
    "J4": (80.0, 69.0, 0),        # optional vibration motor harness
    "SW1": (82.0, 80.0, 0),
    "SW2": (93.0, 80.0, 0),
    "SW3": (104.0, 80.0, 0),
    # RF/GNSS modules fixed before the supporting circuitry.
    "GPS1": (17.0, 19.0, 0),
    "U1": (60.0, 28.0, 0),
    "RF1": (106.0, 28.0, 0),
    "RF2": (15.0, 52.0, 0),
    # Power and USB functional block.
    "R1": (29.0, 78.0, 0),
    "R2": (32.0, 78.0, 0),
    "F1": (33.0, 72.0, 90),
    "D1": (39.0, 76.0, 90),
    "C1": (45.0, 76.0, 0),
    "U2": (32.0, 63.0, 0),
    "R3": (38.0, 61.0, 0),
    "R4": (38.0, 64.0, 0),
    "U3": (47.0, 69.0, 0),
    "L1": (57.0, 69.0, 0),
    "C2": (51.0, 64.0, 0),
    "C3": (64.0, 66.0, 0),
    "C4": (64.0, 72.0, 0),
    # MCU local support and controls.
    "C5": (54.0, 44.0, 0),
    "C6": (58.0, 44.0, 0),
    "R5": (46.0, 47.0, 0),
    "C7": (50.0, 47.0, 0),
    "R6": (93.0, 75.0, 0),
    "R7": (101.0, 75.0, 0),
    # RF module local decoupling.
    "C8": (94.0, 25.0, 0),
    "C9": (94.0, 29.0, 0),
    "C10": (26.0, 48.0, 0),
    "C11": (26.0, 53.0, 0),
    # GNSS support, including optional 0-ohm I2C links.
    "R8": (28.0, 15.0, 0),
    "R9": (28.0, 20.0, 0),
    "R10": (28.0, 25.0, 0),
    "C12": (17.0, 30.0, 0),
    "C13": (22.0, 30.0, 0),
    # microSD pull-ups and local energy storage.
    "R11": (96.0, 51.0, 0),
    "R12": (96.0, 55.0, 0),
    "R13": (96.0, 59.0, 0),
    "R14": (96.0, 63.0, 0),
    "C14": (104.0, 68.0, 0),
    "C15": (109.0, 68.0, 0),
    "C16": (68.0, 72.0, 0),
    # Audible/visual/haptic alert block.
    "BZ1": (79.0, 58.0, 0),
    "Q1": (89.0, 58.0, 0),
    "R15": (89.0, 53.0, 0),
    "R16": (90.0, 62.0, 0),
    "D2": (68.5, 58.0, 0),
    "D3": (71.0, 76.0, 0),
    "R17": (67.0, 76.0, 0),
    "Q2": (94.0, 70.0, 0),
    "R18": (97.0, 66.0, 0),
    "R19": (98.0, 70.0, 0),
    "D4": (74.0, 70.0, 90),
    # Accessible diagnostic pads, not hidden beneath modules or the display.
    "TP1": (68.0, 48.0, 0),
    "TP2": (73.0, 48.0, 0),
    "TP3": (78.0, 48.0, 0),
    "TP4": (83.0, 48.0, 0),
    "TP5": (88.0, 48.0, 0),
}


def configure_board(board: pcbnew.BOARD) -> None:
    board.SetCopperLayerCount(4)
    board.SetLayerName(pcbnew.In1_Cu, "GND_PLANE")
    board.SetLayerName(pcbnew.In2_Cu, "POWER_PLANE")
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_MIXED)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    board.GetDesignSettings().m_MinThroughDrill = mm(0.2)
    board.GetDesignSettings().m_HoleClearance = mm(0.15)

    settings = board.GetDesignSettings().m_NetSettings
    default = settings.GetDefaultNetclass()
    default.SetClearance(mm(0.20))
    default.SetTrackWidth(mm(0.25))
    default.SetViaDiameter(mm(0.70))
    default.SetViaDrill(mm(0.30))

    power = pcbnew.NETCLASS("Power")
    power.SetClearance(mm(0.20))
    power.SetTrackWidth(mm(0.80))
    power.SetViaDiameter(mm(0.90))
    power.SetViaDrill(mm(0.40))
    settings.SetNetclass("Power", power)
    for pattern in ("VBUS*", "3V3", "BUCK_SW", "BUCK_BST"):
        settings.SetNetclassPatternAssignment(pattern, "Power")

    usb = pcbnew.NETCLASS("USB")
    usb.SetClearance(mm(0.20))
    usb.SetTrackWidth(mm(0.25))
    usb.SetViaDiameter(mm(0.70))
    usb.SetViaDrill(mm(0.30))
    usb.SetDiffPairWidth(mm(0.25))
    usb.SetDiffPairGap(mm(0.20))
    settings.SetNetclass("USB", usb)
    for pattern in ("USB_D_P*", "USB_D_N*"):
        settings.SetNetclassPatternAssignment(pattern, "USB")

    rf = pcbnew.NETCLASS("RF_50R")
    rf.SetClearance(mm(0.20))
    rf.SetTrackWidth(mm(0.30))
    rf.SetViaDiameter(mm(0.70))
    rf.SetViaDrill(mm(0.30))
    settings.SetNetclass("RF_50R", rf)
    settings.SetNetclassPatternAssignment("SUBGHZ_ANT", "RF_50R")
    settings.RecomputeEffectiveNetclasses()


def add_outline(board: pcbnew.BOARD) -> None:
    x0, y0, x1, y1, radius = 0.0, 0.0, 120.0, 85.0, 3.0
    for start, end in (
        ((radius, y0), (x1 - radius, y0)),
        ((x1, radius), (x1, y1 - radius)),
        ((x1 - radius, y1), (radius, y1)),
        ((x0, y1 - radius), (x0, radius)),
    ):
        shape = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetStart(point(*start))
        shape.SetEnd(point(*end))
        shape.SetWidth(mm(0.1))
        board.Add(shape)
    for start, mid, end in (
        ((x1 - radius, y0), (x1 - 0.879, y0 + 0.879), (x1, radius)),
        ((x1, y1 - radius), (x1 - 0.879, y1 - 0.879), (x1 - radius, y1)),
        ((radius, y1), (0.879, y1 - 0.879), (x0, y1 - radius)),
        ((x0, radius), (0.879, 0.879), (radius, y0)),
    ):
        shape = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetArcGeometry(point(*start), point(*mid), point(*end))
        shape.SetWidth(mm(0.1))
        board.Add(shape)


def add_text(board: pcbnew.BOARD, text: str, x: float, y: float, size: float = 1.0, layer: int = pcbnew.F_SilkS) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetLayer(layer)
    item.SetTextSize(point(size, size))
    item.SetTextThickness(mm(max(0.15, size * 0.12)))
    if layer == pcbnew.B_SilkS:
        item.SetMirrored(True)
    board.Add(item)


def add_mounting_hole(board: pcbnew.BOARD, reference: str, x: float, y: float) -> None:
    footprint = load_footprint("SkySweep32RevC:MountingHole_M3_5mm_Keepout")
    footprint.SetReference(reference)
    footprint.SetValue("M3 NPTH / 10mm FASTENER KEEPOUT")
    footprint.SetPosition(point(x, y))
    board.Add(footprint)


def add_zone(board: pcbnew.BOARD, net_name: str, layer: int, points: list[tuple[float, float]], clearance: float) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(board.FindNet(net_name))
    zone.SetLocalClearance(mm(clearance))
    zone.SetMinThickness(mm(0.20))
    if layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    else:
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    outline = zone.Outline()
    contour = outline.NewOutline()
    for x, y in points:
        outline.Append(point(x, y), contour)
    board.Add(zone)


def validate_net_contract(board: pcbnew.BOARD, mapping: dict[tuple[str, str], str]) -> None:
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    for (reference, pin), expected in mapping.items():
        footprint = footprints.get(reference)
        if footprint is None:
            raise ValueError(f"Missing footprint {reference}")
        pads = [pad for pad in footprint.Pads() if pad.GetNumber() == pin]
        if not pads:
            raise ValueError(f"{reference} footprint has no pad {pin}")
        for pad in pads:
            if pad.GetNetname() != expected:
                raise ValueError(f"{reference}.{pin} is {pad.GetNetname()!r}, expected {expected!r}")


def generate() -> pcbnew.BOARD:
    subprocess.run([sys.executable, str(HERE / "generate_footprints.py")], check=True)
    export_netlist()
    components, nets = parse_netlist()

    board = pcbnew.BOARD()
    board.SetFileName(str(BASE_BOARD))
    configure_board(board)
    add_outline(board)

    net_objects: dict[str, pcbnew.NETINFO_ITEM] = {}
    for code, (name, _members) in enumerate(nets, 1):
        net = pcbnew.NETINFO_ITEM(board, name, code)
        board.Add(net)
        net_objects[name] = net

    member_net: dict[tuple[str, str], pcbnew.NETINFO_ITEM] = {}
    member_names: dict[tuple[str, str], str] = {}
    for name, members in nets:
        for member in members:
            member_net[member] = net_objects[name]
            member_names[member] = name

    for data in sorted(components, key=lambda value: natural_reference(value["ref"])):
        reference = data["ref"]
        if reference not in PLACEMENT:
            raise ValueError(f"No reviewed placement for {reference}")
        footprint = load_footprint(data["footprint"])
        footprint.SetReference(reference)
        footprint.SetValue(data["value"])
        footprint.SetFPIDAsString(data["footprint"])
        footprint.SetDNP(data["dnp"] == "yes")
        if reference in MODEL_OVERRIDES:
            replace_3d_model(footprint, MODEL_OVERRIDES[reference])
        x, y, rotation = PLACEMENT[reference]
        footprint.SetPosition(point(x, y))
        footprint.SetOrientationDegrees(rotation)
        footprint.Reference().SetVisible(False)
        for pad in footprint.Pads():
            net = member_net.get((reference, pad.GetNumber()))
            if net is not None:
                pad.SetNet(net)
        board.Add(footprint)

    for index, (x, y) in enumerate(((5, 5), (115, 5), (115, 80), (5, 80)), 1):
        add_mounting_hole(board, f"H{index}", x, y)

    add_text(board, "SKYSWEEP32 REV C", 60, 83, 1.25)
    add_text(board, "PASSIVE MONITOR", 60, 5.0, 0.9)
    add_text(board, "PROTOTYPE C / NOT PRODUCTION", 60, 3.0, 1.0)
    add_text(board, "J1 USB", 20, 75.2, 0.8)
    add_text(board, "RF2 SUB-G", 6.0, 65.0, 0.8)
    add_text(board, "RF1 2.4G", 106, 47, 0.8)
    add_text(board, "J5 SUB-G SMA", 7.0, 38.0, 0.8)
    add_text(board, "GPS1", 17, 7.5, 0.8)
    add_text(board, "J2 SD", 116, 59, 0.8)
    add_text(board, "RESET", 82, 76.3, 0.8)
    add_text(board, "BOOT", 93, 76.3, 0.8)
    add_text(board, "USER", 104, 76.3, 0.8)
    add_text(board, "GPL-3.0-only | github.com/bobberdolle1/SkySweep32", 60, 1.2, 0.8, pcbnew.B_SilkS)

    perimeter = [(0.6, 0.6), (119.4, 0.6), (119.4, 84.4), (0.6, 84.4)]
    add_zone(board, "GND", pcbnew.In1_Cu, perimeter, 0.30)
    add_zone(board, "3V3", pcbnew.In2_Cu, perimeter, 0.30)
    add_zone(board, "GND", pcbnew.F_Cu, perimeter, 0.30)
    add_zone(board, "GND", pcbnew.B_Cu, perimeter, 0.30)

    validate_net_contract(board, member_names)
    pcbnew.SaveBoard(str(BASE_BOARD), board)
    pcbnew.SaveBoard(str(BOARD), board)
    inject_stackup(BASE_BOARD)
    inject_stackup(BOARD)
    validate_net_contract(pcbnew.LoadBoard(str(BOARD)), member_names)
    print(f"[OK] Wrote placed board: {BOARD}")
    print(f"[INFO] Components: {len(board.GetFootprints())}; nets: {board.GetNetCount()}")
    return board


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--placed-only", action="store_true", help="Generate the reviewed placed, unrouted board")
    parser.parse_args()
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
