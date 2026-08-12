#include "mavlink_parser.h"

// CRC_EXTRA values for the MAVLink v1 common-dialect messages this parser
// explicitly recognizes. Unknown IDs are rejected; a zero placeholder would
// otherwise accept non-MAVLink frames whose checksum omits CRC_EXTRA.
static int mavlinkCrcExtra(uint8_t messageId) {
    switch (messageId) {
        case MAVLINK_MSG_ID_HEARTBEAT: return 50;
        case MAVLINK_MSG_ID_SYS_STATUS: return 124;
        case MAVLINK_MSG_ID_SYSTEM_TIME: return 137;
        case MAVLINK_MSG_ID_GPS_RAW_INT: return 24;
        case MAVLINK_MSG_ID_ATTITUDE: return 39;
        case MAVLINK_MSG_ID_GLOBAL_POSITION_INT: return 104;
        case MAVLINK_MSG_ID_RC_CHANNELS_RAW: return 244;
        case MAVLINK_MSG_ID_COMMAND_LONG: return 152;
        case MAVLINK_MSG_ID_COMMAND_ACK: return 143;
        default: return -1;
    }
}

MAVLinkParser::MAVLinkParser() {
    rxIndex = 0;
    memset(rxBuffer, 0, sizeof(rxBuffer));
    memset(&currentPacket, 0, sizeof(MAVLinkPacket));
}

static uint16_t mavlinkCrcAccumulate(uint16_t crc, uint8_t data) {
    uint8_t tmp = data ^ static_cast<uint8_t>(crc & 0xFF);
    tmp ^= static_cast<uint8_t>(tmp << 4);
    return static_cast<uint16_t>(
        (crc >> 8) ^ (static_cast<uint16_t>(tmp) << 8) ^
        (static_cast<uint16_t>(tmp) << 3) ^ (tmp >> 4));
}

bool MAVLinkParser::validateChecksum(MAVLinkPacket* packet) {
    const int crcExtra = mavlinkCrcExtra(packet->msgid);
    if (crcExtra < 0) {
        return false;
    }
    uint16_t crc = 0xFFFF;
    crc = mavlinkCrcAccumulate(crc, packet->len);
    crc = mavlinkCrcAccumulate(crc, packet->seq);
    crc = mavlinkCrcAccumulate(crc, packet->sysid);
    crc = mavlinkCrcAccumulate(crc, packet->compid);
    crc = mavlinkCrcAccumulate(crc, packet->msgid);
    for (uint16_t i = 0; i < packet->len; i++) {
        crc = mavlinkCrcAccumulate(crc, packet->payload[i]);
    }
    crc = mavlinkCrcAccumulate(crc, static_cast<uint8_t>(crcExtra));
    return crc == packet->checksum;
}

bool MAVLinkParser::parseByte(uint8_t byte) {
    if (rxIndex == 0 && byte == MAVLINK_STX_V1) {
        rxBuffer[rxIndex++] = byte;
        return false;
    }
    
    if (rxIndex > 0 && rxIndex < 280) {
        rxBuffer[rxIndex++] = byte;
        
        if (rxIndex >= 6) {
            uint16_t expectedLength = 8 + rxBuffer[1]; // Header + payload + CRC (widened so len 248-255 doesn't wrap)
            
            if (rxIndex >= expectedLength) {
                currentPacket.magic = rxBuffer[0];
                currentPacket.len = rxBuffer[1];
                currentPacket.seq = rxBuffer[2];
                currentPacket.sysid = rxBuffer[3];
                currentPacket.compid = rxBuffer[4];
                currentPacket.msgid = rxBuffer[5];
                memcpy(currentPacket.payload, &rxBuffer[6], currentPacket.len);
                currentPacket.checksum = rxBuffer[6 + currentPacket.len] | 
                                        (rxBuffer[7 + currentPacket.len] << 8);
                
                currentPacket.valid = validateChecksum(&currentPacket);
                rxIndex = 0;
                return currentPacket.valid;
            }
        }
    }
    
    return false;
}

bool MAVLinkParser::parseBuffer(uint8_t* data, uint16_t length) {
    for (uint16_t i = 0; i < length; i++) {
        if (parseByte(data[i])) {
            return true;
        }
    }
    return false;
}


bool MAVLinkParser::isHeartbeat(MAVLinkPacket* packet) {
    return packet->msgid == MAVLINK_MSG_ID_HEARTBEAT;
}

bool MAVLinkParser::isGPSData(MAVLinkPacket* packet) {
    return packet->msgid == MAVLINK_MSG_ID_GPS_RAW_INT;
}

bool MAVLinkParser::isRCChannels(MAVLinkPacket* packet) {
    return packet->msgid == MAVLINK_MSG_ID_RC_CHANNELS_RAW;
}

MAVLinkHeartbeat MAVLinkParser::parseHeartbeat(MAVLinkPacket* packet) {
    MAVLinkHeartbeat hb;
    memset(&hb, 0, sizeof(hb));
    if (packet->len >= 9) {
        hb.type = packet->payload[0];
        hb.autopilot = packet->payload[1];
        hb.base_mode = packet->payload[2];
        memcpy(&hb.custom_mode, &packet->payload[3], 4);
        hb.system_status = packet->payload[7];
        hb.mavlink_version = packet->payload[8];
    }
    return hb;
}

MAVLinkGPS MAVLinkParser::parseGPS(MAVLinkPacket* packet) {
    MAVLinkGPS gps;
    memset(&gps, 0, sizeof(MAVLinkGPS));
    if (packet->len >= 30) {
        memcpy(&gps.time_usec, &packet->payload[0], 8);
        memcpy(&gps.lat, &packet->payload[8], 4);
        memcpy(&gps.lon, &packet->payload[12], 4);
        memcpy(&gps.alt, &packet->payload[16], 4);
        memcpy(&gps.eph, &packet->payload[20], 2);
        memcpy(&gps.epv, &packet->payload[22], 2);
        memcpy(&gps.vel, &packet->payload[24], 2);
        memcpy(&gps.cog, &packet->payload[26], 2);
        gps.fix_type = packet->payload[28];
        gps.satellites_visible = packet->payload[29];
    }
    return gps;
}

const char* MAVLinkParser::getMessageName(uint8_t msgid) {
    switch(msgid) {
        case MAVLINK_MSG_ID_HEARTBEAT: return "HEARTBEAT";
        case MAVLINK_MSG_ID_SYS_STATUS: return "SYS_STATUS";
        case MAVLINK_MSG_ID_GPS_RAW_INT: return "GPS_RAW_INT";
        case MAVLINK_MSG_ID_ATTITUDE: return "ATTITUDE";
        case MAVLINK_MSG_ID_GLOBAL_POSITION_INT: return "GLOBAL_POSITION_INT";
        case MAVLINK_MSG_ID_RC_CHANNELS_RAW: return "RC_CHANNELS_RAW";
        case MAVLINK_MSG_ID_COMMAND_LONG: return "COMMAND_LONG";
        case MAVLINK_MSG_ID_COMMAND_ACK: return "COMMAND_ACK";
        default: return "UNKNOWN";
    }
}

const char* MAVLinkParser::getVehicleType(uint8_t type) {
    switch(type) {
        case 0: return "Generic";
        case 1: return "Fixed Wing";
        case 2: return "Quadrotor";
        case 3: return "Coaxial Heli";
        case 4: return "Helicopter";
        case 5: return "Antenna Tracker";
        case 6: return "GCS";
        case 13: return "Hexarotor";
        case 14: return "Octorotor";
        default: return "Unknown";
    }
}
