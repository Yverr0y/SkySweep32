#include "rx5808.h"

#ifdef MODULE_RX5808

RX5808Driver::RX5808Driver(ControlMode mode, uint8_t pin1, uint8_t pin2,
                           uint8_t pin3, uint8_t rssiAnalogPin)
    : controlMode(mode),
      dataPin(pin1),
      clockPin(pin2),
      selectPin(pin3),
      rssiPin(rssiAnalogPin),
      currentBand(mode == THREE_BIT_STRAP ? RX5808_BAND_E : RX5808_BAND_R),
      currentChannel(0),
      initialized(false),
      scanStarted(false) {
}

RX5808Driver::RX5808Driver(uint8_t dataPin, uint8_t clockPin,
                           uint8_t selectPin, uint8_t rssiAnalogPin)
    : RX5808Driver(RTC6715_SERIAL, dataPin, clockPin, selectPin,
                   rssiAnalogPin) {
}

RX5808Driver::RX5808Driver(uint8_t legacyControlPin, uint8_t rssiAnalogPin)
    : RX5808Driver(RTC6715_SERIAL, legacyControlPin, legacyControlPin,
                   legacyControlPin, rssiAnalogPin) {
}

bool RX5808Driver::begin() {
    if (dataPin == clockPin || dataPin == selectPin || clockPin == selectPin) {
        Serial.println("[RX5808] ERROR: three independent control pins required");
        return false;
    }

    pinMode(dataPin, OUTPUT);
    pinMode(clockPin, OUTPUT);
    pinMode(selectPin, OUTPUT);
    pinMode(rssiPin, INPUT);
    digitalWrite(dataPin, LOW);
    digitalWrite(clockPin, LOW);
    digitalWrite(selectPin, controlMode == RTC6715_SERIAL ? HIGH : LOW);

    delay(100);
    initialized = true;
    setChannel(
        controlMode == THREE_BIT_STRAP ? RX5808_BAND_E : RX5808_BAND_R, 0);

    Serial.println(controlMode == THREE_BIT_STRAP
                       ? "[RX5808] Initialized with CH1/CH2/CH3 strap control"
                       : "[RX5808] Initialized with modified RTC6715 serial control");
    return true;
}

void RX5808Driver::writeFrame(uint32_t frame) {
    digitalWrite(selectPin, LOW);
    digitalWrite(clockPin, LOW);
    delayMicroseconds(1);

    for (uint8_t bit = 0; bit < rx5808_protocol::kFrameBitCount; ++bit) {
        digitalWrite(dataPin, rx5808_protocol::frameBit(frame, bit) ? HIGH : LOW);
        delayMicroseconds(1);
        digitalWrite(clockPin, HIGH);
        delayMicroseconds(1);
        digitalWrite(clockPin, LOW);
        delayMicroseconds(1);
    }

    digitalWrite(dataPin, LOW);
    digitalWrite(selectPin, HIGH);
    delayMicroseconds(1);
}

uint16_t RX5808Driver::getFrequencyForChannel(uint8_t band, uint8_t channel) {
    if (band > 4 || channel > 7) {
        return 5800; // Default fallback
    }
    return RX5808_FREQ_TABLE[band][channel];
}


void RX5808Driver::setChannel(uint8_t band, uint8_t channel) {
    if (band > 4 || channel > 7) {
        Serial.println("[RX5808] Invalid band/channel");
        return;
    }

    const uint16_t frequency = getFrequencyForChannel(band, channel);
    if (controlMode == THREE_BIT_STRAP) {
        if (band != RX5808_BAND_E) {
            Serial.println("[RX5808] Strap mode supports Band E only");
            return;
        }
        // RX5808 V1.0 table: CH1 is the LSB, CH3 is the MSB.
        digitalWrite(dataPin, (channel & 0b001) ? HIGH : LOW);
        digitalWrite(clockPin, (channel & 0b010) ? HIGH : LOW);
        digitalWrite(selectPin, (channel & 0b100) ? HIGH : LOW);
        delay(30);
    } else {
        setFrequency(frequency);
    }

    currentBand = band;
    currentChannel = channel;
    Serial.printf("[RX5808] Set to %s CH%d (%d MHz)\n",
                  getBandName(band), channel + 1, frequency);
}

void RX5808Driver::setFrequency(uint16_t frequencyMHz) {
    if (controlMode == THREE_BIT_STRAP) {
        for (uint8_t channel = 0; channel < 8; ++channel) {
            if (RX5808_FREQ_TABLE[RX5808_BAND_E][channel] == frequencyMHz) {
                setChannel(RX5808_BAND_E, channel);
                return;
            }
        }
        Serial.println("[RX5808] Frequency unavailable in strap mode");
        return;
    }

    const uint32_t frame = rx5808_protocol::synthWriteFrame(frequencyMHz);
    writeFrame(frame);
    delay(30);
}

