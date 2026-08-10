#!/usr/bin/env python3
"""
SkySweep32 Pro — PCB Layout Visualization
=========================================

Renders a readable PCB preview (PNG) matching the ``skysweep32_pro.kicad_pcb``
layout produced by ``build_kicad.py``. Requires matplotlib.

Usage
-----
    python3 render_pcb.py                    # writes ./pcb_layout_preview.png
    python3 render_pcb.py -o preview.png
    python3 render_pcb.py --dpi 240

The output path defaults to a file next to this script (previously it was
hardcoded to a single Windows path).
"""

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe

# Board dimensions (mm) — must match build_kicad.py.
W, H = 120, 80

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_SEGMENT_RE = re.compile(
    rf'\(segment\s+\(start\s+({_NUMBER})\s+({_NUMBER})\)\s+'
    rf'\(end\s+({_NUMBER})\s+({_NUMBER})\).*?'
    rf'\(layer\s+"(F\.Cu|B\.Cu)"\).*?\(net\s+(\d+)\)'
)
_VIA_RE = re.compile(
    rf'\(via\s+\(at\s+({_NUMBER})\s+({_NUMBER})\).*?\(net\s+(\d+)\)'
)

_STROKE_DARK = [pe.withStroke(linewidth=1.5, foreground='black')]
_STROKE_SILK = [pe.withStroke(linewidth=1, foreground='#0a2a0a')]


# ── DRAW HELPERS ────────────────────────────────────────────────────────────────
# Each helper takes the target axes explicitly (no module-level globals), so the
# renderer is importable and testable.

def pad(ax, x, y, w=1.7, h=1.7, color='#c8a000', shape='circle'):
    if shape == 'circle':
        ax.add_patch(plt.Circle((x, y), w / 2, color=color, zorder=5))
    else:
        ax.add_patch(patches.Rectangle((x - w / 2, y - h / 2), w, h, color=color, zorder=5))
    # Drill hole
    ax.add_patch(plt.Circle((x, y), 0.5, color='#0a2a0a', zorder=6))


def header_1xN(ax, label, x, y, n, color='#3a3a3a', pitch=2.54, horiz=False):
    """Draw a 1×N pin-header block."""
    if horiz:
        bw, bh = n * pitch + 1, pitch + 1
        bx, by = x - 0.5, y - bh / 2
    else:
        bw, bh = pitch + 1, n * pitch + 1
        bx, by = x - bw / 2, y - 0.5

    ax.add_patch(patches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.2",
        facecolor=color, edgecolor='#888888', linewidth=0.8, zorder=3))

    for i in range(n):
        if horiz:
            pad(ax, x + i * pitch, y)
        else:
            pad(ax, x, y + i * pitch)

    ax.text(bx + bw / 2, by - 2.5, label, color='white', ha='center', va='top',
            fontsize=5.5, weight='bold', path_effects=_STROKE_DARK)


def header_2xN(ax, label, x, y, n, color='#3a3a3a', pitch=2.54):
    """Draw a 2×N pin-header block."""
    bw, bh = 2 * pitch + 1, n * pitch + 1
    bx, by = x - bw / 2, y - 0.5

    ax.add_patch(patches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.2",
        facecolor=color, edgecolor='#888888', linewidth=0.8, zorder=3))

    for row in range(n):
        for ox in (-pitch / 2, pitch / 2):
            pad(ax, x + ox, y + row * pitch)

    ax.text(bx + bw / 2, by - 2.5, label, color='white', ha='center', va='top',
            fontsize=5.5, weight='bold', path_effects=_STROKE_DARK)


def comp_box(ax, label, value, x, y, w, h, color='#2a2a6a', edge='#5555cc'):
    """Generic component block (IC / module placeholder)."""
    ax.add_patch(patches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.3",
        facecolor=color, edgecolor=edge, linewidth=1.2, zorder=3))
    ax.text(x + w / 2, y + h / 2 + 1, label, color='white', ha='center', va='center',
            fontsize=6, weight='bold')
    ax.text(x + w / 2, y + h / 2 - 2, value, color='#aaaaff', ha='center', va='center',
            fontsize=4.5)


def mounting_hole(ax, x, y):
    ax.add_patch(plt.Circle((x, y), 3.2 / 2, color='#0a2a0a', zorder=4))
    # Courtyard ring
    ax.add_patch(plt.Circle((x, y), 3.5, facecolor='none', linewidth=0.5,
                            linestyle='--', edgecolor='#ff8800', zorder=5))
    # Hole outline
    ax.add_patch(patches.Circle((x, y), 3.2 / 2, fill=False, edgecolor='#ffd700',
                                linewidth=1, linestyle='--', zorder=6))


def power_trace(ax, x1, y1, x2, y2, color='#ff4444', width=2):
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=width, zorder=2, solid_capstyle='round')


