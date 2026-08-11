#!/usr/bin/env python3
"""Fetch and checksum external hardware tools pinned in hardware/toolchain.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "hardware" / "toolchain.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only verify cached files")
    args = parser.parse_args()

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    router = lock["freerouting"]
    destination = ROOT / router["cache_path"]
    expected = router["sha256"]
    if destination.is_file() and sha256(destination) == expected:
        print(f"[PASS] {destination.relative_to(ROOT)} sha256={expected}")
        return 0
    if args.check:
        raise SystemExit(f"[FAIL] missing or invalid pinned router: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    print(f"[INFO] Fetching {router['url']}")
    with urllib.request.urlopen(router["url"], timeout=120) as response:
        temporary.write_bytes(response.read())
    actual = sha256(temporary)
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"[FAIL] Freerouting checksum {actual}; expected {expected}")
    temporary.replace(destination)
    print(f"[PASS] {destination.relative_to(ROOT)} sha256={expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
