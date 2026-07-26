#!/usr/bin/env python3
"""
SkySweep32 Pro Tier — FreeCAD Case Generator (Sentinel Style)
=============================================================

Generates a field-ready enclosure for the 120x80mm carrier PCB and exports the
two shell STLs. Optional textured preview renders are produced when a FreeCAD
GUI is available.

Sentinel specs (from enclosures.md):
  - Robust, industrial box; ASA/PETG for outdoor use
  - 4x SMA/N-Type bulkhead connectors spread apart
  - Mounting brackets (wing ears) for pole/wall mount
  - Rear ventilation slots
  - OLED window on top panel; USB access port
  - M3 brass heat-set standoffs; case halves joined with M3 screws

Running
-------
FreeCAD GUI (menu Macro ▸ Execute)  — exports STLs *and* renders previews.

Headless (recommended for CI / batch STL export)::

    freecadcmd build_case.py                 # STL next to this script
    freecadcmd build_case.py /path/to/outdir

Headless mode skips the preview renders (they need the GUI) but still writes
both STL files. All output paths are derived from the script location, so the
generator is portable (previously every path was hardcoded to one Windows box).
"""

import sys
import traceback
from pathlib import Path

import FreeCAD
import Part

# GUI is optional — only needed for the preview renders and shape colours.
try:
    import FreeCADGui
    _HAVE_GUI_MODULE = True
except Exception:
    _HAVE_GUI_MODULE = False


# ── DIMENSIONS (mm) ─────────────────────────────────────────────────────────────
PCB_W = 120.0   # PCB width
PCB_H = 80.0    # PCB height (depth)
PCB_T = 1.6     # PCB thickness

WALL = 3.0      # Wall thickness
FLOOR = 3.0     # Bottom floor thickness
LID = 3.0       # Lid thickness

STANDOFF_H = 5.0    # PCB sits on 5mm standoffs from the floor
COMP_H = 22.0       # Max component height above PCB (NRF24 antenna + SMA body)
INNER_H = STANDOFF_H + PCB_T + COMP_H  # ~28.6mm inner height needed
BOT_H = 32.0        # Outer box height (bottom shell), rounded up from FLOOR+INNER_H
LID_H = 12.0        # Lid height

OUTER_W = PCB_W + 2 * WALL   # 126
OUTER_D = PCB_H + 2 * WALL   # 86
OUTER_H = BOT_H + LID_H      # 44mm total

FILLET_R = 4.0   # Corner fillet radius

# PCB corner mounting-hole positions (matching build_kicad.py holes at
# (5,5),(115,5),(5,75),(115,75) of the 120×80mm board).
MOUNT_HOLES = [(5, 5), (115, 5), (5, 75), (115, 75)]

# Lid/bottom corner boss inset from each outer corner.
CORNER_INSET = 5.0


# ── PART HELPERS ────────────────────────────────────────────────────────────────

def vec(x, y, z):
    return FreeCAD.Vector(x, y, z)


def _rot(axis, deg):
    pl = FreeCAD.Placement()
    pl.Rotation = FreeCAD.Rotation(FreeCAD.Vector(*axis), deg)
    return pl


def rot_x(deg):
    return _rot((1, 0, 0), deg)


def rot_y(deg):
    return _rot((0, 1, 0), deg)


def rot_z(deg):
    return _rot((0, 0, 1), deg)


def cylinder(r, h, pos, axis_rot=None):
    c = Part.makeCylinder(r, h)
    if axis_rot:
        c.Placement = axis_rot
    c.translate(FreeCAD.Vector(*pos))
    return c


def box(dx, dy, dz, pos=(0, 0, 0)):
    b = Part.makeBox(dx, dy, dz)
    b.translate(FreeCAD.Vector(*pos))
    return b


def fillet_edges(shape, radius, edge_indices=None):
    """Fillet all edges, or a specific subset. Returns the input on failure."""
    try:
        edges = [edge for i, edge in enumerate(shape.Edges)
                 if edge_indices is None or i in edge_indices]
        if edges:
            return shape.makeFillet(radius, edges)
    except Exception:
        pass
    return shape


def _corner_points():
    """The four outer corners of the box footprint."""
    return [(0, 0), (OUTER_W, 0), (0, OUTER_D), (OUTER_W, OUTER_D)]


