# SkySweep32 Pro Rev B module lock

Status: **DESIGN INPUT — UNVALIDATED IN PHYSICAL HARDWARE — DO NOT ORDER A PCB**

Only the exact variants below are canonical. Similar-looking modules and generic
marketplace clones are not drop-in substitutes. Dimensions are design inputs;
they must be checked against the referenced manufacturer drawing/CAD before the
PCB and enclosure validation status can change.

## Locked modules

| ID | Exact product / variant | Supply and design current | Interface / pin order used | Mechanical source and maximum envelope | Antenna / connector | Compatibility rule |
|---|---|---|---|---|---|---|
| MCU1 | Espressif **ESP32-S3-WROOM-1-N8**, 8 MB Quad SPI flash, no PSRAM | 3.0–3.6 V; reserve 500 mA RF transient pending bench measurement | castellated module pins per Espressif datasheet; GPIO19/20 native USB, EN reset, GPIO0 boot | exact Espressif land pattern and 18.0 × 25.5 × 3.1 mm maximum module envelope; mandatory PCB-antenna keepout | onboard 2.4 GHz PCB antenna | exact `ESP32-S3-WROOM-1-N8` only; octal-PSRAM variants consume GPIO35–37 and are rejected |
| RF1 | Ebyte **E01-ML01DP5**, nRF24L01P PA/LNA module, SMA version | 2.0–3.6 V; ~20 mA RX, reserve 130 mA TX transient although passive profile disables TX | 1×8 through-hole row at 2.54 mm: GND, VCC, CE, CSN, SCK, MOSI, MISO, IRQ per Ebyte product table | Ebyte product drawing; exact 18 × 33.4 mm body including edge SMA envelope | module-native SMA-K; no carrier RF trace | must be marked E01-ML01DP5; 2×4 commodity PA/LNA boards and other Ebyte variants are not footprint-compatible |
| RF2 | Ebyte **E07-900M10S**, CC1101 855–925 MHz SMD module | 1.8–3.6 V logic/supply; 36 mA TX, 18 mA RX; 50 mA design branch | 22 castellated pads at 1.27 mm per Ebyte manual; CSN/SCK/MOSI/MISO, GDO0/GDO2 test pads; all GND/NC/ANT pads preserved | official Ebyte 14 × 20 mm land pattern and module drawing | module-native IPEX → qualified RG178 pigtail → panel SMA; ANT stamp pad not routed in the canonical IPEX build | exact E07-900M10S 855–925 MHz module only; the similarly named E07-M1101D-SMA is a 433 MHz part and is prohibited |
| RF3 | **RX5808 2012-layout 8-pin receiver module**, RTC6715-based, qualified per the inspection gate below | 5 V nominal; provisional 200 mA design allocation until bench measurement | pin row: CH1/DATA, CH2/SELECT, CH3/CLOCK, RSSI, AUDIO/NC, VIDEO/NC, GND, +5V; SPI-enable modification required | **REFERENCE_ENVELOPE** from rx5808-pro 2012 photos/drawing: 32 × 21 × 13 mm body until a purchased lot is measured | module RF pad to specified short 50 Ω pigtail and panel SMA | this is the only unresolved commodity module. A received lot must pass photo, pin-continuity, dimension and SPI-enable inspection before PCB release |
| RF4 | Adafruit **RFM95W LoRa Radio Transceiver Breakout, PID 3072**, 868/915 MHz | 3.3–5 V breakout input; reserve 120 mA TX at +20 dBm, 12 mA RX | VIN, GND, SCK, MISO, MOSI, CS, RST, G0/DIO0, G1/DIO1 on Adafruit breakout | Adafruit Eagle CAD/drawing; nominal 29 × 25 mm body; connector/header height from model/drawing | onboard U.FL → 50 Ω RG178 pigtail → panel SMA | PID 3072 only; raw 16 × 16 mm RFM95W is not footprint-compatible |
| GPS1 | Adafruit **Ultimate GPS Breakout v3, PID 746**, MTK3339/PA6H-family UART board with integrated patch | 3.0–5.5 V input; reserve 30 mA tracking plus active-antenna margin only if fitted | VIN, GND, TX, RX; PPS to diagnostic GPIO/test point | Adafruit Eagle CAD/drawing; nominal 35 × 25.5 × 6.5 mm; patch top and sky-view keepout are functional envelopes | integrated ceramic patch; optional U.FL is not populated/used in canonical build | PID 746 v3 geometry only; product revision must match the committed reference envelope |
| UI1 | Adafruit **Monochrome 0.96-inch 128×64 OLED breakout, PID 326**, SSD1306, I2C mode | 3.3 V logic/supply; reserve 30 mA all-pixels allowance | GND, VCC, SCL, SDA via keyed 4-wire harness; board configured for I2C | Adafruit PCB drawing; 29.2 × 26.7 mm PCB, 26.6 × 19 mm glass, 6.2 mm nominal thickness; visible area taken from drawing | none | PID 326 only; common 4-pin OLED clones have incompatible glass/holes/pin order |
| SD1 | Adafruit **MicroSD Card Breakout Board+, PID 254** | 5 V/VIN breakout input accepted; logic routed at 3.3 V; reserve 200 mA write transient | GND, VCC, CLK, DO/MISO, DI/MOSI, CS on a dedicated SPI bus | Adafruit PCB drawing; 31.85 × 25.4 mm PCB, 3.75 mm nominal board/socket thickness excluding headers, plus card insertion envelope | push-push microSD socket at service edge | PID 254 only; generic modules often reverse pin order and use different level shifters/socket depths |

