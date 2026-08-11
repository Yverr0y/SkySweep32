# SkySweep32 Engineering Baseline Audit — 2026-08-11

## Scope and evidence priority

This audit records the state of `master` at `8dd3499` before redesign. It treats
KiCad reports, source, generator code and rendered geometry as evidence; status
prose is not evidence. The corrective branch is
`hardware/real-rev-redesign`.

Baseline commands:

```text
git fetch --all --prune
git rev-list --left-right --count HEAD...origin/master  # 0 0
KiCad 10.0.5: kicad-cli sch erc --severity-all --exit-code-violations ...
KiCad 10.0.5: kicad-cli pcb drc --refill-zones --schematic-parity \
  --severity-all --exit-code-violations ...
```

The fresh reports were written outside the repository so stale checked-in
reports were not overwritten during forensics.

## Confirmed defects

### Validation pipeline and status

- The former `rev_b/HARDWARE_VALIDATION_REPORT.md` claimed 22/22 PASS and
  `FULLY VALIDATED` while the checked-in DRC report says `Found 375 DRC
  violations` and the checked-in ERC report says `Errors 0 Warnings 8`.
- Fresh KiCad 10.0.5 ERC reproduces **8 warnings** and exits nonzero. Seven
  warnings are unresolved `SkySweep32` footprint-library links; one is an
  isolated `RX5808_RF_PAD` label.
- Fresh KiCad 10.0.5 DRC reproduces **374 DRC violations**, **186 unconnected
  pads**, and **259 schematic-parity footprint errors**, then exits nonzero.
  The one-count difference from the checked-in 375 report is a tool/version
  result, not a pass.
- Fresh DRC categories include: 77 courtyard overlaps, 29 copper clearances,
  8 hole clearances, 11 plated holes in courtyards, 5 NPTH holes in
  courtyards, 9 starved thermals, 4 solder-mask bridges, 140 silkscreen-over-
  copper, 78 silkscreen overlaps, 4 silkscreen-edge clearances, and 1 isolated
  copper item. Schematic parity additionally reports 199 net conflicts, 32
  footprint-field mismatches, 24 footprint mismatches and 4 extra footprints.
- The former PASS table cherry-picked DRC categories that happened to be zero
  and omitted the failing categories and unconnected items. It therefore could
  not establish an overall DRC pass.
- CI builds firmware and checks a generated pin header, but does not run KiCad
  ERC or DRC. A Markdown PASS edit could merge without machine evidence.

### Placement, routing and mechanics

- `generate_pcb.py` places parts from hard-coded `MAJOR_PLACEMENT` and
  `generated_placement()` coordinate tables rather than from solved mechanical
  constraints. It puts C9 at `(15, 14)` beside H1 at `(15, 15)`, and SW1 at
  `(18, 85)` beside H4 at `(15, 85)`.
- DRC confirms H1 intersects both C9 pads and H4 intersects both SW1 pads.
- The top 3D preview visibly shows large module envelopes covering unrelated
  components and obscuring mounting/service regions. It is not a plausible
  assembled placement.
- Fresh DRC reports 186 unconnected pads. The checked-in board is not a
  completed routed design.
- `logs/freerouting.log` repeatedly warns that four-thread route optimization
  is known to generate clearance violations and recommends single-thread mode.
  It also says the route should be finished manually. The workflow nevertheless
  treated SES import as a routing PASS.
- `generate_pcb.py` writes the unrouted generated baseline directly to the
  canonical board unless an external, undocumented SES import step is performed.
  Generation is therefore not a deterministic reproduction of the checked-in
  routed artifact.
- `generate_3d_models.py` constructs the seven custom STEP files exclusively
  from `Part.makeBox` and `Part.makeCylinder`. These are simplified envelopes,
  not manufacturer CAD. The former report called them high-fidelity.
- Both `generate_3d_models.py` and `build_case_rev_b.py` hard-code
  `C:\Users\kiril\AppData\Local\Programs\FreeCAD 1.1\bin`.
- `build_case_rev_b.py` duplicates a 120 x 80 mm board outline, mounting-hole
  coordinates, component cutouts and panel openings as magic numbers. It never
  imports the complete PCB assembly STEP and performs no body-to-body
  interference check.
- The enclosure generator only asserts that two isolated enclosure shapes are
  valid solids. Valid solids do not prove assembly fit.
- `render_enclosure_previews.py` concatenates only bottom and lid STL meshes.
  Its “assembled” and “interior” images contain no PCB assembly, fasteners,
  display, harnesses, cards, plugs, pigtails or antennas.
- No source was found that reproducibly builds the checked-in
  `skysweep32_pro_sentinel_assembly.step` from the PCB and enclosure.

### Electrical and component contract

- The current `hardware_manifest.yaml` is JSON stored under a YAML extension.
  It asserts authority over pin mapping but cannot validate symbols,
  footprints, placement, routing or mechanical fit.
- The RX5808 entry is explicitly a `QUALIFIED-LOT` placeholder requiring a
  future physical sample. It is not an exact orderable MPN and cannot support
  final footprint or mechanical sign-off.
- The firmware CC1101 driver scans 433.92, 868 and 915 MHz while the selected
  E07-900M10S module is specified in the manifest as 855–925 MHz. The 433 MHz
  operation is incompatible with that exact selected module.
- Rev B's firmware `TIER_PRO` contract automatically enables RX5808, GPS, SD and
  LoRa, so the provisional RX5808 is not isolated from the canonical target.
- The schematic/PCB net-name parity is broken (`GND` versus `/GND` and similar
  generated-name conflicts), producing 199 fresh parity conflicts.
