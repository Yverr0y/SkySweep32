#!/usr/bin/env python3
"""
SkySweep32 Pro Tier — KiCad 6 PCB Generator
============================================

Generates a complete ``.kicad_pcb`` file with proper footprints, nets and layout.

  Board : 120 mm x 80 mm, 2-layer (F.Cu + B.Cu), 1.6 mm FR4
  Tier  : PRO — ESP32 + NRF24 + CC1101 + RX5808 + OLED + GPS + LoRa + SD

Usage
-----
    python3 build_kicad.py                 # writes ./skysweep32_pro.kicad_pcb
    python3 build_kicad.py -o board.kicad_pcb
    python3 build_kicad.py --stdout        # print to stdout instead of a file

The output path defaults to a file *next to this script*, so the generator is
portable across machines (previously it was hardcoded to a single Windows path).
"""

import argparse
import heapq
import re
import math
import uuid
from datetime import datetime
from pathlib import Path

# ─── NETS ──────────────────────────────────────────────────────────────────────
# Net index → net name. Indices are referenced by the footprint net-maps below.
NETS = {
    0:  "",
    1:  "GND",
    2:  "VCC_5V",
    3:  "VCC_3V3",
    4:  "SPI_MOSI",      # GPIO23
    5:  "SPI_MISO",      # GPIO19
    6:  "SPI_SCK",       # GPIO18
    7:  "NRF_CS",        # GPIO15
    8:  "NRF_CE",        # GPIO32
    9:  "CC_CS",         # GPIO5
    10: "RX_CS",         # GPIO13
    11: "RX_RSSI",       # GPIO34 ADC
    12: "I2C_SDA",       # GPIO21
    13: "I2C_SCL",       # GPIO22
    14: "GPS_RX",        # GPIO16 (ESP RX ← GPS TX)
    15: "GPS_TX",        # GPIO17 (ESP TX → GPS RX)
    16: "LORA_CS",       # GPIO14
    17: "LORA_DIO0",     # GPIO33
    18: "LORA_DIO1",     # GPIO35
    19: "LORA_RST",      # GPIO12
    20: "SD_CS",         # GPIO27
    21: "BUZZER",        # GPIO4
    22: "BAT_ADC",       # GPIO36 (through voltage divider)
    23: "BAT_VRAW",      # Raw battery voltage (before divider)
    24: "ALERT_LED",     # GPIO2
    25: "VIBRATION",     # GPIO0
    26: "LED_ANODE",     # LED current-limited node
}

# Convenience reverse lookup (name → index) for readable call sites.
NET = {name: idx for idx, name in NETS.items() if name}


def uid():
    return str(uuid.uuid4())


def net_str(idx):
    """Render a ``(net ...)`` clause, or an empty string for net 0."""
    if idx == 0:
        return ""
    return f'(net {idx} "{NETS[idx]}")'


# ─── PRIMITIVE EMIT HELPERS ────────────────────────────────────────────────────
# Small builders shared by every footprint so the S-expression formatting lives
# in exactly one place.

def _effects(size, thick):
    return f'(effects (font (size {size} {size}) (thickness {thick})))'


def gr_line(x1, y1, x2, y2, layer, width=0.1):
    return f'  (gr_line (start {x1} {y1}) (end {x2} {y2}) (layer "{layer}") (width {width}) (tstamp {uid()}))'


def gr_arc(sx, sy, mx, my, ex, ey, layer, width=0.1):
    return f'  (gr_arc (start {sx} {sy}) (mid {mx} {my}) (end {ex} {ey}) (layer "{layer}") (width {width}) (tstamp {uid()}))'


def gr_text(t, x, y, layer, size=1.0, thick=0.15, extra=""):
    """Board-level text. ``extra`` allows e.g. ``(justify mirror)`` inside effects."""
    eff = f'(effects (font (size {size} {size}) (thickness {thick})){extra})'
    return f'''  (gr_text "{t}" (at {x} {y}) (layer "{layer}")
    {eff} (tstamp {uid()}))'''


def fp_ref(ref, x, y, layer, size=1, thick=0.15):
    return (f'    (fp_text reference "{ref}" (at {x} {y}) (layer "{layer}")\n'
            f'      {_effects(size, thick)} (tstamp {uid()}))')


def fp_val(value, x, y, layer, size=1, thick=0.15):
    return (f'    (fp_text value "{value}" (at {x} {y}) (layer "{layer}")\n'
            f'      {_effects(size, thick)} (tstamp {uid()}))')


def fp_rect(x1, y1, x2, y2, layer, width):
    return f'    (fp_rect (start {x1} {y1}) (end {x2} {y2}) (layer "{layer}") (width {width}) (tstamp {uid()}))'


def fp_circle(cx, cy, ex, ey, layer, width):
    return f'    (fp_circle (center {cx} {cy}) (end {ex} {ey}) (layer "{layer}") (width {width}) (tstamp {uid()}))'


def fp_line(x1, y1, x2, y2, layer, width):
    return f'    (fp_line (start {x1} {y1}) (end {x2} {y2}) (layer "{layer}") (width {width}) (tstamp {uid()}))'


# ─── BOARD OUTLINE (120×80mm with rounded corners r=3mm) ──────────────────────

def board_outline(w=120, h=80, r=3):
    k = r / math.sqrt(2)
    lines = [
        # Straight edges
        gr_line(r, 0,   w-r, 0,   "Edge.Cuts", 0.1),
        gr_line(w, r,   w,   h-r, "Edge.Cuts", 0.1),
        gr_line(r, h,   w-r, h,   "Edge.Cuts", 0.1),
        gr_line(0, r,   0,   h-r, "Edge.Cuts", 0.1),
        # Closed quarter-circle corners.  KiCad 6+ requires an explicit mid.
        gr_arc(0, r,       r-k, r-k,       r, 0,       "Edge.Cuts", 0.1),
        gr_arc(w-r, 0,     w-r+k, r-k,     w, r,       "Edge.Cuts", 0.1),
        gr_arc(w, h-r,     w-r+k, h-r+k,   w-r, h,     "Edge.Cuts", 0.1),
        gr_arc(r, h,       r-k, h-r+k,     0, h-r,     "Edge.Cuts", 0.1),
    ]
    return "\n".join(lines)


# ─── MOUNTING HOLE M3 ──────────────────────────────────────────────────────────