def _corner_inset(bx, by):
    """Inset a corner point toward the box interior by CORNER_INSET."""
    return (bx + (CORNER_INSET if bx == 0 else -CORNER_INSET),
            by + (CORNER_INSET if by == 0 else -CORNER_INSET))


# ── ① BOTTOM SHELL ──────────────────────────────────────────────────────────────

def build_bottom():
    # Outer solid minus inner cavity → walls + floor
    bottom = box(OUTER_W, OUTER_D, BOT_H).cut(
        box(PCB_W, PCB_H, BOT_H - FLOOR, pos=(WALL, WALL, FLOOR)))
    bottom = fillet_edges(bottom, FILLET_R)

    # Mounting standoffs (OD 7mm, drilled for M3 heat-set insert)
    for hx, hy in MOUNT_HOLES:
        stoff = cylinder(3.5, STANDOFF_H, (WALL + hx, WALL + hy, FLOOR))
        ins_hole = cylinder(1.6, STANDOFF_H + 1, (WALL + hx, WALL + hy, FLOOR - 0.5))
        bottom = bottom.fuse(stoff.cut(ins_hole))

    # Corner screw bosses on the top rim for M3 screws to hold the lid
    boss_h = 5.0
    for bx, by in _corner_points():
        cx, cy = _corner_inset(bx, by)
        boss = cylinder(4.0, boss_h, (cx, cy, BOT_H))
        screw_hole = cylinder(1.5, boss_h + 1, (cx, cy, BOT_H - 1))
        bottom = bottom.fuse(boss.cut(screw_hole))

    # USB-C / Micro-USB port cutout (left wall, aligned with the ESP32)
    usb_cut = box(WALL + 2, 10, 4.5, pos=(-1, WALL + 10, FLOOR + STANDOFF_H + PCB_T + 1))
    bottom = bottom.cut(usb_cut)

    # Rear-wall ventilation slots (horizontal), stacked vertically
    slot_w, slot_l = 2.5, 30.0
    slot_start_x, slot_z_base = WALL + 10, FLOOR + 5
    for i in range(8):
        sz = slot_z_base + i * 3.2
        if sz + slot_w > BOT_H - 2:
            break
        bottom = bottom.cut(box(slot_l, WALL + 2, slot_w, pos=(slot_start_x, OUTER_D - 1, sz)))

    # SMA bulkhead holes (right wall), 4 connectors spread along Y
    sma_z = FLOOR + STANDOFF_H + PCB_T + 8
    for sy in (WALL + 12, WALL + 30, WALL + 50, WALL + 68):
        sma_cyl = cylinder(3.25, WALL + 2, (OUTER_W - 1, sy, sma_z), axis_rot=rot_y(90))
        bottom = bottom.cut(sma_cyl)

    # Wing mounting brackets (pole / wall mount) with U-bolt / zip-tie slot
    for side in (-1, 1):
        ear_y = OUTER_D / 2
        ear_x = OUTER_W / 2 + side * (OUTER_W / 2 + 12)
        ear = box(8, 40, 8, pos=(ear_x - (8 if side > 0 else 0), ear_y - 20, BOT_H - 8))
        ear_slot = box(6, 20, 10, pos=(ear_x - (7 if side > 0 else 1), ear_y - 10, BOT_H - 9))
        bottom = bottom.fuse(ear.cut(ear_slot))

    return bottom


# ── ② LID / TOP SHELL ───────────────────────────────────────────────────────────