def gnd_trace(ax, x1, y1, x2, y2, width=1.5):
    ax.plot([x1, x2], [y1, y2], color='#4488ff', linewidth=width, zorder=2, solid_capstyle='round')


def spi_trace(ax, x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color='#ffaa00', linewidth=0.8, zorder=2, linestyle='--', alpha=0.7)


def silk_label(ax, x, y, text, size=5, color='#ccffcc', angle=0):
    ax.text(x, y, text, color=color, ha='center', va='center', fontsize=size,
            rotation=angle, style='italic', path_effects=_STROKE_SILK)


def sma_connector(ax, x, y, label):
    """Edge-mount SMA connector."""
    ax.add_patch(patches.Rectangle((x - 4, y - 3), 8, 6,
                                   facecolor='#888888', edgecolor='#dddddd', linewidth=1.5, zorder=4))
    ax.add_patch(plt.Circle((x, y), 1.5, color='#c8a000', zorder=5))
    ax.add_patch(plt.Circle((x, y), 0.6, color='#cccccc', zorder=6))
    ax.text(x - 6, y, label, color='#ffff88', ha='right', va='center', fontsize=4.5, weight='bold')


def _small_cap(ax, x, y, label='100n'):
    ax.add_patch(patches.Rectangle((x - 1, y - 0.6), 2, 1.2,
                                   facecolor='#554400', edgecolor='#aaaa00', linewidth=0.5, zorder=3))
    ax.text(x, y + 1.5, label, color='#ffff88', ha='center', va='bottom', fontsize=3.5)


def _read_board_routes(pcb_path):
    """Read actual copper segments and vias from a generated KiCad PCB."""
    if pcb_path is None or not pcb_path.exists():
        return [], []

    segments = []
    vias = []
    for line in pcb_path.read_text(encoding='utf-8', errors='replace').splitlines():
        segment = _SEGMENT_RE.search(line)
        if segment:
            x1, y1, x2, y2, layer, net = segment.groups()
            segments.append((float(x1), float(y1), float(x2), float(y2), layer, int(net)))
            continue
        via = _VIA_RE.search(line)
        if via:
            x, y, net = via.groups()
            vias.append((float(x), float(y), int(net)))
    return segments, vias


def _draw_board_routes(ax, pcb_path):
    """Overlay generated PCB routing so the preview matches the source board."""
    segments, vias = _read_board_routes(pcb_path)
    for x1, y1, x2, y2, layer, net in segments:
        color = '#ffbf4a' if layer == 'F.Cu' else '#4d9cff'
        alpha = 0.28 if net == 1 else 0.62
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=0.45,
                alpha=alpha, zorder=1, solid_capstyle='round')
    for x, y, _ in vias:
        ax.add_patch(patches.Circle(
            (x, y), 0.45, facecolor='#d9e7ff', edgecolor='#4d9cff',
            linewidth=0.3, alpha=0.85, zorder=2))
    return len(segments), len(vias)


# ── SCENE ────────────────────────────────────────────────────────────────────────

