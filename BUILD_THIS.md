# Build the current SkySweep32

**Current hardware: Rev C.** It is ready for its first physical prototype, not
production validated.

Start with the detailed [Rev C build guide](hardware/rev_c/BUILD.md). It is the
canonical fabrication and assembly procedure; this page only routes to the
current files.

## Current Rev C files

- [Detailed build guide](hardware/rev_c/BUILD.md)
- [Gerber and drill package](hardware/rev_c/manufacturing/skysweep32_rev_c_gerbers.zip)
- [Fitted BOM](hardware/rev_c/manufacturing/bom_fitted.csv)
- [Non-PCB assembly items](hardware/rev_c/manufacturing/assembly_items.csv)
- [Enclosure CAD and print files](hardware/rev_c/enclosure/)
- [Canonical firmware target](README.md#firmware-compatibility):
  `esp32s3_rev_c_passive`
- [Assembly and bring-up](hardware/rev_c/ASSEMBLY_AND_BRINGUP.md)
- [Physical validation checklist](hardware/rev_c/PROTOTYPE_VALIDATION_CHECKLIST.md)

> **Do not mix revisions.** Rev A, Rev B, and public `v0.6.1` binaries are
> incompatible with Rev C. Do not use their PCB files, BOMs, enclosure files,
> pin maps, wiring guides, or firmware binaries for this build.

Before purchase, run the current electrical, mechanical, fabrication, and
firmware checks specified by the [detailed guide](hardware/rev_c/BUILD.md).
A successful CAD/build check does not replace the first-board measurements in
the [physical validation checklist](hardware/rev_c/PROTOTYPE_VALIDATION_CHECKLIST.md).
