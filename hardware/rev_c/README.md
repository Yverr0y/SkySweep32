# SkySweep32 Rev C Passive Monitor

## Maturity

**READY FOR FIRST PHYSICAL PROTOTYPE — NOT PRODUCTION VALIDATED**

Rev C is the only canonical current hardware revision. KiCad 10 ERC/DRC,
firmware compilation, fabrication export, full-PCBA STEP generation, and
FreeCAD interference/service-envelope checks are reproducible from this
directory. No Rev C board has been assembled or powered. The package supports
one engineering prototype spin whose bring-up may require changes; it is not a
mass-production release.

Rev A and Rev B are historical, incompatible, and non-orderable. The revision
decision is in [`ADR_001_NEW_REVISION.md`](ADR_001_NEW_REVISION.md).

## Product boundary

Rev C is a passive receive/energy-observation instrument. It has no RF jamming,
protocol-injection, GPS-denial, LoRa, trained TinyML inference, or RF
direction-finding hardware.

| Function | Rev C implementation | Evidence boundary |
|---|---|---|
| 855–925 MHz | Ebyte `E07-900M10S` / CC1101 RSSI and activity | Schematic/layout checked; RF response unmeasured; no 433 MHz operation |
| 2.4 GHz | Ebyte `E28-2G4M12SX` / SX1281 RSSI sweep | Firmware contract and CAD checked; no RF calibration or protocol identity |
| 5.8 GHz | Qualified-envelope `RX5808-2012-12P`, eight selected channels and analog RSSI | Source/pinout/calibration must pass incoming inspection and bench test |
| Wi-Fi/BLE | ESP32-S3 receive functions, web UI, ESP-NOW, experimental Remote ID | Firmware compiles; no physical or standards-conformance test |
| Position/time | u-blox `SAM-M10Q-00B` | UART/TIMEPULSE contract checked; no live-fix test |
| Storage | Molex `104031-0811` microSD | SPI/card-detect contract checked; no card test |
| Display/controls | Adafruit PID 326 OLED on PID 4210 keyed cable, LED, buzzer, three buttons | CAD fit/actuation checked; no physical operation test |
| Portable power | Adafruit PID 328 protected 1S LiPo through BQ24074 power path | Electrical/CAD design checked; charge, runtime, thermal, and safety behavior unmeasured |

The exact parts, GPIO allocation, exclusions, power contract, assembly items,
and mechanical datums are in
[`hardware_manifest.json`](hardware_manifest.json). Manufacturer documentation
defines physical reality; the KiCad schematic and PCB define the manufactured
circuit and geometry.

## Electrical design

- MCU: Espressif `ESP32-S3-WROOM-1-N16R8`, 16 MB flash and 8 MB octal PSRAM.
- USB: GCT `USB4105-GF-A`; 5 V source rated at least 2 A; 5.1 kΩ CC pull-downs;
  no USB-PD voltage negotiation.
- Protection: Bourns `MF-MSMF200-2`, Littelfuse `SMAJ5.0A`, and ST
  `USBLC6-2SC6`.
- Battery/power path: Adafruit `PID 328 / LP785060` protected 1S pack,
  `BQ24074RGTR` at 800 mA charge and 1.3 A input limit.
- Rails: `TPS61232DRCR` fixed 5 V boost with `SRN6028C-1R0Y`, then
  `AP63203WU-7` 3.3 V / 2 A buck with `SRN6028-3R9M`.
- Encoded peak estimate: 1.35 A. This is a design input, not a measured current
  or thermal result.
- Programming: native ESP32-S3 USB, manual BOOT/RESET, and labelled UART0 and
  power test pads.
- Optional vibration output parts are DNP and excluded from fitted BOM and
  placement exports.

The native KiCad schematic is
[`skysweep32_rev_c.kicad_sch`](skysweep32_rev_c.kicad_sch). Fresh unexcluded
ERC evidence is [`validation/erc.rpt`](validation/erc.rpt); the eight narrowly
documented stock-symbol footprint-filter exceptions are machine-audited in
[`validation/erc_exclusions.json`](validation/erc_exclusions.json).

## PCB construction and routing

Board: 150.0 × 95.0 mm, 1.6 mm nominal, four layers, 3.0 mm corner radius, and
four Ø3.2 mm mounting holes on a 140 × 85 mm pattern.

| Layer | Function | Nominal construction |
|---|---|---|
| L1 / F.Cu | components, USB/RF/power signals, local ground pour | 35 µm copper |
| L2 / GND_PLANE | continuous signal reference plane | 0.18 mm L1–L2 dielectric, 35 µm copper |
| L3 / POWER_PLANE | 3V3 distribution and secondary routing | 1.10 mm core, 35 µm copper |
| L4 / B.Cu | secondary signals and ground pour | 0.18 mm L3–L4 dielectric, 35 µm copper |

