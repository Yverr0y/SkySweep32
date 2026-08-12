#include "crsf_parser.h"

CRSFParser::CRSFParser() {
    rxIndex = 0;
    memset(rxBuffer, 0, sizeof(rxBuffer));
    memset(&currentPacket, 0, sizeof(CRSFPacket));
}

static uint8_t crsfCrcAccumulate(uint8_t crc, uint8_t data) {
    crc ^= data;
    for (uint8_t bit = 0; bit < 8; bit++) {
        crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0xD5)
                           : static_cast<uint8_t>(crc << 1);
    }
    return crc;
}

bool CRSFParser::validateCRC(CRSFPacket* packet) {
    uint8_t crc = crsfCrcAccumulate(0, packet->type);
    const uint8_t payloadLength = packet->length - 2;
    for (uint8_t i = 0; i < payloadLength; i++) {
        crc = crsfCrcAccumulate(crc, packet->payload[i]);
    }
    return crc == packet->crc;
}

bool CRSFParser::parseByte(uint8_t byte) {
    if (rxIndex == 0 && byte == CRSF_SYNC_BYTE) {
        rxBuffer[rxIndex++] = byte;
        return false;
    }
    
    if (rxIndex > 0 && rxIndex < CRSF_MAX_PACKET_SIZE) {
        rxBuffer[rxIndex++] = byte;
        
        if (rxIndex >= 3) {
            // rxBuffer[1] (frame length) is attacker-controlled over the air.
            // Reject out-of-range values before they overflow the fixed 60-byte
            // payload buffer, and widen expectedLength so 0xFE/0xFF cannot wrap to 0/1.
            if (rxBuffer[1] < 2 || (rxBuffer[1] - 2) > CRSF_PAYLOAD_SIZE_MAX) {
                rxIndex = 0;
                return false;
            }
            uint16_t expectedLength = rxBuffer[1] + 2; // Address + Length + Payload + CRC

            if (rxIndex >= expectedLength) {
                currentPacket.address = rxBuffer[0];
                currentPacket.length = rxBuffer[1];
                currentPacket.type = rxBuffer[2];

                uint8_t payloadLength = currentPacket.length - 2;
                memcpy(currentPacket.payload, &rxBuffer[3], payloadLength);
                // CRC is the last byte of the frame, at index (1 + length), not (2 + length).
                currentPacket.crc = rxBuffer[1 + currentPacket.length];
                
                currentPacket.valid = validateCRC(&currentPacket);
                rxIndex = 0;
                return currentPacket.valid;
            }
        }
    }
    
    if (rxIndex >= CRSF_MAX_PACKET_SIZE) {
        rxIndex = 0;
    }
    
    return false;
}

bool CRSFParser::parseBuffer(uint8_t* data, uint16_t length) {
    for (uint16_t i = 0; i < length; i++) {
        if (parseByte(data[i])) {
            return true;
        }
    }
    return false;
}


bool CRSFParser::isLinkStats(CRSFPacket* packet) {
    return packet->type == CRSF_FRAMETYPE_LINK_STATS;
}

bool CRSFParser::isGPS(CRSFPacket* packet) {
    return packet->type == CRSF_FRAMETYPE_GPS;
}

bool CRSFParser::isRCChannels(CRSFPacket* packet) {
    return packet->type == CRSF_FRAMETYPE_RC_CHANNELS;
}

CRSFLinkStats CRSFParser::parseLinkStats(CRSFPacket* packet) {
    CRSFLinkStats stats;
    memset(&stats, 0, sizeof(CRSFLinkStats));
    
    if (packet->length >= 11) {
        stats.uplink_RSSI_1 = packet->payload[0];
        stats.uplink_RSSI_2 = packet->payload[1];
        stats.uplink_Link_quality = packet->payload[2];
        stats.uplink_SNR = packet->payload[3];
        stats.active_antenna = packet->payload[4];
        stats.rf_Mode = packet->payload[5];
        stats.uplink_TX_Power = packet->payload[6];
        stats.downlink_RSSI = packet->payload[7];
        stats.downlink_Link_quality = packet->payload[8];
        stats.downlink_SNR = packet->payload[9];
    }
    
    return stats;
}

CRSFGPS CRSFParser::parseGPS(CRSFPacket* packet) {
    CRSFGPS gps;
    memset(&gps, 0, sizeof(CRSFGPS));
    
    if (packet->length >= 17) {
        memcpy(&gps.latitude, &packet->payload[0], 4);
        memcpy(&gps.longitude, &packet->payload[4], 4);
        memcpy(&gps.groundspeed, &packet->payload[8], 2);
        memcpy(&gps.heading, &packet->payload[10], 2);
        memcpy(&gps.altitude, &packet->payload[12], 2);
        gps.satellites = packet->payload[14];
    }
    
    return gps;
}

CRSFRCChannels CRSFParser::parseRCChannels(CRSFPacket* packet) {
    CRSFRCChannels rc;
    memset(&rc, 0, sizeof(CRSFRCChannels));
    
    if (packet->length >= 24) {
        uint8_t* payload = packet->payload;
        
        for (uint8_t i = 0; i < 16; i++) {
            uint16_t bitOffset = i * 11;
            uint8_t byteOffset = bitOffset / 8;
            uint8_t bitInByte = bitOffset % 8;
            
            uint16_t value = payload[byteOffset] >> bitInByte;
            if (bitInByte + 11 > 8) {
                value |= payload[byteOffset + 1] << (8 - bitInByte);
            }
            if (bitInByte + 11 > 16) {
                value |= payload[byteOffset + 2] << (16 - bitInByte);
            }
            
            rc.channels[i] = value & 0x07FF;
        }
    }
    
    return rc;
}

const char* CRSFParser::getFrameTypeName(uint8_t type) {
    switch(type) {
        case CRSF_FRAMETYPE_GPS: return "GPS";
        case CRSF_FRAMETYPE_BATTERY: return "BATTERY";
        case CRSF_FRAMETYPE_LINK_STATS: return "LINK_STATS";
        case CRSF_FRAMETYPE_RC_CHANNELS: return "RC_CHANNELS";
        case CRSF_FRAMETYPE_ATTITUDE: return "ATTITUDE";
        case CRSF_FRAMETYPE_FLIGHT_MODE: return "FLIGHT_MODE";
        default: return "UNKNOWN";
    }
}

int8_t CRSFParser::getRSSIFromLinkStats(CRSFLinkStats* stats) {
    // Convert CRSF RSSI (0-255) to dBm
    // CRSF RSSI formula: dBm = -(RSSI value)
    return -(int8_t)stats->uplink_RSSI_1;
}