int RX5808Driver::readRSSI() {
    // Conservative uncalibrated endpoints for common RX5808 module RSSI
    // outputs. Physical prototype characterization must replace these before
    // absolute field-strength or detection-range claims are made.
    constexpr int kRssiMinimumMilliVolts = 350;
    constexpr int kRssiMaximumMilliVolts = 1400;
    uint32_t sumMilliVolts = 0;
    constexpr uint8_t kSamples = 8;
    for (uint8_t sample = 0; sample < kSamples; ++sample) {
        sumMilliVolts += analogReadMilliVolts(rssiPin);
        delayMicroseconds(100);
    }
    const int averageMilliVolts = sumMilliVolts / kSamples;
    return constrain(
        map(averageMilliVolts, kRssiMinimumMilliVolts,
            kRssiMaximumMilliVolts, 0, 100),
        0, 100);
}

int RX5808Driver::scanNextChannel() {
    if (!initialized) return 0;

    if (scanStarted) {
        ++currentChannel;
        if (currentChannel >= 8) {
            currentChannel = 0;
            if (controlMode == RTC6715_SERIAL) {
                currentBand = (currentBand + 1) % 5;
            }
        }
        setChannel(currentBand, currentChannel);
    } else {
        scanStarted = true;
    }

    return readRSSI();
}

int RX5808Driver::readRSSIRaw() {
    // Average multiple readings for stability
    uint32_t sum = 0;
    const uint8_t samples = 10;
    
    for (uint8_t i = 0; i < samples; i++) {
        sum += analogRead(rssiPin);
        delayMicroseconds(100);
    }
    
    return sum / samples;
}

void RX5808Driver::scanBand(uint8_t band, int* rssiValues) {
    if (band > 4) {
        Serial.println("[RX5808] Invalid band");
        return;
    }
    if (controlMode == THREE_BIT_STRAP && band != RX5808_BAND_E) {
        for (uint8_t channel = 0; channel < 8; ++channel) {
            rssiValues[channel] = 0;
        }
        Serial.println("[RX5808] Strap mode can scan Band E only");
        return;
    }
    
    Serial.printf("[RX5808] Scanning %s band...\n", getBandName(band));
    
    for (uint8_t ch = 0; ch < 8; ch++) {
        setChannel(band, ch);
        delay(50); // Settling time
        rssiValues[ch] = readRSSI();
        Serial.printf("  CH%d (%d MHz): %d%%\n", 
                     ch + 1, 
                     getFrequencyForChannel(band, ch), 
                     rssiValues[ch]);
    }
}

RX5808Channel RX5808Driver::findStrongestChannel() {
    RX5808Channel strongest = {0, 0, 0};
    int maxRSSI = 0;
    
    Serial.println(controlMode == THREE_BIT_STRAP
                       ? "[RX5808] Scanning eight strap-selected channels..."
                       : "[RX5808] Scanning all serially tuned bands...");

    const uint8_t firstBand =
        controlMode == THREE_BIT_STRAP ? RX5808_BAND_E : 0;
    const uint8_t bandLimit =
        controlMode == THREE_BIT_STRAP ? RX5808_BAND_E + 1 : 5;
    for (uint8_t band = firstBand; band < bandLimit; band++) {
        for (uint8_t ch = 0; ch < 8; ch++) {
            setChannel(band, ch);
            delay(50);
            int rssi = readRSSI();

            if (rssi > maxRSSI) {
                maxRSSI = rssi;
                strongest.band = band;
                strongest.channel = ch;
                strongest.frequency = getFrequencyForChannel(band, ch);
            }
        }
    }
    
    Serial.printf("[RX5808] Strongest: %s CH%d (%d MHz) - %d%%\n",
                  getBandName(strongest.band),
                  strongest.channel + 1,
                  strongest.frequency,
                  maxRSSI);
    
    return strongest;
}

uint16_t RX5808Driver::getCurrentFrequency() {
    return getFrequencyForChannel(currentBand, currentChannel);
}

const char* RX5808Driver::getBandName(uint8_t band) {
    switch(band) {
        case RX5808_BAND_A: return "Boscam A";
        case RX5808_BAND_B: return "Boscam B";
        case RX5808_BAND_E: return "Boscam E";
        case RX5808_BAND_F: return "Fatshark";
        case RX5808_BAND_R: return "Raceband";
        default: return "Unknown";
    }
}

#endif // MODULE_RX5808