def draw(ax, pcb_path=None):
    """Draw the stylized board layout and actual generated copper routes."""
    # Board outline + edge highlight
    ax.add_patch(patches.FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=3",
                                        linewidth=2, edgecolor='#ffd700', facecolor='#1e5c1e'))
    ax.add_patch(patches.FancyBboxPatch((0.5, 0.5), W - 1, H - 1, boxstyle="round,pad=0,rounding_size=2.5",
                                        linewidth=1, edgecolor='#2a7a2a', facecolor='none'))
    _draw_board_routes(ax, pcb_path)

    # Mounting holes
    for mx, my in [(5, 5), (115, 5), (5, 75), (115, 75)]:
        mounting_hole(ax, mx, my)
        ax.text(mx, my - 5, 'M3', color='#ffaa00', ha='center', va='top', fontsize=4)

    # Power section (top-left)
    comp_box(ax, 'J_PWR', '5V DC IN', 3, 10, 10, 8, '#5a2a00', '#ff8800')
    silk_label(ax, 8, 19.5, '5V IN', 4.5, '#ffcc88')
    comp_box(ax, 'U1', 'AMS1117-3.3', 3, 24, 10, 6, '#2a2a5a', '#8888ff')
    silk_label(ax, 8, 31.5, 'LDO 3.3V', 4.5, '#aaaaff')
    for cx, cy, cv in [(16, 19, '100µF'), (16, 27, '10µF')]:
        ax.add_patch(plt.Circle((cx, cy), 2.5, facecolor='#555500', edgecolor='#aaaa00', linewidth=1, zorder=3))
        ax.text(cx, cy - 4, cv, color='#ffff88', ha='center', va='top', fontsize=4)

    # Battery + divider
    comp_box(ax, 'J_BAT', 'JST-PH\nLiPo', 3, 34, 7, 6, '#5a1a00', '#ff6600')
    for rx, ry, rv in [(13, 33, '100k'), (13, 37, '100k')]:
        ax.add_patch(patches.Rectangle((rx - 1.5, ry - 0.6), 3, 1.2,
                                       facecolor='#4a3a00', edgecolor='#aaaa00', linewidth=0.8, zorder=3))
        ax.text(rx, ry - 1.8, rv, color='#ffff88', ha='center', va='top', fontsize=4)
    silk_label(ax, 10, 41, 'BAT DIV', 4, '#ffcc88')

    # ESP32 decoupling caps
    for cx, cy in [(30, 7.5), (37, 7.5)]:
        _small_cap(ax, cx, cy)

    # ESP32 socket (center)
    comp_box(ax, 'ESP32', 'DevKit V1\n240MHz dual-core\nWiFi + BLE', 22, 9, 30, 42, '#1a2a5a', '#4488ff')
    silk_label(ax, 37, 52.5, 'GPIO SOCKET', 5, '#88aaff')
    header_1xN(ax, 'L-ROW\n3V3..GPIO13', 25, 11, 15, color='#253a6a')
    header_1xN(ax, 'R-ROW\nVIN..GPIO15', 50, 11, 15, color='#253a6a')
    for px, py, lbl in [(28, 11, '3V3'), (28, 11 + 13 * 2.54, 'GND'),
                        (53, 11, 'VIN'), (53, 11 + 2.54, 'GND'),
                        (53, 11 + 7 * 2.54, 'MISO'), (53, 11 + 8 * 2.54, 'SCK')]:
        ax.text(px, py, lbl, color='#aaddff', va='center', fontsize=3.5)

    # NRF24 2×4
    comp_box(ax, '', '', 71, 8.5, 10, 11, '#1a4a1a', '#44aa44')
    header_2xN(ax, 'J_NRF24\nNRF24L01+\n2.4 GHz', 76, 10, 4, '#1a4a1a')
    ax.add_patch(plt.Circle((68, 13), 2, facecolor='#555500', edgecolor='#aaaa00', linewidth=0.8, zorder=3))
    _small_cap(ax, 67, 9.6)
    silk_label(ax, 76, 21, '10µF+100nF', 4, '#88ff88')

    # CC1101 2×4
    comp_box(ax, '', '', 71, 26.5, 10, 11, '#4a1a1a', '#aa4444')
    header_2xN(ax, 'J_CC1101\nCC1101\n900 MHz', 76, 28, 4, '#4a1a1a')
    _small_cap(ax, 68, 30.6)
    silk_label(ax, 76, 39, '100nF', 4, '#ff8888')

    # RX5808 1×6
    comp_box(ax, '', '', 71, 44, 10, 17, '#4a2a00', '#cc6600')
    header_1xN(ax, 'J_RX5808\nRX5808\n5.8 GHz', 76, 45, 6, color='#4a2a00')
    ax.add_patch(plt.Circle((68, 49), 2.5, facecolor='#555500', edgecolor='#aaaa00', linewidth=0.8, zorder=3))
    ax.text(68, 53, '100µF\n5V!', color='#ffaa44', ha='center', va='bottom', fontsize=3.5)

    # GPS 1×4
    comp_box(ax, '', '', 21, 60, 10, 11, '#1a3a4a', '#44aacc')
    header_1xN(ax, 'J_GPS\nNEO-6M\nUART', 26, 62, 4, color='#1a3a4a')
    _small_cap(ax, 22, 59.6)

    # LoRa 2×5
    comp_box(ax, '', '', 38, 60, 12, 15, '#3a1a4a', '#aa44cc')
    header_2xN(ax, 'J_LORA\nSX1276\n915 MHz', 44, 62, 5, '#3a1a4a')
    _small_cap(ax, 39, 59.6)

    # MicroSD 1×6
    comp_box(ax, '', '', 58, 60, 10, 17, '#2a3a2a', '#66aa66')
    header_1xN(ax, 'J_SD\nMicroSD\nSPI', 63, 62, 6, color='#2a3a2a')
    _small_cap(ax, 59, 59.6)

    # Buzzer
    ax.add_patch(plt.Circle((88, 65), 4.5, facecolor='#2a2a2a', edgecolor='#888888', linewidth=1.5, zorder=3))
    ax.text(88, 65, 'BZ1', color='white', ha='center', va='center', fontsize=5, weight='bold')
    ax.text(88, 71, 'BUZZER\nGPIO4', color='#cccccc', ha='center', va='bottom', fontsize=4)
    pad(ax, 86, 65)
    pad(ax, 90, 65)

    # LED + resistor
    ax.add_patch(patches.Rectangle((97, 53), 3, 1.2, facecolor='#4a3a00', edgecolor='#aaaa00', linewidth=0.8, zorder=3))
    ax.text(98.5, 52, '330Ω\nR_LED', color='#ffff88', ha='center', va='top', fontsize=4)
    ax.add_patch(plt.Circle((103, 54), 1.5, facecolor='#cc2200', edgecolor='#ff4444', linewidth=1.5, zorder=3))
    ax.text(103, 51.5, 'LED1\nGPIO2', color='#ff8888', ha='center', va='top', fontsize=4)
    pad(ax, 101.5, 54)
    pad(ax, 104.5, 54)

    # SMA edge connectors (right edge)
    for sy, slabel in [(13, '900 MHz\n(CC1101)'), (28, '2.4 GHz\n(NRF24)'),
                       (46, '5.8 GHz\n(RX5808)'), (61, '915 MHz\n(LoRa)')]:
        sma_connector(ax, 116, sy, slabel)

    # OLED header 1×4 (top)
    header_1xN(ax, 'J_OLED\n0.96" SSD1306 I2C', 20, 7, 4, color='#2a2a3a', horiz=True)

    # Copper routing is overlaid from the generated PCB near the board outline.

    # Title + credit
    ax.text(60, 78.5, 'SkySweep32  —  Pro Tier Carrier PCB  |  120×80mm  |  2-Layer FR4  |  v1.1',
            color='#ccffcc', ha='center', va='bottom', fontsize=7, weight='bold',
            path_effects=[pe.withStroke(linewidth=2, foreground='#0a2a0a')])
    ax.text(60, 1.5, 'github.com/bobberdolle1/SkySweep32  |  GPL-3.0 Open Hardware',
            color='#88cc88', ha='center', va='bottom', fontsize=5, style='italic')

    # Legend
    legend_items = [
        patches.Patch(color='#1a2a5a', label='ESP32 DevKit V1'),
        patches.Patch(color='#1a4a1a', label='NRF24L01+ 2.4GHz'),
        patches.Patch(color='#4a1a1a', label='CC1101 900MHz'),
        patches.Patch(color='#4a2a00', label='RX5808 5.8GHz'),
        patches.Patch(color='#1a3a4a', label='GPS NEO-6M'),
        patches.Patch(color='#3a1a4a', label='LoRa SX1276'),
        patches.Patch(color='#2a3a2a', label='MicroSD SPI'),
        patches.Patch(color='#5a2a00', label='Power Section'),
    ]
    leg = ax.legend(handles=legend_items, loc='upper right', fontsize=5.5, framealpha=0.85,
                    facecolor='#0a1a0a', labelcolor='white', edgecolor='#44aa44',
                    title='Components', title_fontsize=6)
    leg.get_title().set_color('#88ff88')

    # Scale grid
    ax.set_xlim(-5, 130)
    ax.set_ylim(-8, 85)
    ax.axis('off')
    for gx in range(0, 121, 10):
        ax.axvline(gx, color='#2a5a2a', linewidth=0.3, alpha=0.4, zorder=0)
        ax.text(gx, -1, f'{gx}', color='#4a8a4a', ha='center', va='top', fontsize=3.5)
    for gy in range(0, 81, 10):
        ax.axhline(gy, color='#2a5a2a', linewidth=0.3, alpha=0.4, zorder=0)
        ax.text(-1, gy, f'{gy}', color='#4a8a4a', ha='right', va='center', fontsize=3.5)


