# Rev C First-Prototype Assembly and Bring-Up

## Scope and safety

This procedure is for the first engineering prototype only. Rev C has passed
encoded ERC/DRC and CAD checks but has not been physically powered. Use an ESD
workstation, current-limited bench supply or current-limited USB fixture,
multimeter, oscilloscope, USB protocol-capable host, and thermal camera or
contact probe. Do not connect antennas or transmit during initial rail tests.

## PCB procurement

Use only the files in [`manufacturing/`](manufacturing/). Send the fabricator:

- `skysweep32_rev_c_gerbers.zip`;
- both PTH and NPTH drill files from `gerbers/` if the supplier does not accept
  the zip as-is;
- `bom_fitted.csv` and `positions.csv` for assembly;
- `assembly_drawing.pdf` and `schematic.pdf` for review.

Specify 120 × 85 mm, four-layer FR-4, 1.6 mm finished thickness, ENIG, 35 µm
finished copper, minimum 0.20 mm spacing, minimum 0.20 mm finished drill, and the
stackup documented in [`README.md`](README.md). Require the fabricator to
field-solve the USB 90 Ω differential pair and J5 50 Ω launch against its actual
materials. Any geometry change requires a new DRC and impedance review.

Do not substitute major parts by package appearance. Check every quoted MPN
against `bom_fitted.csv`. `bom.csv` also contains intentional DNP parts and is
not the assembly order list. Choose exactly one regional J5 antenna from
`assembly_items.csv`.

## Assembly order

1. Inspect bare-board dimensions, layer count, finish, castellations/edge launch,
   USB connector edge, microSD opening, and all four Ø3.2 mm mounting holes.
2. Assemble bottom-side SMT parts first, then top-side SMT parts. Follow the
   component rotations in `positions.csv`; do not infer pin 1 from renderings.
3. Inspect the AP63203 regulator loop, USBLC6-2SC6 orientation, SAM-M10Q pad
   wetting, E07-900M10S castellations, microSD socket coplanarity, USB-C shell
   joints, and J5 ground tabs under magnification.
4. Fit through-hole components. Keep the E01-ML01DP5 module square and within
   its courtyard so its SMA connector aligns with the right-wall opening.
5. Leave the microSD card, OLED harness, RF antennas, and enclosure disconnected
   for initial power tests.
6. Clean flux only with materials approved for the fitted components and socket.
   Dry completely before resistance tests.

## Unpowered checks

Record all values in the prototype checklist.

1. Visual inspection: no solder bridges, tombstones, reversed polarized parts,
   unsoldered exposed pads, damaged connectors, or debris under modules.
2. Verify continuity from USB shell to chassis/shield network and confirm it is
   not accidentally shorted to a signal pad.
3. Measure resistance between TP1 `VBUS_PROTECTED` and TP3 `GND`, then TP2
   `3V3` and TP3. A hard short is a stop condition. Do not use an arbitrary
   resistance pass threshold without allowing capacitors to charge; record the
   stabilized readings and investigate values below 10 Ω.
4. Verify no continuity between USB D+ and D−, or either data line and VBUS/GND.
5. Verify BOOT, RESET, and USER switches are normally open to their active nets
   and close only when pressed.

## Current-limited first power

1. Feed 5.00 V through a USB-C breakout/fixture with D+/D− disconnected. Start at
   a 100 mA current limit.
2. Confirm TP1 reaches approximately 5 V and TP2 rises toward 3.3 V. If the
   supply limits, a rail is outside 5%, or any part heats rapidly, remove power.
3. Raise the limit to 300 mA only after the first observation passes. Measure
   TP1, TP2, regulator switch-node behavior, input current, and regulator/module
   temperatures after 60 s.
4. Raise the limit to 1.5 A only when firmware starts exercising radios, GNSS,
   SD, display, and alerts. Rev C's calculated peak is 1.05 A; unexpected
   sustained current or regulator temperature must be investigated, not
   normalized in documentation.
5. Capture 3V3 ripple and transient droop at TP2 while each high-current module
   is enabled. Record oscilloscope bandwidth limit, probe method, and load state.

## USB and firmware

1. Connect a known-good USB-C data cable. Confirm ESP32-S3 ROM/CDC enumeration.
2. Hold BOOT, tap RESET, then release BOOT if manual download mode is needed.
3. Build and upload only the canonical profile:

   ```bash
   pio run -e esp32s3_rev_c_passive
   pio run -e esp32s3_rev_c_passive --target upload
   pio device monitor --baud 115200
   ```

4. Record the firmware commit, binary hash, USB VID/PID, boot log, reset reason,
   and whether native USB remains stable through ten reconnect cycles.
5. Verify RESET, BOOT, USER, status LED, and buzzer. The optional vibration parts
   are DNP and must not be marked passed unless intentionally assembled.

## Peripheral checks

Perform one function at a time before combined operation.

- **OLED:** connect Adafruit PID 326 using the keyed Adafruit PID 4210 cable;
  verify orientation before power. Check every pixel region and lid alignment.
- **microSD:** insert a known FAT32 card, verify card detect, create/read/verify a
  file, remove/reinsert ten times, and confirm the card clears the case opening.
- **GNSS:** use open sky, log time to first fix, NMEA validity, reported antenna
  status if available, and TIMEPULSE at TP/MCU input.
- **2.4 GHz module:** attach `ANT-2.4-CW-HWR-SMA` before any transmit test.
  Verify register identity and RPD response with a controlled signal source.
  RPD is one-bit energy indication, not RSSI or protocol identification.
- **855–925 MHz module:** fit the antenna variant for the configured legal band.
  Verify CC1101 register identity, channel tuning, RSSI response, and spurious
  behavior with shielded/attenuated equipment. Do not command 433 MHz.
- **Wi-Fi/BLE:** verify receive/web functions without claiming Remote ID
  conformance. Standards conformance requires separate captured-frame tests.

## Enclosure assembly

1. Print base, lid, and three button plungers from the checked-in STLs. Start with
   PETG, 0.20 mm layers, four perimeters, and 30% infill. Deburr openings without
   changing functional dimensions.
2. Check four DIN 934 M3 nuts fit the traps without splitting the base. Install
   them before the PCB.
3. Confirm the bare PCB lowers onto all four supports without force and every
   connector lines up. Remove it before installing electronics if this fit fails.
4. Fit the PCBA, route the RF1 antenna body through the right opening, and check
   J5, USB-C, and microSD service access.
5. Snap Adafruit PID 326 into the lid cradle, connect the PID 4210 cable, and
   dress the cable so it cannot touch the antenna regions or be pinched.
6. Insert the three plungers from the outside. Confirm each returns freely and
   operates only its corresponding switch.
7. Lower the lid vertically while monitoring the OLED cable. Install four DIN
   912 M3 × 20 screws gradually in a diagonal pattern. Tighten only enough to
   seat the lid; printed plastic is not a torque-qualified joint.
8. Repeat USB insertion, card removal, button operation, LED visibility, and RF
   connector access in the closed enclosure. Record any file modification needed
   for fit; do not hand-correct a print and then call the CAD validated.
