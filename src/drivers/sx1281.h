#ifndef SX1281_H
#define SX1281_H

#include <Arduino.h>
#include <RadioLib.h>
#include "../config.h"

#ifdef MODULE_SX1281

class SX1281RssiRadio : public SX1281 {
public:
    using SX1281::SX1281;

    float readInstantaneousRSSI();
};

class SX1281Driver {
public:
    SX1281Driver();

    bool begin();
    int readRSSI();
    float readRSSIDbm();
    float getCurrentFrequencyMHz() const { return currentFrequencyMHz; }

private:
    Module module;
    SX1281RssiRadio radio;
    bool initialized;
    uint8_t channelIndex;
    float currentFrequencyMHz;
};

#endif  // MODULE_SX1281
#endif  // SX1281_H