- Manufacturer pinout, land-pattern and model evidence was not vendored or
  indexed in a way that permits repeatable component review.

### Firmware and public capability claims

- `src/model_data.h` explicitly contains 78 dummy bytes. `MLClassifier::begin()`
  nevertheless reports “TinyML classifier ready”, sets `modelLoaded = true`,
  and sends the dummy data to inference. TinyML classification is not an
  implemented validated capability.
- `config.h` auto-enables `MODULE_ML` whenever any RF module is enabled, so the
  placeholder path is included in ordinary release tiers rather than being an
  isolated experiment.
- NRF24 scanning uses the nRF24L01+ one-bit RPD threshold, not true RSSI or
  protocol decoding. It can report energy above approximately -64 dBm but
  cannot by itself identify DJI/OcuSync/Crossfire.
- Public docs describe signal fingerprint identification, accurate TinyML drone
  classification, compass direction finding and compliant Remote ID behavior
  more strongly than source/test evidence supports.
- A magnetometer provides the enclosure heading; without a directional antenna
  or bearing sensor it cannot calculate the direction of an incoming RF signal.
- “Hardened & Field-Tested” conflates host parser fuzzing/static analysis with
  field or hardware validation.
- `TODO.md` says all core requirements are met and the project is stable while
  the current hardware fails ERC/DRC and key advertised capabilities are
  placeholders or simulations.
- Canonical passive Rev B documents exclude countermeasure hardware, but the
  root README, website and tier navigation still prominently advertise a
  Juggernaut jammer/GPS-denial tier. This conflicts with current passive scope.

## Stale or misleading artifacts

- `skysweep32_pro_rev_b-drc.rpt`: valid failing baseline evidence, but previously
  misrepresented as a pass.
- `skysweep32_pro_rev_b-erc.rpt`: valid failing baseline evidence, but previously
  misreported as zero warnings.
- `skysweep32_pro_rev_b_base.*`, DSN, SES, XML, NET, PDF, PNG and placement SVG:
  generated intermediates lack one deterministic source-to-output workflow and
  can drift from the canonical board.
- Three checked-in Freerouting JARs (1.9.0, 2.2.4 and 2.3.0) are duplicated
  binary dependencies without one selected version/checksum workflow.
- Custom STEP models are usable only as clearly labelled maximum mechanical
  envelopes after dimensions are verified; they are not precision CAD.
- Legacy Rev A remains at `hardware/` root beside current work, making revision
  authority easy to misunderstand even though warning prose exists.

## Contradictory claims

- Rev B README formerly said “production” while root/hardware navigation said
  design in progress and do not order.
- Rev B validation formerly said 0 ERC warnings; its referenced report says 8.
- Rev B validation formerly implied DRC clean; its referenced report says 375.
- Enclosure docs said generated around the actual assembly; the generator never
  imports that assembly.
- 3D docs said high-fidelity; generator source proves primitive envelopes.
- Website advertises TinyML neural inference; model source says placeholder.
- Website advertises field-tested status; repository evidence covers host
  parser tests, not field or physical hardware tests.

## Suspected defects requiring design-stage verification

- LM73100 and AP63203 implementation, passive values, power sequencing, thermal
  margin and layout have not yet been checked pin-by-pin against current primary
  datasheets.
- USB-C connector pin mapping, shield strategy, CC resistors, ESD topology and
  native USB routing require schematic and layout review.
- Exact module footprints and rotations require manufacturer-drawing review.
- RF-module coexistence and antenna/pigtail service envelopes require a real
  assembly layout and enclosure cable model.
- Firmware protocol classification inputs may not originate from decodable
  over-air data on the selected receivers; source-path tracing is required.
- Remote ID parser standards coverage and claimed compliance require dedicated
  conformance evidence; compilation and length checks are insufficient.

## Missing evidence

- No assembled Rev B board photographs, bring-up log, measured rails, current
  traces, USB enumeration evidence, RF response measurements, antenna tests,
  thermal measurements or environmental results.
- No controlled-impedance fabrication stackup from a selected prototype vendor.
- No complete exact BOM with sourcing status and alternates policy.
- No footprint review checklist tied to primary package drawings.
- No assembly interference matrix or measured zero-collision CAD report.
- No plug/card/button/pigtail motion envelopes or documented assembly order.
- No fresh-clone end-to-end hardware verification command.

## Design decisions required

1. Archive published failed Rev B and create a clean Rev C, or explicitly replace
   Rev B identity. A clean Rev C is the leading option because electrical and
   mechanical identity will change substantially.
2. Define the honest passive product: which RF observations are energy-only,
   which protocols are actually decoded, and which advertised bands are
   mandatory.
3. Replace or remove the provisional RX5808 before any orderable design gate.
4. Decide whether LoRa is mandatory; ESP-NOW already supplies local mesh and a
   second 900 MHz radio adds cost, current, antennas and coexistence burden.
5. Choose carrier modules versus direct ICs from reproducibility and RF-layout
   evidence, not aesthetics.
6. Establish one current-revision manifest that generates firmware pin maps and
   validation inputs while KiCad plus manufacturer documents remain physical
   authority.
7. Remove active countermeasure hardware from canonical navigation and clearly
   archive software experiments outside passive product claims.

## Immediate corrective action

Commit `3d3b438` replaced the false 22/22 validation report and added an
`EXPERIMENTAL / UNVERIFIED / DO NOT ORDER` warning to Rev B. This is a safety
correction, not a redesign or validation result.
