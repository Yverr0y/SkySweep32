#!/usr/bin/env python3
"""Generate the canonical SkySweep32 Rev C KiCad schematic from reviewed parts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from tool_discovery import discover_kicad_root

import kicad_sch_api as ksa

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "hardware_manifest.json"
SCHEMATIC = HERE / "skysweep32_rev_c.kicad_sch"
PROJECT = HERE / "skysweep32_rev_c.kicad_pro"

ERC_EXCLUSION_COMMENTS = {
    "J6": "J6 uses the reviewed side-entry JST PH footprint; the stock generic connector filter only matches underscore-prefixed connector names.",
    "RF1": "RF1 uses the exact E28-2G4M12SX module footprint; the stock generic 2x07 connector filter is intentionally narrower.",
    "F1": "F1 uses KiCad's standard 1812 fuse footprint for the reviewed Bourns MF-MSMF200-2; the stock Polyfuse filter omits Fuse:Fuse_*.",
    "RF2": "RF2 uses the exact E07-900M10S module footprint; the stock generic 2x11 connector filter is intentionally narrower.",
    "U6": "U6 uses the reviewed MAX17048 TDFN footprint while its nine electrical lands are represented by a generic numbered symbol.",
    "RF3": "RF3 uses the procurement-qualified RX5808-2012-12P footprint; the stock generic 2x06 connector filter is intentionally narrower.",
    "GPS1": "GPS1 uses the exact u-blox SAM-M10Q footprint; the stock generic 2x10 connector filter is intentionally narrower.",
    "J3": "J3 uses the reviewed horizontal JST SH footprint; the stock generic connector filter only matches underscore-prefixed connector names.",
}

KICAD_ROOT = discover_kicad_root()
SYMBOL_DIR = KICAD_ROOT / "share" / "kicad" / "symbols"



def apply_dnp_flags(path: Path, references: set[str]) -> None:
    """Set native KiCad DNP flags that kicad-sch-api 0.5.6 cannot write."""
    separator = "\n\t(symbol\n"
    chunks = path.read_text(encoding="utf-8").split(separator)
    seen: set[str] = set()
    for index in range(1, len(chunks)):
        match = re.search(r'\n\t\t\(property "Reference" "([^"]+)"', chunks[index])
        if match and match.group(1) in references:
            chunks[index] = chunks[index].replace("\n\t\t(dnp no)", "\n\t\t(dnp yes)", 1)
            seen.add(match.group(1))
    missing = references - seen
    if missing:
        raise RuntimeError(f"could not apply native DNP flags: {', '.join(sorted(missing))}")
    path.write_text(separator.join(chunks), encoding="utf-8")


def promote_labels_to_global(path: Path) -> None:
    """Turn correctly oriented local labels into cross-sheet KiCad global labels."""
    source = path.read_text(encoding="utf-8")
    promoted, count = re.subn(
        r'^(\t*)\(label ("[^"]+"\n)',
        r'\1(global_label \2\1\t(shape input)\n',
        source,
        flags=re.MULTILINE,
    )
    if not count:
        raise RuntimeError(f"could not find generated labels in {path}")
    path.write_text(promoted, encoding="utf-8")


def hide_metadata_fields(path: Path) -> None:
    """Retain sourcing fields for BOM export without cluttering human drawings."""
    source = path.read_text(encoding="utf-8")
    hidden, count = re.subn(
        r'(?ms)^(\t\t\(property "(?:MPN|Manufacturer|Datasheet)" .*?\n\t\t\t\(effects\n.*?)(\n\t\t\t\)\n\t\t\))',
        r'\1\n\t\t\t\t(hide yes)\2',
        source,
    )
    if not count:
        raise RuntimeError(f"could not find component sourcing fields in {path}")
    path.write_text(hidden, encoding="utf-8")
def sync_project_erc_exclusions(schematic_paths: list[Path], project_path: Path) -> None:
    """Regenerate narrow footprint-filter exclusions with current sheet UUIDs."""
    symbols: dict[str, tuple[int, int, str]] = {}
    for schematic_path in schematic_paths:
        symbol_chunks = schematic_path.read_text(encoding="utf-8").split("\n\t(symbol\n")[1:]
        for chunk in symbol_chunks:
            reference = re.search(r'\n\t\t\(property "Reference" "([^"]+)"', chunk)
            position = re.search(r"\n\t\t\(at (-?[\d.]+) (-?[\d.]+)", chunk)
            uuid = re.search(r'\n\t\t\(uuid "([^"]+)"\)', chunk)
            if not reference or reference.group(1) not in ERC_EXCLUSION_COMMENTS:
                continue
            if not position or not uuid:
                raise RuntimeError(
                    f"could not read exclusion identity for {reference.group(1)}"
                )
            symbols[reference.group(1)] = (
                round(float(position.group(1)) * 10000),
                round(float(position.group(2)) * 10000),
                uuid.group(1),
            )
    missing = ERC_EXCLUSION_COMMENTS.keys() - symbols.keys()
    if missing:
        raise RuntimeError(f"could not find ERC exclusion symbols: {', '.join(sorted(missing))}")

    project = json.loads(project_path.read_text(encoding="utf-8"))
    erc = project.setdefault("erc", {})
    erc.setdefault(
        "rule_severities",
        {
            "four_way_junction": "warning",
            "footprint_filter": "warning",
            "simulation_model_issue": "warning",
            "single_global_label": "warning",
        },
    )
    erc["erc_exclusions"] = [
        [
            f"footprint_filter|{symbols[ref][0]}|{symbols[ref][1]}|{symbols[ref][2]}|"
            "00000000-0000-0000-0000-000000000000|||",
            comment,
        ]
        for ref, comment in ERC_EXCLUSION_COMMENTS.items()
    ]
    project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")




SHEET_FILES = {
    "power": HERE / "01_power.kicad_sch",
    "control": HERE / "02_control_and_alerts.kicad_sch",
    "rf24": HERE / "03_rf_2g4_subghz.kicad_sch",
    "rf58": HERE / "04_rf_5g8.kicad_sch",
    "peripherals": HERE / "05_gnss_storage_display.kicad_sch",
}



SHEET_TRANSFORMS = {
    "01_power": (1.0, 1.0, 0.0, 0.0),
    "02_control_and_alerts": (1.0, 1.0, 0.0, 0.0),
    "03_rf_2g4_subghz": (1.0, 1.0, 0.0, 0.0),
    "04_rf_5g8": (1.0, 1.0, 0.0, 0.0),
    "05_gnss_storage_display": (1.0, 1.0, 0.0, 0.0),
}
def set_title_block(sch: ksa.Schematic, title: str, page: str) -> None:
    sch.set_title_block(
        title=title,
        date="2026-08-12",
        rev="C-PROTOTYPE",
        company="SkySweep32 Project",
        comments={
            1: "PASSIVE RECEIVE/ENERGY OBSERVATION ONLY",
            2: "READY FOR FIRST PROTOTYPE / NOT PRODUCTION VALIDATED",
            3: page,
        },
    )


def generate() -> None:
    dnp_references: set[str] = set()
    generated_sheets: list[Path] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    os.environ["KICAD_SYMBOL_DIR"] = str(SYMBOL_DIR)
    cache = ksa.get_symbol_cache()
    cache.clear_cache()
    cache.discover_libraries([str(SYMBOL_DIR)])
    root = ksa.create_schematic("SkySweep32 Rev C Passive Monitor")
    sch = root
    current_path = SCHEMATIC
    sheet_component_index = 0

    def start_sheet(path: Path, title: str) -> None:
        nonlocal sch, current_path, dnp_references, sheet_component_index
        sch = ksa.create_schematic(title)
        current_path = path
        dnp_references = set()
        sheet_component_index = 0

    def finish_sheet(title: str, page: str) -> None:
        sch.add_text(title.upper(), position=(20, 18), size=1.8)
        sch.add_text(
            "Named global labels are the reviewed inter-sheet net contract.",
            position=(20, 22),
            size=1.0,
        )
        set_title_block(sch, title, page)
        sch.save(current_path)
        apply_dnp_flags(current_path, dnp_references)
        hide_metadata_fields(current_path)
        promote_labels_to_global(current_path)
        generated_sheets.append(current_path)

    def component(
        lib_id: str,
        ref: str,
        value: str,
        position: tuple[float, float],
        footprint: str,
        *,
        mpn: str = "",
        manufacturer: str = "",
        datasheet: str = "",
        rotation: float = 0,
        dnp: bool = False,
    ):
        nonlocal sheet_component_index
        # Preserve enough clearance for labels on opposite-side module pins.
        column, row = divmod(sheet_component_index, 5)
        layout_position = (48.0 + row * 34.0, 62.0 + column * 30.0)
        sheet_component_index += 1
        part = sch.components.add(
            lib_id=lib_id,
            reference=ref,
            value=value,
            position=layout_position,
            footprint=footprint,
            rotation=rotation,
        )
        if mpn:
            part.set_property("MPN", mpn)
        if manufacturer:
            part.set_property("Manufacturer", manufacturer)
        if datasheet:
            part.set_property("Datasheet", datasheet)
        if dnp:
            part.set_property("DNP", "yes")
            dnp_references.add(ref)
        return part

    def pin_position(ref: str, number: str) -> tuple[float, float]:
        part = sch.components.get(ref)
        pin = part.get_pin(number)
        if pin is None:
            raise ValueError(f"No pin {ref}.{number}")
        if part.rotation != 0:
            raise ValueError(f"Connection helper requires an unrotated symbol: {ref}")
        # Translation keeps the reviewed symbol-to-pin geometry unchanged.
        return (part.position.x + pin.position.x, part.position.y - pin.position.y)

    def label(ref: str, pin: str, net: str) -> None:
        # Component positions are transformed into the readable sheet space, so
        # the underlying pin coordinates already include that transform.
        sch.add_label(net, position=pin_position(ref, pin), size=1.0)

    def no_connect(ref: str, pin: str) -> None:
        sch.no_connects.add(pin_position(ref, pin))

    capacitor_parts = {
        ("10n", "Capacitor_SMD:C_0603_1608Metric"): ("Murata", "GRM188R71H103KA01D"),
        ("100n", "Capacitor_SMD:C_0603_1608Metric"): ("Murata", "GRM188R71E104KA01D"),
        ("1u", "Capacitor_SMD:C_0603_1608Metric"): ("Murata", "GRM188R61A105KA61D"),
        ("10u", "Capacitor_SMD:C_0805_2012Metric"): ("Murata", "GRM21BR61A106KE19L"),
        ("10u", "Capacitor_SMD:C_1206_3216Metric"): ("Murata", "GRM31CR61A106KA01L"),
        ("22u", "Capacitor_SMD:C_1206_3216Metric"): ("Murata", "GRM31CR61A226ME15L"),
    }
    resistor_parts = {
        "0R": "RC0603JR-070RL",
        "22R": "RC0603FR-0722RL",
        "100R": "RC0603FR-07100RL",
        "1k": "RC0603FR-071KL",
        "1.13k": "RC0603FR-071K13L",
        "1.18k": "RC0603FR-071K18L",
        "1.5k": "RC0603FR-071K5L",
        "4.12k": "RC0603FR-074K12L",
        "4.7k": "RC0603FR-074K7L",
        "5.1k": "RC0603FR-075K1L",
        "10k": "RC0603FR-0710KL",
        "46.4k": "RC0603FR-0746K4L",
        "47k": "RC0603FR-0747KL",
        "100k": "RC0603FR-07100KL",
    }

    def add_cap(
        ref: str,
        value: str,
        pos: tuple[float, float],
        net: str,
        footprint: str = "Capacitor_SMD:C_0603_1608Metric",
        *,
        dnp: bool = False,
    ) -> None:
        try:
            manufacturer, mpn = capacitor_parts[(value, footprint)]
        except KeyError as error:
            raise ValueError(f"No reviewed capacitor MPN for {value} in {footprint}") from error
        component(
            "Device:C", ref, value, pos, footprint,
            manufacturer=manufacturer, mpn=mpn, dnp=dnp,
        )
        label(ref, "1", net)
        label(ref, "2", "GND")

    def add_resistor(
        ref: str,
        value: str,
        pos: tuple[float, float],
        a: str,
        b: str,
        footprint: str = "Resistor_SMD:R_0603_1608Metric",
        *,
        dnp: bool = False,
    ) -> None:
        if footprint != "Resistor_SMD:R_0603_1608Metric" or value not in resistor_parts:
            raise ValueError(f"No reviewed resistor MPN for {value} in {footprint}")
        component(
            "Device:R", ref, value, pos, footprint,
            manufacturer="Yageo", mpn=resistor_parts[value], dnp=dnp,
        )
        label(ref, "1", a)
        label(ref, "2", b)


    start_sheet(SHEET_FILES["power"], "01 — USB, Battery and Power")

    # USB-C and protection.
    component(
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "J1",
        "USB4105-GF-A",
        (28, 58),
        "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
        mpn="USB4105-GF-A",
        manufacturer="GCT",
    )
    for pin in ("A1", "A12", "B1", "B12", "SH"):
        label("J1", pin, "GND")
    for pin in ("A4", "A9", "B4", "B9"):
        label("J1", pin, "VBUS_RAW")
    for pin in ("A6", "B6"):
        label("J1", pin, "USB_D_P_CONN")
    for pin in ("A7", "B7"):
        label("J1", pin, "USB_D_N_CONN")
    no_connect("J1", "A8")
    no_connect("J1", "B8")

    add_resistor("R1", "5.1k", (18, 91), "USB_CC1", "GND")
    add_resistor("R2", "5.1k", (25, 91), "USB_CC2", "GND")
    label("J1", "A5", "USB_CC1")
    label("J1", "B5", "USB_CC2")

    component(
        "Device:Polyfuse",
        "F1",
        "MF-MSMF200-2",
        (40, 41),
        "Fuse:Fuse_1812_4532Metric",
        mpn="MF-MSMF200-2",
        manufacturer="Bourns",
    )
    label("F1", "1", "VBUS_RAW")
    label("F1", "2", "VBUS_PROTECTED")
    component(
        "Device:D_Zener",
        "D1",
        "SMAJ5.0A",
        (47, 53),
        "Diode_SMD:D_SMA",
        mpn="SMAJ5.0A",
        manufacturer="Littelfuse",
    )
    # SMAJ5.0A is unidirectional: pin 1 is cathode/stripe.
    label("D1", "1", "VBUS_PROTECTED")
    label("D1", "2", "GND")
    add_cap("C1", "10u", (54, 53), "VBUS_PROTECTED", "Capacitor_SMD:C_1206_3216Metric")

    component(
        "Power_Protection:USBLC6-2SC6",
        "U2",
        "USBLC6-2SC6",
        (47, 76),
        "Package_TO_SOT_SMD:SOT-23-6",
        mpn="USBLC6-2SC6",
        manufacturer="STMicroelectronics",
    )
    label("U2", "1", "USB_D_P_CONN")
    label("U2", "6", "USB_D_P_ESD")
    label("U2", "3", "USB_D_N_CONN")
    label("U2", "4", "USB_D_N_ESD")
    label("U2", "2", "GND")
    label("U2", "5", "VBUS_PROTECTED")
    add_resistor("R3", "22R", (62, 69), "USB_D_P_ESD", "USB_D_P")
    add_resistor("R4", "22R", (69, 69), "USB_D_N_ESD", "USB_D_N")

    # Protected 1S battery, standalone charger/power path and fuel gauge.
    component(
        "Connector_Generic:Conn_01x02",
        "J6",
        "BATTERY — ADAFRUIT PID 328",
        (18, 108),
        "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
        mpn="S2B-PH-SM4-TB(LF)(SN)",
        manufacturer="JST",
        datasheet=manifest["major_parts"]["BAT1"]["datasheet"],
    )
    label("J6", "1", "BAT_CELL")
    label("J6", "2", "GND")
    component(
        "Battery_Management:BQ24074RGT",
        "U4",
        "BQ24074RGTR",
        (38, 108),
        "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
        mpn="BQ24074RGTR",
        manufacturer="Texas Instruments",
        datasheet="https://www.ti.com/lit/ds/symlink/bq24074.pdf",
    )
    label("U4", "1", "BQ_TS")
    label("U4", "2", "BAT_CELL")
    label("U4", "3", "BAT_CELL")
    label("U4", "4", "GND")
    label("U4", "5", "VSYS_BAT")
    label("U4", "6", "GND")
    no_connect("U4", "7")
    label("U4", "8", "GND")
    label("U4", "9", "CHG_N")
    label("U4", "10", "VSYS_BAT")
    label("U4", "11", "VSYS_BAT")
    label("U4", "12", "BQ_ILIM")
    label("U4", "13", "VBUS_PROTECTED")
    label("U4", "14", "BQ_TMR")
    label("U4", "15", "BQ_ITERM")
    label("U4", "16", "BQ_ISET")
    label("U4", "17", "GND")
    add_resistor("R20", "10k", (19, 118), "BQ_TS", "GND")
    add_resistor("R21", "46.4k", (26, 118), "BQ_TMR", "GND")
    add_resistor("R22", "1.13k", (33, 118), "BQ_ISET", "GND")
    add_resistor("R23", "1.18k", (40, 118), "BQ_ILIM", "GND")
    add_resistor("R24", "4.12k", (47, 118), "BQ_ITERM", "GND")
    add_cap("C17", "10u", (54, 118), "VBUS_PROTECTED", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C18", "10u", (61, 118), "BAT_CELL", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C19", "10u", (68, 118), "VSYS_BAT", "Capacitor_SMD:C_1206_3216Metric")
    component("Device:LED", "D5", "CHARGE", (56, 102), "LED_SMD:LED_0603_1608Metric", mpn="APT1608LZGCK", manufacturer="Kingbright")
    label("D5", "1", "CHG_N")
    label("D5", "2", "CHG_LED_A")
    add_resistor("R25", "1.5k", (64, 102), "VSYS_BAT", "CHG_LED_A")

    component(
        "Connector_Generic:Conn_01x09",
        "U6",
        "MAX17048G+T10",
        (77, 111),
        "Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.9x1.3mm",
        mpn="MAX17048G+T10",
        manufacturer="Analog Devices",
        datasheet="https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf",
    )
    for pin in ("1", "4", "9"):
        label("U6", pin, "GND")
    for pin in ("2", "3"):
        label("U6", pin, "BAT_CELL")
    # QSTRT and active-low ALRT are unused; outputs must not be tied to ground.
    no_connect("U6", "5")
    no_connect("U6", "6")
    label("U6", "7", "I2C_SCL")
    label("U6", "8", "I2C_SDA")
    add_cap("C29", "100n", (86, 118), "BAT_CELL")
    add_resistor("R26", "4.7k", (91, 118), "3V3", "I2C_SDA")
    add_resistor("R27", "4.7k", (98, 118), "3V3", "I2C_SCL")

    # Battery/system power switch controls the boost enable. The charger and
    # protected battery remain connected while the switched rails are off.
    component(
        "Switch:SW_SPDT",
        "SW4",
        "SYSTEM POWER",
        (76, 92),
        "Button_Switch_THT:SW_Slide_SPDT_Angled_CK_OS102011MA1Q",
        mpn="OS102011MA1QN1",
        manufacturer="C&K",
    )
    label("SW4", "1", "GND")
    label("SW4", "2", "BOOST_EN")
    label("SW4", "3", "VSYS_BAT")
    component(
        "Regulator_Switching:TPS61230DRC",
        "U5",
        "TPS61232DRCR",
        (88, 92),
        "Package_SON:Texas_S-PVSON-N10_ThermalVias",
        mpn="TPS61232DRCR",
        manufacturer="Texas Instruments",
        datasheet="https://www.ti.com/lit/ds/symlink/tps61232.pdf",
    )
    label("U5", "1", "BOOST_SW")
    label("U5", "2", "BOOST_SW")
    label("U5", "3", "SYS_5V")
    label("U5", "4", "SYS_5V")
    no_connect("U5", "5")
    no_connect("U5", "6")
    label("U5", "7", "SYS_5V")
    no_connect("U5", "8")
    label("U5", "9", "BOOST_EN")
    label("U5", "10", "VSYS_BAT")
    label("U5", "11", "GND")
    component(
        "Device:L",
        "L2",
        "1uH SRN6028C-1R0Y",
        (101, 86),
        "Inductor_SMD:L_Bourns-SRN6028",
        mpn="SRN6028C-1R0Y",
        manufacturer="Bourns",
    )
    label("L2", "1", "VSYS_BAT")
    label("L2", "2", "BOOST_SW")
    add_cap("C20", "22u", (106, 113), "VSYS_BAT", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C21", "22u", (113, 113), "SYS_5V", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C22", "22u", (120, 113), "SYS_5V", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C23", "22u", (127, 113), "SYS_5V", "Capacitor_SMD:C_1206_3216Metric")

    component(
        "Regulator_Switching:AP63203WU",
        "U3",
        "AP63203WU-7",
        (112, 101),
        "Package_TO_SOT_SMD:TSOT-23-6",
        mpn="AP63203WU-7",
        manufacturer="Diodes Incorporated",
        datasheet="https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf",
    )
    label("U3", "1", "3V3")
    label("U3", "2", "SYS_5V")
    label("U3", "3", "SYS_5V")
    label("U3", "4", "GND")
    label("U3", "5", "BUCK_SW")
    label("U3", "6", "BUCK_BST")
    component(
        "Device:L",
        "L1",
        "3.9uH SRN6028-3R9M",
        (127, 94),
        "Inductor_SMD:L_Bourns-SRN6028",
        mpn="SRN6028-3R9M",
        manufacturer="Bourns",
    )
    label("L1", "1", "BUCK_SW")
    label("L1", "2", "3V3")
    component("Device:C", "C2", "100n", (127, 108), "Capacitor_SMD:C_0603_1608Metric", manufacturer="Murata", mpn="GRM188R71E104KA01D")
    label("C2", "1", "BUCK_BST")
    label("C2", "2", "BUCK_SW")
    add_cap("C3", "22u", (136, 97), "3V3", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C4", "22u", (143, 97), "3V3", "Capacitor_SMD:C_1206_3216Metric")

    # ERC power-source declarations identify the protected input, switched
    # system supply, regulated rail and common return.
    component("power:PWR_FLAG", "#FLG01", "PWR_FLAG", (63, 34), "")
    label("#FLG01", "1", "VBUS_PROTECTED")
    component("power:PWR_FLAG", "#FLG02", "PWR_FLAG", (69, 34), "")
    label("#FLG02", "1", "3V3")
    component("power:PWR_FLAG", "#FLG03", "PWR_FLAG", (75, 34), "")
    label("#FLG03", "1", "GND")

    finish_sheet("01 — USB, Battery and Power", "Sheet 1 of 5")
    start_sheet(SHEET_FILES["control"], "02 — ESP32-S3 Control and Alerts")

    # MCU and programming.
    mcu = manifest["mcu"]
    component(
        "RF_Module:ESP32-S3-WROOM-1",
        "U1",
        mcu["mpn"],
        (116, 74),
        "RF_Module:ESP32-S3-WROOM-1",
        mpn=mcu["mpn"],
        manufacturer=mcu["manufacturer"],
        datasheet=mcu["datasheet"],
    )
    label("U1", "1", "GND")
    label("U1", "2", "3V3")
    label("U1", "3", "MCU_EN")
    label("U1", "4", "SD_DETECT")
    label("U1", "5", "RX5808_RSSI_ADC")
    label("U1", "6", "RX5808_CH1")
    label("U1", "7", "RX5808_CH2")
    label("U1", "8", "CC1101_GDO0")
    label("U1", "9", "CC1101_GDO2")
    label("U1", "10", "SX1281_RESET")
    label("U1", "11", "SX1281_DIO1")
    label("U1", "12", "SX1281_BUSY")
    label("U1", "13", "USB_D_N")
    label("U1", "14", "USB_D_P")
    label("U1", "17", "SX1281_CSN")
    label("U1", "18", "CC1101_CSN")
    label("U1", "19", "RF_SPI_MOSI")
    label("U1", "20", "RF_SPI_SCK")
    label("U1", "21", "RF_SPI_MISO")
    label("U1", "22", "RX5808_CH3")
    label("U1", "23", "GPS_PPS")
    label("U1", "24", "GPS_RX")
    label("U1", "25", "GPS_TX")
    label("U1", "27", "BOOT_N")
    no_connect("U1", "28")
    no_connect("U1", "29")
    no_connect("U1", "30")
    label("U1", "31", "SD_CSN")
    label("U1", "32", "ALERT_BUZZER_GATE")
    label("U1", "33", "ALERT_LED")
    label("U1", "34", "VIBRATION_GATE")
    label("U1", "35", "USER_BUTTON_N")
    label("U1", "36", "UART0_RX")
    label("U1", "37", "UART0_TX")
    label("U1", "38", "I2C_SCL")
    label("U1", "39", "I2C_SDA")
    for pin in ("15", "16", "26"):
        no_connect("U1", pin)

    add_cap("C5", "10u", (93, 106), "3V3", "Capacitor_SMD:C_0805_2012Metric")
    add_cap("C6", "100n", (100, 106), "3V3")
    add_resistor("R5", "10k", (91, 38), "3V3", "MCU_EN")
    add_cap("C7", "1u", (98, 38), "MCU_EN")
    component("Switch:SW_Push", "SW1", "RESET", (108, 38), "Button_Switch_SMD:SW_SPST_SKQG_WithoutStem", manufacturer="Alps Alpine", mpn="SKQGABE010")
    label("SW1", "1", "MCU_EN")
    label("SW1", "2", "GND")
    add_resistor("R6", "10k", (116, 38), "3V3", "BOOT_N")
    component("Switch:SW_Push", "SW2", "BOOT", (126, 38), "Button_Switch_SMD:SW_SPST_SKQG_WithoutStem", manufacturer="Alps Alpine", mpn="SKQGABE010")
    label("SW2", "1", "BOOT_N")
    label("SW2", "2", "GND")
    add_resistor("R7", "10k", (134, 38), "3V3", "USER_BUTTON_N")
    component("Switch:SW_Push", "SW3", "USER", (144, 38), "Button_Switch_SMD:SW_SPST_SKQG_WithoutStem", manufacturer="Alps Alpine", mpn="SKQGABE010")
    label("SW3", "1", "USER_BUTTON_N")
    label("SW3", "2", "GND")

    for ref, net, pos in (
        ("TP1", "VBUS_PROTECTED", (91, 116)),
        ("TP2", "3V3", (99, 116)),
        ("TP3", "GND", (107, 116)),
        ("TP4", "UART0_TX", (115, 116)),
        ("TP5", "UART0_RX", (123, 116)),
        ("TP6", "BAT_CELL", (131, 116)),
        ("TP7", "SYS_5V", (139, 116)),
        ("TP8", "RX5808_RSSI_ADC", (147, 116)),
    ):
        component("Connector:TestPoint", ref, net, pos, "TestPoint:TestPoint_Pad_D1.0mm", dnp=True)
        label(ref, "1", net)


    control_sch = sch
    control_path = current_path
    control_dnp_references = dnp_references
    start_sheet(SHEET_FILES["rf24"], "03 — 2.4 GHz and Sub-GHz Receivers")
    # Exact passive RF modules. Connector symbols expose every manufacturer pad
    # number; footprints encode the physical land patterns.
    component(
        "Connector_Generic:Conn_02x07_Odd_Even",
        "RF1",
        "E28-2G4M12SX",
        (32, 158),
        "SkySweep32RevC:Module_Ebyte_E28_2G4M12SX",
        mpn="E28-2G4M12SX",
        manufacturer="Chengdu Ebyte Electronic Technology",
        datasheet=manifest["major_parts"]["RF1"]["datasheet"],
    )
    for pin, net in {
        "1": "3V3", "2": "GND", "3": "RF_SPI_MISO", "4": "RF_SPI_MOSI",
        "5": "RF_SPI_SCK", "6": "SX1281_CSN", "7": "GND", "8": "GND",
        "9": "SX1281_RESET", "10": "SX1281_BUSY", "11": "SX1281_DIO1",
        "14": "GND",
    }.items():
        label("RF1", pin, net)
    no_connect("RF1", "12")
    no_connect("RF1", "13")
    add_cap("C8", "10u", (17, 183), "3V3", "Capacitor_SMD:C_0805_2012Metric")
    add_cap("C9", "100n", (24, 183), "3V3")

    component(
        "Connector_Generic:Conn_02x11_Odd_Even",
        "RF2",
        "E07-900M10S",
        (63, 158),
        "SkySweep32RevC:Module_Ebyte_E07_900M10S",
        mpn="E07-900M10S",
        manufacturer="Chengdu Ebyte Electronic Technology",
    )
    e07_nets = {
        "1": "GND", "2": "GND", "3": "GND", "4": "GND", "5": "GND",
        "9": "3V3", "11": "GND", "12": "GND", "14": "CC1101_GDO2",
        "15": "CC1101_GDO0", "16": "RF_SPI_MISO", "17": "RF_SPI_MOSI",
        "18": "RF_SPI_SCK", "19": "CC1101_CSN", "20": "GND",
        "21": "SUBGHZ_ANT", "22": "GND",
    }
    for pin, net in e07_nets.items():
        label("RF2", pin, net)
    for pin in ("6", "7", "8", "10", "13"):
        no_connect("RF2", pin)
    component(
        "Connector:Conn_Coaxial",
        "J5",
        "SUB-GHZ SMA",
        (76, 140),
        "Connector_Coaxial:SMA_Amphenol_132289_EdgeMount",
        mpn="132289",
        manufacturer="Amphenol RF",
        datasheet="https://www.amphenolrf.com/library/download/link/link_id/595984/parent/132289/",
    )
    label("J5", "1", "SUBGHZ_ANT")
    label("J5", "2", "GND")
    add_cap("C10", "10u", (80, 183), "3V3", "Capacitor_SMD:C_0805_2012Metric")
    add_cap("C11", "100n", (87, 183), "3V3")

    finish_sheet("03 — 2.4 GHz and Sub-GHz Receivers", "Sheet 3 of 5")
    start_sheet(SHEET_FILES["rf58"], "04 — 5.8 GHz Receiver")

    component(
        "Connector_Generic:Conn_02x06_Odd_Even",
        "RF3",
        "RX5808-2012-12P",
        (92, 158),
        "SkySweep32RevC:Module_RX5808_2012_12P",
        mpn="RX5808-2012-12P",
        manufacturer="Multi-source legacy module",
        datasheet=manifest["major_parts"]["RF3"]["datasheet"],
    )
    for pin, net in {
        "1": "GND", "2": "RX5808_RF_IN", "3": "GND",
        "4": "RX5808_CH1", "5": "RX5808_CH2", "6": "RX5808_CH3",
        "7": "GND", "8": "SYS_5V", "9": "RX5808_RSSI_RAW",
        "12": "GND",
    }.items():
        label("RF3", pin, net)
    # CH4 and raw VIDEO OUT have no qualified Rev C consumer/interface.
    no_connect("RF3", "10")
    no_connect("RF3", "11")
    component(
        "Connector:Conn_Coaxial",
        "J7",
        "5.8-GHZ SMA",
        (105, 140),
        "Connector_Coaxial:SMA_Amphenol_132289_EdgeMount",
        mpn="132289",
        manufacturer="Amphenol RF",
        datasheet="https://www.amphenolrf.com/library/download/link/link_id/595984/parent/132289/",
    )
    label("J7", "1", "RX5808_RF_IN")
    label("J7", "2", "GND")
    add_resistor("R28", "100k", (92, 183), "RX5808_CH1", "GND")
    add_resistor("R29", "100k", (99, 183), "RX5808_CH2", "GND")
    add_resistor("R30", "100k", (106, 183), "RX5808_CH3", "GND")
    add_resistor("R31", "1k", (113, 183), "RX5808_RSSI_RAW", "RX5808_RSSI_ADC")
    add_cap("C30", "10n", (120, 183), "RX5808_RSSI_ADC")
    add_cap("C24", "100n", (127, 183), "SYS_5V")
    add_cap("C25", "10u", (134, 183), "SYS_5V", "Capacitor_SMD:C_0805_2012Metric")
    component(
        "Device:C_Polarized",
        "C26",
        "470u 10V",
        (141, 183),
        "Capacitor_SMD:CP_Elec_10x10",
        mpn="EEE-FK1A471P",
        manufacturer="Panasonic",
    )
    label("C26", "1", "SYS_5V")
    label("C26", "2", "GND")

    finish_sheet("04 — 5.8 GHz Receiver", "Sheet 4 of 5")
    start_sheet(SHEET_FILES["peripherals"], "05 — GNSS, Storage and Display")

    # GNSS with the exact 20-pad u-blox pin contract.
    component(
        "Connector_Generic:Conn_02x10_Odd_Even",
        "GPS1",
        "SAM-M10Q-00B",
        (108, 158),
        "SkySweep32RevC:Module_UBlox_SAM_M10Q",
        mpn="SAM-M10Q-00B",
        manufacturer="u-blox AG",
        datasheet=manifest["major_parts"]["GPS1"]["datasheet"],
    )
    sam_nets = {
        "1": "GND", "2": "3V3", "3": "3V3", "4": "GND", "5": "GND",
        "6": "GND", "7": "GPS_PPS", "9": "GPS_I2C_SDA", "10": "GND",
        "11": "GND", "12": "GPS_I2C_SCL", "13": "GPS_RX", "14": "GPS_TX",
        "15": "GND", "16": "GND", "17": "3V3", "18": "GPS_RESET_N", "20": "GND",
    }
    for pin, net in sam_nets.items():
        label("GPS1", pin, net)
    no_connect("GPS1", "8")
    no_connect("GPS1", "19")
    add_resistor("R8", "10k", (96, 184), "3V3", "GPS_RESET_N")
    add_resistor("R9", "0R", (103, 184), "I2C_SDA", "GPS_I2C_SDA")
    add_resistor("R10", "0R", (110, 184), "I2C_SCL", "GPS_I2C_SCL")
    add_cap("C12", "10u", (117, 184), "3V3", "Capacitor_SMD:C_0805_2012Metric")
    add_cap("C13", "100n", (124, 184), "3V3")
    # Direct microSD socket; pins 9/10 are the normally-open card detect switch.
    component(
        "Connector:Micro_SD_Card_Det2",
        "J2",
        "Molex 104031-0811",
        (146, 154),
        "Connector_Card:microSD_HC_Molex_104031-0811",
        mpn="104031-0811",
        manufacturer="Molex",
    )
    sd_nets = {
        "1": "SD_DAT2", "2": "SD_CSN", "3": "RF_SPI_MOSI", "4": "3V3",
        "5": "RF_SPI_SCK", "6": "GND", "7": "RF_SPI_MISO", "8": "SD_DAT1",
        "9": "SD_DETECT", "10": "GND", "SH": "GND",
    }
    for pin, net in sd_nets.items():
        label("J2", pin, net)
    add_resistor("R11", "47k", (137, 183), "3V3", "SD_DAT1")
    add_resistor("R12", "47k", (144, 183), "3V3", "SD_DAT2")
    add_resistor("R13", "47k", (151, 183), "3V3", "SD_CSN")
    add_resistor("R14", "47k", (158, 183), "3V3", "SD_DETECT")
    add_cap("C14", "10u", (165, 183), "3V3", "Capacitor_SMD:C_0805_2012Metric")
    add_cap("C15", "100n", (172, 183), "3V3")

    # Keyed Qwiic/STEMMA QT cable to the lid-mounted Adafruit PID 326.
    component(
        "Connector_Generic:Conn_01x04",
        "J3",
        "OLED STEMMA QT",
        (169, 139),
        "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
        mpn="SM04B-SRSS-TB(LF)(SN)",
        manufacturer="JST",
    )
    for pin, net in {"1": "GND", "2": "3V3", "3": "I2C_SDA", "4": "I2C_SCL"}.items():
        label("J3", pin, net)
    add_cap("C16", "10u", (178, 151), "3V3", "Capacitor_SMD:C_0805_2012Metric")

    finish_sheet("05 — GNSS, Storage and Display", "Sheet 5 of 5")
    sch = control_sch
    current_path = control_path
    dnp_references = control_dnp_references

    # Local alerts. The flyback diodes return to the respective positive rail;
    # gate pull-downs guarantee off state during reset.
    component(
        "Device:Buzzer",
        "BZ1",
        "CMT-1203-SMT-TR",
        (163, 69),
        "SkySweep32RevC:Buzzer_CUI_CMT_1203_SMT_TR",
        mpn="CMT-1203-SMT-TR",
        manufacturer="CUI Devices",
    )
    label("BZ1", "1", "3V3")
    label("BZ1", "2", "BUZZER_DRAIN")
    component("Transistor_FET:Q_NMOS_GSD", "Q1", "AO3400A", (163, 88), "Package_TO_SOT_SMD:SOT-23", mpn="AO3400A", manufacturer="Alpha & Omega Semiconductor")
    label("Q1", "1", "ALERT_BUZZER_GATE_R")
    label("Q1", "2", "GND")
    label("Q1", "3", "BUZZER_DRAIN")
    add_resistor("R15", "100R", (151, 78), "ALERT_BUZZER_GATE", "ALERT_BUZZER_GATE_R")
    add_resistor("R16", "100k", (151, 91), "ALERT_BUZZER_GATE_R", "GND")
    component("Device:D", "D2", "PMEG3020EP", (174, 78), "Diode_SMD:D_SOD-128", mpn="PMEG3020EP,115", manufacturer="Nexperia")
    label("D2", "1", "3V3")
    label("D2", "2", "BUZZER_DRAIN")

    component("Device:LED", "D3", "GREEN", (142, 101), "LED_SMD:LED_0603_1608Metric", mpn="APT1608LZGCK", manufacturer="Kingbright")
    add_resistor("R17", "1k", (132, 101), "ALERT_LED", "STATUS_LED_A")
    label("D3", "1", "GND")
    label("D3", "2", "STATUS_LED_A")

    component(
        "Connector_Generic:Conn_01x02",
        "J4",
        "OPTIONAL VIBRATION MOTOR",
        (181, 80),
        "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
        mpn="B2B-PH-K-S(LF)(SN)",
        manufacturer="JST",
        dnp=True,
    )
    label("J4", "1", "SYS_5V")
    label("J4", "2", "VIBRATION_DRAIN")
    component("Transistor_FET:Q_NMOS_GSD", "Q2", "AO3400A", (183, 99), "Package_TO_SOT_SMD:SOT-23", mpn="AO3400A", manufacturer="Alpha & Omega Semiconductor", dnp=True)
    label("Q2", "1", "VIBRATION_GATE_R")
    label("Q2", "2", "GND")
    label("Q2", "3", "VIBRATION_DRAIN")
    add_resistor("R18", "100R", (174, 99), "VIBRATION_GATE", "VIBRATION_GATE_R", dnp=True)
    add_resistor("R19", "100k", (174, 111), "VIBRATION_GATE_R", "GND", dnp=True)
    component("Device:D", "D4", "PMEG3020EP", (190, 91), "Diode_SMD:D_SOD-128", mpn="PMEG3020EP,115", manufacturer="Nexperia", dnp=True)
    label("D4", "1", "SYS_5V")
    label("D4", "2", "VIBRATION_DRAIN")

    finish_sheet("02 — ESP32-S3 Control and Alerts", "Sheet 2 of 5")

    root.add_text("SkySweep32 Rev C Passive Monitor", position=(24, 24), size=2.2)
    root.add_text(
        "DESIGN OVERVIEW — PASSIVE RECEIVE / ENERGY OBSERVATION ONLY",
        position=(24, 30),
        size=1.5,
    )
    root.add_text(
        "READY FOR FIRST PHYSICAL PROTOTYPE — NOT PRODUCTION VALIDATED",
        position=(24, 35),
        size=1.2,
    )
    for name, filename, position, description in (
        (
            "01 — USB, Battery and Power",
            "01_power.kicad_sch",
            (22, 48),
            "USB-C protection, charger/power path, fuel gauge, 5 V and 3.3 V rails",
        ),
        (
            "02 — ESP32-S3 Control and Alerts",
            "02_control_and_alerts.kicad_sch",
            (112, 48),
            "ESP32-S3, native USB, reset/boot/user controls, test points and alerts",
        ),
        (
            "03 — 2.4 GHz and Sub-GHz Receivers",
            "03_rf_2g4_subghz.kicad_sch",
            (22, 105),
            "E28/SX1281 and E07/CC1101 receiver modules and J5 antenna interface",
        ),
        (
            "04 — 5.8 GHz Receiver",
            "04_rf_5g8.kicad_sch",
            (112, 105),
            "RX5808 selected-channel RSSI receiver and J7 antenna interface",
        ),
        (
            "05 — GNSS, Storage and Display",
            "05_gnss_storage_display.kicad_sch",
            (67, 162),
            "SAM-M10Q GNSS, microSD, and keyed OLED I2C harness",
        ),
    ):
        root.add_sheet(name, filename, position, (70, 32), page_number="1")
        root.add_text(description, position=(position[0] + 2, position[1] + 22), size=0.9)
    root.add_text(
        "Electrical contract: named global labels are attached to reviewed numbered pins. "
        "Exact MPNs and firmware GPIO contract: hardware_manifest.json.",
        position=(24, 205),
        size=1.0,
    )
    set_title_block(root, "SkySweep32 Rev C Passive Monitor", "Sheet 0 — System Overview")
    root.save(SCHEMATIC)
    sync_project_erc_exclusions([SCHEMATIC, *generated_sheets], PROJECT)
    print(f"[OK] Wrote {SCHEMATIC} and {len(generated_sheets)} functional sheets")


if __name__ == "__main__":
    generate()
