# SkySweep32 Rev C Passive Monitor

## Maturity

**READY FOR FIRST PHYSICAL PROTOTYPE — NOT PRODUCTION VALIDATED**

Rev C is the only canonical current hardware revision. KiCad 10 ERC and PCB DRC,
CAD interference checks, firmware compilation, and fabrication export are
reproducible from this directory. No Rev C board has yet been assembled or
bench-tested. The package is suitable only for an engineering prototype whose
bring-up may expose changes.

Rev A and Rev B are historical, incompatible, and explicitly non-orderable.
The revision decision is recorded in [`ADR_001_NEW_REVISION.md`](ADR_001_NEW_REVISION.md).

## Product boundary

Rev C is a passive receive/energy-observation instrument. It contains no RF
jamming, protocol-injection, GPS-denial, battery-charging, LoRa, or 5.8 GHz
receiver hardware.

| Function | Rev C implementation | Evidence boundary |
|---|---|---|
| 855–925 MHz | Ebyte E07-900M10S / CC1101 RSSI and activity observation | Schematic/layout checked; RF response not measured |
| 2.4 GHz | Ebyte E01-ML01DP5 / nRF24L01+ one-bit RPD energy observation | Not protocol identification; RF response not measured |
| Wi-Fi/BLE | ESP32-S3 receive functions and web UI | Firmware compiles; no RF/standards conformance test |
| Position/time | u-blox SAM-M10Q-00B | UART/TIMEPULSE contract checked; no live fix test |
| Storage | Molex 104031-0811 microSD socket | SPI/card-detect contract checked; no card test |
| Display/controls | Adafruit PID 326 OLED on keyed harness, LED, buzzer, three buttons | CAD actuation checked; no physical operation test |

The complete contract, exact major MPNs, GPIO allocation, exclusions, power
budget, and mechanical datum are in [`hardware_manifest.json`](hardware_manifest.json).
Manufacturer documentation remains authoritative for parts and packages; the
KiCad schematic and PCB remain authoritative for the physical design.

## Electrical design

- MCU: Espressif `ESP32-S3-WROOM-1-N8`, 8 MB flash, no PSRAM.
- Input: GCT `USB4105-GF-A`, USB-C 5 V source, 2 A minimum. CC1/CC2 each use
  5.1 kΩ pull-downs. There is no USB-PD high-voltage negotiation.
- Protection: Bourns `MF-MSMF200-2` resettable fuse, Littelfuse `SMAJ5.0A`
  VBUS TVS, and ST `USBLC6-2SC6` USB data ESD array.
- Regulator: Diodes Incorporated `AP63203WU-7`, Bourns `SRN6028-3R9M`, 3.3 V,
  2 A rating. Calculated design peak is 1.05 A; first-board current and thermal
  measurements remain mandatory.
- Programming: native ESP32-S3 USB, manual BOOT/RESET, and labelled UART0 TX/RX
  test pads.
- Optional vibration output parts are native KiCad DNP symbols/footprints and
  are excluded from the fitted BOM and placement export.

The native KiCad 10 schematic is
[`skysweep32_rev_c.kicad_sch`](skysweep32_rev_c.kicad_sch). Fresh ERC evidence is
[`validation/erc.rpt`](validation/erc.rpt).

## PCB construction and routing

Board: 120.0 × 85.0 mm, 1.6 mm nominal, four layers, 3.0 mm corner radius, four
Ø3.2 mm grounded mounting holes on a 110 × 75 mm pattern.

| Layer | Function | Nominal construction |
|---|---|---|
| L1 / F.Cu | components, USB/RF/power signals, local ground pour | 35 µm copper |
| L2 / GND_PLANE | uninterrupted signal reference plane | 0.18 mm L1–L2 prepreg, then 35 µm copper |
| L3 / POWER_PLANE | 3V3 power plane | 1.10 mm core, then 35 µm copper |
| L4 / B.Cu | secondary signals and ground pour | 0.18 mm L3–L4 prepreg, then 35 µm copper |

