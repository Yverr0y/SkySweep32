#include "rx5808.h"

#ifdef MODULE_RX5808

RX5808Driver::RX5808Driver(uint8_t dataPin, uint8_t clockPin,
                           uint8_t selectPin, uint8_t rssiAnalogPin)
    : dataPin(dataPin),
      clockPin(clockPin),
      selectPin(selectPin),
      rssiPin(rssiAnalogPin),
      currentBand(RX5808_BAND_R),
      currentChannel(0),
      initialized(false) {
}

RX5808Driver::RX5808Driver(uint8_t legacyControlPin, uint8_t rssiAnalogPin)
    : RX5808Driver(legacyControlPin, legacyControlPin, legacyControlPin,
                   rssiAnalogPin) {
}

bool RX5808Driver::begin() {
    if (dataPin == clockPin || dataPin == selectPin || clockPin == selectPin) {
        Serial.println(
            "[RX5808] ERROR: DATA, CLOCK and SELECT require independent pins");
        return false;
    }

    pinMode(dataPin, OUTPUT);
    pinMode(clockPin, OUTPUT);
    pinMode(selectPin, OUTPUT);
    pinMode(rssiPin, INPUT);
    digitalWrite(dataPin, LOW);
    digitalWrite(clockPin, LOW);
    digitalWrite(selectPin, HIGH);

    delay(100);
    initialized = true;
    setChannel(RX5808_BAND_R, 0);

    Serial.println("[RX5808] Initialized with RTC6715 3-wire control");
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
    
    uint16_t frequency = getFrequencyForChannel(band, channel);
    setFrequency(frequency);
    
    currentBand = band;
    currentChannel = channel;
    
    Serial.printf("[RX5808] Set to %s CH%d (%d MHz)\n", 
                  getBandName(band), channel + 1, frequency);
}

void RX5808Driver::setFrequency(uint16_t frequencyMHz) {
    const uint32_t frame = rx5808_protocol::synthWriteFrame(frequencyMHz);
    writeFrame(frame);
    delay(30); // Allow PLL to lock
}

int RX5808Driver::readRSSI() {
    int rawValue = readRSSIRaw();
    // Convert 12-bit ADC (0-4095) to percentage (0-100)
    return map(rawValue, 0, 4095, 0, 100);
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
    
    Serial.println("[RX5808] Scanning all bands for strongest signal...");
    
    for (uint8_t band = 0; band < 5; band++) {
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
