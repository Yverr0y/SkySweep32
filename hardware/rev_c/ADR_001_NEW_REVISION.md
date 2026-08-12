# ADR-001: Replace the published Rev B prototype with Rev C

- **Decision date:** 2026-08-11
- **Status:** Accepted
- **Decision:** Archive Rev B as an abandoned, unverified prototype and create a clean Rev C hardware identity.

## Context

Rev B was published as a distinct four-layer PCB/enclosure redesign and was described by checked-in documents as fully validated. Reproduction with KiCad 10.0.5 instead found 374 PCB DRC violations and 8 ERC warnings. The board source was generated from hard-coded placement, then routed with Freerouting despite placement collisions. Generated rectangular/cylindrical component envelopes were called high-fidelity and the enclosure repeated nominal dimensions rather than consuming and checking the complete PCB assembly. Rev B also mixed development breakouts, an unqualified RX5808 envelope and canonical feature claims that the firmware or physical design could not substantiate.

Replacing the circuit, connector set, module set, pin map, board datum, outline and enclosure while retaining the Rev B name would silently redefine a public revision. It could also make old documentation, photos and community discussions appear applicable to incompatible hardware.

## Decision

Rev B remains in `hardware/rev_b/` solely as historical, non-orderable evidence and carries `EXPERIMENTAL / UNVERIFIED / DO NOT ORDER` warnings. Rev C is the only current canonical hardware once its source files exist. It begins at `CONCEPT` and may advance only through reproducible gates.

Rev C deliberately:

- limits canonical hardware to passive receive/energy observation;
- uses `ESP32-S3-WROOM-1-N16R8`, `E28-2G4M12SX`, `E07-900M10S`,
  `SAM-M10Q-00B`, and Molex `104031-0811` as exact production-intended parts;
- admits only the drawing-qualified `RX5808-2012-12P` envelope and requires
  incoming electrical/mechanical qualification before assembly;
- removes LoRa, GPS, microSD, and OLED development breakouts;
- excludes TinyML, direction finding, and active countermeasures from hardware
  claims;
- uses a single JSON contract for firmware pins, exact parts, assembly items,
  and mechanical datums;
- co-designs a new enclosure from the routed PCBA, protected battery, display,
  antenna, harness, connector, and fastener envelopes rather than inheriting
  Rev B dimensions.

## Consequences

Rev B boards, enclosure parts, and firmware pin maps are incompatible with Rev
C. Rev C now has a first-prototype-only fabrication package after reproducible
ERC, DRC, firmware-build, export, and CAD gates. That package does not advance
the design beyond `READY_FOR_FIRST_PROTOTYPE`; actual assembly, bring-up, RF and
power characterization, tolerance checks, and serviceability tests remain
mandatory.
