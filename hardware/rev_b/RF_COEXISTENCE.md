# SkySweep32 Pro Rev B RF architecture and coexistence

Status: **DESIGN ANALYSIS — UNVALIDATED IN PHYSICAL HARDWARE — DO NOT ORDER**

Rev B combines three passive detector bands with three locally transmit-capable
radios. Physical separation reduces overload; it cannot identify self-generated
RF. Firmware scheduling and explicit invalid windows are therefore part of the
hardware contract.

## Traceable antenna paths

| Panel label | Radio/module | Complete RF path | Carrier-board RF trace |
|---|---|---|---|
| `2.4G` | Ebyte E01-ML01DP5 / NRF24 | module PA/LNA → module-native SMA-K → external 2.4 GHz antenna | none |
| `SUB-G` | Ebyte E07-900M10S / CC1101 | module matching network → module-native IPEX → ≤100 mm qualified RG178 pigtail → panel SMA female → regional 868/915 MHz antenna | none; ANT castellated pad is NC in canonical IPEX build |
| `LORA` | Adafruit PID 3072 RFM95W | breakout U.FL → ≤100 mm qualified RG178 pigtail → panel SMA female → regional 868/915 MHz antenna | none |
| `5.8G` | qualified 2012-layout RX5808 | module RF pad → ≤60 mm qualified RG316 soldered pigtail → panel SMA female → 5.8 GHz antenna | no arbitrary trace; only the qualified pad launch |
| none | ESP32-S3-WROOM-1-N8 | module onboard PCB antenna → plastic enclosure wall | Espressif module antenna/keepout only |
| none | Adafruit PID 746 GPS | onboard patch antenna → non-metallic top surface | none |

There is no decorative SMA. Every external connector has a radio, cable/launch,
frequency label and antenna requirement. The GPS module has an integrated patch;
adding a fake GPS bulkhead would make the enclosure worse. The ESP32 module also
uses its integrated antenna and receives no carrier-board RF feed.

E01's module-native SMA sits on an RF-facing board edge. The E07-900M10S,
RFM95W and RX5808 use real panel bulkheads because their canonical modules
expose IPEX/U.FL or a qualified solder pad rather than an edge SMA. Pigtail bend
radius, connector nut/tool access and strain relief are assembly constraints.

## Physical placement and PCB rules

1. ESP32 and E01 are on opposite board edges with their antennas pointing away
   from the board center. Neither antenna keepout contains copper, components,
   fasteners, batteries or metallized enclosure surfaces.
2. E07 and RFM95W occupy opposite sub-GHz edges. Their panel antennas are not
   adjacent, even though no practical spacing can isolate a local +20 dBm LoRa
   transmission from the CC1101 receiver by itself.
3. RX5808 is adjacent to the 5.8 GHz bulkhead. Its pigtail is the shortest RF
   path in the assembly; CLOCK/DATA/SELECT and RSSI exit toward the board center.
4. GPS is on the sky-facing side, away from the buck switch node, both sub-GHz
   transmitters, digital clocks and enclosure metal.
5. The carrier uses four layers. L2 is an uninterrupted reference plane under
   RF_SPI and control signals. Source-series resistors are adjacent to the MCU;
   long stubs are prohibited. Ground stitching surrounds module edges and cable
   launches without violating module antenna keepouts.
6. No fixed “50 Ω width” is copied from another stackup. Rev B routes no long
   carrier RF line. If the RX5808 launch requires PCB copper after sample
   qualification, its width/gap is calculated from the selected fabricator's
   actual dielectric/copper data and recorded with the board constraints.

## Shared bus does not mean shared RF path

`RF_SPI` serves E01, E07 and RFM95W only. Each device has an independent CSN
pull-up; NRF24 CE is held low at reset. RX5808 is not on this bus: its RTC6715
interface has independent DATA, CLOCK and SELECT pins. microSD uses ESP32-S3
HSPI on a separate route so card writes do not create a long branch on RF_SPI.

## Firmware invalid-window policy

### LoRa transmit versus CC1101

* Every RFM95W transmit executes while holding the shared RF SPI mutex.
* `MeshtasticClient` records an RF-activity timestamp after every transmit
  attempt, including attempts that return an error because energy may still have
  reached the antenna.
* CC1101 point samples and band sweeps are suppressed during the transmit and a
  **25 ms post-transmit recovery guard**. The guard is a conservative initial
  value, not a measured receiver-recovery result.
* A local LoRa packet is never eligible to create a CC1101 threat record.
* Prototype testing must measure overload/recovery and increase the guard if any
  post-key-up response remains.

### ESP32 Wi-Fi/ESP-NOW/BLE versus NRF24

The ESP32 and NRF24 occupy the same 2.4 GHz ISM band. Wi-Fi AP beacons, ESP-NOW
and BLE activity are local interferers, not drone evidence.

* The dashboard and ESP-NOW use the configured Wi-Fi channel. NRF24 spectrum
  results overlapping that approximately 20 MHz channel are marked
  **self-interference possible** in validation data and cannot independently
  establish a drone classification.
* The normal threat loop samples NRF24 channel 76 (2476 MHz), away from the
  default Wi-Fi channel 6 center (2437 MHz), but BLE advertising near 2480 MHz
  remains a known local interferer.
* NRF24 transmission is disabled in the canonical passive profile. Its PA/LNA
  supply path is nevertheless sized for a fault/startup transient.
* A future RF-quiet scan may suspend Wi-Fi/BLE, but Rev B does **not** claim that
  feature as validated or use a dashboard-disconnecting stop/start cycle as fake
  evidence. Until a prototype establishes a useful schedule, 2.4 GHz RSSI/RPD
  alone is only an activity indication; protocol evidence or an independent band
  is required for a high-confidence classification.

### GPS and switching noise

GPS is a receiver, not a self-interference transmitter. The 1.1 MHz buck switch
node and harmonics can still reduce sensitivity. Placement, a shielded/semi-
shielded power inductor, short hot loop, continuous ground plane and GPS local
decoupling are mandatory. A GPS cold-start comparison with buck, Wi-Fi, SD and
all radios toggled independently is part of validation.

## Prototype coexistence matrix

Every row is initially `UNVERIFIED` and must produce raw measurements, not only a
PASS label.

| Aggressor | Victim | Test | Acceptance before release |
|---|---|---|---|
| Wi-Fi AP traffic | NRF24 RPD sweep | idle/AP upload/ESP-NOW comparison by channel | local channel identified; no independent high-confidence alert from local traffic |
| BLE Remote ID scan | NRF24 channel 76 and full sweep | BLE off/on comparison | limitation quantified; no undocumented false alert |
| LoRa +20 dBm transmit | CC1101 868/915 receive | keyed packet with pre/post time sweep | no accepted CC1101 sample inside measured recovery window |
| CC1101 accidental TX | LoRa receive | forced bench-only fault test | rail stable; event not reported as external LoRa packet |
| NRF24 accidental TX | ESP32 Wi-Fi/BLE | forced bench-only fault test | rail stable; recovery recorded |
| buck + SD write | GPS | TTFF/CN0 comparison | no unexplained loss of fix; mitigation documented if degraded |
| all digital buses | RX5808 RSSI | terminated-input noise histogram | no threshold-crossing digital spur |
| Wi-Fi + SD write | VBAT ADC | DC source/noise histogram | battery error remains within documented calibration bound |

No RF isolation, antenna match, desense or coexistence row is `PASS` until a
populated board, specified antennas and controlled test setup have produced the
committed evidence.
