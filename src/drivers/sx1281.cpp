#include "sx1281.h"

#ifdef MODULE_SX1281

#include <cmath>

namespace {
constexpr float kSweepStartMHz = 2400.0f;
constexpr float kSweepStepMHz = 5.0f;
constexpr uint8_t kSweepChannelCount = 21;
constexpr uint8_t kRssiSamples = 4;
constexpr float kRssiFloorDbm = -120.0f;
constexpr float kRssiCeilingDbm = -30.0f;
}  // namespace

float SX1281RssiRadio::readInstantaneousRSSI() {
    uint8_t raw = 0;
    const int16_t state = getMod()->SPIreadStream(
        RADIOLIB_SX128X_CMD_GET_RSSI_INST, &raw, 1);
    if (state != RADIOLIB_ERR_NONE) {
        return NAN;
    }
    return -static_cast<float>(raw) / 2.0f;
}

SX1281Driver::SX1281Driver()
    : module(PIN_SX1281_CS, PIN_SX1281_DIO1, PIN_SX1281_RESET,
             PIN_SX1281_BUSY, SPI),
      radio(&module),
      initialized(false),
      channelIndex(0),
      currentFrequencyMHz(kSweepStartMHz) {}

bool SX1281Driver::begin() {
    // GFSK is used only to place the receiver in a defined wideband RX mode.
    // SkySweep32 never invokes any SX1281 transmit API.
    const int16_t state = radio.beginGFSK(kSweepStartMHz, 800, 400, 0, 16);
    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("[SX1281] Initialization failed: %d\n", state);
        return false;
    }

    const int16_t rxState = radio.startReceive();
    if (rxState != RADIOLIB_ERR_NONE) {
        Serial.printf("[SX1281] RX start failed: %d\n", rxState);
        return false;
    }

    initialized = true;
    Serial.println("[SX1281] Passive 2400-2500 MHz RSSI sweep ready");
    return true;
}

float SX1281Driver::readRSSIDbm() {
    if (!initialized) {
        return kRssiFloorDbm;
    }

    currentFrequencyMHz = kSweepStartMHz + channelIndex * kSweepStepMHz;
    if (radio.standby() != RADIOLIB_ERR_NONE ||
        radio.setFrequency(currentFrequencyMHz) != RADIOLIB_ERR_NONE ||
        radio.startReceive() != RADIOLIB_ERR_NONE) {
        return kRssiFloorDbm;
    }

    delay(2);
    float sum = 0.0f;
    uint8_t validSamples = 0;
    for (uint8_t sample = 0; sample < kRssiSamples; ++sample) {
        const float rssi = radio.readInstantaneousRSSI();
        if (!std::isnan(rssi)) {
            sum += rssi;
            ++validSamples;
        }
        delayMicroseconds(250);
    }

    channelIndex = (channelIndex + 1) % kSweepChannelCount;
    return validSamples == 0 ? kRssiFloorDbm : sum / validSamples;
}

int SX1281Driver::readRSSI() {
    const float rssiDbm = readRSSIDbm();
    const float normalized =
        (rssiDbm - kRssiFloorDbm) * 100.0f /
        (kRssiCeilingDbm - kRssiFloorDbm);
    return constrain(static_cast<int>(normalized + 0.5f), 0, 100);
}

#endif  // MODULE_SX1281
