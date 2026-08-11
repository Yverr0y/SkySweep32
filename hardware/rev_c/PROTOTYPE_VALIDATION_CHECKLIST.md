# Rev C Physical Prototype Validation Checklist

**Prototype serial:** __________  **PCB lot:** __________  **Assembly lot:** __________

**Hardware commit:** __________  **Firmware commit:** __________  **Date:** __________

**Operator / equipment IDs:** ________________________________________________

A generated report cannot complete this checklist. Attach photographs, raw logs,
scope captures, RF analyzer files, measurements, failures, and rework history.
Mark each item `PASS`, `FAIL`, or `N/A` with a reason. Any failed safety, rail,
USB, RF, or mechanical-service item blocks advancement beyond
`READY_FOR_FIRST_PROTOTYPE`.

## A. Incoming and assembly

| ID | Observable contract | Result / evidence |
|---|---|---|
| A1 | PCB is 120.0 × 85.0 × 1.6 mm within supplier tolerance; four layers and ENIG verified from lot documents | |
| A2 | Four Ø3.2 mm holes and 110 × 75 mm pattern measured | |
| A3 | Impedance coupon/report records USB 90 Ω differential and J5 50 Ω result, or deviation is documented | |
| A4 | Fitted parts match every manufacturer/MPN row in `bom_fitted.csv`; substitutions listed and reviewed | |
| A5 | X-ray/optical inspection covers SAM-M10Q, AP63203 exposed pad, USB ESD, modules, microSD, USB-C, and J5 | |
| A6 | No shorts on VBUS_PROTECTED, 3V3, USB D+/D−, or adjacent fine-pitch pins | |
| A7 | DNP R18/R19/Q2/D4/J4 are absent unless a separately reviewed vibration option is being tested | |

## B. Power and USB

| ID | Observable contract | Result / evidence |
|---|---|---|
| B1 | Stabilized unpowered TP1–TP3 and TP2–TP3 resistance recorded | |
| B2 | 5.00 V / 100 mA limited first power does not current-limit or produce rapid heating | |
| B3 | TP1 and TP2 values are within ±5%; startup waveforms attached | |
| B4 | Idle, radio-active, SD-write, display/buzzer, and combined peak current recorded | |
| B5 | 3V3 ripple/droop under combined peak load is recorded with probe/bandwidth method and accepted by part limits | |
| B6 | AP63203, inductor, fuse, TVS, MCU, RF modules, and GNSS temperatures recorded at 5, 15, and 30 min | |
| B7 | USB-C works in both plug orientations with two known-good cables | |
| B8 | Native USB enumerates, uploads, and reconnects ten times without reset-loop or data error | |
| B9 | CC1/CC2 source behavior tested against at least two standards-compliant 5 V sources; no >5 V PD mode requested | |

## C. Firmware and local interfaces

| ID | Observable contract | Result / evidence |
|---|---|---|
| C1 | `esp32s3_rev_c_passive` exact commit builds and boots; binary hash and boot log attached | |
| C2 | RESET and BOOT each perform their documented function; USER produces only one logical press per actuation | |
| C3 | Status LED and buzzer patterns operate; no boot-strap or reset interference | |
| C4 | OLED initializes, all display regions work, and ten cable reconnects cause no connector damage | |
| C5 | microSD detect, create/write/read/hash/delete, and ten insert/remove cycles pass | |
| C6 | GNSS obtains a valid fix; time to first fix, NMEA data, and TIMEPULSE captured | |
| C7 | Wi-Fi dashboard and BLE scanning run concurrently for 30 min without watchdog/reset or unacceptable current | |
| C8 | Any Remote ID result is labelled experimental; captured frames are compared to the applicable ASTM/ASD-STAN format before a conformance claim | |

## D. Passive RF behavior

Use shielded fixtures or legally compliant low-level sources. Attach antenna only
where the test requires it. Record frequency, level, attenuation, equipment
calibration date, firmware configuration, and raw response.

| ID | Observable contract | Result / evidence |
|---|---|---|
| D1 | E01-ML01DP5/nRF24 register identity and SPI operation verified | |
| D2 | nRF24 RPD remains inactive below its specified threshold and changes under controlled 2.4 GHz energy; no RSSI/protocol claim is inferred | |
| D3 | E07-900M10S/CC1101 register identity and SPI operation verified | |
| D4 | CC1101 RSSI response measured at multiple levels on the configured 868 or 915 MHz channel; 433 MHz command is rejected/not emitted | |
| D5 | Simultaneous 2.4 GHz, sub-GHz, Wi-Fi/BLE, SD, GNSS, and display operation shows no unexplained resets, bus corruption, or GNSS loss | |
| D6 | J5 return loss/insertion behavior and RF1 antenna connection inspected or measured with the selected antennas | |
| D7 | Emissions/pre-compliance scan records unintended clocks/spurs; failures are corrected before broader use | |

## E. Enclosure fit and service

| ID | Observable contract | Result / evidence |
|---|---|---|
| E1 | Printed base/lid outer dimensions and critical openings measured; material, printer, orientation, and slicer settings recorded | |
| E2 | PCB seats on four supports without bending; all four M3 screws/nuts fit and retain after five assembly cycles | |
| E3 | No visible contact between PCBA and base/lid except designed supports/compression posts | |
| E4 | OLED snaps in/out without damage, aperture is aligned, and cable is neither pinched nor routed over antenna keepouts | |
| E5 | RESET/BOOT/USER plungers return freely, operate only their switches, and pass 100 actuations | |
| E6 | USB-C cable inserts/removes without case load on connector; both plug orientations work | |
| E7 | microSD can be removed by finger and passes ten closed-case cycles without ejection obstruction | |
| E8 | RF1 antenna and J5 antenna fit, rotate as intended, and do not collide with case, cable, or each other | |
| E9 | LED is visible; buzzer sound is usable; enclosure temperature after 30 min remains within every component/material limit | |
| E10 | PCB, display, buttons, and nuts can be removed without destructive case modification | |

## F. Reliability and maturity decision

| ID | Observable contract | Result / evidence |
|---|---|---|
| F1 | 8 h powered functional soak passes with event/reset/current/temperature log | |
| F2 | Ten cold starts and ten warm resets pass | |
| F3 | Known failure modes and all rework are recorded against PCB/enclosure revision | |
| F4 | Fresh ERC, DRC, fabrication export, mechanical CAD check, firmware build, and host tests pass at the tested commit | |
| F5 | Review explicitly decides whether another prototype spin is required | |

## Status sign-off

- [ ] Prototype assembled
- [ ] Electrical bring-up passed
- [ ] Bench functional tests passed
- [ ] RF characterization passed for the stated passive observations
- [ ] Mechanical fit/service passed
- [ ] Reliability soak passed

**Allowed status after evidence review:**
`PROTOTYPE_ASSEMBLED` / `BENCH_TESTED` / `REQUIRES_REVISION`

**Not established by this checklist alone:** `FIELD_TESTED`, regulatory
compliance, production yield, environmental qualification, or
`PRODUCTION_VALIDATED`.

**Reviewer:** __________________  **Decision date:** __________________

**Open failures / required next revision:**

______________________________________________________________________________
