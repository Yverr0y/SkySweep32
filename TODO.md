# TODO

## Current engineering status

Rev C is **READY FOR FIRST PHYSICAL PROTOTYPE**, not stable/production-validated
hardware. Electrical, PCB, fabrication, firmware-build, and mechanical-CAD gates
must remain reproducible. The next work is physical evidence, not more generated
PASS prose.

## First Rev C prototype

- [ ] Order exactly one engineering PCBA lot from the checked Rev C fabrication package.
- [ ] Inspect exact MPN population and assembly quality.
- [ ] Perform current-limited first power and record TP1/TP2 rails, startup, current, ripple, and temperature.
- [ ] Verify native USB enumeration/upload in both cable orientations.
- [ ] Exercise RESET, BOOT, USER, LED, buzzer, OLED, microSD, and GNSS.
- [ ] Characterize E28-2G4M12SX / SX1281 instantaneous-RSSI response with a controlled 2.4 GHz source.
- [ ] Characterize E07-900M10S RSSI response in the selected 868/915 MHz band.
- [ ] Run simultaneous-radio/storage/display/GNSS coexistence tests.
- [ ] Print one enclosure and measure every critical fit/service interface.
- [ ] Complete `hardware/rev_c/PROTOTYPE_VALIDATION_CHECKLIST.md` with raw evidence.
- [ ] Decide whether Rev C requires a PCB/enclosure respin before any broader build.

## Firmware evidence gaps

- [ ] Replace the legacy 78-byte dummy TinyML model with a trained, versioned model and dataset/test evidence, or remove the optional TinyML path entirely.
- [ ] Validate BLE Remote ID parsing against captured standards-conformant frames before making any compliance claim.
- [ ] Demonstrate that any protocol parser receives a real demodulated byte stream before advertising over-air protocol detection.
- [ ] Validate ESP-NOW range/coexistence on physical Rev C nodes.
- [ ] Treat legacy LoRa “Meshtastic” and RSSI trilateration code as experimental unless protocol interoperability and calibrated localization tests are added.

## Maturity rule

Do not use `PROTOTYPE_ASSEMBLED`, `BENCH_TESTED`, `FIELD_TESTED`, or
`PRODUCTION_VALIDATED` until the corresponding physical evidence is committed.
