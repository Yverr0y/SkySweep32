# Legacy Rev A concept status

> **EXPERIMENTAL / UNVERIFIED / DO NOT ORDER**

The files currently stored at `hardware/skysweep32_pro.kicad_pcb` and
`hardware/enclosures/skysweep32_pro_case_*.stl` are retained as the historical
Rev A concept. They are not released manufacturing data.

## What has been checked

| Claim | Status | Evidence |
|---|---|---|
| KiCad file syntax | PASS | KiCad 10 parses the KiCad 6-format file. Issue #10 covered parser compatibility only. |
| Firmware compilation | PASS | The existing ESP32 PlatformIO targets compiled for release v0.6.1. |
| PCB electrical design | UNVERIFIED | No authoritative native schematic/ERC and no fabricated-board bring-up. |
| Footprints and module fit | UNVERIFIED | Generic module names and estimated envelopes were used. |
| RF paths and antenna ports | FAIL | The edge SMA footprints are not connected to demonstrated RF paths; do not treat them as functional antenna connections. |
| Power integrity and thermal margin | UNVERIFIED | No validated worst-case rail/transient/thermal design. |
| PCB/enclosure fit | UNVERIFIED | The enclosure was generated around nominal dimensions, not a checked full assembly with authoritative module models. |
| Connector access and serviceability | UNVERIFIED | USB, microSD, OLED and antenna mating/removal envelopes were not validated. |
| Physical prototype | NOT TESTED | No fabricated Rev A assembly has been reported or inspected by this project. |

A zero-unconnected-item PCB report means only that KiCad found no unmatched
connectivity items in that generated file. It does not establish correct module
pinouts, safe power design, RF performance, mechanical fit, manufacturability or
assembled operation.

## Subsequent revisions

Rev B was also retired as a failed/unverified historical baseline; it is not an
in-progress redesign and must not be ordered. Rev C is the only current
engineering prototype design. Its source, exact procurement data, firmware
target, and CAD evidence are under [`rev_c/`](rev_c/).

Rev A and Rev B remain incompatible with Rev C. Their PCB files, enclosures,
BOMs, pin maps, generators, and DevKit firmware are historical evidence only;
they must not be mixed into a Rev C order or build.
