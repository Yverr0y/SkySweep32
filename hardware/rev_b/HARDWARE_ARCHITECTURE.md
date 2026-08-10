# SkySweep32 Pro Rev B hardware architecture

Status: **DESIGN IN PROGRESS — UNVALIDATED IN PHYSICAL HARDWARE — DO NOT ORDER**

Rev B is a new requirements-first design. Rev A coordinates, board dimensions,
footprints, decorative antenna connectors and enclosure geometry are not inputs.
The passive observation/communications scope is retained; active RF jamming
hardware is excluded.

## 1. Firmware-to-hardware requirements audit

| Function | Firmware implementation | Required electrical interface | Rev B decision |
|---|---|---|---|
| Web dashboard, ESP-NOW, BLE Remote ID | ESP32 Wi-Fi/BLE stack | MCU 2.4 GHz radio and antenna keepout | Integrated ESP32-S3-WROOM-1-N8; PCB antenna faces a plastic wall and has the Espressif carrier-board keepout |
| OLED | U8g2 SSD1306 hardware I2C | 3V3, GND, SDA, SCL | Adafruit PID 326 on a short removable 4-wire harness at the front panel |
| NRF24 scanning | `NRF24L01Driver`, SPI + CE | 3V3, GND, SCK, MOSI, MISO, CSN, CE; IRQ not used | Ebyte E01-ML01DP5; module-native SMA; IRQ routed only to a test pad |
| CC1101 scanning | `CC1101Driver`, SPI | 3V3, GND, SCK, MOSI, MISO, CSN | Ebyte E07-900M10S, 855–925 MHz; module IPEX to panel SMA pigtail; GDO0/GDO2 to test pads |
| 5.8 GHz RSSI scanning | `RX5808Driver` | 5V, GND, DATA, CLOCK, SELECT, analog RSSI | Qualified 2012-layout RX5808 module with documented SPI-enable modification; four independent MCU signals |
| GPS | TinyGPS++ over UART NMEA | 3V3/5V, GND, GPS_TX→MCU_RX, GPS_RX←MCU_TX | Adafruit Ultimate GPS v3 PID 746; onboard patch antenna; optional PPS test point |
| LoRa mesh | RadioLib SX1276 | 3V3, GND, SPI, CS, DIO0, DIO1, RESET | Adafruit RFM95W breakout PID 3072; U.FL to labelled panel SMA pigtail |
| SD logging | Arduino SD library | 3V3, GND, dedicated SPI, CS | Adafruit microSD breakout PID 254 at service edge; separate SPI controller |
| Battery measurement | `PowerManager` | divided/filtered analog input | Dedicated `VBAT_ADC`; never shared with RX5808 RSSI |
| RX5808 strength | `RX5808Driver` | filtered analog input | Dedicated `RX5808_RSSI`; never shared with battery measurement |
| Audible alert | `AlertManager` | GPIO-controlled load | Exact magnetic transducer through NMOS, gate resistor and flyback diode |
| Visual alert | `AlertManager` | GPIO-controlled LED | Dedicated status LED and resistor |
| Stealth vibration | `AlertManager` | GPIO-controlled motor load | JST-PH output through its own NMOS/flyback stage; no motor direct from GPIO |
| Reset / boot | ESP32-S3 EN and GPIO0 | Physical tool/finger access | Dedicated service-edge buttons with Espressif reference pull-up/RC network; no other load on GPIO0 or strap pins |
| Optional compass | QMC5883L on I2C | Shared SDA/SCL | Expansion connector only; not fitted in the canonical Pro BOM |
| Optional acoustic input | I2S microphone | BCLK, WS, DIN | Not fitted or routed on the canonical Pro Rev B; it remains a separate firmware option |
| Countermeasures | legacy DAC/VCO code | active RF transmit hardware | Explicitly excluded from Rev B |

## 2. MCU architecture comparison

