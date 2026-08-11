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
- uses ESP32-S3-WROOM-1-N8, E01-ML01DP5, E07-900M10S, SAM-M10Q-00B and Molex 104031-0811 as exact parts;
- removes the provisional RX5808, LoRa breakout, GPS breakout and microSD breakout;
- excludes TinyML, direction finding and active countermeasures from hardware claims;
- uses a single JSON contract for firmware pins, exact parts and mechanical datums;
- co-designs a new enclosure from the routed PCB assembly rather than inheriting Rev B dimensions.

## Consequences

Rev B boards, enclosure parts and firmware pin maps are incompatible with Rev C. The public release remains v0.6.1 software plus historical Rev A/Rev B hardware until Rev C reaches `READY_FOR_PROTOTYPE`; no Rev C manufacturing package is published before that gate. Actual prototype assembly and bench testing remain required after all CAD gates pass.
