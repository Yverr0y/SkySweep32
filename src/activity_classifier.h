#ifndef ACTIVITY_CLASSIFIER_H
#define ACTIVITY_CLASSIFIER_H

#include <Arduino.h>

// Relative levels derived only from each receiver's normalized 0-100 energy/RSSI
// output. They do not identify a transmitter, protocol, range, intent, or threat.
enum ActivityLevel {
    ACTIVITY_NONE = 0,
    ACTIVITY_LOW = 1,
    ACTIVITY_MEDIUM = 2,
    ACTIVITY_HIGH = 3,
    ACTIVITY_CRITICAL = 4,
};

struct ActivityThresholds {
    int low;
    int medium;
    int high;
    int critical;
};

struct ActivityData {
    uint8_t moduleIndex;
    int normalizedRssi;
    ActivityLevel level;
    uint32_t firstObservedTime;
    uint32_t lastUpdateTime;
    bool isActive;
};

inline ActivityLevel classifyActivityLevel(
    int normalizedRssi,
    const ActivityThresholds& thresholds) {
    if (normalizedRssi >= thresholds.critical) return ACTIVITY_CRITICAL;
    if (normalizedRssi >= thresholds.high) return ACTIVITY_HIGH;
    if (normalizedRssi >= thresholds.medium) return ACTIVITY_MEDIUM;
    if (normalizedRssi >= thresholds.low) return ACTIVITY_LOW;
    return ACTIVITY_NONE;
}

class ActivityClassifier {
public:
    ActivityClassifier();

    ActivityLevel assessActivity(uint8_t moduleIndex, int normalizedRssi);
    ActivityData getCurrentActivity() const { return currentActivity; }
    const char* getActivityLevelString(ActivityLevel level) const;

private:
    ActivityData currentActivity;
};

#endif  // ACTIVITY_CLASSIFIER_H