Fabricator requirements: FR-4, ENIG, minimum 0.20 mm copper spacing, minimum
0.20 mm finished drill, 0.25 mm default signals, 0.8 mm nominal power traces,
and 0.6/0.3 mm nominal via diameter/drill. USB D+/D− use a 0.25/0.25 mm nominal
geometry and must be field-solver adjusted for 90 Ω differential using the
fabricator's actual stackup. J5 and J7 use short 0.30 mm nominal RF launches and
likewise require 50 Ω confirmation.

L2 remains continuous under signal routes. Antenna keepouts for the
ESP32-S3, GNSS, E28, and E07 paths are free of unrelated copper and parts. The
layout's DRC result proves only the encoded KiCad rules; RF response, USB signal
integrity, power integrity, and manufacturing yield remain unmeasured.

Fresh unexcluded DRC evidence is [`validation/drc.rpt`](validation/drc.rpt).
[`validation/drc_exclusions.json`](validation/drc_exclusions.json) records the
single audited `TPS61232` mixed SMD/thermal-via footprint-type exception.
TP1–TP5 expose protected VBUS, 3V3, GND, UART0 TX, and UART0 RX with the lid
removed.

## Mechanical system

The enclosure generator consumes the complete KiCad PCBA STEP. It includes:

- a protected PID 328 battery bay below the PCBA;
- four DIN 912 M3 × 30 screws, DIN 934 M3 nut traps, PCB supports, and lid
  compression posts at the actual mounting holes;
- USB-C insertion, microSD removal, J5/J7 SMA plug, and external antenna service
  envelopes;
- Adafruit PID 2308 internal 2.4 GHz antenna and its 100 mm U.FL cable envelope;
- lid-mounted Adafruit PID 326 OLED and PID 4210 100 mm cable envelope;
- checked closed and 30 mm-open cable routes;
- independent RESET, BOOT, and USER plungers plus status-LED aperture;
- base, lid, button, service-envelope, open/closed/exploded/cutaway STEP files
  and printable STL parts.

The checked closed outer envelope is 165.4 × 117.4 × 33.5 mm. The case is an
indoor printed enclosure, not sealed and not IP rated. Start the first-fit PETG
print at 0.20 mm layers, four perimeters, and 30% infill. Measure one complete
print and the first PCBA before any batch.

- Generator: [`generate_enclosure.py`](generate_enclosure.py)
- Interface drawing:
  [`enclosure/rev_c_mechanical_drawing.svg`](enclosure/rev_c_mechanical_drawing.svg)
- Machine report:
  [`enclosure/mechanical_validation.json`](enclosure/mechanical_validation.json)
- Assembly/bring-up: [`ASSEMBLY_AND_BRINGUP.md`](ASSEMBLY_AND_BRINGUP.md)
- Physical checks:
  [`PROTOTYPE_VALIDATION_CHECKLIST.md`](PROTOTYPE_VALIDATION_CHECKLIST.md)

Custom RF/GNSS/OLED/battery STEP bodies are explicitly conservative mechanical
envelopes built from referenced drawings. They are not manufacturer precision
CAD. Standard KiCad models are used only where package geometry was checked.
CAD collision checks do not replace sample measurement.

## Reproducible verification

Requirements are pinned in [`../toolchain.json`](../toolchain.json). From the
repository root:

```bash
python hardware/verify.py
```

The command checks the generated firmware contract, runs ERC/DRC, rebuilds
mechanical envelopes and the PCBA STEP, regenerates case/assembly/drawing files,
runs collision, cable-length, and service-volume checks, regenerates fabrication
files, builds `esp32s3_rev_c_passive`, and refreshes renders. A deliberately
skipped gate is recorded as `SKIPPED`, never `PASS`.

Primary outputs:

- [`validation/verification_summary.json`](validation/verification_summary.json)
- [`manufacturing/fabrication_manifest.json`](manufacturing/fabrication_manifest.json)
- [`manufacturing/bom_fitted.csv`](manufacturing/bom_fitted.csv)
- [`manufacturing/assembly_items.csv`](manufacturing/assembly_items.csv)
- [`manufacturing/positions.csv`](manufacturing/positions.csv)
- [`manufacturing/skysweep32_rev_c_gerbers.zip`](manufacturing/skysweep32_rev_c_gerbers.zip)

Do not infer `PROTOTYPE_ASSEMBLED`, `BENCH_TESTED`, `FIELD_TESTED`, or
`PRODUCTION_VALIDATED` from any generated file.