def mounting_hole(x, y, ref):
    return f'''  (footprint "MountingHole:MountingHole_3.2mm_M3" (layer "F.Cu")
    (at {x} {y})
{fp_ref(ref, 0, -2.5, "F.Fab")}
{fp_val("MH_M3", 0, 2.5, "F.Fab")}
{fp_circle(0, 0, 2.2, 0, "F.CrtYd", 0.05)}
{fp_circle(0, 0, 1.6, 0, "Edge.Cuts", 0.1)}
    (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers *.Cu *.Mask) (tstamp {uid()}))
  )'''


# ─── GENERIC PIN HEADER 1×N ───────────────────────────────────────────────────

def header_1xN(ref, value, x, y, n, net_map=None, angle=0):
    """
    1×N through-hole pin header, 2.54mm pitch.
    net_map: dict {pin_number(1-based): net_index}
    """
    if net_map is None:
        net_map = {}
    pitch = 2.54
    pad_size = 1.7
    drill = 1.0
    courtyard_w = 2.54 + 1.0

    fp = f'''  (footprint "Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical" (layer "F.Cu")
    (at {x} {y} {angle})
{fp_ref(ref, 0, -(n*pitch/2 + 1.5), "F.SilkS", 0.8, 0.12)}
{fp_val(value, 0, n*pitch/2 + 1.5, "F.Fab", 0.8, 0.12)}
{fp_rect(-courtyard_w/2, -pitch/2-0.5, courtyard_w/2, (n-1)*pitch+pitch/2+0.5, "F.CrtYd", 0.05)}
{fp_rect(-1.0, -pitch/2-0.3, 1.0, (n-1)*pitch+pitch/2+0.3, "F.Fab", 0.1)}
'''
    for i in range(1, n+1):
        net_idx = net_map.get(i, 0)
        py = (i-1) * pitch
        shape = "rect" if i == 1 else "oval"
        net_clause = f' {net_str(net_idx)}' if net_idx else ''
        fp += f'    (pad "{i}" thru_hole {shape} (at 0 {py}) (size {pad_size} {pad_size}) (drill {drill}) (layers "*.Cu" "*.Mask"){net_clause} (tstamp {uid()}))\n'
    fp += '  )'
    return fp


# ─── GENERIC PIN HEADER 2×N ───────────────────────────────────────────────────

def header_2xN(ref, value, x, y, n, net_map=None, angle=0):
    """
    2×N dual-row through-hole pin header, 2.54mm pitch.
    net_map: dict {pin_number(1-based): net_index}
    Pin numbering: odd=left column (col 0), even=right column (col 1)
    Rows go top-to-bottom.
    """
    if net_map is None:
        net_map = {}
    pitch = 2.54
    pad_size = 1.7
    drill = 1.0

    fp = f'''  (footprint "Connector_PinHeader_2.54mm:PinHeader_2x{n:02d}_P2.54mm_Vertical" (layer "F.Cu")
    (at {x} {y} {angle})
{fp_ref(ref, 0, -(n*pitch/2 + 1.5), "F.SilkS", 0.8, 0.12)}
{fp_val(value, 0, n*pitch/2 + 1.5, "F.Fab", 0.8, 0.12)}
{fp_rect(-pitch-0.5, -pitch/2-0.5, pitch+0.5, (n-1)*pitch+pitch/2+0.5, "F.CrtYd", 0.05)}
'''
    for row in range(n):
        # Left column: pin 2*row+1, at (-1.27, row*pitch)
        # Right column: pin 2*row+2, at (+1.27, row*pitch)
        for col, px_off in enumerate([-1.27, 1.27]):
            pin_num = 2 * row + col + 1
            net_idx = net_map.get(pin_num, 0)
            py = row * pitch
            shape = "rect" if pin_num == 1 else "oval"
            net_clause = f' {net_str(net_idx)}' if net_idx else ''
            fp += f'    (pad "{pin_num}" thru_hole {shape} (at {px_off} {py}) (size {pad_size} {pad_size}) (drill {drill}) (layers "*.Cu" "*.Mask"){net_clause} (tstamp {uid()}))\n'
    fp += '  )'
    return fp


# ─── ESP32 DevKit V1 30-pin socket (2×15) ─────────────────────────────────────
# Left row (L, col A, pin 1-15 top→bottom):
# 1=3V3, 2=EN, 3=GPIO36(VP), 4=GPIO39(VN), 5=GPIO34, 6=GPIO35,
# 7=GPIO32, 8=GPIO33, 9=GPIO25, 10=GPIO26, 11=GPIO27, 12=GPIO14,
# 13=GPIO12, 14=GND, 15=GPIO13
#
# Right row (R, col B, pin 16-30 top→bottom):
# 16=VIN(5V), 17=GND, 18=GPIO22, 19=GPIO21, 20=GPIO0, 21=TX0(1),
# 22=RX0(3), 23=GPIO19, 24=GPIO18, 25=GPIO5, 26=GPIO17, 27=GPIO16,
# 28=GPIO4, 29=GPIO2, 30=GPIO15

def esp32_socket(x, y):
    """
    Two separate 1×15 headers side by side (standard DevKit V1 socket approach).
    Row spacing: 25.4mm (1 inch) between columns.
    """
    # Left header net map (pin 1-15)
    left_nets = {
        1:  3,   # 3V3 → VCC_3V3
        2:  0,   # EN (no net, user controlled)
        3:  22,  # GPIO36 → BAT_ADC
        4:  0,   # GPIO39 (optional I2S data, no Pro header net)
        5:  11,  # GPIO34 → RX_RSSI
        6:  18,  # GPIO35 → LORA_DIO1
        7:  8,   # GPIO32 → NRF_CE
        8:  17,  # GPIO33 → LORA_DIO0
        9:  0,   # GPIO25 (DAC1, unused in Pro)
        10: 0,   # GPIO26 (DAC2, unused in Pro)
        11: 20,  # GPIO27 → SD_CS
        12: 16,  # GPIO14 → LORA_CS
        13: 19,  # GPIO12 → LORA_RST
        14: 1,   # GND
        15: 10,  # GPIO13 → RX_CS
    }
    # Right header net map (pin 1-15, maps to ESP32 pins R1-R15)
    right_nets = {
        1:  2,   # VIN → VCC_5V
        2:  1,   # GND
        3:  13,  # GPIO22 → I2C_SCL
        4:  12,  # GPIO21 → I2C_SDA
        5:  25,  # GPIO0 → VIBRATION (buffered motor driver)
        6:  0,   # GPIO1 (TX0/UART0)
        7:  0,   # GPIO3 (RX0/UART0)
        8:  5,   # GPIO19 → SPI_MISO
        9:  6,   # GPIO18 → SPI_SCK
        10: 9,   # GPIO5  → CC_CS
        11: 15,  # GPIO17 → GPS_TX
        12: 14,  # GPIO16 → GPS_RX
        13: 21,  # GPIO4  → BUZZER
        14: 24,  # GPIO2  → ALERT_LED
        15: 7,   # GPIO15 → NRF_CS
    }

    # Left header at (x, y), Right header at (x + 25.4, y)
    parts = [
        header_1xN("J_ESP32_L", "ESP32 Left", x, y, 15, left_nets),
        header_1xN("J_ESP32_R", "ESP32 Right", x + 25.4, y, 15, right_nets),
    ]
    return "\n".join(parts)


