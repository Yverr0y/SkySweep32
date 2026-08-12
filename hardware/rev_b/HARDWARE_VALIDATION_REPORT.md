# SkySweep32 Pro Rev B Baseline Validation Status

Status date: **2026-08-11**

> **EXPERIMENTAL / UNVERIFIED / DO NOT ORDER**
>
> Rev B is not validated for manufacture. This file replaces the previous
> 22/22 PASS claim, which contradicted the checked-in KiCad reports and did not
> constitute evidence of electrical or mechanical correctness.

## Reproduced checked-in evidence

| Domain | Current status | Evidence |
|---|---|---|
| Schematic ERC | **FAIL** | `skysweep32_pro_rev_b-erc.rpt` records 0 errors and **8 warnings**, not 0 warnings. |
| PCB DRC | **FAIL** | `skysweep32_pro_rev_b-drc.rpt` records **375 violations**, including hole-clearance and copper-clearance failures. |
| Placement | **FAIL** | The DRC report records H1/C9 and H4/SW1 mounting-hole conflicts. Placement and courtyard violations were omitted from the former PASS table. |
| Component CAD | **UNVERIFIED** | The custom STEP files are generated simplified envelopes. Their existence does not establish manufacturer-model fidelity. |
| Enclosure fit | **UNVERIFIED** | Valid enclosure solids and rendered previews do not establish PCB assembly fit, connector access, fastener clearance, or zero interference. |
| Electrical architecture | **UNVERIFIED** | Net-name assertions and generated files do not independently verify component selection, pinouts, power integrity, RF behavior, or manufacturability. |
| Physical hardware | **UNVERIFIED** | No assembled Rev B prototype or bench evidence is present in the repository. |

## Maturity

Current maturity: **CONCEPT / FAILED BASELINE CAD CHECKS**

Rev B must not advance to `SCHEMATIC_CHECKED`, `LAYOUT_DRC_CLEAN`,
`MECHANICAL_CAD_CHECKED`, or `READY_FOR_PROTOTYPE` until fresh reproducible
evidence satisfies those gates. Even after CAD gates pass, physical assembly and
bench validation remain separate future milestones.

The failing reports are intentionally retained as baseline evidence. Do not
change this status from prose alone; regenerate ERC, DRC, fabrication, firmware,
and mechanical evidence from canonical sources.
