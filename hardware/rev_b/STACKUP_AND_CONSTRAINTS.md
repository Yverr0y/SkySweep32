# SkySweep32 Pro Rev B stackup and routing constraints

Status: **DESIGN INPUT — UNVALIDATED IN FABRICATION — DO NOT ORDER**

This file is the routing contract for the native Rev B PCB. Values must also be
encoded in the KiCad board setup; prose alone is not a constraint.

## Fabrication target

Initial target: JLCPCB four-layer, 1.6 mm FR-4 stack
**JLC04161H-7628**. The order must use the same named stack or the board must be
recalculated before release.

| Order | Layer/material | Nominal thickness | Function |
|---:|---|---:|---|
| 1 | F.Cu | 0.035 mm | components and short signal/power routes |
| 2 | 7628 prepreg | 0.2104 mm | F.Cu to reference plane dielectric |
| 3 | In1.Cu | 0.0152 mm | continuous GND reference plane |
| 4 | FR-4 core | 1.065 mm | plane separation |
| 5 | In2.Cu | 0.0152 mm | 3V3_MAIN islands plus GND fill |
| 6 | 7628 prepreg | 0.2104 mm | B.Cu to reference plane dielectric |
| 7 | B.Cu | 0.035 mm | low-speed signals and local power |

Nominal dielectric data for preliminary calculations is Dk 4.4 for 7628 prepreg
and 4.6 for the core. The fabricator's live stackup and impedance calculator are
a release input, not optional reference material:
<https://jlcpcb.com/impedance>

The stack is symmetric. Finished thickness, copper and dielectric tolerances are
controlled by the fabrication drawing/order. Solder mask is excluded from any
unverified hand calculation.

## KiCad net classes

| Net class | Width | Clearance | Via / drill | Additional rule |
|---|---:|---:|---:|---|
| `Default` | 0.20 mm | 0.20 mm | 0.60 / 0.30 mm | low-speed digital and analog |
| `RF_SPI` | 0.25 mm | 0.25 mm | 0.60 / 0.30 mm | F.Cu over In1.GND; no stubs |
| `I2C` | 0.20 mm | 0.20 mm | 0.60 / 0.30 mm | route SDA/SCL together; avoid switch node |
| `USB90` | 0.20 mm | 0.20 mm | 0.60 / 0.30 mm | 0.15 mm pair gap; 90 Ω differential target |
| `3V3_MAIN` | 0.50 mm | 0.25 mm | 0.80 / 0.40 mm | use pours/trunks; not trace-only at regulator |
| `VBUS_PROTECTED` | 0.80 mm | 0.25 mm | 0.80 / 0.40 mm | 2 A design path; use pours where possible |
| `USB_VBUS_RAW` | 1.00 mm | 0.25 mm | 0.80 / 0.40 mm | connector → fuse/TVS/protector, shortest path |
| `SW_NODE` | 0.60 mm | 0.40 mm | no via | F.Cu only; minimum copper area |
| `VBAT_SENSE` | 0.20 mm | 0.40 mm | 0.60 / 0.30 mm | guard with GND; no parallel clock route |
| `RX5808_RSSI` | 0.20 mm | 0.40 mm | 0.60 / 0.30 mm | RC filter at ADC; guard with GND |

`USB90` is a preliminary geometry for this named stack, not a released impedance
coupon result. Before fabrication, the exact finished copper and coating options
must be entered in the fabricator calculator. Any returned width/gap replaces
these two values in both KiCad and this document. USB is full-speed, but it is
still routed as a continuous pair: no plane split, test-point stub or unmatched
via.

## Length and topology constraints

| Interface | Constraint |
|---|---|
| USB D+/D− | ≤50 mm connector-to-module, pair mismatch ≤0.5 mm, zero vias preferred, ESD device adjacent to receptacle |
| RF_SPI SCK/MOSI/MISO | MCU-to-farthest-module ≤90 mm; no branch stub >5 mm; SCK source resistor adjacent to MCU |
| Individual CSN/CE | ≤120 mm; 10 kΩ inactive-state resistor local to module/header |
| RX5808 CLOCK/DATA/SELECT | ≤120 mm; independent point-to-point routes; 22–47 Ω source damping footprint at MCU |
| RX5808 RSSI | ≤100 mm after RC node; no adjacency to buck inductor/SW or digital clocks |
| VBAT_SENSE | ≤100 mm after divider/filter; protected ADC input; no connection to RX5808_RSSI |
| I2C SDA/SCL | ≤180 mm total harness plus PCB; 4.7 kΩ pull-ups to 3V3_MAIN; no unpopulated long branch |
| GPS UART/PPS | ≤180 mm; keep PPS away from GPS antenna and RX5808 RSSI |

Lengths are maxima, not routing targets. Shorter direct routes win. No serpentine
is added unless a listed mismatch constraint requires it.

## Planes, return paths and zones

* In1.Cu is one uninterrupted GND plane except plated holes and mandatory
  antenna keepouts. No power island or signal route cuts it.
* In2.Cu uses a contiguous 3V3_MAIN area where useful; every remaining region is
  GND. Islands without a return via are forbidden.
* F.Cu and B.Cu GND zones are stitched to In1.GND along the perimeter, connector
  entries, module ground rows and power stage. Stitching pitch target is 5–10 mm,
  tightened around digital cable entries, but no via enters an antenna keepout.
* Every signal layer transition has a GND return via within 2 mm. USB pair
  transitions, if unavoidable, use symmetric signal vias and adjacent return
  vias.
* The AP63203 input capacitor, regulator ground and output capacitor form the
  shortest possible high-current loops. `SW_NODE` includes only regulator SW,
  the inductor pad and required copper; no copper exists beneath the inductor on
  other signal layers unless the manufacturer layout explicitly requires it.
* 3V3 output capacitors and each radio bulk capacitor connect directly to the
  local plane/trunk, not through thin shared daisy-chain traces.

## Mechanical and keepout constraints

* Board outline target is 130 × 96 mm with four M3 mounting holes. Final values
  come from the assembly model and are shared with the enclosure source.
* General copper-to-edge clearance: 0.50 mm. USB shell/ESD grounding and any
  qualified RX5808 launch may use an explicit local exception.
* No component courtyard crosses the board edge or another courtyard. Minimum
  component-to-component physical clearance is 1.0 mm unless connector tooling,
  module envelope or rework access requires more.
* The ESP32-S3-WROOM-1-N8 antenna keepout follows the Espressif recommended land
  pattern through **all copper and mechanical layers**, and extends to plain
  plastic in the enclosure.
* E01 onboard RF section/module edge keepout follows its exact purchased module
  drawing. No generic NRF24 footprint substitutes for it.
* GPS patch has no copper, cable, battery, fastener or display above it.
* SMA/U.FL/pigtail corridors include connector body, washer/nut tool envelope,
  cable bend radius and strain relief. Silkscreen labels state band and antenna.

## DRC release gates

A board is not released merely because KiCad reports zero violations. Required
checks are:

1. KiCad parser, schematic ERC and PCB DRC complete with no unexplained
   exclusions;
2. every schematic net maps to the PCB and every PCB copper item belongs to the
   intended net;
3. all copper zones are refilled and no unconnected islands remain;
4. board setup contains the classes and rules above;
5. four-layer stackup in the PCB matches the selected order stack;
6. native USB pair is checked against the live fabricator calculator;
7. power hot-loop and return-path review is recorded separately;
8. STEP collision and connector-access checks use the same board revision;
9. fabrication outputs are regenerated from the committed native PCB;
10. physical bring-up and RF validation remain `UNVERIFIED` until measured.
