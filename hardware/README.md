# SkySweep32 Hardware Revisions

## Canonical current design: Rev C

**Rev C status: READY FOR FIRST PHYSICAL PROTOTYPE — NOT PRODUCTION
VALIDATED.**

[`rev_c/`](rev_c/) is the only current hardware source. Its native KiCad 10
schematic and four-layer PCB, exact BOM, generated fabrication package, complete
PCBA STEP, co-designed enclosure, firmware pin contract, and validation evidence
are documented in [`rev_c/README.md`](rev_c/README.md).

Run the complete local gate from the repository root:

```bash
python hardware/verify.py
```

Passing this command establishes encoded ERC/DRC, CAD interference, export, and
firmware-build results. It does not establish an assembled, bench-tested,
field-tested, compliant, or production-validated device.

## Revision authority

| Revision | Status | Use |
|---|---|---|
| [`rev_c/`](rev_c/) | Ready for first physical prototype | Current engineering source and prototype fabrication package |
| [`rev_b/`](rev_b/) | Failed/unverified; do not order | Historical audit evidence only |
| Root-level files / [`enclosures/`](enclosures/) | Legacy Rev A; do not order | Historical issue #10 parser-compatibility artifacts only |

Rev C is electrically, mechanically, and firmware incompatible with Rev A and
Rev B. No legacy pin map, BOM, enclosure, generated report, or manufacturing
file applies to Rev C.

## Legacy Rev A files

This directory retains historical open-hardware concept files and generators for
the Pro Tier carrier and enclosure. They are reproducible development artifacts,
not released manufacturing data.

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

KiCad 10 reports no unconnected connectivity items in the generated file.
This is a parser/connectivity result only; it does **not** validate the circuit,
module pinouts, footprints, RF design, power integrity or manufacturability.
Inline footprints also produce library and geometry warnings.

Nets, footprints and placement live in `build_kicad.py`; net names have a
readable `NET["SPI_MOSI"]`-style lookup and the layout is assembled in
`build_components()`.

## Rendering the preview

`render_pcb.py` needs matplotlib (`pip install matplotlib`):

```bash
python3 hardware/render_pcb.py                   # writes hardware/pcb_layout_preview.png
python3 hardware/render_pcb.py -o preview.png --dpi 240
```
The renderer is a diagnostic view of the legacy concept. It reads generated
copper segments and vias, but it is not a CAD or manufacturing validation.

## Enclosure

See [`enclosures/README.md`](enclosures/README.md). The FreeCAD generator
(`enclosures/build_case.py`) now exports both shell STLs **headless**:

```bash
freecadcmd hardware/enclosures/build_case.py            # STL export, no GUI
```

Run it from the FreeCAD GUI to additionally produce the textured `preview_*.png`
renders.
