# SkySweep32 Rev C Roadmap

**Current maturity: READY_FOR_FIRST_PROTOTYPE — NOT PRODUCTION VALIDATED.**

SkySweep32 is a passive RSSI/activity monitor. This roadmap sequences work by
physical evidence; it does not authorize a design change before the evidence
that would justify it.

## Current

### Rev C — Prototype #1

The architecture is frozen. The next engineering truth must come from physical
measurements, recorded with the
[prototype validation checklist](PROTOTYPE_VALIDATION_CHECKLIST.md).

Required validation:

- power, charging, rails, thermals, and runtime;
- 855–925 MHz RF response;
- SX1281 2.4 GHz sweep and self-interference;
- RX5808 5.8 GHz response;
- GNSS, microSD, OLED, controls, and local web functions;
- enclosure, connectors, battery, and cable fit.

CAD/build gates do not satisfy these physical tests.

## Next

### Rev C.1 — Evidence-driven refinement

Rev C.1 is possible **only after physical Rev C testing**. It may address:

- actual electrical fixes;
- RF isolation;
- antenna placement;
- an optional external 2.4 GHz connector, if measurements justify it;
- RX5808 improvements;
- power efficiency;
- a switchable 5 V rail, if useful;
- enclosure and assembly refinements;
- size reduction where evidence permits.

Do not create Rev C.1 merely because CAD can look prettier.

## Compact variant

### Possible future SkySweep32 Mini

A compact derivative is possible only after full Rev C functionality is
physically proven. Potential goals are a smaller PCB and battery, reduced
connector set, optional omission of subsystems, and a smaller enclosure.

This is a derivative, not a reason to compromise Prototype #1.

## 5.8 GHz video

**Current Rev C: RSSI/activity only.**

A future experimental path is deliberately staged:

1. expose RX5808 `VIDEO OUT` to an external monitor and verify analog video;
2. prototype a CVBS decoder separately;
3. evaluate ESP32-S3 capture feasibility;
4. determine display and web bandwidth requirements;
5. only then evaluate an integrated CVBS decoder, secondary MCU, ESP32-P4, or
   another video-capable processor.

Do not migrate compute platforms before experimental evidence establishes a
requirement.

## Mesh

### Stage 1: ESP-NOW

Use ESP-NOW between SkySweep32 devices for possible timestamped detection
sharing, node GNSS positions, a centralized dashboard, and multi-node event
correlation.

### Stage 2: optional external LoRa/Meshtastic-class expansion

LoRa remains excluded from the Rev C motherboard. Optional future expansion is
not canonical Rev C hardware and does not imply Meshtastic protocol
compatibility.

## Remote ID

Experimental until tested with known-compliant transmitters or captured frames.
No ASTM/ASD-STAN conformance claim is valid before that evidence exists.

## TinyML

No feature claim until all of the following exist:

- a real dataset;
- reproducible training;
- a real model;
- recorded metrics;
- physical validation.

## Rev D

Rev D is justified only by a major evidence-driven architectural change, such
as video becoming a core feature, experimentally demonstrated ESP32-S3
insufficiency, a fundamentally changed RF frontend, manufacturing evidence
requiring major integration, or a fundamental requirement revealed by real
users.

Rev D is **not** justified by prettier CAD, a newer MCU existing, AI preference,
or theoretical optimization.

## Maturity sequence

```text
READY_FOR_FIRST_PROTOTYPE
→ PROTOTYPE_ASSEMBLED
→ POWER_VALIDATED
→ FUNCTIONALLY_BENCH_TESTED
→ RF_CHARACTERIZED
→ FIELD_TESTED
→ PRODUCTION_CANDIDATE
```
