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

## Historical material

Everything outside `rev_c/` is retained only for historical review:

- [`rev_b/`](rev_b/) documents the failed/unverified Rev B baseline;
- root-level KiCad 6 files, generators, previews, and [`enclosures/`](enclosures/)
  are legacy Rev A / issue #10 parser-compatibility artifacts.

They are **not** part of any Rev C manufacture, assembly, enclosure, pin-map,
or firmware workflow. Do not regenerate them unless investigating history. The
current build path is [`rev_c/BUILD.md`](rev_c/BUILD.md).
