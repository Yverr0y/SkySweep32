#!/usr/bin/env python3
"""Validate the Rev B hardware manifest and generate its firmware pin map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "hardware" / "rev_b" / "hardware_manifest.yaml"
DEFAULT_HEADER = ROOT / "src" / "generated" / "hardware_rev_b.h"


class ManifestError(ValueError):
    """The hardware manifest violates a design invariant."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError("manifest root must be an object")
    return value


def require_object(parent: dict[str, Any], name: str) -> dict[str, Any]:
    value = parent.get(name)
    if not isinstance(value, dict) or not value:
        raise ManifestError(f"{name} must be a non-empty object")
    return value


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ManifestError("schema_version must be 1")

    design = require_object(manifest, "design")
    firmware = require_object(manifest, "firmware")
    mcu = require_object(manifest, "mcu")
    rails = require_object(manifest, "rails")
    buses = require_object(manifest, "buses")
    signals = require_object(manifest, "signals")
    modules = require_object(manifest, "modules")

    if design.get("orderable") is not False:
        raise ManifestError("Rev B must remain non-orderable until physical validation")
    if mcu.get("part_number") != "ESP32-S3-WROOM-1-N8":
        raise ManifestError("only the locked no-PSRAM ESP32-S3-WROOM-1-N8 is valid")
    if firmware.get("board_macro") != "BOARD_SKYSWEEP32_REV_B":
        raise ManifestError("unexpected Rev B firmware board macro")

    forbidden = {int(pin) for pin in require_object(mcu, "forbidden_gpio")}
    used: dict[int, str] = {}
    macros: dict[str, str] = {}
    nets: dict[str, str] = {}
    for name, signal in signals.items():
        if not isinstance(signal, dict):
            raise ManifestError(f"signal {name} must be an object")
        gpio = signal.get("gpio")
        macro = signal.get("firmware_macro")
        net = signal.get("net")
        if not isinstance(gpio, int) or not 0 <= gpio <= 48:
            raise ManifestError(f"signal {name} has invalid GPIO {gpio!r}")
        if gpio in forbidden:
            raise ManifestError(f"signal {name} uses forbidden GPIO{gpio}")
        if gpio in used:
            raise ManifestError(f"GPIO{gpio} is shared by {used[gpio]} and {name}")
        if not isinstance(macro, str) or not macro.startswith("PIN_"):
            raise ManifestError(f"signal {name} has invalid firmware_macro")
        if macro in macros:
            raise ManifestError(f"firmware macro {macro} is shared by {macros[macro]} and {name}")
        if not isinstance(net, str) or not net.startswith("/"):
            raise ManifestError(f"signal {name} has invalid KiCad net name")
        if net in nets:
            raise ManifestError(f"KiCad net {net} is shared by {nets[net]} and {name}")
        used[gpio] = name
        macros[macro] = name
        nets[net] = name

    analog = {
        name: signal
        for name, signal in signals.items()
        if signal.get("direction") == "analog_input"
    }
    if set(analog) != {"RX5808_RSSI", "VBAT_ADC"}:
        raise ManifestError("exactly RX5808_RSSI and VBAT_ADC must be analog inputs")
    analog_pins = {signal["gpio"] for signal in analog.values()}
    if len(analog_pins) != 2:
        raise ManifestError("RX5808 RSSI and VBAT ADC must use independent GPIOs")
    for name, signal in analog.items():
        if signal.get("adc_unit") != 1:
            raise ManifestError(f"{name} must use ADC1 for Wi-Fi coexistence")

    assigned_bus_signals: set[str] = set()
    for bus_name, bus in buses.items():
        if not isinstance(bus, dict):
            raise ManifestError(f"bus {bus_name} must be an object")
        for signal_name in bus.get("signals", []):
            if signal_name not in signals:
                raise ManifestError(f"bus {bus_name} references unknown signal {signal_name}")
            if signal_name in assigned_bus_signals:
                raise ManifestError(f"signal {signal_name} belongs to multiple buses")
            assigned_bus_signals.add(signal_name)
        for module_ref in bus.get("members", []):
            if module_ref not in modules:
                raise ManifestError(f"bus {bus_name} references unknown module {module_ref}")

    allowed_non_signal = set(rails) | {
        "GND",
        "NC",
        "RX5808_RF_COAX",
        "TP_NRF24_IRQ",
        "TP_CC1101_GDO0",
        "TP_CC1101_GDO2",
    }
    for ref, module in modules.items():
        if not isinstance(module, dict):
            raise ManifestError(f"module {ref} must be an object")
        rail = module.get("rail")
        if rail is not None and rail not in rails:
            raise ManifestError(f"module {ref} references unknown rail {rail}")
        pin_map = module.get("module_pins", {})
        if not isinstance(pin_map, dict):
            raise ManifestError(f"module {ref} module_pins must be an object")
        for pin, connection in pin_map.items():
            if connection not in signals and connection not in allowed_non_signal:
                raise ManifestError(
                    f"module {ref} pin {pin} references unknown connection {connection}"
                )

    required_test_points = {
        "GND",
        "VBUS_PROTECTED",
        "3V3_MAIN",
        "VBAT_ADC",
        "RX5808_RSSI",
        "RF_SPI_SCK",
        "RF_SPI_MOSI",
        "RF_SPI_MISO",
    }
    test_points = manifest.get("test_points")
    if not isinstance(test_points, list) or not required_test_points.issubset(test_points):
        missing = sorted(required_test_points - set(test_points or []))
        raise ManifestError(f"missing mandatory test points: {', '.join(missing)}")


def render_header(manifest: dict[str, Any], manifest_path: Path) -> str:
    firmware = manifest["firmware"]
    signals = manifest["signals"]
    relative_manifest = manifest_path.resolve().relative_to(ROOT).as_posix()
    lines = [
        "// Generated by scripts/generate_rev_b_pinmap.py; do not edit.",
        f"// Source: {relative_manifest}",
        "#pragma once",
        "",
        f"#define {firmware['board_macro']} 1",
        "",
    ]
    for signal_name, signal in signals.items():
        lines.append(f"#define {signal['firmware_macro']:<22} {signal['gpio']:<2} // {signal_name}")
    lines.extend(
        [
            "",
            "#define GPS_BAUD_RATE          9600",
            "#define GPS_UPDATE_INTERVAL    1000",
            "",
            "#if defined(TIER_JUGGERNAUT) || defined(ENABLE_COUNTERMEASURES)",
            '#error "Rev B is passive-only and has no countermeasure hardware"',
            "#endif",
            "",
            "#ifdef MODULE_ACOUSTIC",
            '#error "The canonical Rev B PCB does not route an I2S acoustic input"',
            "#endif",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--check", action="store_true", help="fail if output is stale")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    validate_manifest(manifest)
    rendered = render_header(manifest, args.manifest)

    if args.check:
        try:
            existing = args.output.read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"[FAIL] generated pin map missing: {exc}") from exc
        if existing != rendered:
            raise SystemExit(
                "[FAIL] generated Rev B pin map is stale; run "
                "python scripts/generate_rev_b_pinmap.py"
            )
        print(f"[PASS] manifest and generated pin map agree: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"[PASS] validated {args.manifest}")
    print(f"[OK] generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
