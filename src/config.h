#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// SkySweep32 Configuration File
// Central configuration for all modules, pins, and feature flags
// ============================================================================

// ============================================================================
// TIER SELECTION — Choose your hardware configuration
// Uncomment ONE tier, or define via platformio.ini build_flags
// ============================================================================

// #define TIER_BASE       // ESP32 + OLED + NRF24L01+ (~$15-20)
// #define TIER_STANDARD   // Base + CC1101 + RX5808 (~$35-45)
// #define TIER_PRO        // Standard + GPS + SD + LoRa (~$60-80)

// Default to TIER_STANDARD if nothing defined
#if !defined(PROFILE_PASSIVE_MONITOR) && !defined(TIER_BASE) && !defined(TIER_STANDARD) && !defined(TIER_PRO)
    #define TIER_STANDARD
#endif

// ============================================================================
// MODULE FLAGS — Auto-configured by tier, or override individually
// ============================================================================

// Canonical Rev C passive profile. Keep this list synchronized through the
// manifest-gated PlatformIO target rather than inheriting legacy release tiers.
#ifdef PROFILE_PASSIVE_MONITOR
    #define MODULE_SX1281
    #define MODULE_CC1101
    #define MODULE_RX5808
    #define MODULE_BATTERY_GAUGE
    #define MODULE_OLED
    #define MODULE_WEB_SERVER
    #define MODULE_REMOTE_ID
    #define MODULE_GPS
    #define MODULE_SD_CARD
    #define MODULE_ESPNOW
#endif

// --- Tier: Base ---
#if defined(TIER_BASE) || defined(TIER_STANDARD) || defined(TIER_PRO)
    #ifndef MODULE_NRF24
        #define MODULE_NRF24              // 2.4 GHz monitoring (NRF24L01+)
    #endif
    #ifndef MODULE_OLED
        #define MODULE_OLED               // 128x64 OLED display
    #endif
    #ifndef MODULE_WEB_SERVER
        #define MODULE_WEB_SERVER         // WiFi AP + Web Dashboard
    #endif
    #ifndef MODULE_REMOTE_ID
        #define MODULE_REMOTE_ID          // BLE Remote ID (free, uses ESP32 BLE)
    #endif
#endif

// --- Tier: Standard (adds RF modules) ---
#if defined(TIER_STANDARD) || defined(TIER_PRO)
    #ifndef MODULE_CC1101
        #define MODULE_CC1101             // 900 MHz monitoring (CC1101)
    #endif
    #ifndef MODULE_RX5808
        #define MODULE_RX5808             // 5.8 GHz monitoring (RX5808)
    #endif
#endif

// --- Tier: Pro (adds GPS, SD, LoRa) ---
#if defined(TIER_PRO)
    #ifndef MODULE_GPS
        #define MODULE_GPS                // GPS geolocation (NEO-6M/7M)
    #endif
    #ifndef MODULE_SD_CARD
        #define MODULE_SD_CARD            // SD card forensic logging
    #endif
    #ifndef MODULE_LORA
        #define MODULE_LORA               // LoRa mesh networking (SX1276)
    #endif
#endif


// --- Optional modules (enable manually in any tier) ---
// #define MODULE_ACOUSTIC            // MEMS microphone acoustic detection (~$5)
// TinyML is never auto-enabled. MODULE_ML remains an explicit experimental
// opt-in because the repository does not contain a trained production model.

// ============================================================================
// PIN DEFINITIONS
// ============================================================================

#ifdef BOARD_SKYSWEEP32_REV_C

// Generated from hardware/rev_c/hardware_manifest.json. The PlatformIO Rev C
// environment rejects a stale generated header before compilation.
#include "generated/hardware_rev_c.h"

#elif defined(BOARD_SKYSWEEP32_REV_B)

// Legacy, non-orderable Rev B pin map retained only for reproducibility.
#include "generated/hardware_rev_b.h"
#define PIN_RX5808_CONTROL  PIN_RX5808_SELECT

#else

// Legacy Rev A / ESP32 DevKit pin map. Rev A hardware is unverified and retained
// only for compatibility with the existing release targets.
#define PIN_SPI_MOSI        23
#define PIN_SPI_MISO        19
#define PIN_SPI_SCK         18

#define PIN_CC1101_CS       5

#define PIN_NRF24_CS        15
#define PIN_NRF24_CE        2

// The legacy board exposed only one RX5808 control pin and cannot drive the
// RTC6715 three-wire protocol. The corrected Rev B driver is board-gated.
#define PIN_RX5808_CS       13
#define PIN_RX5808_RSSI     34
#define PIN_RX5808_CONTROL  PIN_RX5808_CS

#define PIN_I2C_SDA         21
#define PIN_I2C_SCL         22

#define PIN_GPS_RX          16
#define PIN_GPS_TX          17
#define GPS_BAUD_RATE       9600
#define GPS_UPDATE_INTERVAL 1000

#define PIN_LORA_CS         14
#define PIN_LORA_DIO0       33
#define PIN_LORA_DIO1       32
#define PIN_LORA_RESET      12

