# Host unit tests

Desktop-compiled unit tests for the pure-logic protocol parsers
(`src/protocols/crsf_parser.cpp`, `src/protocols/mavlink_parser.cpp`).

These parsers decode **attacker-controlled RF input**, so they are the highest-value
code to test for memory safety. They depend only on fixed-width integer types and
`memcpy`/`memset`, so they build against the tiny [`Arduino.h`](Arduino.h) stub in
this directory with any desktop compiler — **no ESP32 toolchain or PlatformIO
registry required**.

## Run

```bash
make -C test/host
```

This compiles the real parser sources with **AddressSanitizer + UndefinedBehaviorSanitizer**
and runs the suite. Any out-of-bounds read/write on a malformed frame aborts the
process, so the "malicious frame" cases double as overflow regression guards.

Coverage includes:

- CRSF: hostile length bytes (`0xFE`/`0xFF`) and over-max payloads are rejected
  without overflowing the 60-byte payload buffer; known-good receive fixtures
  validate CRC handling and field offsets.
- MAVLink: a valid heartbeat fixture parses; a maximum 255-byte-payload frame
  validates without length wrap; message IDs lacking a known CRC_EXTRA entry
  and truncated frames are rejected; `parseHeartbeat` zero-initializes on short
  payloads.
- Field helpers: a known-good CRSF RC-channel fixture validates 11-bit
  unpacking, and the CRSF/MAVLink GPS + heartbeat `parse*` helpers decode full
  payloads correctly while returning zeroed structs on short (out-of-bounds)
  payloads.
- Fuzz: ~460k random and adversarial frames (valid sync + random length byte,
  hitting every boundary incl. `0xFE`/`0xFF`) fed to both parsers — the
  sanitizers turn any out-of-bounds access into a hard failure. Deterministic
  (seeded xorshift), runs in well under a second.

CI runs the same command via [`.github/workflows/host-tests.yml`](../../.github/workflows/host-tests.yml).