# ─── AMS1117-3.3V LDO (SOT-223) ───────────────────────────────────────────────

def ams1117(x, y):
    # SOT-223: pins: 1=ADJ/GND, 2=OUTPUT(tab), 3=INPUT, tab=OUTPUT
    # We use it as fixed 3.3V: pin1=GND, pin2/tab=3V3 out, pin3=5V in
    return f'''  (footprint "Package_TO_SOT_SMD:SOT-223-3_TabPin2" (layer "F.Cu")
    (at {x} {y})
{fp_ref("U1", 0, -4.5, "F.SilkS")}
{fp_val("AMS1117-3.3", 0, 4.5, "F.Fab")}
{fp_rect(-4, -2.5, 4, 4.5, "F.CrtYd", 0.05)}
{fp_rect(-2.3, -1.5, 2.3, 1.5, "F.Fab", 0.1)}
{fp_line(-2.3, -1.5, -2.3, 1.5, "F.Fab", 0.1)}
    (pad "1" smd rect (at -2.3 1.8) (size 1.5 2.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(1)} (tstamp {uid()}))
    (pad "2" smd rect (at 0 1.8) (size 1.5 2.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(3)} (tstamp {uid()}))
    (pad "3" smd rect (at 2.3 1.8) (size 1.5 2.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(2)} (tstamp {uid()}))
    (pad "4" smd rect (at 0 -1.5) (size 3.6 2.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(3)} (tstamp {uid()}))
  )'''


# ─── CAPACITOR SMD 0805 ────────────────────────────────────────────────────────

_cap_count = [0]


def cap_smd(x, y, value, net_a, net_b, ref=None):
    _cap_count[0] += 1
    r = ref or f"C{_cap_count[0]}"
    return f'''  (footprint "Capacitor_SMD:C_0805_2012Metric" (layer "F.Cu")
    (at {x} {y})
{fp_ref(r, 0, -1.5, "F.SilkS", 0.6, 0.09)}
{fp_val(value, 0, 1.5, "F.Fab", 0.6, 0.09)}
{fp_rect(-1.8, -1.0, 1.8, 1.0, "F.CrtYd", 0.05)}
    (pad "1" smd rect (at -1.5 0) (size 1.0 1.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(net_a)} (tstamp {uid()}))
    (pad "2" smd rect (at  1.5 0) (size 1.0 1.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(net_b)} (tstamp {uid()}))
  )'''


# ─── ELECTROLYTIC CAPACITOR TH ────────────────────────────────────────────────

_ecap_count = [0]


def cap_electrolytic_th(x, y, value, net_pos, net_neg, ref=None):
    _ecap_count[0] += 1
    r = ref or f"CE{_ecap_count[0]}"
    return f'''  (footprint "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm" (layer "F.Cu")
    (at {x} {y})
{fp_ref(r, 0, -4.5, "F.SilkS", 0.8, 0.12)}
{fp_val(value, 0, 4.5, "F.Fab", 0.8, 0.12)}
{fp_circle(0, 0, 3.8, 0, "F.CrtYd", 0.05)}
{fp_circle(0, 0, 3.15, 0, "F.Fab", 0.1)}
{fp_line(-1, -3.15, 1, -3.15, "F.Fab", 0.3)}
    (pad "1" thru_hole circle (at -1.25 0) (size 1.8 1.8) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(net_pos)} (tstamp {uid()}))
    (pad "2" thru_hole oval (at  1.25 0) (size 1.8 1.8) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(net_neg)} (tstamp {uid()}))
  )'''


# ─── RESISTOR SMD 0805 ────────────────────────────────────────────────────────

_res_count = [0]


def res_smd(x, y, value, net_a, net_b, ref=None):
    _res_count[0] += 1
    r = ref or f"R{_res_count[0]}"
    return f'''  (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
    (at {x} {y})
{fp_ref(r, 0, -1.5, "F.SilkS", 0.6, 0.09)}
{fp_val(value, 0, 1.5, "F.Fab", 0.6, 0.09)}
{fp_rect(-1.8, -1.0, 1.8, 1.0, "F.CrtYd", 0.05)}
    (pad "1" smd rect (at -1.5 0) (size 1.0 1.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(net_a)} (tstamp {uid()}))
    (pad "2" smd rect (at  1.5 0) (size 1.0 1.2) (layers "F.Cu" "F.Mask" "F.Paste") {net_str(net_b)} (tstamp {uid()}))
  )'''


# ─── EDGE-MOUNT SMA CONNECTOR ─────────────────────────────────────────────────

_sma_count = [0]


def sma_edge(x, y, ref_label):
    _sma_count[0] += 1
    r = f"J_SMA{_sma_count[0]}"
    # Simplified SMA edge mount footprint
    return f'''  (footprint "Connector_Coaxial:SMA_Amphenol_132289_EdgeMount" (layer "F.Cu")
    (at {x} {y} 90)
{fp_ref(r, 0, -5, "F.SilkS", 0.8, 0.12)}
{fp_val(ref_label, 0, 5, "F.Fab", 0.8, 0.12)}
{fp_rect(-4, -3, 4, 7, "F.CrtYd", 0.05)}
{fp_rect(-2.3, -1.5, 2.3, 5, "F.Fab", 0.1)}
    (pad "1" thru_hole circle (at 0 0) (size 2.0 2.0) (drill 1.3) (layers "*.Cu" "*.Mask") (tstamp {uid()}))
    (pad "2" thru_hole oval (at -2.54 3.0) (size 2.0 2.0) (drill 1.3) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
    (pad "3" thru_hole oval (at  2.54 3.0) (size 2.0 2.0) (drill 1.3) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
  )'''


# ─── DC BARREL JACK (5V INPUT) ────────────────────────────────────────────────