| Criterion | Classic ESP32 DevKit V1 carrier | ESP32-S3 DevKitC-1 carrier | Integrated ESP32-S3-WROOM-1-N8 carrier |
|---|---:|---:|---:|
| Safe usable GPIO after straps/USB | Insufficient for two ADCs, RX5808 3-wire control, two SPI buses and alerts without compromises | Current v1.1 orderable variants use octal memory that consumes GPIO35–37; GPIO38 also drives the onboard RGB LED | Sufficient with the exact no-PSRAM N8 module |
| Independent ADC inputs | Possible on ADC1, but old map was already pin-constrained | Possible | Two ADC1 inputs assigned independently |
| Native USB | No | Yes | Yes; one carrier USB-C is power, flash and data |
| BLE Remote ID / Wi-Fi / ESP-NOW | Supported | Supported | Supported |
| Current Arduino firmware migration | Baseline | Pin-map and target migration required | Same target migration plus reference-design USB/reset/power circuitry |
| Community assembly | Easy, but unsafe pin compromises remain | Easy, but exact currently documented v1.1 variants do not meet the required GPIO map | Castellated module requires PCB assembly; the result has one exact BOM and no clone DevKit geometry |
| RF/layout risk | Moderate | Moderate | Higher, controlled by a four-layer reference plane, exact Espressif land pattern and antenna keepout |
| Cost / area | Low / medium | Medium / largest MCU board | Lowest BOM and smallest area for an assembled Rev B |
| Decision | Rejected | Rejected after exact-variant audit | **Selected** |

**Selected MCU:** official **Espressif ESP32-S3-WROOM-1-N8**
(8 MB Quad SPI flash, no PSRAM), not a development board. Espressif lists this
exact module in the WROOM-1 datasheet. The N8 variant is deliberate: Rev B does
not require PSRAM and GPIO35–37 remain available, unlike octal-PSRAM variants.
The carrier implements the manufacturer land pattern, antenna keepout, EN/BOOT,
native USB and power recommendations. Module substitutions with PSRAM are not
pin-compatible with this layout.

## 3. Rev B GPIO map

[`hardware_manifest.yaml`](hardware_manifest.yaml) is authoritative and generates
the firmware header; this table explains the intent.

| Signal | GPIO | Direction | Notes |
|---|---:|---|---|
| I2C_SDA | 1 | bidirectional | OLED and optional compass expansion |
| I2C_SCL | 2 | output | 4.7 kΩ pull-ups to 3V3 |
| RX5808_RSSI | 4 | ADC1 input | dedicated RC-filtered analog route |
| VBAT_ADC | 5 | ADC1 input | dedicated protected divider; not connected to RSSI |
| RX5808_DATA | 6 | output | independent 3-wire control, LSB first |
| RX5808_CLOCK | 7 | output | independent clock, idle low |
| NRF24_CE | 8 | output | held low at boot |
| NRF24_CSN | 9 | output | 10 kΩ pull-up |
| CC1101_CSN | 10 | output | 10 kΩ pull-up |
| RF_SPI_MOSI | 11 | output | CC1101, NRF24 and LoRa only |
| RF_SPI_SCK | 12 | output | short trunk; series damping fitted at MCU end |
| RF_SPI_MISO | 13 | input | shared return |
| LORA_CSN | 14 | output | 10 kΩ pull-up |
| LORA_DIO0 | 15 | input | RadioLib interrupt |
| LORA_DIO1 | 16 | input | RadioLib interrupt/status |
| LORA_RESET | 17 | output | pulled up; asserted low |
| RX5808_SELECT | 18 | output | independent select/latch, idle high |
| GPS_PPS | 21 | input | optional timing/diagnostic input |
| SD_SPI_MOSI | 35 | output | dedicated SD bus; valid on selected N8 variant |
| SD_SPI_SCK | 36 | output | dedicated SD bus; series damping |
| SD_SPI_MISO | 37 | input | dedicated SD bus |
| SD_CSN | 38 | output | 10 kΩ pull-up |
| ALERT_BUZZER | 39 | output | NMOS gate, 100 kΩ pulldown |
| ALERT_LED | 40 | output | series resistor |
| VIBRATION | 41 | output | NMOS gate, 100 kΩ pulldown |
| USER_BUTTON | 42 | input | optional normally-open button to GND |
| GPS_RX | 47 | input | MCU receives GPS TX |
| GPS_TX | 48 | output | MCU sends to GPS RX |

