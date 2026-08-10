#ifndef RX5808_PROTOCOL_H
#define RX5808_PROTOCOL_H

#include <stdint.h>

namespace rx5808_protocol {

constexpr uint8_t kSynthRegisterAddress = 0x01;
constexpr uint8_t kFrameBitCount = 25;
constexpr uint32_t kPayloadMask = 0x000FFFFFUL;
constexpr uint16_t synthDivider(uint16_t frequencyMHz) {
    return static_cast<uint16_t>((frequencyMHz - 479U) / 2U);
}

// RTC6715 synthesizer divider encoding:
// F_LO = (frequency_MHz - 479) / 2, N = F_LO / 32, A = F_LO % 32.
constexpr uint32_t synthPayload(uint16_t frequencyMHz) {
    return (static_cast<uint32_t>(synthDivider(frequencyMHz) / 32U) << 7U) |
           static_cast<uint32_t>(synthDivider(frequencyMHz) % 32U);
}

// Wire order is address[3:0], write bit, then data[19:0], all LSB first.
constexpr uint32_t writeFrame(uint8_t address, uint32_t payload) {
    return (static_cast<uint32_t>(address) & 0x0FUL) |
           (1UL << 4U) |
           ((payload & kPayloadMask) << 5U);
}

constexpr uint32_t synthWriteFrame(uint16_t frequencyMHz) {
    return writeFrame(kSynthRegisterAddress, synthPayload(frequencyMHz));
}

constexpr bool frameBit(uint32_t frame, uint8_t bitIndex) {
    return ((frame >> bitIndex) & 0x01UL) != 0;
}

}  // namespace rx5808_protocol

#endif  // RX5808_PROTOCOL_H