def power_jack(x, y):
    return f'''  (footprint "Connector_BarrelJack:BarrelJack_CUI_PJ-102A_Horizontal" (layer "F.Cu")
    (at {x} {y})
{fp_ref("J_PWR", 0, -6, "F.SilkS")}
{fp_val("5V DC IN", 0, 6, "F.Fab")}
{fp_rect(-5.5, -3.5, 5.5, 6, "F.CrtYd", 0.05)}
    (pad "1" thru_hole circle (at 0 0) (size 2.4 2.4) (drill 1.5) (layers "*.Cu" "*.Mask") {net_str(2)} (tstamp {uid()}))
    (pad "2" thru_hole oval (at -3.5 0) (size 2.4 2.4) (drill 1.5) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
    (pad "3" thru_hole oval (at  3.5 0) (size 2.4 2.4) (drill 1.5) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
  )'''


# ─── LED + RESISTOR 0805 ──────────────────────────────────────────────────────

def led_indicator(x, y):
    parts = []
    # GPIO2 drives the LED through a 330Ω series resistor.
    parts.append(res_smd(x, y, "330R", 24, 26, "R_LED"))
    parts.append(f'''  (footprint "LED_THT:LED_D3.0mm" (layer "F.Cu")
    (at {x+5} {y})
{fp_ref("LED1", 0, -3, "F.SilkS", 0.8, 0.12)}
{fp_val("LED_RED", 0, 3, "F.Fab", 0.8, 0.12)}
{fp_circle(0, 0, 2.5, 0, "F.CrtYd", 0.05)}
    (pad "1" thru_hole circle (at -1.27 0) (size 1.7 1.7) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(26)} (tstamp {uid()}))
    (pad "2" thru_hole oval (at  1.27 0) (size 1.7 1.7) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
  )''')
    return "\n".join(parts)

# ─── VIBRATION MOTOR HEADER ──────────────────────────────────────────────────

def vibration_header(x, y):
    return header_1xN(
        "J_VIB", "VIBRATION MOTOR (GPIO0)", x, y, 2,
        {1: 25, 2: 1},
    )


# ─── PASSIVE BUZZER ───────────────────────────────────────────────────────────

def buzzer(x, y):
    return f'''  (footprint "Buzzer_Beeper:BZ_12x9.5mm" (layer "F.Cu")
    (at {x} {y})
{fp_ref("BZ1", 0, -7, "F.SilkS", 0.8, 0.12)}
{fp_val("BUZZER", 0, 7, "F.Fab", 0.8, 0.12)}
{fp_circle(0, 0, 7, 0, "F.CrtYd", 0.05)}
{fp_circle(0, 0, 6, 0, "F.Fab", 0.1)}
    (pad "1" thru_hole circle (at  2.54 0) (size 1.8 1.8) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(21)} (tstamp {uid()}))
    (pad "2" thru_hole oval  (at -2.54 0) (size 1.8 1.8) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
  )'''


# ─── BATTERY CONNECTOR (JST-PH 2-pin) ────────────────────────────────────────

def bat_connector(x, y):
    return f'''  (footprint "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical" (layer "F.Cu")
    (at {x} {y})
{fp_ref("J_BAT", 0, -4, "F.SilkS", 0.8, 0.12)}
{fp_val("LIPO IN", 0, 4, "F.Fab", 0.8, 0.12)}
{fp_rect(-2, -2, 2, 3.5, "F.CrtYd", 0.05)}
    (pad "1" thru_hole rect (at -1.0 0) (size 1.5 1.5) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(23)} (tstamp {uid()}))
    (pad "2" thru_hole oval (at  1.0 0) (size 1.5 1.5) (drill 0.8) (layers "*.Cu" "*.Mask") {net_str(1)} (tstamp {uid()}))
  )'''


# ─── BOARD TITLE BLOCK ────────────────────────────────────────────────────────

def title_block():
    now = datetime.now().strftime("%Y-%m-%d")
    return "\n".join([
        gr_text("SkySweep32 — Pro Tier Carrier PCB", 60, 2, "F.SilkS", 1.2, 0.18),
        gr_text(f"v1.1  {now}  GPL-3.0", 60, 4.5, "F.SilkS", 0.8, 0.12),
        gr_text("github.com/bobberdolle1/SkySweep32", 60, 78, "B.SilkS", 0.8, 0.12,
                extra=" (justify mirror)"),
    ])
# ─── DETERMINISTIC PCB ROUTER ────────────────────────────────────────────────
# The board is intentionally generated without proprietary autorouter state.
# This orthogonal two-layer router connects power and signal nets, reserves
# copper/via clearances, and leaves GND/3V3 planes to the KiCad zone filler.

GRID = 0.25
GRID_W = int(120 / GRID)
GRID_H = int(80 / GRID)
# High-fanout and physically constrained nets are routed first.
ROUTE_PRIORITY = (1, 3, 11, 9, 14, 24, 10, 2, 6, 4, 13, 8, 15, 17, 19, 21, 5, 20)