Reserved and unloaded: GPIO0 (Boot only), GPIO3, GPIO45 and GPIO46 (strapping),
GPIO19/20 (native USB), GPIO43/44 (console/test pads). Dedicated Reset and Boot
buttons follow the Espressif reference design. No Rev B peripheral may reuse a
reserved pin.

## 4. Bus architecture and signal integrity

* `RF_SPI` serves only CC1101, NRF24 and RFM95W. Each device has an independent
  CS pull-up. Clock and MOSI use 22–33 Ω source-series footprints next to the MCU.
  The physical trunk is short; it is not routed as long star stubs.
* `SD_SPI` is an independent controller and is routed directly to the service-edge
  microSD breakout with 22–33 Ω source-series footprints and local 47 µF + 100 nF.
* RX5808 is **not SPI-bus compatible** with the three RF modules. It uses separate
  DATA, CLOCK and SELECT GPIOs. The selected RTC6715 protocol is a 25-bit,
  LSB-first write: 4 address bits, write bit, then 20 data bits; data is sampled
  on clock rising edges. Rev A's one-pin pseudo-interface cannot operate it.
* RX5808 RSSI and battery ADC traces are separate, kept away from SCK, buck SW,
  antenna feeds and board edges. Each has its own RC filter and test point.
* I2C and UART are routed as low-speed point-to-point interfaces with labelled
  connectors. There are no unlabelled generic headers in the canonical build.

## 5. RF architecture

| Radio | Antenna path | Placement rule |
|---|---|---|
| ESP32-S3 Wi-Fi/BLE | WROOM-1 PCB antenna | Clear plastic wall; Espressif copper/component keepout below and in front of antenna |
| CC1101 868/915 MHz | E07 module-native SMA | Left RF edge; no carrier-board RF trace |
| NRF24 2.4 GHz | E01 module-native SMA | Opposite the ESP32 antenna as far as enclosure permits |
| LoRa 868/915 MHz | RFM95W U.FL → specified 50 Ω pigtail → panel SMA | Opposite side from CC1101; no carrier RF trace |
| RX5808 5.8 GHz | receiver module RF pad → shortest qualified 50 Ω pigtail → panel SMA | Near its panel entry; RSSI/control exit toward board center |
| GPS | PID 746 integrated patch | Under non-metallic top, clear view to sky; away from buck, LoRa and CC1101 |

No Rev B SMA is decorative. The schematic and harness table identify the module,
coax and panel label for every port. The carrier itself does not route a long
arbitrary 50 Ω RF feed. For the short RX5808 pad launch, geometry and assembly are
qualified with the selected module before fabrication release; until then its
status remains UNVERIFIED.

## 6. RF self-interference policy

The complete port map, placement rules, firmware invalid windows and prototype
test matrix are specified in
[`RF_COEXISTENCE.md`](RF_COEXISTENCE.md). The release-critical rules are:

* **ESP32 Wi-Fi/BLE versus NRF24:** physical separation reduces overload but
  cannot make local packets distinguishable. Unqualified 2.4 GHz RSSI/RPD is
  activity evidence, not drone identity. Normal dashboard operation must not
  classify the configured AP channel as an independent target. A true RF-quiet
  scan remains unimplemented and is not claimed.
* **LoRa TX versus CC1101:** every local LoRa transmit holds the RF SPI mutex.
  CC1101 samples are invalid through a 25 ms initial post-transmit guard. The
  final guard comes from prototype recovery measurements.
