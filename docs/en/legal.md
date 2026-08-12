# Legal and regulatory scope

SkySweep32 Rev C is a receive-oriented passive monitor. The repository contains
no RF-jamming, protocol-injection, deauthentication, or GPS-denial
implementation and no corresponding transmit hardware.

Passive does not mean unregulated. Wi-Fi, Bluetooth, ESP-NOW, and any fitted
sub-GHz module can transmit during normal operation. Radio approvals, permitted
frequencies, antenna limits, privacy rules, data-retention rules, and aviation
reporting requirements vary by jurisdiction. Rev C has not been tested for
regulatory compliance and must not be sold or deployed on the basis of the CAD
checks in this repository.

Before operating a prototype:

1. Verify that every enabled transmitter and antenna combination is permitted
   in the country of use.
2. Disable features whose frequency or radio approval does not apply locally.
3. Do not infer identity, intent, distance, or aircraft presence from a coarse
   energy/RSSI observation.
4. Handle received Remote ID and location data under applicable privacy and
   retention rules.
5. Report safety concerns through the competent local authority; do not attempt
   interference.

Primary regulatory sources include the
[FCC](https://www.fcc.gov/),
[European Commission Radio Equipment Directive](https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red_en),
and national spectrum authorities. Consult qualified local counsel for a real
deployment. This page is engineering-scope information, not legal advice.