def _fmt(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _balanced(text, start):
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValueError("unbalanced S-expression")


def _float_tokens(text):
    return [float(token) for token in text.split()[:3]]


def _collect_pads(components):
    pads = []
    for component in components:
        cursor = 0
        while True:
            start = component.find("(footprint ", cursor)
            if start < 0:
                break
            footprint = _balanced(component, start)
            cursor = start + len(footprint)
            header_end = footprint.find("(fp_text")
            header = footprint if header_end < 0 else footprint[:header_end]
            footprint_at = re.search(r"\(at\s+([^)]+)\)", header)
            if not footprint_at:
                continue
            origin = _float_tokens(footprint_at.group(1))
            fx, fy = origin[:2]
            angle = math.radians(origin[2] if len(origin) > 2 else 0)
            cosine, sine = math.cos(angle), math.sin(angle)

            pad_cursor = 0
            while True:
                pad_start = footprint.find("(pad ", pad_cursor)
                if pad_start < 0:
                    break
                pad = _balanced(footprint, pad_start)
                pad_cursor = pad_start + len(pad)
                pad_kind = re.match(r'\(pad\s+"[^"]+"\s+([^\s]+)', pad)
                pad_at = re.search(r"\(at\s+([^)]+)\)", pad)
                net_match = re.search(r'\(net\s+(\d+)\s+"[^"]*"\)', pad)
                size_match = re.search(r"\(size\s+([^)]+)\)", pad)
                if not (pad_kind and pad_at):
                    continue
                net = int(net_match.group(1)) if net_match else 0
                local = _float_tokens(pad_at.group(1))
                lx, ly = local[:2]
                x = fx + cosine * lx - sine * ly
                y = fy + sine * lx + cosine * ly
                size = _float_tokens(size_match.group(1)) if size_match else [1.0]
                pads.append({
                    "net": net,
                    "x": x,
                    "y": y,
                    "kind": pad_kind.group(1),
                    "radius": max(size[:2]) / 2,
                })
    return pads


def _cell(x, y):
    return (round(x / GRID), round(y / GRID))

def _pad_clearance_radius(pad):
    return max(1, math.ceil((pad["radius"] + 0.1 + 0.2 + GRID) / GRID))


def _point(cell):
    return (cell[0] * GRID, cell[1] * GRID)


def _neighbours(cell):
    x, y = cell
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def _astar(sources, target, blocked):
    if target in sources:
        return [target]
    queue = []
    distance = {}
    previous = {}
    for source in sources:
        distance[source] = 0
        heapq.heappush(queue, (0, source))

    while queue:
        _, current = heapq.heappop(queue)
        if current == target:
            path = [current]
            while path[-1] not in sources:
                path.append(previous[path[-1]])
            path.reverse()
            return path
        current_distance = distance[current]
        for neighbour in _neighbours(current):
            nx, ny = neighbour
            if not (2 <= nx < GRID_W - 2 and 2 <= ny < GRID_H - 2):
                continue
            if neighbour != target and blocked(neighbour):
                continue
            new_distance = current_distance + 1
            if new_distance >= distance.get(neighbour, 1 << 30):
                continue
            distance[neighbour] = new_distance
            previous[neighbour] = current
            heuristic = abs(nx - target[0]) + abs(ny - target[1])
            heapq.heappush(queue, (new_distance + heuristic, neighbour))
    return None

def _astar_3d(sources, targets, blocked, via_blocked=None):
    """A* over both copper layers, including via transitions."""
    if sources & targets:
        return [next(iter(sources & targets))]
    queue = []
    distance = {}
    previous = {}
    for source in sources:
        distance[source] = 0
        heapq.heappush(queue, (0, source))

    while queue:
        _, current = heapq.heappop(queue)
        if current in targets:
            path = [current]
            while path[-1] not in sources:
                path.append(previous[path[-1]])
            path.reverse()
            return path
        layer, cx, cy = current
        neighbours = []
        for nx, ny in _neighbours((cx, cy)):
            if 2 <= nx < GRID_W - 2 and 2 <= ny < GRID_H - 2:
                neighbours.append((layer, nx, ny, 1))
        other = "B.Cu" if layer == "F.Cu" else "F.Cu"
        neighbours.append((other, cx, cy, 8))
        current_distance = distance[current]
        for next_layer, nx, ny, cost in neighbours:
            state = (next_layer, nx, ny)
            if (next_layer != layer and via_blocked is not None
                    and via_blocked(cx, cy)):
                continue
            if state not in targets and blocked(state):
                continue
            new_distance = current_distance + cost
            if new_distance >= distance.get(state, 1 << 30):
                continue
            distance[state] = new_distance
            previous[state] = current
            heuristic = min(
                abs(nx - target[1]) + abs(ny - target[2])
                for target in targets
            )
            heapq.heappush(queue, (new_distance + heuristic, state))
    return None


def _mark_clearance(reserved, path, net, layer):
    for x, y in path:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                key = (layer, x + dx, y + dy)
                if key not in reserved:
                    reserved[key] = net


def _mark_via_clearance(reserved, x, y, net):
    for layer in ("F.Cu", "B.Cu"):
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    key = (layer, x + dx, y + dy)
                    if key not in reserved:
                        reserved[key] = net

def _via_conflict(reserved, x, y, net):
    for layer in ("F.Cu", "B.Cu"):
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    owner = reserved.get((layer, x + dx, y + dy))
                    if owner is not None and owner != net:
                        return True
    return False

def _via_obstacle_conflict(net_obstacles, x, y):
    for obstacles in net_obstacles.values():
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9 and (x + dx, y + dy) in obstacles:
                    return True
    return False

def _via_hole_conflict(tht_holes, x, y):
    for hx, hy in tht_holes:
        dx, dy = x - hx, y - hy
        if dx * dx + dy * dy <= 16:
            return True
    return False

def _segment_coords(net, start, end, layer):
    x1, y1 = start
    x2, y2 = end
    return (
        f'  (segment (start {_fmt(x1)} {_fmt(y1)}) '
        f'(end {_fmt(x2)} {_fmt(y2)}) (width 0.2) '
        f'(layer "{layer}") (net {net}) (tstamp {uid()}))'
    )


def _segment(net, start, end, layer):
    return _segment_coords(net, _point(start), _point(end), layer)


def _via(net, x, y):
    return (
        f'  (via (at {_fmt(x)} {_fmt(y)}) (size 0.8) (drill 0.4) '
        f'(layers "F.Cu" "B.Cu") (net {net}) (tstamp {uid()}))'
    )


def _path_endpoint(net, cell, pad_points):
    return pad_points.get((net, cell), _point(cell))


def _append_path_segment(result, net, start, end, layer, pad_points):
    # Copper pours already join same-net THT pads; a direct ground segment
    # between two such pads is redundant and can be flagged as dangling.
    if net == 1 and (net, start) in pad_points and (net, end) in pad_points:
        return
    result.append(_segment_coords(
        net, _path_endpoint(net, start, pad_points),
        _path_endpoint(net, end, pad_points), layer))


def _path_segments(path, net, layer, pad_points=None):
    if len(path) < 2:
        return []
    if pad_points is None:
        pad_points = {}
    result = []
    start = path[0]
    previous = path[0]
    direction = None
    for current in path[1:]:
        current_direction = (current[0] - previous[0], current[1] - previous[1])
        if direction is not None and current_direction != direction:
            _append_path_segment(result, net, start, previous, layer, pad_points)
            start = previous
        direction = current_direction
        previous = current
    _append_path_segment(result, net, start, previous, layer, pad_points)
    return result


def _path_segments_3d(path, net, pad_points=None):
    tracks = []
    vias = []
    if not path:
        return tracks, vias
    if pad_points is None:
        pad_points = {}
    layer = path[0][0]
    run = [(path[0][1], path[0][2])]
    for state in path[1:]:
        next_layer, x, y = state
        if next_layer != layer:
            tracks.extend(_path_segments(run, net, layer, pad_points))
            px, py = _point((x, y))
            vias.append(_via(net, px, py))
            layer = next_layer
            run = [(x, y)]
        else:
            run.append((x, y))
    tracks.extend(_path_segments(run, net, layer, pad_points))
    return tracks, vias


def _zone(net, layer):
    polygon = "(pts (xy 1 1) (xy 119 1) (xy 119 79) (xy 1 79))"
    return f'''  (zone (net {net}) (net_name "{NETS[net]}") (layer "{layer}")
    (hatch edge 0.5)
    (connect_pads (clearance 0.3))
    (min_thickness 0.25)
    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))
    (polygon {polygon})
  )'''


def _ground_zones():
    # Keep one plane per copper layer.  3V3 is a top-side pour; GND is the
    # bottom return plane, reached from SMD pads through stitching vias.
    return "\n".join([
        _zone(1, "B.Cu"),
        _zone(3, "F.Cu"),
    ])


def route_components(components):
    """Return deterministic two-layer tracks, vias, and copper pours."""
    pads = _collect_pads(components)
    by_net = {}
    for pad in pads:
        by_net.setdefault(pad["net"], []).append(pad)

    obstacles = set()
    smd_obstacles = set()
    smd_via_obstacles = set()
    for hole_x, hole_y in ((5, 5), (115, 5), (5, 75), (115, 75)):
        hx, hy = _cell(hole_x, hole_y)
        for dx in range(-10, 11):
            for dy in range(-10, 11):
                obstacles.add((hx + dx, hy + dy))
    for pad in pads:
        px, py = _cell(pad["x"], pad["y"])
        radius = _pad_clearance_radius(pad)
        target = smd_obstacles if pad["kind"] == "smd" else obstacles
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    target.add((px + dx, py + dy))
        if pad["kind"] == "smd":
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx * dx + dy * dy <= 9:
                        smd_via_obstacles.add((px + dx, py + dy))

    tht_holes = {
        _cell(pad["x"], pad["y"])
        for pad in pads
        if pad["kind"] != "smd"
    }

    tht_pad_points = {
        (pad["net"], _cell(pad["x"], pad["y"])): (pad["x"], pad["y"])
        for pad in pads
        if pad["kind"] != "smd" and pad["net"]
    }

    reserved = {}
    tracks = []
    vias = []
    routed_layers = {}
    route_count = 0
    failed = []
    priority = {net: index for index, net in enumerate(ROUTE_PRIORITY)}
    signal_nets = sorted(
        (n for n in by_net if n != 0 and len(by_net[n]) > 1),
        key=lambda n: (priority.get(n, 99), -len(by_net[n]), n),
    )
    for net in signal_nets:
        terminals = by_net[net]
        net_obstacles = {
            "F.Cu": set(obstacles) | smd_obstacles,
            "B.Cu": set(obstacles) | smd_via_obstacles,
        }
        for pad in terminals:
            px, py = _cell(pad["x"], pad["y"])
            if pad["kind"] == "smd":
                layers = (("F.Cu", _pad_clearance_radius(pad)), ("B.Cu", 3))
            else:
                layers = (("F.Cu", _pad_clearance_radius(pad)),
                           ("B.Cu", _pad_clearance_radius(pad)))
            for layer_name, radius in layers:
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if dx * dx + dy * dy <= radius * radius:
                            net_obstacles[layer_name].discard((px + dx, py + dy))

        terminal_ids = {id(pad) for pad in terminals}
        for pad in pads:
            if id(pad) in terminal_ids:
                continue
            px, py = _cell(pad["x"], pad["y"])
            if pad["kind"] == "smd":
                layers = (("F.Cu", _pad_clearance_radius(pad)), ("B.Cu", 3))
            else:
                layers = (("F.Cu", _pad_clearance_radius(pad)),
                           ("B.Cu", _pad_clearance_radius(pad)))
            for layer_name, radius in layers:
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if dx * dx + dy * dy <= radius * radius:
                            net_obstacles[layer_name].add((px + dx, py + dy))

        routed = False
        layer_order = ("B.Cu", "F.Cu") if net == 2 else ("F.Cu", "B.Cu")
        for layer in layer_order:
            local_reserved = dict(reserved)
            if layer == "B.Cu":
                if any(
                    _via_conflict(
                        local_reserved,
                        *_cell(terminal["x"], terminal["y"]),
                        net,
                    )
                    or _via_obstacle_conflict(
                        net_obstacles,
                        *_cell(terminal["x"], terminal["y"]),
                    )
                    or _via_hole_conflict(
                        tht_holes,
                        *_cell(terminal["x"], terminal["y"]),
                    )
                    for terminal in terminals
                    if terminal["kind"] == "smd"
                ):
                    continue
                for terminal in terminals:
                    if terminal["kind"] == "smd":
                        _mark_via_clearance(
                            local_reserved,
                            *_cell(terminal["x"], terminal["y"]),
                            net,
                        )
            local_tracks = []
            tree = {_cell(terminals[0]["x"], terminals[0]["y"])}

            def blocked(cell):
                owner = local_reserved.get((layer, cell[0], cell[1]))
                return (cell in net_obstacles[layer] or
                        (owner is not None and owner != net))

            for terminal in terminals[1:]:
                target = _cell(terminal["x"], terminal["y"])
                path = _astar(tree, target, blocked)
                if path is None:
                    break
                local_tracks.extend(_path_segments(path, net, layer, tht_pad_points))
                _mark_clearance(local_reserved, path, net, layer)
                tree.update(path)
            else:
                reserved = local_reserved
                tracks.extend(local_tracks)
                routed_layers[net] = layer
                route_count += len(terminals) - 1
                routed = True
                break

        if not routed:
            local_reserved = dict(reserved)
            local_tracks = []
            local_vias = []

            def terminal_states(pad):
                cell = _cell(pad["x"], pad["y"])
                if pad["kind"] == "smd":
                    return {("F.Cu", cell[0], cell[1])}
                return {
                    ("F.Cu", cell[0], cell[1]),
                    ("B.Cu", cell[0], cell[1]),
                }

            tree = terminal_states(terminals[0])

            def blocked_3d(state):
                layer, x, y = state
                owner = local_reserved.get(state)
                return ( (x, y) in net_obstacles[layer] or
                         (owner is not None and owner != net))

            for terminal in terminals[1:]:
                path = _astar_3d(
                    tree,
                    terminal_states(terminal),
                    blocked_3d,
                    via_blocked=lambda x, y: (
                        _via_conflict(local_reserved, x, y, net)
                        or _via_obstacle_conflict(net_obstacles, x, y)
                        or _via_hole_conflict(tht_holes, x, y)
                    ),
                )
                if path is None:
                    break
                path_tracks, path_vias = _path_segments_3d(path, net, tht_pad_points)
                local_tracks.extend(path_tracks)
                local_vias.extend(path_vias)
                for index, (layer, x, y) in enumerate(path):
                    _mark_clearance(local_reserved, [(x, y)], net, layer)
                    previous_layer = path[index - 1][0] if index else layer
                    next_layer = path[index + 1][0] if index + 1 < len(path) else layer
                    if previous_layer != layer or next_layer != layer:
                        _mark_via_clearance(local_reserved, x, y, net)
                tree.update(path)
            else:
                reserved = local_reserved
                tracks.extend(local_tracks)
                vias.extend(local_vias)
                routed_layers[net] = "mixed"
                route_count += len(terminals) - 1
                routed = True

        if not routed:
            failed.append(NETS[net])


    for pad in pads:
        net = pad["net"]
        if pad["kind"] != "smd" or not net:
            continue
        if net == 1 or routed_layers.get(net) == "B.Cu":
            vias.append(_via(net, pad["x"], pad["y"]))

    if failed:
        print("[WARN] Unrouted nets: " + ", ".join(sorted(set(failed))))
    print(f"[OK] Routed connections: {route_count}, vias: {len(vias)}")
    return "\n".join(vias + tracks + [_ground_zones()])




# ─── MASTER PCB ASSEMBLY ──────────────────────────────────────────────────────

def _reset_ref_counters():
    """Reset the auto-numbering counters so repeated builds are deterministic."""
    _cap_count[0] = 0
    _ecap_count[0] = 0
    _res_count[0] = 0
    _sma_count[0] = 0


def build_components():
    """Return the ordered list of footprint / graphic S-expressions."""
    _reset_ref_counters()
    components = []

    # ── Power Section (top-left) ──────────────────────────────────────────────
    # DC Jack at left edge
    components.append(power_jack(8, 15))

    # AMS1117-3.3V LDO (5V→3.3V)
    components.append(ams1117(8, 28))

    # C_IN: 100µF electrolytic on 5V rail (after jack, before LDO)
    components.append(cap_electrolytic_th(18, 22, "100uF/16V", 2, 1, "C_IN"))

    # C_OUT: 10µF after LDO on 3.3V rail
    components.append(cap_electrolytic_th(17, 31, "10uF/10V", 3, 1, "C_OUT"))

    # ── Battery connector ─────────────────────────────────────────────────────
    components.append(bat_connector(8, 38))
    # Voltage divider for battery ADC: 100kΩ from VBAT → middle node → 100kΩ → GND
    # Middle node goes to GPIO36 (BAT_ADC)
    # VRAW (23) → R_BAT1 → BAT_ADC (22) → R_BAT2 → GND (1)
    components.append(res_smd(14, 36, "100k", 23, 22, "R_BAT1"))
    components.append(res_smd(14, 39, "100k", 22, 1,  "R_BAT2"))

    # ── ESP32 DevKit V1 Socket (center) ──────────────────────────────────────
    # Left header at (25, 12), right header at (25+25.4=50.4, 12)
    components.append(esp32_socket(25, 12))

    # ── Decoupling caps for ESP32 3.3V and 5V ────────────────────────────────
    components.append(cap_smd(30, 8, "100nF", 3, 1, "C_ESP32_A"))
    components.append(cap_smd(37, 8, "100nF", 3, 1, "C_ESP32_B"))

    # ── OLED I2C Display Header (1×4) ────────────────────────────────────────
    # Pins: 1=GND, 2=VCC, 3=SCL, 4=SDA
    oled_nets = {1: 1, 2: 3, 3: 13, 4: 12}
    components.append(header_1xN("J_OLED", "OLED SSD1306", 20, 7, 4, oled_nets))
    components.append(cap_smd(20, 3.5, "100nF", 3, 1, "C_OLED"))

    # ── NRF24L01+ 2×4 Header ─────────────────────────────────────────────────
    # Standard pinout (2×4 right-angle or vertical):
    # Pin 1=GND, 2=VCC, 3=CE, 4=CSN, 5=SCK, 6=MOSI, 7=MISO, 8=IRQ(NC)
    nrf_nets = {1: 1, 2: 3, 3: 8, 4: 7, 5: 6, 6: 4, 7: 5, 8: 0}
    components.append(header_2xN("J_NRF24", "NRF24L01+", 75, 10, 4, nrf_nets))
    # 10µF decoupling cap (NRF24 is known to be sensitive)
    components.append(cap_electrolytic_th(68, 15, "10uF/10V", 3, 1, "C_NRF24_BIG"))
    components.append(cap_smd(68, 10, "100nF", 3, 1, "C_NRF24_100N"))

    # ── CC1101 2×4 Header ─────────────────────────────────────────────────────
    # Pin 1=VCC, 2=GND, 3=MOSI, 4=SCK, 5=MISO, 6=GDO2(NC), 7=GDO0(NC), 8=CS
    cc_nets = {1: 3, 2: 1, 3: 4, 4: 6, 5: 5, 6: 0, 7: 0, 8: 9}
    components.append(header_2xN("J_CC1101", "CC1101 900MHz", 75, 28, 4, cc_nets))
    components.append(cap_smd(68, 30, "100nF", 3, 1, "C_CC1101"))

    # ── RX5808 1×5 Header ─────────────────────────────────────────────────────
    # Pin 1=5V, 2=GND, 3=RSSI(analog), 4=SPI_DATA(MOSI), 5=SPI_CLK(SCK), 6=CS(SPI_SEL)
    # Note: RX5808 needs 5V!
    rx_nets = {1: 2, 2: 1, 3: 11, 4: 4, 5: 6, 6: 10}
    components.append(header_1xN("J_RX5808", "RX5808 5.8GHz", 75, 46, 6, rx_nets))
    # RX5808 needs a 100µF cap on its 5V line
    components.append(cap_electrolytic_th(68, 48, "100uF/10V", 2, 1, "C_RX5808"))

    # ── GPS NEO-6M 1×4 Header ────────────────────────────────────────────────
    # Pin 1=VCC, 2=RX(GPS), 3=TX(GPS), 4=GND
    # GPS TX → ESP GPIO16 (GPS_RX net), GPS RX ← ESP GPIO17 (GPS_TX net)
    gps_nets = {1: 3, 2: 15, 3: 14, 4: 1}
    components.append(header_1xN("J_GPS", "GPS NEO-6M", 25, 62, 4, gps_nets))
    components.append(cap_smd(25, 58, "100nF", 3, 1, "C_GPS"))

    # ── LoRa SX1276 2×5 Header ───────────────────────────────────────────────
    # Common SX1276 module pinout (2×5):
    # 1=GND, 2=GND, 3=VCC, 4=MISO, 5=MOSI, 6=SCK, 7=NSS(CS), 8=DIO0, 9=DIO1, 10=RST
    lora_nets = {1: 1, 2: 1, 3: 3, 4: 5, 5: 4, 6: 6, 7: 16, 8: 17, 9: 18, 10: 19}
    components.append(header_2xN("J_LORA", "LoRa SX1276", 42, 62, 5, lora_nets))
    components.append(cap_smd(42, 58, "100nF", 3, 1, "C_LORA"))

    # ── MicroSD Module 1×6 Header ────────────────────────────────────────────
    # Pin 1=VCC(3.3V), 2=GND, 3=CS, 4=MOSI, 5=SCK, 6=MISO
    sd_nets = {1: 3, 2: 1, 3: 20, 4: 4, 5: 6, 6: 5}
    components.append(header_1xN("J_SD", "MicroSD SPI", 62, 62, 6, sd_nets))
    components.append(cap_smd(62, 58, "100nF", 3, 1, "C_SD"))

    # ── Buzzer ────────────────────────────────────────────────────────────────
    components.append(buzzer(88, 62))
    # Optional vibration motor output.  Use a transistor/driver; do not power
    # a motor directly from GPIO0.
    components.append(vibration_header(100, 68))

    # ── LED indicator ─────────────────────────────────────────────────────────
    components.append(led_indicator(100, 55))

    # ── SMA Connectors (edge-mount, right side of board) ─────────────────────
    # 4 antennas: CC1101 (900MHz), NRF24 (2.4GHz), RX5808 (5.8GHz), LoRa (915MHz)
    components.append(sma_edge(113, 15, "900MHz CC1101"))
    components.append(sma_edge(113, 30, "2.4GHz NRF24"))
    components.append(sma_edge(113, 45, "5.8GHz RX5808"))
    components.append(sma_edge(113, 60, "915MHz LoRa"))

    # ── Mounting Holes ────────────────────────────────────────────────────────
    components.append(mounting_hole(5,   5,  "H1"))
    components.append(mounting_hole(115, 5,  "H2"))
    components.append(mounting_hole(5,   75, "H3"))
    components.append(mounting_hole(115, 75, "H4"))

    # ── Title text ────────────────────────────────────────────────────────────
    components.append(title_block())

    return components


def _solid_zone_connections(component):
    """Use solid copper connections for thermal-starved power pads."""
    lines = []
    for line in component.splitlines():
        lines.append(line)
        if line.lstrip().startswith("(footprint "):
            lines.append("    (zone_connect 2)")
    return "\n".join(lines)


def build_pcb():
    """Assemble and return the full ``.kicad_pcb`` file contents as a string."""
    components = [
        _solid_zone_connections(component)
        for component in build_components()
    ]
    net_decls = "\n".join(f'  (net {k} "{v}")' for k, v in NETS.items())
    body = "\n".join(components)
    routes = route_components(components)

    pcb = f"""(kicad_pcb (version 20211014) (generator pcbnew)

  (general
    (thickness 1.6)
    (drawings 0)
    (tracks 0)
    (zones 0)
    (modules {len(components)})
    (nets {len(NETS)})
  )

  (paper "A3")

  (title_block
    (title "SkySweep32 Pro Tier Carrier PCB")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (rev "1.1")
    (company "SkySweep32 Project")
    (comment 1 "GPL-3.0 License — Open Hardware")
    (comment 2 "2-Layer PCB, 120x80mm, 1.6mm FR4")
    (comment 3 "Pro Tier: ESP32 + NRF24 + CC1101 + RX5808 + OLED + GPS + LoRa + SD")
  )

  (layers
    (0  "F.Cu"          signal)
    (31 "B.Cu"          signal)
    (34 "B.Mask"        user)
    (35 "F.Mask"        user)
    (36 "B.SilkS"        user)
    (37 "F.SilkS"        user)
    (40 "B.CrtYd"        user)
    (41 "F.CrtYd"        user)
    (42 "B.Fab"         user)
    (43 "F.Fab"         user)
    (44 "Edge.Cuts"     user)
  )

  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask"  (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu"    (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu"    (type "copper") (thickness 0.035))
      (layer "B.Mask"  (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
    )
    (pad_to_mask_clearance 0.1)
    (solder_mask_min_width 0.05)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (usegerberextensions false)
      (usegerberattributes true)
      (usegerberadvancedattributes true)
      (creategerberjobfile true)
      (svgprecision 6)
      (excludeedgelayer true)
      (plotframeref false)
      (viasonmask false)
      (mode 1)
      (useauxorigin false)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.0)
      (dxfpolygonmode true)
      (dxfimperialunits false)
      (dxfusepcbnewfont true)
      (psnegative false)
      (plotreference true)
      (plotvalue true)
      (plotinvisibletext false)
      (sketchpadsonfab false)
      (subtractmaskfromsilk false)
      (outputformat 1)
      (mirror false)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "gerber/")
    )
  )

{net_decls}

{board_outline(120, 80, 3)}

{body}

{routes}

)
"""
    return pcb, len(components)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the SkySweep32 Pro Tier KiCad PCB.")
    default_out = Path(__file__).resolve().parent / "skysweep32_pro.kicad_pcb"
    parser.add_argument("-o", "--output", type=Path, default=default_out,
                        help=f"output .kicad_pcb path (default: {default_out.name} next to this script)")
    parser.add_argument("--stdout", action="store_true",
                        help="write the PCB to stdout instead of a file")
    args = parser.parse_args(argv)

    pcb, n_components = build_pcb()

    if args.stdout:
        print(pcb, end="")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(pcb, encoding="utf-8")

    n_footprints = sum(1 for c in build_components() if "footprint" in c)
    print(f"[OK] Written: {args.output}")
    print(f"     Components placed: {n_footprints}")
    print(f"     Nets defined: {len(NETS)}")
    print(f"     Board: 120mm x 80mm, 2-layer FR4 1.6mm")


if __name__ == "__main__":
    main()