## Locked support parts

These are board parts rather than removable modules; substitutions require an
engineering-change review because they affect power, protection or mechanics.

| Function | Locked part | Key requirement |
|---|---|---|
| Primary power / USB | GCT **USB4105-GF-A** USB-C receptacle | USB 2.0 native data and 5 V input |
| USB-C sink configuration | Yageo **RC0402FR-075K1L**, one each on CC1 and CC2 | independent 5.1 kΩ Rd; never short CC1 to CC2 |
| USB data ESD | STMicroelectronics **USBLC6-2SC6** | low-capacitance protection for D+/D− adjacent to the receptacle |
| VBUS surge clamp | Littelfuse **SMAJ5.0A** | unidirectional 5 V standoff TVS after the fuse; short return to ground |
| Input resettable fuse | Bourns **MF-MSMF200-2** | 2.0 A hold class; final trip/thermal behavior verified on PCB |
| Reverse/backfeed protection | Texas Instruments **LM73100RPWR** | integrated 5.5 A ideal diode; reverse-polarity and reverse-current blocking; UVLO/OVLO/slew network from TI calculation |
| 3V3 regulator | Diodes Inc. **AP63203WU-7** fixed 3.3 V, 2 A buck | manufacturer reference layout and component set followed exactly |
| Buck inductor | Bourns **SRN6028-3R9M** | 3.9 µH, ≥3 A class, <100 mΩ DCR; supplier record rechecked before BOM release |
| Buck capacitors | Murata **GRM32ER61A106KA12L** 10 µF input; 2 × **GRM32ER61A226KE20L** 22 µF output; **GRM155R71H104KE14D** 100 nF bootstrap | voltage-biased effective capacitance checked; place on the manufacturer reference layout |
| RF branch ferrite | Murata **BLM21PG221SN1D** | one separate filtered branch per 3.3 V RF module; local 100 nF plus bulk capacitor |
| Alert transducer | CUI Devices **CMT-1203-SMT-TR** magnetic transducer | low-side NMOS drive; GPIO never drives coil directly |
| Alert/vibration MOSFET | Alpha & Omega Semiconductor **AO3400A** | one dedicated low-side stage per load; 100 Ω gate resistor, 100 kΩ pulldown and flyback diode |
| Flyback diode | Nexperia **PMEG3020EP,115** | one local diode across each inductive load |
| Optional vibration motor | Precision Microdrives **310-101** 10 mm coin motor on JST-PH-2 harness | separately switched; connector polarity labelled |
| Board-to-OLED harness | JST **PHR-4** cable side / **B4B-PH-K-S** board header | keyed, removable lid harness; pin 1 GND |
| Vibration harness | JST **PHR-2** / **B2B-PH-K-S** | keyed; pin 1 supply, pin 2 switched return |
| LoRa pigtail | U.FL-compatible to panel SMA female, RG178, 100 mm maximum | bend radius and nut/tool envelope included in CAD; exact supplier lot measured |
| CC1101 pigtail | IPEX/U.FL-compatible to panel SMA female, RG178, 100 mm maximum | used with E07-900M10S module IPEX; ANT castellated pad remains NC |
| RX5808 pigtail | solder-pad to panel SMA female, RG316 or equivalent qualified 50 Ω coax, 60 mm target | assembly drawing defines shield/center termination and strain relief |

