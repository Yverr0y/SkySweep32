# SkySweep32

Passive RF energy-observation and logging platform based on ESP32.

[![Firmware CI](https://github.com/bobberdolle1/SkySweep32/actions/workflows/platformio.yml/badge.svg)](https://github.com/bobberdolle1/SkySweep32/actions/workflows/platformio.yml)
[![Hardware gates](https://github.com/bobberdolle1/SkySweep32/actions/workflows/hardware.yml/badge.svg)](https://github.com/bobberdolle1/SkySweep32/actions/workflows/hardware.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

[English](#english) | [Русский](#russian)

---

<a name="english"></a>
## English

### Current status

**Hardware Rev C: READY FOR FIRST PHYSICAL PROTOTYPE — NOT PRODUCTION
VALIDATED.**

Rev C has a native KiCad 10 schematic and four-layer PCB, exact fitted BOM,
zero unexcluded ERC errors/warnings, zero unexcluded DRC violations and zero
unconnected pads, a complete PCBA STEP, CAD-checked enclosure with
fasteners/service envelopes, fabrication exports, and a compiling canonical
firmware target. Eight ERC footprint-filter exceptions and one DRC mixed-pad
exception are explicit, narrowly scoped, and machine-audited. No Rev C board has
yet been assembled or bench-tested. These are design/CAD results, not proof of
RF performance, reliability, compliance, manufacturing yield, or field
operation.

The public `v0.6.1` firmware release predates Rev C and targets legacy ESP32
DevKit wiring. Do not flash those prebuilt binaries onto Rev C. Build the
`esp32s3_rev_c_passive` environment from current source.

| Revision | Status | Authority |
|---|---|---|
| [Rev C](hardware/rev_c/) | Current; first physical prototype only | Canonical schematic, PCB, BOM, pin contract, enclosure, and evidence |
| [Rev B](hardware/rev_b/) | Failed/unverified; do not order | Historical audit evidence only |
| [Rev A](hardware/LEGACY_REV_A_STATUS.md) | Legacy/unverified; do not order | Issue #10 parser-compatibility history only |

### Honest capability matrix

`Implemented in source` does not mean physically validated.

| Capability | Source state | Rev C hardware state | Evidence / limit |
|---|---|---|---|
| 855–925 MHz observation | CC1101 register/RSSI driver compiles | Ebyte E07-900M10S fitted | Channelized RSSI/activity only; RF response unmeasured; no 433 MHz |
| 2.4 GHz observation | SX1281 instantaneous-RSSI driver compiles | Ebyte E28-2G4M12SX fitted | Coarse RSSI/activity sweep only; no protocol or transmitter identity |
| Wi-Fi dashboard | Implemented and compiles | ESP32-S3 radio present | Not run on physical Rev C |
| BLE Remote ID | Experimental parser compiles | ESP32-S3 BLE present | No ASTM/ASD-STAN conformance suite; no FAA/ANSI compliance claim |
| GNSS | NMEA path compiles | u-blox SAM-M10Q-00B fitted | No live-fix or antenna test |
| microSD logging | Implemented and compiles | Molex 104031-0811 fitted | No physical write/endurance test |
| ESP-NOW alerts | Implemented and compiles | ESP32-S3 radio present | No range, coexistence, or multi-node bench test |
| MAVLink / CRSF parsing | Host unit tests and sanitizers pass | No current RF demodulator supplies these byte streams | Parser capability only; not over-air protocol detection |
| TinyML inference | Placeholder dummy model exists in legacy optional source | Excluded from Rev C | Not implemented; rule-based labels are not trained inference |
| 5.8 GHz FPV observation | RX5808 channel/RSSI driver compiles | Procurement-qualified `RX5808-2012-12P` envelope fitted | Eight hardware-selected channels and analog RSSI; supplier/pinout and RF response require incoming/bench checks |
| LoRa / “Meshtastic” | Proprietary experimental packet code | Excluded from Rev C | Not Meshtastic protocol compatibility; no localization validation |
| ATAK CoT | Optional source compiles in legacy full-feature builds | No special Rev C hardware | No interoperability or field test |
| Compass direction finding | Heading-source code only | Excluded from Rev C | A magnetometer cannot determine RF bearing by itself |
| Active countermeasures | Removed from current source and hardware | Excluded | SkySweep32 is a passive monitor |

SkySweep32 must not be described as field-tested, compliant, accurate drone
classification, direction finding, or production-ready without new physical
evidence.

### Rev C architecture

- Espressif `ESP32-S3-WROOM-1-N16R8` with native USB-C programming.
- Ebyte `E07-900M10S` for passive 855–925 MHz RSSI/activity observation.
- Ebyte `E28-2G4M12SX` / SX1281 for passive 2.4 GHz instantaneous-RSSI
  observation, with Adafruit `PID 2308` internal U.FL antenna.
- Qualified-envelope `RX5808-2012-12P` for eight-channel 5.8 GHz analog RSSI
  observation; every procured lot requires the documented incoming checks.
- u-blox `SAM-M10Q-00B`, Molex `104031-0811` microSD socket, and Adafruit
  `PID 326` OLED on a keyed harness.
- Protected USB-C/battery power path using BQ24074, TPS61232, MAX17048, and
  `AP63203WU-7`, with the specified protected Adafruit `PID 328` battery.
- 150 × 95 mm four-layer PCB; continuous L2 ground reference.
- 165.4 × 117.4 × 33.5 mm printed indoor enclosure generated around the
  complete PCBA, battery, display, antennas, harnesses, and fasteners. Not
  sealed or IP rated.
- No LoRa, trained TinyML, RF direction-finding, or active-countermeasure
  hardware.

See [Rev C architecture](hardware/rev_c/ARCHITECTURE.md), [exact manifest](hardware/rev_c/hardware_manifest.json), and [engineering audit](hardware/ENGINEERING_AUDIT_2026-08-11.md).

### Build and verify

Requirements: Python 3.11+, PlatformIO, KiCad 10, FreeCAD 1.0+, and the pinned
Python package/checksums in [`hardware/toolchain.json`](hardware/toolchain.json).

```bash
# Canonical Rev C firmware
python scripts/generate_rev_c_pinmap.py --check
pio run -e esp32s3_rev_c_passive

# Host parser tests
make -C test/host

# Complete electrical, PCB, mechanical, fabrication, render, and firmware gate
python hardware/verify.py
```

The verifier records tool versions, commands, timestamp, source revision, gate
results, and evidence paths in
[`hardware/rev_c/validation/verification_summary.json`](hardware/rev_c/validation/verification_summary.json).
Skipped gates are recorded as skipped, never as passes.

### First-prototype files

- [Rev C engineering README](hardware/rev_c/README.md)
- [Rev C build guide](hardware/rev_c/BUILD.md)
- [Fitted BOM](hardware/rev_c/manufacturing/bom_fitted.csv)
- [Assembly and bring-up](hardware/rev_c/ASSEMBLY_AND_BRINGUP.md)
- [Physical validation checklist](hardware/rev_c/PROTOTYPE_VALIDATION_CHECKLIST.md)
- [Mechanical drawing](hardware/rev_c/enclosure/rev_c_mechanical_drawing.svg)
- [Evidence roadmap](hardware/rev_c/ROADMAP.md)
- [Fabrication manifest](hardware/rev_c/manufacturing/fabrication_manifest.json)

These files support one engineering prototype spin. They are not a
mass-production release.

### Legacy firmware profiles

`esp32dev_base`, `esp32dev_standard`, `esp32dev_pro`, and
`esp32s3_rev_b_pro` remain compile-checked for regression/history. Their pin
maps, BOMs, and enclosure files are incompatible with Rev C. Documentation under
`docs/en/` and `docs/ru/` that describes DevKit “tiers” is retained only as
legacy v0.6.1 firmware history and must not be used to procure Rev C hardware.

### License and lawful use

GNU GPL v3. Passive reception can still be regulated and can expose private or
protected information. Follow local radio, privacy, aviation, and data laws.
The canonical hardware contains no active interference functions.

---

<a name="russian"></a>
## Русский

### Текущий статус

**Hardware Rev C: ГОТОВ К ПЕРВОМУ ФИЗИЧЕСКОМУ ПРОТОТИПУ — НЕ ПРОВЕРЕН ДЛЯ
СЕРИЙНОГО ПРОИЗВОДСТВА.**

Для Rev C подготовлены нативная схема KiCad 10, четырёхслойная PCB, точный BOM,
ERC без неисключённых ошибок/предупреждений и DRC без неисключённых нарушений
или неподключённых цепей, полная STEP-сборка PCBA, корпус с CAD-проверками
коллизий и сервисных зон, Gerber/drill/placement-файлы и отдельная собираемая
конфигурация прошивки. Восемь исключений ERC для фильтров посадочных мест и одно
исключение DRC для смешанных контактных площадок явно задокументированы и
проверяются автоматически. Физическая плата Rev C ещё не собрана и не испытана.
RF-характеристики, надёжность, соответствие нормам и производственный выход не
подтверждены.

Готовые бинарные файлы релиза `v0.6.1` относятся к старой разводке ESP32 DevKit
и несовместимы с Rev C. Для Rev C собирайте только
`esp32s3_rev_c_passive` из текущего исходного кода.

### Что реально делает Rev C

- E07-900M10S: пассивное наблюдение RSSI/активности 855–925 МГц; 433 МГц
  запрещены контрактом.
- E28-2G4M12SX/SX1281: пассивный обзор мгновенного RSSI в диапазоне 2.4 ГГц.
  Это не демодуляция и не распознавание DJI/ELRS/другого протокола.
- RX5808-2012-12P: восемь аппаратно выбираемых каналов 5645–5945 МГц и
  аналоговый RSSI; поставщик, распиновка и RF-отклик проверяются на первом
  экземпляре.
- ESP32-S3: Wi-Fi/BLE и ESP-NOW; работа на физической Rev C ещё не проверена.
- SAM-M10Q, microSD, OLED, защищённый аккумулятор и зарядный тракт
  предусмотрены конкретными деталями, но требуют стендовых испытаний.
- BLE Remote ID остаётся экспериментальным: тестов на соответствие
  ASTM/ASD-STAN нет.
- TinyML не реализован: в legacy-исходниках лежит фиктивная модель.
- LoRa, радиопеленгация и активное подавление исключены из Rev C.

Rev A и Rev B — несовместимые, непроверенные исторические версии. Их нельзя
заказывать и нельзя использовать их pin map/BOM/корпуса для Rev C.

### Сборка и проверка

```bash
python scripts/generate_rev_c_pinmap.py --check
pio run -e esp32s3_rev_c_passive
make -C test/host
python hardware/verify.py
```

Основные документы: [Rev C](hardware/rev_c/README.md),
[сборка и первый запуск](hardware/rev_c/ASSEMBLY_AND_BRINGUP.md),
[чек-лист физического прототипа](hardware/rev_c/PROTOTYPE_VALIDATION_CHECKLIST.md),
[аудит](hardware/ENGINEERING_AUDIT_2026-08-11.md).

Лицензия: GNU GPL v3. Каноническая Rev C — только пассивное устройство и не
содержит аппаратуры активных помех.