* **ESP-NOW/Wi-Fi and BLE:** configured channel and local feature state must
  accompany validation records. BLE activity near NRF24 channel 76 is a known
  limitation.
* All three transmit-capable radios default to the minimum power needed by their
  communication role. NRF24 transmission is disabled in the passive Pro profile.

## 7. Physical placement order

1. Service edge: one protected USB-C for 5 V power, native USB flashing/data,
   reset/boot access and removable microSD.
2. Front panel: OLED daughterboard behind a real clear window; status LED and
   optional user button; keyed harness so the lid can be removed.
3. RF perimeter: CC1101 and LoRa on opposite sides; NRF24 away from the ESP32
   antenna; RX5808 at the 5.8 GHz panel entry.
4. Top/sky region: integrated-patch GPS under plain plastic with a no-copper/no-
   battery volume above it.
5. Center: integrated MCU module and low-speed logic.
6. Power corner: USB input protection and buck regulator, away from GPS, RSSI and
   antenna connectors.

Long digital routes do not cross antenna keepouts. Mounting holes, enclosure
walls, screw access, coax bend radii, module insertion and connector mating
volumes are placement constraints, not post-layout decorations.

## 8. Mechanical and user-access targets

The board size is determined after locked envelopes are placed; 120 × 80 mm is
not retained as a target. Initial placement budget: no larger than 150 × 100 mm,
four layers, 1.6 mm FR-4. The first enclosure is an indoor/portable two-part
printable instrument enclosure, not waterproof and not IP-rated.

Required access without removing the PCB:

* one USB-C connector for protected 5 V input, native programming and data;
* push-push microSD card, removable with enclosure closed;
* visible 0.96-inch OLED;
* Reset and Boot buttons through recessed tool apertures;
* four correctly labelled RF ports: `SUB-G`, `LORA`, `2.4G`, `5.8G`;
* antenna wrench/nut and pigtail bend clearance;
* lid removal without disconnecting soldered wires.

## 9. Power architecture

The canonical input is 5 V from a USB-C source rated at least 2 A. A resettable
2 A fuse, VBUS TVS and LM73100 integrated ideal diode provide input and backfeed
protection. AP63203WU-7 generates 3V3_MAIN with its official 3.9 µH / 10 µF /
2 × 22 µF / 100 nF component set. RF modules have independent filtered branches;
microSD has local burst capacitance. The calculated simultaneous load is 1.115 A
on 3V3_MAIN and 1.316 A at USB before source reserve. See the authoritative
[`POWER_BUDGET.md`](POWER_BUDGET.md) for assumptions, arithmetic, locked parts
and required bench evidence.

## 10. Stackup target

The selected preliminary fabrication target is the symmetric four-layer,
1.6 mm JLC04161H-7628 stack: F.Cu signals, uninterrupted In1.GND, In2 power/GND
and B.Cu signals. The authoritative layer dimensions, net classes, length limits,
return-path rules, keepouts and DRC gates are in
[`STACKUP_AND_CONSTRAINTS.md`](STACKUP_AND_CONSTRAINTS.md).

The fabricator's live dielectric and copper data control impedance. Rev B has no
long carrier-board RF feed. Native USB is the only controlled pair and its
preliminary width/gap must be recalculated before fabrication.

## 11. Known uncertainties before layout release

* RX5808 lacks a stable manufacturer part number. Rev B defines a photo/dimension/
  pin qualification gate and a reference envelope; a random clone is not accepted.
* Exact module STEP sources must be checked against physical/mechanical drawings.
  Models without trustworthy CAD are labelled `REFERENCE_ENVELOPE`.
* USB source capability, RX5808 current and SD write peaks require bench
  measurement during bring-up.
* RF coexistence can be mitigated and tagged in firmware but cannot be declared
  validated without a populated prototype and controlled RF tests.
* No physical prototype has been built. All CAD-only checks remain explicitly
  distinct from assembled-hardware validation.
