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

def generate() -> None:
    dnp_references: set[str] = set()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    os.environ["KICAD_SYMBOL_DIR"] = str(SYMBOL_DIR)
    cache = ksa.get_symbol_cache()
    cache.clear_cache()
    cache.discover_libraries([str(SYMBOL_DIR)])
    sch = ksa.create_schematic("SkySweep32 Rev C Passive Monitor")

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
        part = sch.components.add(
            lib_id=lib_id,
            reference=ref,
            value=value,
            position=position,
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
        # kicad-sch-api 0.5.6 mirrors the KiCad symbol-local Y axis when its
        # pin= convenience is used. Calculate KiCad's screen-coordinate
        # transform explicitly so labels and no-connect flags land on the
        # intended numbered pins rather than vertically mirrored neighbors.
        return (part.position.x + pin.position.x, part.position.y - pin.position.y)

    def label(ref: str, pin: str, net: str) -> None:
        sch.add_label(net, position=pin_position(ref, pin), size=1.0)

    def no_connect(ref: str, pin: str) -> None:
        sch.no_connects.add(pin_position(ref, pin))

    capacitor_parts = {
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
        "5.1k": "RC0603FR-075K1L",
        "10k": "RC0603FR-0710KL",
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

    # Sheet annotations establish a readable functional hierarchy without
    # introducing duplicated cross-sheet power and interface definitions.
    sch.add_text("USB-C INPUT, PROTECTION AND 3.3 V POWER", position=(35, 25), size=1.6)
    sch.add_text("ESP32-S3 CONTROL, PROGRAMMING AND USER I/O", position=(105, 25), size=1.6)
    sch.add_text("PASSIVE RF RECEIVERS", position=(35, 125), size=1.6)
    sch.add_text("GNSS, STORAGE AND REMOVABLE DISPLAY", position=(105, 125), size=1.6)
    sch.add_text("READY FOR FIRST PROTOTYPE — NOT PRODUCTION VALIDATED", position=(105, 202), size=1.4)

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
        "Device:D_TVS",
        "D1",
        "SMAJ5.0A",
        (47, 53),
        "Diode_SMD:D_SMA",
        mpn="SMAJ5.0A",
        manufacturer="Littelfuse",
    )
    label("D1", "1", "GND")
    label("D1", "2", "VBUS_PROTECTED")
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

    component(
        "Regulator_Switching:AP63203WU",
        "U3",
        "AP63203WU-7",
        (45, 101),
        "Package_TO_SOT_SMD:TSOT-23-6",
        mpn="AP63203WU-7",
        manufacturer="Diodes Incorporated",
        datasheet="https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf",
    )
    label("U3", "1", "3V3")
    label("U3", "2", "VBUS_PROTECTED")
    label("U3", "3", "VBUS_PROTECTED")
    label("U3", "4", "GND")
    label("U3", "5", "BUCK_SW")
    label("U3", "6", "BUCK_BST")
    component(
        "Device:L",
        "L1",
        "3.9uH SRN6028-3R9M",
        (60, 94),
        "Inductor_SMD:L_Bourns-SRN6028",
        mpn="SRN6028-3R9M",
        manufacturer="Bourns",
    )
    label("L1", "1", "BUCK_SW")
    label("L1", "2", "3V3")
    component("Device:C", "C2", "100n", (60, 108), "Capacitor_SMD:C_0603_1608Metric", manufacturer="Murata", mpn="GRM188R71E104KA01D")
    label("C2", "1", "BUCK_BST")
    label("C2", "2", "BUCK_SW")
    add_cap("C3", "22u", (69, 97), "3V3", "Capacitor_SMD:C_1206_3216Metric")
    add_cap("C4", "22u", (76, 97), "3V3", "Capacitor_SMD:C_1206_3216Metric")

    # ERC power-source declarations are explicit and intentionally limited to
    # the protected USB rail and regulated rail.
    component("power:PWR_FLAG", "#FLG01", "PWR_FLAG", (63, 34), "")
    label("#FLG01", "1", "VBUS_PROTECTED")
    component("power:PWR_FLAG", "#FLG02", "PWR_FLAG", (69, 34), "")
    label("#FLG02", "1", "3V3")
    component("power:PWR_FLAG", "#FLG03", "PWR_FLAG", (75, 34), "")
    label("#FLG03", "1", "GND")

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
    label("U1", "8", "CC1101_GDO0")
    label("U1", "9", "CC1101_GDO2")
    label("U1", "12", "NRF24_CE")
    label("U1", "13", "USB_D_N")
    label("U1", "14", "USB_D_P")
    label("U1", "17", "NRF24_CSN")
    label("U1", "18", "CC1101_CSN")
    label("U1", "19", "RF_SPI_MOSI")
    label("U1", "20", "RF_SPI_SCK")
    label("U1", "21", "RF_SPI_MISO")
    label("U1", "23", "GPS_PPS")
    label("U1", "24", "GPS_RX")
    label("U1", "25", "GPS_TX")
    label("U1", "27", "BOOT_N")
    label("U1", "28", "SD_SPI_MOSI")
    label("U1", "29", "SD_SPI_SCK")
    label("U1", "30", "SD_SPI_MISO")
    label("U1", "31", "SD_CSN")
    label("U1", "32", "ALERT_BUZZER_GATE")
    label("U1", "33", "ALERT_LED")
    label("U1", "34", "VIBRATION_GATE")
    label("U1", "35", "USER_BUTTON_N")
    label("U1", "36", "UART0_RX")
    label("U1", "37", "UART0_TX")
    label("U1", "38", "I2C_SCL")
    label("U1", "39", "I2C_SDA")
    for pin in ("5", "6", "7", "10", "11", "15", "16", "22", "26"):
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
    ):
        component("Connector:TestPoint", ref, net, pos, "TestPoint:TestPoint_Pad_D1.0mm", dnp=True)
        label(ref, "1", net)

    # Exact passive RF modules. Connector symbols expose every manufacturer pad
    # number; footprints encode the physical land patterns.
    component(
        "Connector_Generic:Conn_01x08",
        "RF1",
        "E01-ML01DP5",
        (32, 158),
        "SkySweep32RevC:Module_Ebyte_E01_ML01DP5",
        mpn="E01-ML01DP5",
        manufacturer="Chengdu Ebyte Electronic Technology",
    )
    for pin, net in {
        "1": "GND", "2": "3V3", "3": "NRF24_CE", "4": "NRF24_CSN",
        "5": "RF_SPI_SCK", "6": "RF_SPI_MOSI", "7": "RF_SPI_MISO",
    }.items():
        label("RF1", pin, net)
    no_connect("RF1", "8")
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
        "1": "SD_DAT2", "2": "SD_CSN", "3": "SD_SPI_MOSI", "4": "3V3",
        "5": "SD_SPI_SCK", "6": "GND", "7": "SD_SPI_MISO", "8": "SD_DAT1",
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
    label("D2", "1", "BUZZER_DRAIN")
    label("D2", "2", "3V3")

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
    label("J4", "1", "VBUS_PROTECTED")
    label("J4", "2", "VIBRATION_DRAIN")
    component("Transistor_FET:Q_NMOS_GSD", "Q2", "AO3400A", (183, 99), "Package_TO_SOT_SMD:SOT-23", mpn="AO3400A", manufacturer="Alpha & Omega Semiconductor", dnp=True)
    label("Q2", "1", "VIBRATION_GATE_R")
    label("Q2", "2", "GND")
    label("Q2", "3", "VIBRATION_DRAIN")
    add_resistor("R18", "100R", (174, 99), "VIBRATION_GATE", "VIBRATION_GATE_R", dnp=True)
    add_resistor("R19", "100k", (174, 111), "VIBRATION_GATE_R", "GND", dnp=True)
    component("Device:D", "D4", "PMEG3020EP", (190, 91), "Diode_SMD:D_SOD-128", mpn="PMEG3020EP,115", manufacturer="Nexperia", dnp=True)
    label("D4", "1", "VIBRATION_DRAIN")
    label("D4", "2", "VBUS_PROTECTED")

    # Project metadata used in title block and BOM review.
    sch.set_title_block(
        title="SkySweep32 Rev C Passive Monitor",
        date="2026-08-11",
        rev="C-PROTOTYPE",
        company="SkySweep32 Project",
        comments={
            1: "PASSIVE RECEIVE/ENERGY OBSERVATION ONLY",
            2: "READY FOR FIRST PROTOTYPE / NOT PRODUCTION VALIDATED",
            3: "Generated from reviewed exact-part contract",
        },
    )
    sch.save(SCHEMATIC)
    apply_dnp_flags(SCHEMATIC, dnp_references)
    print(f"[OK] Wrote {SCHEMATIC}")


if __name__ == "__main__":
    generate()
