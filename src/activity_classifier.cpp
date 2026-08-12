#include "activity_classifier.h"

#include "config.h"
#include "config_manager.h"

ActivityClassifier::ActivityClassifier()
    : currentActivity{0, 0, ACTIVITY_NONE, 0, 0, false} {}

ActivityLevel ActivityClassifier::assessActivity(
    uint8_t moduleIndex,
    int normalizedRssi) {
    const RuntimeConfig& cfg = configManager.get();
    const ActivityThresholds thresholds = {
        cfg.rssiThresholdLow,
        cfg.rssiThresholdMedium,
        cfg.rssiThresholdHigh,
        cfg.rssiThresholdCritical,
    };
    const ActivityLevel level = classifyActivityLevel(normalizedRssi, thresholds);
    const uint32_t now = millis();

    if (level > ACTIVITY_NONE) {
        if (!currentActivity.isActive) currentActivity.firstObservedTime = now;
        currentActivity.moduleIndex = moduleIndex;
        currentActivity.normalizedRssi = normalizedRssi;
        currentActivity.level = level;
        currentActivity.lastUpdateTime = now;
        currentActivity.isActive = true;
    } else if (currentActivity.isActive &&
               now - currentActivity.lastUpdateTime > ACTIVITY_TIMEOUT_MS) {
        currentActivity.level = ACTIVITY_NONE;
        currentActivity.isActive = false;
    }

    return level;
}

const char* ActivityClassifier::getActivityLevelString(ActivityLevel level) const {
    switch (level) {
        case ACTIVITY_NONE: return "NONE";
        case ACTIVITY_LOW: return "LOW";
        case ACTIVITY_MEDIUM: return "MEDIUM";
        case ACTIVITY_HIGH: return "HIGH";
        case ACTIVITY_CRITICAL: return "CRITICAL";
        default: return "UNKNOWN";
    }
}
