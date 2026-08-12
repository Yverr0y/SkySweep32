#!/usr/bin/env python3
"""Generate the placed four-layer SkySweep32 Rev C PCB from the KiCad netlist."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from tool_discovery import discover_kicad_cli, discover_kicad_root

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

MANIFEST_PATH = HERE / "hardware_manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
BOARD_WIDTH, BOARD_HEIGHT = MANIFEST["mechanical"]["board_dimensions_mm"]
MOUNTING_HOLES = tuple(tuple(hole[:2]) for hole in MANIFEST["mechanical"]["mounting_holes"])
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
PROJECT = HERE / "skysweep32_rev_c.kicad_pro"

TPS61232_DRC_EXCLUSION = (
    "TPS61232 is an SMD device; its exposed-pad thermal vias intentionally mix "
    "plated through-hole and SMD pads."
)
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
    "L2": "Bourns_SRN6028C_1R0Y_ENVELOPE.step",
    "U4": "TI_BQ24074_RGT_ENVELOPE.step",
    "U6": "ADI_MAX17048_TDFN8_ENVELOPE.step",
    "J6": "JST_S2B_PH_SM4_TB_ENVELOPE.step",
}




def sync_tps61232_drc_exclusion(board_path: Path, project: dict[str, object]) -> None:
    """Keep the one reviewed U5 package-type exception bound to its UUID."""
    chunks = board_path.read_text(encoding="utf-8").split("\n\t(footprint ")[1:]
    u5_chunks = [chunk for chunk in chunks if '(property "Reference" "U5"' in chunk]
    if len(u5_chunks) != 1:
        raise RuntimeError(f"expected one U5 footprint, found {len(u5_chunks)}")
    match = re.search(r'\n\t\t\(uuid "([^"]+)"', u5_chunks[0])
    if not match:
        raise RuntimeError("could not read U5 footprint UUID")

    design_settings = project["board"]["design_settings"]
    design_settings["drc_exclusions"] = [[
        f"footprint_type_mismatch|52000000|69000000|{match.group(1)}|"
        "00000000-0000-0000-0000-000000000000",
        TPS61232_DRC_EXCLUSION,
    ]]
    PROJECT.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")

def natural_reference(reference: str) -> tuple[str, int]:
    match = re.fullmatch(r"([^0-9]+)([0-9]+)", reference)
    return (match.group(1), int(match.group(2))) if match else (reference, 0)


# Placement is a reviewed mechanical/electrical input. The board datum is the
# lower-left corner in the top view; pcbnew screen coordinates increase down,
# so the same file coordinates are described as upper-left in plots.
PLACEMENT: dict[str, tuple[float, float, float]] = {
    # Mechanically constrained external/service interfaces.
    "J1": (35.0, 91.325, 0),      # USB-C mouth at lower board edge
    "J2": (143.0, 70.0, 90),      # microSD insertion through right wall
    "J3": (78.0, 89.0, 0),        # keyed STEMMA QT lid harness
    "J4": (92.0, 88.0, 0),        # optional vibration motor harness
    "J5": (2.55, 50.0, 180),      # sub-GHz edge-launch SMA
    "J6": (18.0, 89.8, 0),        # protected battery harness
    "J7": (147.45, 40.64, 0),     # 5.8-GHz edge-launch SMA aligned to RF3.2
    "SW1": (111.0, 90.0, 0),
    "SW2": (123.0, 90.0, 0),
    "SW3": (135.0, 90.0, 0),
    "SW4": (58.0, 89.0, 0),
    # RF/GNSS modules fixed before supporting circuitry. U1's 48 x 21 mm
    # antenna courtyard is intentionally empty.
    "GPS1": (18.0, 18.0, 0),
    "U1": (72.0, 29.0, 0),
    "RF1": (132.0, 18.0, 0),
    "RF2": (15.0, 52.0, 0),
    "RF3": (128.0, 48.0, 0),
    # USB-C protection and data entry.
    "R1": (27.0, 82.0, 0),
    "R2": (31.0, 82.0, 0),
    "F1": (43.0, 84.0, 90),
    "D1": (49.0, 87.0, 90),
    "C1": (55.0, 82.0, 0),
    "U2": (40.0, 77.0, 0),
    "R3": (45.0, 75.5, 0),
    "R4": (45.0, 78.5, 0),
    # Charger, battery gauge and power-path programming.
    "U4": (29.0, 70.0, 0),
    "U6": (14.0, 71.0, 0),
    "C17": (25.0, 77.0, 0),
    "C18": (27.0, 62.0, 0),
    "C19": (36.0, 63.0, 0),
    "C29": (14.0, 75.0, 0),
    "D5": (22.0, 81.0, 0),
    "R20": (21.0, 67.0, 0),
    "R21": (25.0, 65.0, 0),
    "R22": (28.0, 64.0, 0),
    "R23": (33.0, 65.0, 0),
    "R24": (35.0, 70.0, 0),
    "R25": (26.0, 86.0, 0),
    "R26": (12.0, 80.0, 0),
    "R27": (16.0, 80.0, 0),
    # 5 V boost, switched system rail and 3.3 V buck.
    "U5": (52.0, 69.0, 0),
    "L2": (62.0, 69.0, 0),
    "C20": (44.0, 64.0, 0),
    "C21": (44.0, 69.0, 0),
    "C22": (69.0, 64.0, 0),
    "C23": (69.0, 69.0, 0),
    "U3": (79.0, 69.0, 0),
    "L1": (89.0, 69.0, 0),
    "C2": (83.0, 64.0, 0),
    "C3": (96.0, 62.0, 0),
    "C4": (96.0, 66.0, 0),
    # MCU local support and controls.
    "C5": (62.0, 46.0, 0),
    "C6": (66.0, 46.0, 0),
    "R5": (72.0, 46.0, 0),
    "C7": (76.0, 46.0, 0),
    "R6": (121.0, 85.0, 0),
    "R7": (133.0, 85.0, 0),
    # RF module support and RSSI conditioning.
    "C8": (121.0, 16.0, 0),
    "C9": (121.0, 20.0, 0),
    "C10": (27.0, 49.0, 0),
    "C11": (27.0, 53.0, 0),
    "C24": (104.0, 43.0, 0),
    "C25": (104.0, 47.0, 0),
    "C26": (107.5, 61.5, 0),
    "R28": (109.0, 42.0, 0),
    "R29": (109.0, 46.0, 0),
    "R30": (109.0, 50.0, 0),
    "R31": (105.0, 53.0, 0),
    "C30": (101.0, 53.0, 0),
    # GNSS support, including optional 0-ohm I2C links.
    "R8": (30.0, 14.0, 0),
    "R9": (30.0, 20.0, 0),
    "R10": (30.0, 25.0, 0),
    "C12": (18.0, 31.0, 0),
    "C13": (23.0, 31.0, 0),
    # microSD pull-ups and local energy storage.
    "R11": (132.0, 66.0, 0),
    "R12": (132.0, 70.0, 0),
    "R13": (132.0, 74.0, 0),
    "R14": (132.0, 78.0, 0),
    "C14": (140.0, 82.0, 0),
    "C15": (145.0, 82.0, 0),
    "C16": (80.0, 82.0, 0),
    # Audible/visual/haptic alert block.
    "BZ1": (104.0, 76.0, 0),
    "Q1": (115.0, 72.0, 0),
    "R15": (115.0, 67.0, 0),
    "R16": (120.0, 75.0, 0),
    "D2": (116.0, 82.0, 0),
    "D3": (106.0, 84.0, 0),
    "R17": (110.0, 84.0, 0),
    "Q2": (92.0, 79.0, 0),
    "R18": (88.0, 79.0, 0),
    "R19": (90.0, 83.0, 0),
    "D4": (84.0, 86.0, 90),
    # Accessible diagnostic pads in the open center service corridor.
    "TP1": (51.0, 52.0, 0),
    "TP2": (57.0, 52.0, 0),
    "TP3": (63.0, 52.0, 0),
    "TP4": (69.0, 52.0, 0),
    "TP5": (75.0, 52.0, 0),
    "TP6": (81.0, 52.0, 0),
    "TP7": (87.0, 52.0, 0),
    "TP8": (93.0, 52.0, 0),
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
    for pattern in ("VBUS*", "BAT_CELL", "VSYS_BAT", "SYS_5V", "3V3", "BUCK_SW", "BUCK_BST", "BOOST_SW"):
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
    for pattern in ("SUBGHZ_ANT", "RX5808_RF_IN"):
        settings.SetNetclassPatternAssignment(pattern, "RF_50R")
    settings.RecomputeEffectiveNetclasses()


def add_outline(board: pcbnew.BOARD) -> None:
    x0, y0, x1, y1, radius = 0.0, 0.0, BOARD_WIDTH, BOARD_HEIGHT, 3.0
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
    reviewed_project = json.loads(PROJECT.read_text(encoding="utf-8"))
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

    for index, (x, y) in enumerate(MOUNTING_HOLES, 1):
        add_mounting_hole(board, f"H{index}", x, y)

    add_text(board, "SKYSWEEP32 REV C", BOARD_WIDTH / 2, BOARD_HEIGHT - 2.0, 1.25)
    add_text(board, "PASSIVE RF MONITOR", BOARD_WIDTH / 2, 5.0, 0.9)
    add_text(board, "PROTOTYPE C / NOT PRODUCTION", BOARD_WIDTH / 2, 3.0, 1.0)
    add_text(board, "J1 USB-C", 35, 93.5, 0.8)
    add_text(board, "RF2 SUB-G", 7.0, 64.0, 0.8)
    add_text(board, "RF1 2.4G RSSI", 132, 29.0, 0.8)
    add_text(board, "RF3 5.8G RSSI", 128, 34.0, 0.8)
    add_text(board, "J5 SUB-G", 7.0, 38.0, 0.8)
    add_text(board, "J7 5.8G", 143.0, 33.0, 0.8)
    add_text(board, "GPS1", 18, 7.5, 0.8)
    add_text(board, "J2 SD", 145, 62, 0.8)
    add_text(board, "RESET", 111, 86.0, 0.8)
    add_text(board, "BOOT", 123, 86.0, 0.8)
    add_text(board, "USER", 135, 86.0, 0.8)
    add_text(board, "POWER", 58, 84.0, 0.8)
    add_text(board, "GPL-3.0-only | github.com/bobberdolle1/SkySweep32", BOARD_WIDTH / 2, 1.2, 0.8, pcbnew.B_SilkS)

    perimeter = [(0.6, 0.6), (BOARD_WIDTH - 0.6, 0.6), (BOARD_WIDTH - 0.6, BOARD_HEIGHT - 0.6), (0.6, BOARD_HEIGHT - 0.6)]
    add_zone(board, "GND", pcbnew.In1_Cu, perimeter, 0.30)
    add_zone(board, "3V3", pcbnew.In2_Cu, perimeter, 0.30)

    validate_net_contract(board, member_names)
    pcbnew.SaveBoard(str(BASE_BOARD), board)
    pcbnew.SaveBoard(str(BOARD), board)
    inject_stackup(BASE_BOARD)
    inject_stackup(BOARD)
    sync_tps61232_drc_exclusion(BOARD, reviewed_project)
    validate_net_contract(pcbnew.LoadBoard(str(BOARD)), member_names)
    print(f"[OK] Wrote placed board: {BOARD}")
    print(f"[INFO] Components: {len(board.GetFootprints())}; nets: {board.GetNetCount()}")
    return board


def refresh_model_overrides() -> None:
    """Refresh enclosure-critical model links without touching copper routing."""
    if not BOARD.is_file():
        raise FileNotFoundError(f"board not found: {BOARD}")
    board = pcbnew.LoadBoard(str(BOARD))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    missing = sorted(set(MODEL_OVERRIDES) - set(footprints))
    if missing:
        raise ValueError(f"model override references absent from board: {missing}")
    for reference, filename in MODEL_OVERRIDES.items():
        replace_3d_model(footprints[reference], filename)
    pcbnew.SaveBoard(str(BOARD), board)
    print(f"[OK] Refreshed {len(MODEL_OVERRIDES)} model overrides in {BOARD}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--placed-only", action="store_true", help="Generate the reviewed placed, unrouted board")
    parser.add_argument("--models-only", action="store_true", help="Refresh 3D model links without changing copper")
    args = parser.parse_args()
    if args.models_only:
        refresh_model_overrides()
        return 0
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
