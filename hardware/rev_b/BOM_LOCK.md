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
| RF1 | Ebyte **E01-ML01DP5**, nRF24L01P PA/LNA DIP module, SMA version | 2.0–3.6 V; ~20 mA RX, reserve 130 mA TX transient although passive profile disables TX | 2×4 2.54 mm: GND, VCC, CE, CSN, SCK, MOSI, MISO, IRQ per Ebyte manual | Ebyte manual; 18 × 33.4 mm PCB excluding SMA mating envelope; maximum installed height to be confirmed from drawing | module-native SMA-K; no carrier RF trace | must be marked E01-ML01DP5; low-cost pin-compatible PA/LNA boards are not accepted without a new envelope and power review |
| RF2 | Ebyte **E07-M1101D-SMA**, CC1101 DIP module | 1.8–3.6 V logic/supply; reserve 36 mA TX, ~18 mA RX | SPI CSN/SCK/MOSI/MISO; GDO0/GDO2 only to test pads; exact DIP pin numbering per Ebyte manual | Ebyte manual; nominal 15 × 30 mm module body plus SMA and pins; drawing check required before footprint release | module-native SMA-K | exact Ebyte module only; 868/915 configuration is firmware/antenna-region dependent |
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
| Primary power / USB | GCT **USB4105-GF-A** USB-C receptacle | USB 2.0 native data and 5 V input; CC1/CC2 each have independent 5.1 kΩ Rd; ESD on D+/D− and VBUS |
| Input resettable fuse | Bourns **MF-MSMF200-2** | 2.0 A hold class; final trip/thermal behavior verified on PCB |
| 3V3 regulator | Diodes Inc. **AP63203WU-7** fixed 3.3 V, 2 A buck | manufacturer reference layout, inductor/current rating and input/output capacitors followed exactly |
| 5 V / 3V3 TVS and ESD | parts selected in schematic from manufacturer data | no generic `TVS` value; exact MPN and standoff voltage required before ERC release |
| Alert transducer | CUI Devices **CMT-1203-SMT-TR** magnetic transducer | low-side NMOS drive; GPIO never drives coil directly |
| Alert/vibration MOSFET | onsemi **2N7002LT1G** for buzzer only if current margin passes; otherwise AO3400A-class exact MPN in schematic | gate resistor + pulldown; flyback diode on inductive loads |
| Optional vibration motor | Precision Microdrives **310-101** 10 mm coin motor on JST-PH-2 harness | separately switched; connector polarity labelled |
| Board-to-OLED harness | JST **PHR-4** cable side / **B4B-PH-K-S** board header | keyed, removable lid harness; pin 1 GND |
| Vibration harness | JST **PHR-2** / **B2B-PH-K-S** | keyed; pin 1 supply, pin 2 switched return |
| LoRa pigtail | U.FL-compatible to panel SMA female, RG178, 100 mm maximum | bend radius and nut/tool envelope included in CAD; exact supplier lot measured |
| RX5808 pigtail | solder-pad to panel SMA female, RG316 or equivalent qualified 50 Ω coax, 60 mm target | assembly drawing defines shield/center termination and strain relief |

## Source records

* ESP32-S3-WROOM-1/1U datasheet, ordering variants, land pattern and antenna keepout:
  <https://www.espressif.com/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf>
* Ebyte E01-ML01DP5 product/manual downloads:
  <https://www.cdebyte.com/products/E01-ML01DP5>
* Ebyte E07 family product/manual source:
  <https://www.cdebyte.com/Module-SPISOCUART-CC11>
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
