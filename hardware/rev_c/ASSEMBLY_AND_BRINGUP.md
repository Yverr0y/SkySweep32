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
- `assembly_top.svg` and `assembly_bottom.svg` for zoomable placement and
  orientation review;
- `assembly_drawing.pdf` and `schematic.pdf` for manufacturing review.

Specify 150 × 95 mm, four-layer FR-4, 1.6 mm finished thickness, ENIG, 35 µm
finished copper, minimum 0.20 mm spacing, minimum 0.20 mm finished drill, and the
stackup documented in [`README.md`](README.md). Require the fabricator to
field-solve the USB 90 Ω differential pair and the J5/J7 50 Ω launches against
its actual materials. Any geometry change requires new DRC and impedance review.

Do not substitute major parts by package appearance. Check every quoted MPN
against `bom_fitted.csv`. `bom.csv` also contains intentional DNP parts and is
not the assembly order list. Choose exactly one regional J5 antenna from
`assembly_items.csv`.

## Assembly order

1. Inspect bare-board dimensions, layer count, finish, edge launches, USB
   connector edge, microSD opening, and all four Ø3.2 mm mounting holes.
2. Assemble bottom-side SMT parts first, then top-side SMT parts. Follow the
   component rotations in `positions.csv`; do not infer pin 1 from renderings.
3. Inspect the BQ24074, TPS61232, and AP63203 power loops; USBLC6-2SC6
   orientation; SAM-M10Q center pad; E28/E07/RX5808 castellations; microSD socket
   coplanarity; USB-C shell joints; and J5/J7 ground tabs under magnification.
4. Reject any RX5808 module that is not the documented 12-pad
   28 × 23 × 3 mm pattern. Record its supplier, lot, markings, dimensions, and
   pin-to-function continuity before fitting it.
5. Fit remaining board-edge and connector hardware without forcing alignment.
   J5 and J7 must remain coplanar with their intended enclosure openings.
6. Leave the battery, microSD card, OLED harness, internal U.FL antenna, external
   SMA antennas, and enclosure disconnected for initial power tests.
7. Clean flux only with materials approved for the fitted components and
   sockets. Dry completely before resistance tests.

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
   SD, display, and alerts. Rev C's calculated peak is 1.35 A; unexpected
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
- **2.4 GHz module:** attach Adafruit PID 2308 directly to the E28 module's
  onboard IPEX/U.FL connector before an RF response test.
  Verify E28/SX1281 register identity, configured frequencies, and instantaneous
  RSSI response at multiple controlled levels. RSSI is energy, not protocol or
  transmitter identity.
- **855–925 MHz module:** fit the exact regional J5 antenna from
  `assembly_items.csv`. Verify CC1101 register identity, channel tuning, RSSI
  response, and spurious behavior with shielded/attenuated equipment. Do not
  command 433 MHz.
- **5.8 GHz module:** fit Taoglas `TG.59.0113` to J7. Verify the RX5808
  three-bit channel truth table, all eight expected frequencies
  (5645–5945 MHz), analog RSSI monotonicity, noise floor, and adjacent-channel
  behavior with a controlled attenuated source.
- **Wi-Fi/BLE:** verify receive/web functions without claiming Remote ID
  conformance. Standards conformance requires separate captured-frame tests.

## Battery and power-path checks

Do these only after USB-only bring-up is stable.

1. Verify the battery pack label, protection circuit, JST-PH housing orientation,
   and polarity against Adafruit PID 328 before insertion. Reverse polarity is a
   stop condition.
2. With USB absent, connect the protected pack and verify BQ24074 power-path
   startup, 5 V boost, 3.3 V rail, quiescent current, and firmware fuel-gauge
   reading. Do not infer state of charge from voltage alone.
3. Apply USB through a current-limited fixture. Record input current, charge
   current, pack voltage, system-rail droop, and temperatures at the beginning,
   middle, and charge termination. Confirm the configured 800 mA charge current
   and 1.3 A input limit are not exceeded within measurement tolerance.
4. Remove and restore USB under representative system load. Confirm the system
   transfers between USB and battery without reset or rail excursion outside the
   allowed range.
5. Stop on swelling, pack heating, connector heating, unstable switching, or
   charging behavior inconsistent with the BQ24074 configuration.

## Enclosure assembly

1. Print base, lid, and three button plungers from the checked-in STLs. Start
   with PETG, 0.20 mm layers, four perimeters, and 30% infill. Deburr openings
   without changing functional dimensions.
2. Check four DIN 934 M3 nuts fit the traps without splitting the base. Install
   them before the PCB.
3. Confirm the bare PCB lowers onto all four supports without force and every
   connector aligns. Remove it before installing electronics if this fit fails.
4. Place the protected PID 328 battery in the lower bay with the lead toward J6.
   Confirm 0.5 mm modeled floor clearance, free lead bend, no screw/nut contact,
   and no preload before fitting the PCBA.
5. Fit the PCBA. Connect Adafruit PID 2308 directly to the E28 module's onboard
   IPEX/U.FL connector and attach its 40 × 8 mm element to the marked
   underside-lid location. Dress the cable along the checked route; do not kink
   it, cross an RF keepout, or load the connector.
6. Snap Adafruit PID 326 into the lid cradle and connect the PID 4210 cable.
   Dress both 100 mm cables only within the checked service-loop corridors. The
   antenna route uses 94.96 mm closed / 90.62 mm at 30 mm lid opening
   (5.04 / 9.38 mm slack); the OLED route uses 92.60 / 89.14 mm
   (7.40 / 10.86 mm slack). Keep each loop outside antenna keepouts, button
   travel, fasteners, and connector openings.
7. Insert the three plungers from the outside. Confirm each returns freely and
   operates only its corresponding switch.
8. Lower the lid vertically while watching the battery, OLED, and antenna
   cables. Install four DIN 912 M3 × 30 screws gradually in a diagonal pattern.
   Tighten only enough to seat the lid; printed plastic is not a
   torque-qualified joint.
9. Fit exactly one regional J5 antenna
   (`ANT-868-CW-HWR-SMA` or `ANT-916-CW-HWR-SMA`) and Taoglas `TG.59.0113` to
   J7 from outside. Confirm both hinged bodies rotate without striking the case
   or blocking USB-C/microSD access.
10. Repeat USB insertion, card removal, button operation, LED visibility, lid
    opening by 30 mm, battery removal, and RF connector access. Record any CAD
    or print modification needed for fit; do not hand-correct a print and then
    call the checked CAD valid.