Fabricator requirements: FR-4, ENIG, minimum 0.20 mm copper clearance, 0.20 mm
minimum finished drill, 0.25 mm default signal traces, 0.8 mm nominal power
traces, and 0.6/0.3 mm nominal via diameter/drill. USB D+/D− use a 0.25/0.25 mm
nominal differential geometry and must be field-solver adjusted by the selected
fabricator for 90 Ω differential. The short J5 RF launch uses 0.30 mm nominal
microstrip over the 0.18 mm L1–L2 dielectric and likewise requires fabricator
confirmation for 50 Ω.

L2 remains continuous under signal paths; the L3 power plane avoids splitting
return references. Ground stitching is intentionally concentrated at the J5
edge launch and grounded mounting features. No blanket via fence is used around
the ESP32-S3 or GNSS integrated antennas. RF1/RF2 antenna volumes and the
ESP32/GNSS antenna keepouts are free of copper and unrelated parts.

TP1–TP5 expose protected VBUS, 3V3, GND, UART0 TX, and UART0 RX. They are top
side and accessible with the lid removed; they are not external user ports.

Fresh DRC evidence is [`validation/drc.rpt`](validation/drc.rpt). The current
report records zero violations and zero unconnected pads. This proves the
encoded KiCad rules pass, not that signal integrity or RF performance has been
measured.

## Mechanical system

The enclosure is generated around the complete KiCad PCBA STEP, not around a
duplicate placeholder board. It includes:

- four DIN 912 M3 × 20 screws and DIN 934 M3 nut traps;
- PCB supports and lid compression posts at the actual mounting holes;
- USB-C insertion, microSD removal, RF1 SMA-plug, and J5 SMA-body envelopes;
- lid-mounted Adafruit PID 326 OLED snap cradle and keyed 100 mm harness;
- independent RESET, BOOT, and USER plungers plus a status-LED aperture;
- bottom, lid, button, open/closed/exploded/cutaway STEP assemblies and printable
  STL shells.

The closed outer envelope is 132.4 × 97.4 × 23.5 mm. It is an indoor printed
instrument enclosure, not sealed and not IP rated. The generator assumes PETG
for first-fit parts: 0.20 mm layer height, four perimeters, 30% infill, supports
only where the slicer requires them. Print one case and measure it before any
batch.

- Generator: [`generate_enclosure.py`](generate_enclosure.py)
- Dimensioned interface drawing:
  [`enclosure/rev_c_mechanical_drawing.svg`](enclosure/rev_c_mechanical_drawing.svg)
- Machine report:
  [`enclosure/mechanical_validation.json`](enclosure/mechanical_validation.json)
- Assembly and bring-up: [`ASSEMBLY_AND_BRINGUP.md`](ASSEMBLY_AND_BRINGUP.md)
- Physical validation: [`PROTOTYPE_VALIDATION_CHECKLIST.md`](PROTOTYPE_VALIDATION_CHECKLIST.md)

Custom RF/GNSS/OLED STEP files are explicitly maximum mechanical envelope
approximations built from reviewed drawings. They are not manufacturer precision
CAD. Standard KiCad models are used where their package geometry was checked.
CAD collision checks do not replace sample measurement.

## Reproducible verification

Requirements are in [`../toolchain.json`](../toolchain.json). From the repository
root:

```bash
python hardware/verify.py
```

The command checks the generated firmware pin contract, runs ERC and DRC,
rebuilds mechanical envelopes and the complete PCBA STEP, regenerates the
case/assemblies/drawing, executes collision and service-envelope checks,
regenerates fabrication files, builds `esp32s3_rev_c_passive`, and refreshes
renders. Use `--skip-firmware` or `--skip-renders` only for a deliberately
partial local check; the report records skipped gates.

Primary outputs:

- [`validation/verification_summary.json`](validation/verification_summary.json)
- [`manufacturing/fabrication_manifest.json`](manufacturing/fabrication_manifest.json)
- [`manufacturing/bom_fitted.csv`](manufacturing/bom_fitted.csv)
- [`manufacturing/positions.csv`](manufacturing/positions.csv)
- [`manufacturing/skysweep32_rev_c_gerbers.zip`](manufacturing/skysweep32_rev_c_gerbers.zip)

Do not infer `PROTOTYPE_ASSEMBLED`, `BENCH_TESTED`, `FIELD_TESTED`, or
`PRODUCTION_VALIDATED` from any generated file.