def build_lid():
    lid = box(OUTER_W, OUTER_D, LID_H, pos=(0, 0, BOT_H)).cut(
        box(PCB_W - 2, PCB_H - 2, LID_H - LID, pos=(WALL + 1, WALL + 1, BOT_H + LID)))
    lid = fillet_edges(lid, FILLET_R)

    # OLED window (0.96" display) on the top face
    oled_w, oled_h = 26.0, 14.0
    oled_x, oled_y = WALL + 23, WALL + 5
    lid = lid.cut(box(oled_w, oled_h, LID + 2, pos=(oled_x, oled_y, BOT_H - 1)))

    # Raised frame around the OLED window so the glass rests in it
    oled_frame = box(oled_w + 2, oled_h + 2, 1.2, pos=(oled_x - 1, oled_y - 1, BOT_H + LID_H - 1.2)).cut(
        box(oled_w, oled_h, 1.5, pos=(oled_x, oled_y, BOT_H + LID_H - 1.5)))
    lid = lid.fuse(oled_frame)

    # Top ventilation slots over the GPS area
    for i in range(3):
        tv_x = WALL + 70 + i * 8
        lid = lid.cut(box(3, 25, LID + 2, pos=(tv_x, WALL + 27, BOT_H - 1)))

    # M3 through-holes in the lid corners (line up with the bottom bosses)
    for bx, by in _corner_points():
        cx, cy = _corner_inset(bx, by)
        lid = lid.cut(cylinder(1.6, LID_H + 2, (cx, cy, BOT_H - 1)))

    # GPS patch-antenna cable hole in the lid
    lid = lid.cut(cylinder(4.5, LID + 2, (WALL + 100, WALL + 65, BOT_H - 1)))

    return lid


# ── ③ VISUAL CARRIER PCB PLACEHOLDER ─────────────────────────────────────────────

def build_pcb_placeholder():
    return box(PCB_W, PCB_H, PCB_T, pos=(WALL, WALL, FLOOR + STANDOFF_H))


# ── DOCUMENT ASSEMBLY / EXPORT / RENDER ──────────────────────────────────────────

def _add(doc, name, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if FreeCAD.GuiUp and getattr(obj, "ViewObject", None):
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
    return obj


def _render_previews(out_dir, lid_obj, pcb_obj):
    view = FreeCADGui.activeDocument().activeView()

    # Isometric — full assembly
    view.viewIsometric(); view.fitAll()
    view.saveImage(str(out_dir / "preview_assembly_iso.png"), 1920, 1080, "Transparent")

    # Top view (lid visible)
    view.viewTop(); view.fitAll()
    view.saveImage(str(out_dir / "preview_top.png"), 1280, 720, "Transparent")

    # Interior — hide lid, show PCB
    lid_obj.Visibility = False
    pcb_obj.Visibility = True
    view.viewIsometric(); view.fitAll()
    view.saveImage(str(out_dir / "preview_interior.png"), 1920, 1080, "Transparent")
    lid_obj.Visibility = True

    # Right side — SMA holes
    view.viewRight(); view.fitAll()
    view.saveImage(str(out_dir / "preview_side_sma.png"), 1280, 720, "Transparent")
    print("[OK] Rendered preview images")


def generate(out_dir=None, render=True):
    out_dir = Path(out_dir) if out_dir else Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = FreeCAD.newDocument("SkySweep32_Pro_Case")

    bot_obj = _add(doc, "Case_Bottom", build_bottom(), (0.18, 0.22, 0.28), 0)
    lid_obj = _add(doc, "Case_Lid", build_lid(), (0.22, 0.27, 0.33), 35)
    pcb_obj = _add(doc, "PCB_Placeholder", build_pcb_placeholder(), (0.05, 0.45, 0.05), 0)

    doc.recompute()

    # STL export works headless (no GUI required).
    Part.export([bot_obj], str(out_dir / "skysweep32_pro_case_bottom.stl"))
    print(f"[OK] Exported: {out_dir / 'skysweep32_pro_case_bottom.stl'}")
    Part.export([lid_obj], str(out_dir / "skysweep32_pro_case_lid.stl"))
    print(f"[OK] Exported: {out_dir / 'skysweep32_pro_case_lid.stl'}")

    # Preview renders need the GUI.
    if render and FreeCAD.GuiUp and _HAVE_GUI_MODULE:
        _render_previews(out_dir, lid_obj, pcb_obj)
    else:
        print("[INFO] No GUI — skipped preview renders (STL export complete).")

    print(f"[DONE] Output written to {out_dir}/")
    return doc


if __name__ == "__main__":
    # Optional first CLI arg (e.g. `freecadcmd build_case.py /out/dir`) sets the
    # output directory; otherwise output goes next to this script.
    target = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        generate(target)
    except Exception as exc:
        log = (Path(target) if target else Path(__file__).resolve().parent) / "fc_error.log"
        try:
            log.write_text(f"{exc}\n\n{traceback.format_exc()}", encoding="utf-8")
            print(f"[ERROR] {exc} — see {log}")
        except Exception:
            print(f"[ERROR] {exc}\n{traceback.format_exc()}")
        raise