def render(out_path, dpi=180, pcb_path=None):
    plt.rcParams['font.family'] = 'monospace'
    fig, ax = plt.subplots(figsize=(18, 12))
    fig.patch.set_facecolor('#1a1a1a')
    ax.set_facecolor('#1a4a1a')
    ax.set_aspect('equal')

    draw(ax, pcb_path=pcb_path)

    fig.tight_layout(pad=0.2)
    fig.savefig(out_path, dpi=dpi, bbox_inches='tight', facecolor='#1a1a1a', edgecolor='none')
    plt.close(fig)
    print(f"Saved: {out_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render the SkySweep32 Pro PCB layout preview.")
    default_out = Path(__file__).resolve().parent / "pcb_layout_preview.png"
    default_pcb = Path(__file__).resolve().parent / "skysweep32_pro.kicad_pcb"
    parser.add_argument("-o", "--output", type=Path, default=default_out,
                        help=f"output PNG path (default: {default_out.name} next to this script)")
    parser.add_argument("--pcb", type=Path, default=default_pcb,
                        help=f"source PCB (default: {default_pcb.name})")
    parser.add_argument("--dpi", type=int, default=180, help="output resolution (default: 180)")
    args = parser.parse_args(argv)
    render(args.output, dpi=args.dpi, pcb_path=args.pcb)


if __name__ == "__main__":
    main()
