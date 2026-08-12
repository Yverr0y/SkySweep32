# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| master  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**DO NOT** open public issues for security vulnerabilities.

Report security issues through
[GitHub Security Advisories](https://github.com/bobberdolle1/SkySweep32/security/advisories/new)
so the report and any proof of concept remain private.

### What to include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline:
- Initial response: 48 hours
- Status update: 7 days
- Fix timeline: Depends on severity

## Security considerations

### Passive product scope

Canonical Rev C is passive with respect to the signals it observes: it contains
no RF-jamming, protocol-injection, deauthentication, or GPS-denial
implementation. Those functions are not supported.

“Passive monitor” does not mean RF-silent. The Wi-Fi dashboard and ESP-NOW
status/activity network intentionally transmit ordinary 2.4 GHz communications;
those paths are not countermeasures. The ESP32-S3, CC1101, and SX1281 are also
physically transmit-capable devices. Firmware configuration alone is not a
regulatory authorization. Contributors must preserve the passive observation
profile and comply with local radio, privacy, aviation, and data law.

### Security-relevant interfaces

Treat BLE/Wi-Fi/RF parser input as untrusted. Relevant reports include:

- malformed packets causing memory corruption, reset loops, or resource
  exhaustion;
- unauthenticated web, configuration, logging, or OTA paths;
- leakage of stored GNSS observations, logs, or network credentials;
- malicious firmware, dependency, manufacturing, or component substitutions.

## Responsible Disclosure

We follow responsible disclosure practices:
1. Report received and acknowledged
2. Vulnerability verified
3. Fix developed and tested
4. Security advisory published
5. CVE assigned (if applicable)

## Legal Notice

This project is for:
- Educational purposes
- Authorized defense applications
- Research in controlled environments

**Illegal use is strictly prohibited and not supported by maintainers.**