#define PIN_VCO_DAC_1       25
#define PIN_VCO_DAC_2       26

#define PIN_SD_CS           27

// Legacy optional acoustic mapping; mutually exclusive with LoRa.
#define PIN_I2S_BCLK        14
#define PIN_I2S_WS          12
#define PIN_I2S_DIN         35

// Legacy boot-strap use. Do not copy this assignment into new hardware.
#define PIN_VIBRATION       0

#endif

// ============================================================================
// WIFI CONFIGURATION
// ============================================================================

#define WIFI_AP_SSID        "SkySweep32"
#define WIFI_AP_PASSWORD    "skysweep32"
#define WIFI_AP_CHANNEL     6
#define WIFI_MAX_CLIENTS    4
#define WEB_SERVER_PORT     80

// ============================================================================
// NORMALIZED ENERGY/RSSI ACTIVITY THRESHOLDS
// ============================================================================

#define RSSI_THRESHOLD_LOW          45
#define RSSI_THRESHOLD_MEDIUM       60
#define RSSI_THRESHOLD_HIGH         75
#define RSSI_THRESHOLD_CRITICAL     85

// ============================================================================
// TIMING CONSTANTS
// ============================================================================

#define RF_SCAN_INTERVAL_MS         100   // RF polling interval
#define DISPLAY_UPDATE_INTERVAL_MS  500   // OLED refresh rate
#define WEB_BROADCAST_INTERVAL_MS   500   // WebSocket update rate
#define ACTIVITY_TIMEOUT_MS         5000  // Activity indicator clear timeout
#define BLE_SCAN_INTERVAL_MS        5000  // Remote ID BLE scan
#define REMOTE_ID_CLEANUP_MS        30000 // Remove stale detections

// ============================================================================
// LIMITS
// ============================================================================

#define MAX_DETECTED_DRONES         20    // Max drones in memory
#define MAX_WEBSOCKET_CLIENTS       4     // Max concurrent WS connections
#define MAX_LOG_SIZE_MB             10    // Max single log file size
#define MAX_LOG_FILES               50    // Max log files before rotation
#define RSSI_HISTORY_SIZE           32    // RSSI history buffer

// ============================================================================
// LORA CONFIGURATION
// ============================================================================

#define LORA_FREQUENCY          915.0   // MHz (US ISM band)
#define LORA_BANDWIDTH          125.0   // kHz
#define LORA_SPREADING_FACTOR   7
#define LORA_CODING_RATE        5
#define LORA_SYNC_WORD          0x12
#define LORA_TX_POWER           20      // dBm
#define LORA_TRANSMIT_INTERVAL  30000   // ms between broadcasts

// ============================================================================
// ML CLASSIFIER
// ============================================================================

#define ML_INPUT_SIZE           128
#define ML_OUTPUT_SIZE          5
#define ML_INFERENCE_THRESHOLD  0.6f

// ============================================================================
// DATA LOGGER
// ============================================================================

#define LOG_DIR                 "/logs"

// ============================================================================
// FREERTOS TASK CONFIGURATION
// ============================================================================

#define TASK_STACK_RF_SCAN      4096
#define TASK_STACK_PROTOCOL     3072
#define TASK_STACK_DISPLAY      2048
#define TASK_STACK_WEBSERVER    8192
#define TASK_STACK_REMOTE_ID    4096
#define TASK_STACK_GPS          2048
#define TASK_STACK_DATALOG      3072
#define TASK_STACK_MESH         4096
#define TASK_STACK_ACOUSTIC     4096

// Task priorities (higher = more important)
#define TASK_PRIORITY_RF_SCAN   3
#define TASK_PRIORITY_PROTOCOL  2
#define TASK_PRIORITY_DISPLAY   1
#define TASK_PRIORITY_WEBSERVER 2
#define TASK_PRIORITY_REMOTE_ID 1
#define TASK_PRIORITY_GPS       1
#define TASK_PRIORITY_DATALOG   1
#define TASK_PRIORITY_MESH      1
#define TASK_PRIORITY_ACOUSTIC  2

// ============================================================================
// VERSION
// ============================================================================

#define SKYSWEEP_VERSION        "0.6.1"
#define SKYSWEEP_BUILD_DATE     __DATE__

// ============================================================================
// ACTIVE MODULE COUNT (computed)
// ============================================================================

#define _RF_COUNT_BASE  0
#ifdef MODULE_CC1101
    #define _RF_COUNT_CC  (_RF_COUNT_BASE + 1)
#else
    #define _RF_COUNT_CC  _RF_COUNT_BASE
#endif
#ifdef MODULE_NRF24
    #define _RF_COUNT_NRF (_RF_COUNT_CC + 1)
#else
    #define _RF_COUNT_NRF _RF_COUNT_CC
#endif
#ifdef MODULE_RX5808
    #define RF_MODULE_COUNT (_RF_COUNT_NRF + 1)
#else
    #define RF_MODULE_COUNT _RF_COUNT_NRF
#endif

#endif // CONFIG_H