## Source records

* ESP32-S3-WROOM-1/1U datasheet, ordering variants, land pattern and antenna keepout:
  <https://www.espressif.com/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf>
* Ebyte E01-ML01DP5 product/manual downloads:
  <https://www.cdebyte.com/products/E01-ML01DP5>
* Ebyte E07-900M10S official 855–925 MHz manual:
  <https://www.cdebyte.com/pdf-down.aspx?id=1332>
* RX5808 3-wire modification and reference photos:
  <https://github.com/sheaivey/rx5808-pro-diversity/blob/master/docs/rx5808-spi-mod.md>
* RX5808 protocol reference implementation:
  <https://github.com/sheaivey/rx5808-pro-diversity/blob/master/src/rx5808-pro-diversity/receiver_spi.cpp>
* Adafruit RFM95W PID 3072:
  <https://www.adafruit.com/product/3072>
* Adafruit Ultimate GPS PID 746:
  <https://www.adafruit.com/product/746>
* Adafruit OLED PID 326:
  <https://www.adafruit.com/product/326>
* Adafruit microSD PID 254:
  <https://www.adafruit.com/product/254>
* AP63203 regulator component selection and layout:
  <https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf>
* LM73100 reverse-polarity/reverse-current protection:
  <https://www.ti.com/product/LM73100>
* USBLC6-2SC6 USB data-line ESD protection:
  <https://www.st.com/resource/en/datasheet/usblc6-2.pdf>
* Bourns MF-MSMF resettable fuse series:
  <https://www.bourns.com/docs/product-datasheets/mf-msmf.pdf>
* Bourns SRN6028 inductor series:
  <https://www.bourns.com/products/magnetic-products/power-inductors-smd-semi-shielded/srn6028-series>

Downloaded source files and reference envelopes must record source URL, retrieval
date, license and whether the geometry is exact or a `REFERENCE_ENVELOPE`.

## RX5808 lot qualification gate

The RX5808 family is not released under a stable manufacturer ordering code.
Before the footprint can be frozen, the actual purchased lot must pass all of:

1. top/bottom photographs match the documented 2012 layout;
2. eight module pins and antenna pad continuity match this pin table;
3. PCB length, width, hole/pad pitch and maximum component height are measured;
4. the SPI-enable modification is documented for that exact PCB side/revision;
5. DATA, CLOCK and SELECT are independently accessible after modification;
6. 3.3 V logic-high compatibility and RSSI voltage range are measured;
7. a 25-bit LSB-first channel write changes the tuned channel;
8. RSSI response is measured with a controlled nearby 5.8 GHz source;
9. current at 5.0 V is recorded at idle and during scanning;
10. the received module is compared to the committed reference envelope.

Until all ten checks have evidence, RF3 remains **UNVERIFIED** and Rev B remains
**DO NOT ORDER** even if KiCad ERC/DRC are clean.

## Clone policy

A clone is compatible only after its pin order, voltage, current, mounting,
connector position, antenna keepout and maximum 3D envelope have been verified
and a deliberate alternate footprint/model is committed. Visual resemblance or
an online listing title is not evidence.
