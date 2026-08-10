# SkySweep32 — Hardware

Open-hardware design files and generators for the **Pro Tier** carrier board and
its field enclosure. Everything here is scripted, so the artifacts can be
regenerated on any machine — the scripts derive their output paths from their own
location (no hardcoded paths) and take optional CLI arguments.

## Contents

| File | What it is |
|------|------------|
| `skysweep32_pro.kicad_pcb` | Generated KiCad 6 PCB (120×80 mm, 2-layer FR4) |
| `build_kicad.py` | Generator for the `.kicad_pcb` above (pure Python, no deps) |
| `render_pcb.py` | Matplotlib preview renderer → `pcb_layout_preview.png` |
| `pcb_layout_preview.png` | Rendered layout preview |
| `enclosures/` | FreeCAD case generator + STL/preview files (see its README) |

## Regenerating the PCB

`build_kicad.py` has **no dependencies** (standard library only):

```bash
python3 hardware/build_kicad.py                 # writes hardware/skysweep32_pro.kicad_pcb
python3 hardware/build_kicad.py -o board.kicad_pcb
python3 hardware/build_kicad.py --stdout        # print instead of writing
```

The generator intentionally emits the KiCad 6 file format (`version
20211014`).  The title block uses `(comment 1 ...)` syntax and board arcs use
`(mid ...)`, so the checked-in PCB can be opened by KiCad 6 and newer without
manual repairs.  If a newer KiCad version upgrades the file on save, rerun the
generator to restore the portable source format.

After generation, validate the board with KiCad CLI (KiCad 8+ recommended for
the check; the board itself remains KiCad 6-compatible):

```bash
kicad-cli pcb drc --refill-zones \
  --output hardware/kicad-drc.txt hardware/skysweep32_pro.kicad_pcb
```

The current generated board routes all 94 required connections and reports no
unconnected items in KiCad 10.  Inline footprints may still produce library
configuration warnings because the generator deliberately embeds their
geometry instead of requiring a local footprint library.

Nets, footprints and placement live in `build_kicad.py`; net names have a
readable `NET["SPI_MOSI"]`-style lookup and the layout is assembled in
`build_components()`.

## Rendering the preview

`render_pcb.py` needs matplotlib (`pip install matplotlib`):

```bash
python3 hardware/render_pcb.py                   # writes hardware/pcb_layout_preview.png
python3 hardware/render_pcb.py -o preview.png --dpi 240
```

## Enclosure

See [`enclosures/README.md`](enclosures/README.md). The FreeCAD generator
(`enclosures/build_case.py`) now exports both shell STLs **headless**:

```bash
freecadcmd hardware/enclosures/build_case.py            # STL export, no GUI
```

Run it from the FreeCAD GUI to additionally produce the textured `preview_*.png`
renders.
