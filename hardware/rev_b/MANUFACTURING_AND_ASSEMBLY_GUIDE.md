# SkySweep32 Pro Rev B — Manufacturing & Assembly Guide

---

## 1. PCB Manufacturing Specifications (JLCPCB / PCBWay / Elecrow)

| Parameter | Value / Requirement |
|---|---|
| **Board Dimensions** | 120.0 × 80.0 mm (4-layer PCB) |
| **Board Thickness** | 1.6 mm FR4 |
| **Layer Stackup** | Standard 4-layer (JLC2313 or equivalent):<br>• L1: `F.Cu` (Signal / Power)<br>• L2: `In1.Cu` (Solid GND Plane)<br>• L3: `In2.Cu` (Split Power Plane: 3V3_MAIN / VBUS_PROTECTED)<br>• L4: `B.Cu` (Signal) |
| **Copper Weight** | 1 oz outer / 0.5 oz inner |
| **Surface Finish** | Lead-Free HASL or ENIG (recommended for 1.27 mm castellated pads) |
| **Solder Mask Color** | Green / Black / Blue |
| **Min Trace / Clearance** | 0.20 mm / 0.20 mm |
| **Min Hole Diameter** | 0.20 mm (thermal vias under ESP32-S3) |

---

## 2. Key Component BOM & Sourcing

| Reference | Function / Part | Manufacturer | Exact MPN / Part Number | Notes |
|---|---|---|---|---|
| **U1** | MCU Module | Espressif Systems | `ESP32-S3-WROOM-1-N8` | 8 MB QSPI Flash, **NO PSRAM**. Octal-PSRAM variants consume GPIO35–37 and are incompatible |
| **U2** | Power eFuse IC | Texas Instruments | `LM73100RPWR` | 10-pin VSON 2×2 mm HotRod package |
| **U3** | Synchronous Buck | Diodes Incorporated | `AP63203WU-7` | 2.0 A, 3.3 V fixed output TSOT-23-6 |
| **U4** | USB ESD Protection | STMicroelectronics | `USBLC6-2SC6` | SOT-23-6 TVS diode array |
| **L1** | Buck Inductor | Bourns Inc. | `SRN6028-3R9M` | 3.9 µH, 3.0 A, SMD 6.0×6.0 mm |
| **J1** | USB-C Input | GCT | `USB4105-GF-A` | 16-pin USB-C receptacle, top mount |
| **J2** | 2.4 GHz RF Module | Chengdu Ebyte | `E01-ML01DP5` | nRF24L01+ PA/LNA, 1×8 2.54mm THT header, module-native SMA |
| **J3** | Sub-GHz RF Module | Chengdu Ebyte | `E07-900M10S` | CC1101 855–925 MHz, 22-pad 1.27mm castellated SMD + IPEX connector |
| **J4** | LoRa Transceiver | Adafruit | `PID 3072` (RFM95W) | 868/915 MHz breakout board with U.FL connector |
| **J5** | 5.8 GHz Receiver | Qualified Seller Lot | `RX5808 (2012 Layout)` | RTC6715-based 8-pin module with 3-wire SPI modification |
| **J6** | GPS Module | Adafruit | `PID 746` (Ultimate GPS v3) | MTK3339 module with integrated patch antenna |
| **J7** | MicroSD Breakout | Adafruit | `PID 254` | Dedicated SPI microSD breakout board |
| **J8 / J9**| Display / I2C Header| JST | `B4B-PH-K-S` | 4-pin 2.0mm pitch vertical header |
| **J10 / J11**| Battery / Motor | JST | `B2B-PH-K-S` | 2-pin 2.0mm pitch vertical header |
| **BZ1** | Buzzer | CUI Devices | `CMT-1203-SMT-TR` | 12×12 mm magnetic SMT transducer |
| **SW1..3** | Tactile Switches | C&K / PTS | `PTS810 SJK 250 SMTR LFS` | 4.2×3.2 mm SMT tactile switch |

---

## 3. Assembly Sequence

1. **SMD Solder Paste & Reflow (Top Side)**:
   - Apply solder stencil for `F.Cu`.
   - Place U2 (`LM73100`), U3 (`AP63203`), U4 (`USBLC6-2SC6`), Q1/Q2 (`AO3400A`), D1..D6, L1, F1, J1 (USB-C), J3 (`E07-900M10S`), BZ1, SW1..SW3, and passives C1..C31, R1..R40, FB1..FB6.
   - Reflow solder according to standard lead-free profile (peak $245^\circ\text{C}$).
2. **ESP32-S3 Castellated Module Soldering**:
   - Align `ESP32-S3-WROOM-1-N8` on U1 land pattern.
   - Hand solder or hot-air reflow castellated pins (1..40) and thermal ground via array (pin 41).
3. **Through-Hole & Breakout Board Header Soldering**:
   - Solder J8, J9 (JST-PH 4-pin headers) and J10, J11 (JST-PH 2-pin headers).
   - Solder male header pins for J2 (`E01`), J4 (`RFM95W`), J5 (`RX5808`), J6 (`GPS`), J7 (`MicroSD`).
4. **RF Pigtails & Bulkhead Installation**:
   - Connect IPEX-to-SMA RG178 pigtail to J3 (`E07-900M10S`).
   - Connect U.FL-to-SMA RG178 pigtail to J4 (`RFM95W`).
   - Solder 60 mm RG316 coaxial pigtail from J5 (`RX5808`) RF pad to panel SMA female connector.

---

## 4. 3D Printing Sentinel Enclosure Rev B

- **STL Files**:
  - `hardware/rev_b/enclosures/skysweep32_pro_case_bottom_rev_b.stl`
  - `hardware/rev_b/enclosures/skysweep32_pro_case_lid_rev_b.stl`
- **Recommended Materials**: PETG, ABS, or ASA (UV and heat resistant).
- **Print Parameters**:
  - Layer height: `0.20 mm`
  - Perimeters / Walls: `4 walls` (1.6 mm total thickness)
  - Top / Bottom layers: `5 layers`
  - Infill: `25% Gyroid or Grid`
  - Supports: None required (all overhangs and cutouts self-supporting).
- **Heat-Set Threaded Inserts**:
  - Install 4× M3 × 4.0 mm brass heat-set inserts into the bottom case mounting bosses at (15, 15), (125, 15), (125, 85), (15, 85).
  - Secure carrier PCB with 4× M3 × 6 mm button-head screws.

---

## 5. Firmware Flashing & Bring-up Verification

1. Connect device via USB-C (J1).
2. Build and flash canonical Rev B target using PlatformIO:
   ```bash
   pio run -e esp32s3_rev_b_pro -t upload
   ```
3. Open serial monitor ($115\,200\text{ baud}$):
   ```bash
   pio device monitor -b 115200
   ```
4. Confirm startup log reports hardware manifest agreement (`hardware_rev_b.h`) and all 3 radio scanner bands (900 MHz, 2.4 GHz, 5.8 GHz) active.
