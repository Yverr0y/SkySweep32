#include "power_manager.h"
#ifdef MODULE_BATTERY_GAUGE
#include <Wire.h>
#endif
#include <esp_wifi.h>
#include <esp_bt.h>

PowerManager powerManager;

#ifdef MODULE_BATTERY_GAUGE
namespace {
constexpr uint8_t kMax17048Address = 0x36;
constexpr uint8_t kMax17048VCellRegister = 0x02;
constexpr uint8_t kMax17048SocRegister = 0x04;

bool readMax17048Register(uint8_t reg, uint16_t& value) {
    Wire.beginTransmission(kMax17048Address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) {
        return false;
    }
    if (Wire.requestFrom(kMax17048Address, static_cast<uint8_t>(2)) != 2) {
        return false;
    }
    value = static_cast<uint16_t>(Wire.read()) << 8;
    value |= Wire.read();
    return true;
}
}  // namespace
#endif

PowerManager::PowerManager()
    : currentMode(POWER_FULL),
      batteryVoltage(0.0f),
      batteryPercent(100),
      batteryMonitoring(false),
      lastBatteryRead(0),
      sleepDurationUs(60000000),     // 60 seconds default
      wakeScansBeforeSleep(3) {}

void PowerManager::begin() {
    // Check if woke from deep sleep
    if (isWakeFromSleep()) {
        Serial.println("[PWR] Woke from deep sleep");
    }
    
    #ifdef MODULE_BATTERY_GAUGE
    Wire.beginTransmission(kMax17048Address);
    batteryMonitoring = Wire.endTransmission() == 0;
    if (!batteryMonitoring) {
        Serial.println("[PWR] MAX17048 fuel gauge not detected");
    }
    #else
    pinMode(PIN_VBAT_ADC, INPUT);
    batteryMonitoring = true;
    #endif

    // Initial battery read.
    getBatteryVoltage();
    
    Serial.printf("[PWR] Battery: %.2fV (%d%%)\n", batteryVoltage, batteryPercent);
    Serial.printf("[PWR] Mode: %s\n", getModeName());
}

void PowerManager::update() {
    // Read battery every 10 seconds
    if (millis() - lastBatteryRead > 10000) {
        getBatteryVoltage();
        lastBatteryRead = millis();
        
        // Auto-switch to low power if battery critical
        if (isBatteryCritical() && currentMode != POWER_SLEEP) {
            Serial.println("[PWR] Battery critical; switching to LOW power mode");
            setMode(POWER_LOW);
        }
    }
}

void PowerManager::setMode(PowerMode mode) {
    if (mode == currentMode) return;
    
    PowerMode prevMode = currentMode;
    currentMode = mode;
    
    switch (mode) {
        case POWER_FULL:
            setCPUFrequency(240);
            setWiFiPowerSave(false);
            Serial.println("[PWR] Mode: FULL (240 MHz, WiFi full power)");
            break;
            
        case POWER_BALANCED:
            setCPUFrequency(160);
            setWiFiPowerSave(true);
            Serial.println("[PWR] Mode: BALANCED (160 MHz, WiFi PS)");
            break;
            
        case POWER_LOW:
            setCPUFrequency(80);
            setWiFiPowerSave(true);
            Serial.println("[PWR] Mode: LOW (80 MHz, WiFi PS, reduced scan)");
            break;
            
        case POWER_SLEEP:
            Serial.println("[PWR] Mode: SLEEP (deep sleep between scans)");
            break;
    }
    
    Serial.printf("[PWR] Mode changed: %d -> %d\n", prevMode, mode);
}

const char* PowerManager::getModeName() const {
    switch (currentMode) {
        case POWER_FULL: return "Full";
        case POWER_BALANCED: return "Balanced";
        case POWER_LOW: return "Low Power";
        case POWER_SLEEP: return "Deep Sleep";
        default: return "Unknown";
    }
}

