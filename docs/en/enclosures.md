# SkySweep32 3D Enclosure Designs

> **LEGACY REV A ENCLOSURE — EXPERIMENTAL / UNVERIFIED / DO NOT PRINT FOR ASSEMBLY**
>
> The referenced STL files are concept geometry, not a fit-checked product.
> Their PCB/module clearances, OLED alignment, USB and microSD access, antenna
> hardware, assembly sequence and environmental performance are unverified.
> They are explicitly not IP-rated. See the
> [legacy status](https://github.com/bobberdolle1/SkySweep32/blob/master/hardware/LEGACY_REV_A_STATUS.md).

This document outlines the recommended enclosure designs for the different tiers of the SkySweep32 passive drone detector. We provide conceptual guidelines so that makers and field engineers can design and 3D print cases suited for their specific environment.

---

## 🟢 Starter / Base Tier (Portable Tactical Unit)

The Starter tier is aimed at infantry and field operators who need a compact, low-cost device. It should fit comfortably on MOLLE webbing, a plate carrier, or inside a tactical pouch.


### Design Recommendations
- **Form Factor**: Similar to a ruggedized smartphone or walkie-talkie.
- **Material**: PETG or TPU for impact resistance. Avoid PLA as car/sun temperatures will warp it.
- **Top Panel**: Needs a small window for the 0.96" OLED screen and 2-3 tactile buttons for UI interaction (if physical buttons are added later).
- **Antenna Placement**: A single SMA hole on Top for the 2.4GHz omnidirectional antenna.
- **Battery**: Space for an 18650 cell (~3.7V 3000mAh) or a flat LiPo pack beneath the PCB.
- **Ports**: A covered USB-C port at the bottom for charging and firmware flashes.

---

## 🟡 Hunter / Standard Tier (Multi-Band Scanner)

The Hunter tier introduces wider spectrum monitoring (900MHz + 2.4GHz + 5.8GHz). It requires a slightly larger case to accommodate two or three discrete antenna ports without causing interference.

### Design Recommendations
- **Form Factor**: Walkie-talkie format but wider.
- **Antenna Spacing**: Place the 900MHz (CC1101) antenna on the left, and the 2.4GHz (NRF24) / 5.8GHz (RX5808) antennas grouped on the right. Maintain at least 3-5 cm distance to reduce cross-talk.
- **Cooling**: RX5808 modules can get warm during continuous scanning. Add subtle ventilation fins along the back plate.
- **Mounting**: Add a standard 1/4" tripod thread insert on the bottom to mount it on a car roof or static position.

---

## 🔴 Sentinel / Pro Tier (legacy Rev A concept)

The existing Sentinel files illustrate an earlier stationary-node concept only.
They do not establish a usable or weatherproof enclosure. Rev B will be designed
from the checked PCB assembly and connector mating envelopes; no current Rev A
dimension, vent, antenna hole or mounting feature is a Rev B constraint.

---

## Best Practices for Printing
1. **Infill**: Use Gyroid or Cubic infill at 30-40% for maximum durability.
2. **Wall Thickness**: Minimum 3 perimeters (walls) with a 0.4mm nozzle.
3. **Inserts**: Use M3 brass heat-set inserts for joining the enclosure halves, rather than threading directly into plastic.
4. **Tolerance**: Ensure a 0.2mm tolerance gap between interlocking case parts to guarantee a snug but removable fit.

## Legacy concept files

The following files are retained for history and must not be treated as
validated print/assembly files:

| File | Status |
|------|--------|
| [`hardware/enclosures/skysweep32_pro_case_bottom.stl`](https://github.com/bobberdolle1/SkySweep32/blob/master/hardware/enclosures/skysweep32_pro_case_bottom.stl) | Rev A concept; fit unverified |
| [`hardware/enclosures/skysweep32_pro_case_lid.stl`](https://github.com/bobberdolle1/SkySweep32/blob/master/hardware/enclosures/skysweep32_pro_case_lid.stl) | Rev A concept; openings/clearance unverified |
| [`hardware/skysweep32_pro.kicad_pcb`](https://github.com/bobberdolle1/SkySweep32/blob/master/hardware/skysweep32_pro.kicad_pcb) | Rev A concept; KiCad syntax compatible only |
