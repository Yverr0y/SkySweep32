# Rev C Evidence Roadmap

**Current state: READY FOR FIRST PHYSICAL PROTOTYPE — NOT PRODUCTION VALIDATED.**

Rev C is intentionally a passive RSSI/activity monitor. This roadmap is an
evidence plan, not a promise that every item will be retained in a later board.

## First board: mandatory evidence

| Area | Required recorded evidence | Decision enabled |
|---|---|---|
| Power | Current-limited start-up, USB/battery transitions, 3V3 ripple/transients, charge current, thermal images | Correct rail sizing, charger configuration, and thermal margin |
| ESP32-S3 USB | ROM/CDC enumeration, upload, ten reconnect cycles, reset reason | Native USB reliability |
| 855–925 MHz | CC1101 identity, regional channels, RSSI response, spurious observations | Retain E07 and defined regional antenna |
| 2.4 GHz | SX1281 identity, controlled RSSI sweep, enclosure detuning comparison | Retain internal antenna routing/placement |
| 5.8 GHz | RX5808 incoming pinout/lot record, channel truth table, RSSI monotonicity, noise floor | Accept module source or redesign/omit it |
| GNSS/storage/UI | Live fix and TIMEPULSE, repeated card read/write/removal, display/buttons/buzzer | Retain mechanical harness and service geometry |
| Mechanics | Printed-case fit, connector/card/antenna access, lid cycling, battery removal | Correct enclosure tolerances and cable routes |

Use [PROTOTYPE_VALIDATION_CHECKLIST.md](PROTOTYPE_VALIDATION_CHECKLIST.md) for
raw measurements and failure records. Passing a CAD gate does not satisfy any
row above.

## Possible Rev D changes — only if evidence requires them

- Replace or remove RX5808 if lots cannot meet the documented 12-pad/pinout/RSSI
  acceptance test.
- Revise 2.4 GHz antenna placement, cable, or shielding only after comparative
  enclosure measurements.
- Correct USB impedance, power thermal margin, charging behavior, connector
  access, or case tolerances from first-build evidence.
- Add an optional external 2.4 GHz antenna only if measurements justify the
  additional RF/mechanical risk.
- Add a **separate** CVBS/video-decoder experiment only after a demonstrated
  product need and an independent feasibility design. RX5808 VIDEO OUT is not a
  Rev C product interface.

## Explicit non-goals

- No RF jamming, protocol injection, GPS denial, or other active interference.
- No LoRa/Meshtastic hardware, RF direction finding, or trained TinyML claim
  without a separately reviewed requirement, architecture, data, and evidence.
- No production, field, compliance, or reliability claim before physical
  evidence establishes it.