float PowerManager::getBatteryVoltage() {
    if (!batteryMonitoring) return 0.0f;

    #ifdef MODULE_BATTERY_GAUGE
    uint16_t rawVCell = 0;
    uint16_t rawSoc = 0;
    if (!readMax17048Register(kMax17048VCellRegister, rawVCell) ||
        !readMax17048Register(kMax17048SocRegister, rawSoc)) {
        return batteryVoltage;
    }

    // MAX17048 VCELL register LSB is 78.125 uV; its low nibble is always zero.
    batteryVoltage = static_cast<float>(rawVCell) * 0.000078125f;
    const float stateOfCharge = static_cast<float>(rawSoc) / 256.0f;
    batteryPercent = static_cast<uint8_t>(
        constrain(stateOfCharge, 0.0f, 100.0f) + 0.5f);
    #else
    uint32_t sum = 0;
    for (int sample = 0; sample < 16; ++sample) {
        sum += analogRead(PIN_VBAT_ADC);
    }
    const uint32_t rawADC = sum / 16;
    const float measuredVoltage = (rawADC / 4095.0f) * 3.3f;
    batteryVoltage = measuredVoltage * VBAT_DIVIDER_RATIO;
    if (batteryVoltage >= VBAT_FULL) {
        batteryPercent = 100;
    } else if (batteryVoltage <= VBAT_EMPTY) {
        batteryPercent = 0;
    } else {
        batteryPercent = static_cast<uint8_t>(
            ((batteryVoltage - VBAT_EMPTY) / (VBAT_FULL - VBAT_EMPTY)) *
            100.0f);
    }
    #endif

    return batteryVoltage;
}

uint8_t PowerManager::getBatteryPercent() {
    return batteryPercent;
}

bool PowerManager::isBatteryLow() {
    return batteryPercent < 15;
}

bool PowerManager::isBatteryCritical() {
    return batteryPercent < 5;
}

void PowerManager::configureSleep(uint32_t sleepSeconds, uint8_t scansPerWake) {
    sleepDurationUs = sleepSeconds * 1000000ULL;
    wakeScansBeforeSleep = scansPerWake;
    Serial.printf("[PWR] Sleep config: %us, %d scans/wake\n", sleepSeconds, scansPerWake);
}

void PowerManager::enterDeepSleep() {
    Serial.printf("[PWR] Entering deep sleep for %llu seconds...\n", (unsigned long long)(sleepDurationUs / 1000000));
    Serial.flush();
    
    // Configure wake source: timer
    esp_sleep_enable_timer_wakeup(sleepDurationUs);
    
    // Can also wake on GPIO (e.g., button press)
    // esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);  // Wake on GPIO0 LOW
    
    esp_deep_sleep_start();
    // Never reaches here — ESP32 resets on wake
}

void PowerManager::enterLightSleep(uint32_t durationMs) {
    Serial.printf("[PWR] Light sleep: %u ms\n", durationMs);
    Serial.flush();
    
    esp_sleep_enable_timer_wakeup(durationMs * 1000ULL);
    esp_light_sleep_start();
    
    Serial.println("[PWR] Woke from light sleep");
}

bool PowerManager::isWakeFromSleep() {
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    return (cause == ESP_SLEEP_WAKEUP_TIMER || 
            cause == ESP_SLEEP_WAKEUP_EXT0 ||
            cause == ESP_SLEEP_WAKEUP_EXT1);
}

void PowerManager::setCPUFrequency(uint32_t mhz) {
    if (mhz != 80 && mhz != 160 && mhz != 240) {
        mhz = 240;  // Fallback to default
    }
    setCpuFrequencyMhz(mhz);
    Serial.printf("[PWR] CPU: %u MHz\n", getCpuFrequencyMhz());
}

void PowerManager::disableBluetoothPower() {
    esp_bt_controller_disable();
    Serial.println("[PWR] Bluetooth disabled");
}

void PowerManager::enableBluetoothPower() {
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    Serial.println("[PWR] Bluetooth enabled (BLE)");
}

void PowerManager::setWiFiPowerSave(bool enable) {
    if (enable) {
        esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
    } else {
        esp_wifi_set_ps(WIFI_PS_NONE);
    }
}

uint32_t PowerManager::getEstimatedRuntimeMinutes() {
    if (batteryPercent == 0) return 0;
    
    // Rough estimations based on power mode and 2500mAh battery
    float currentDrawMA;
    switch (currentMode) {
        case POWER_FULL: currentDrawMA = 450; break;
        case POWER_BALANCED: currentDrawMA = 280; break;
        case POWER_LOW: currentDrawMA = 150; break;
        case POWER_SLEEP: currentDrawMA = 30; break;  // Average including sleep
        default: currentDrawMA = 400; break;
    }
    
    float remainingMAh = 2500.0f * (batteryPercent / 100.0f);
    return (uint32_t)((remainingMAh / currentDrawMA) * 60.0f);
}
