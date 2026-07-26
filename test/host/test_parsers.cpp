// Host unit tests for the CRSF and MAVLink protocol parsers.
//
// These target the buffer-safety and correctness fixes for attacker-controlled
// RF input. Build with AddressSanitizer (see Makefile): any out-of-bounds access
// aborts the process, so the "malicious frame" cases double as overflow guards.
//
// Runs on a desktop compiler via the stub Arduino.h in this directory — no ESP32
// toolchain or PlatformIO registry required.

#include "crsf_parser.h"
#include "mavlink_parser.h"

#include <cstdio>
#include <cstdint>
#include <cstring>

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, msg)                              \
    do {                                              \
        if (cond) {                                   \
            g_pass++;                                 \
        } else {                                      \
            g_fail++;                                 \
            printf("  FAIL: %s\n", msg);              \
        }                                             \
    } while (0)

// Feed a byte stream through a CRSF parser; return true if any frame validated.
static bool feedCRSF(CRSFParser& p, const uint8_t* data, size_t n) {
    bool any = false;
    for (size_t i = 0; i < n; i++) {
        if (p.parseByte(data[i])) any = true;
    }
    return any;
}

static bool feedMAV(MAVLinkParser& p, const uint8_t* data, size_t n) {
    bool any = false;
    for (size_t i = 0; i < n; i++) {
        if (p.parseByte(data[i])) any = true;
    }
    return any;
}

// Reference MAVLink v1 CRC (X.25), matching the parser's calculateCRC for
// message IDs >= 100 (no CRC_EXTRA in the parser's 100-entry table).
static uint16_t mavCrcNoExtra(const uint8_t* data, uint8_t len) {
    uint16_t crc = 0xFFFF;
    for (uint8_t i = 0; i < len; i++) {
        uint8_t tmp = data[i] ^ (uint8_t)(crc & 0xFF);
        tmp ^= (tmp << 4);
        crc = (crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4);
    }
    return crc;
}

static void testCRSF() {
    printf("CRSF parser:\n");

    // 1) Hostile length byte (0xFF) must be rejected, not overflow the 60-byte
    //    payload buffer. Under ASAN the pre-fix code aborts here.
    {
        CRSFParser p;
        uint8_t mal[512];
        mal[0] = CRSF_SYNC_BYTE;
        mal[1] = 0xFF;                 // length -> pre-fix wrapped expectedLength to 1
        for (int i = 2; i < 512; i++) mal[i] = 0xAB;
        bool v = feedCRSF(p, mal, sizeof(mal));
        CHECK(!v, "0xFF length frame must not validate (no overflow)");
    }

    // 2) Length byte 0xFE (the other wrap value) must also be rejected.
    {
        CRSFParser p;
        uint8_t mal[300];
        mal[0] = CRSF_SYNC_BYTE;
        mal[1] = 0xFE;
        for (int i = 2; i < 300; i++) mal[i] = 0x7F;
        bool v = feedCRSF(p, mal, sizeof(mal));
        CHECK(!v, "0xFE length frame must not validate (no overflow)");
    }

    // 3) Over-max payload (length 63 -> payload 61 > 60) must be rejected.
    {
        CRSFParser p;
        uint8_t f[80];
        f[0] = CRSF_SYNC_BYTE;
        f[1] = 63;
        for (int i = 2; i < 80; i++) f[i] = 0;
        bool v = feedCRSF(p, f, sizeof(f));
        CHECK(!v, "payload length above 60 rejected");
    }

    // 4) Valid round-trip: build a LINK_STATS frame, parse it back. This exercises
    //    the buildLinkStats length fix (12) and the CRC-offset fix together — a
    //    correctly built frame only validates if the CRC is read at the right byte.
    {
        CRSFLinkStats stats;
        memset(&stats, 0, sizeof(stats));
        stats.uplink_RSSI_1 = 42;
        stats.downlink_SNR = -7;

        CRSFParser builder;
        uint8_t buf[64];
        uint8_t len = 0;
        builder.buildLinkStats(buf, &len, &stats);

        CHECK(len == 14, "buildLinkStats total frame length == 14");
        CHECK(buf[1] == 12, "buildLinkStats frame-length byte == 12");

        CRSFParser p;
        bool v = feedCRSF(p, buf, len);
        CHECK(v, "valid built frame parses & validates (CRC offset fix)");

        CRSFPacket pkt = p.getPacket();
        CHECK(pkt.valid, "parsed packet flagged valid");
        CHECK(pkt.type == CRSF_FRAMETYPE_LINK_STATS, "parsed type == LINK_STATS");

        CRSFLinkStats out = p.parseLinkStats(&pkt);
        CHECK(out.uplink_RSSI_1 == 42, "payload round-trips (uplink_RSSI_1 == 42)");
    }
}

static void testMAVLink() {
    printf("MAVLink parser:\n");

    // 1) Valid round-trip: build a HEARTBEAT frame and parse it back.
    {
        MAVLinkParser builder;
        uint8_t buf[64];
        uint8_t len = 0;
        builder.buildHeartbeat(buf, &len, 1, 1);

        MAVLinkParser p;
        bool v = feedMAV(p, buf, len);
        CHECK(v, "valid built heartbeat parses & validates");

        MAVLinkPacket pkt = p.getPacket();
        CHECK(pkt.valid, "heartbeat flagged valid");
        CHECK(pkt.msgid == MAVLINK_MSG_ID_HEARTBEAT, "msgid == HEARTBEAT");
    }

    // 2) Large payload (len 250): pre-fix, expectedLength was uint8_t and wrapped
    //    (8+250 = 258 -> 2), completing the frame after ~6 bytes on garbage. With
    //    the uint16_t fix the parser buffers the whole 258-byte frame and validates
    //    the real CRC. Build a valid frame with msgid 200 (no CRC_EXTRA).
    {
        const uint8_t payloadLen = 250;
        const uint8_t msgid = 200;
        uint8_t frame[8 + 250];
        frame[0] = MAVLINK_STX_V1;
        frame[1] = payloadLen;
        frame[2] = 7;    // seq
        frame[3] = 42;   // sysid
        frame[4] = 1;    // compid
        frame[5] = msgid;
        for (uint8_t i = 0; i < payloadLen; i++) frame[6 + i] = (uint8_t)(i * 3 + 1);

        // CRC covers [len, seq, sysid, compid, msgid, payload...] == 5 + payloadLen bytes.
        uint16_t crc = mavCrcNoExtra(&frame[1], (uint8_t)(5 + payloadLen));
        frame[6 + payloadLen] = crc & 0xFF;
        frame[7 + payloadLen] = (crc >> 8) & 0xFF;

        MAVLinkParser p;
        bool v = feedMAV(p, frame, sizeof(frame));
        CHECK(v, "len=250 frame validates (expectedLength uint16 fix)");

        MAVLinkPacket pkt = p.getPacket();
        CHECK(pkt.len == 250, "parsed len == 250");
        CHECK(pkt.msgid == 200, "parsed msgid == 200");
    }

    // 3) Truncated large frame must not be accepted or over-read.
    {
        MAVLinkParser p;
        uint8_t frag[12];
        frag[0] = MAVLINK_STX_V1;
        frag[1] = 255;
        for (int i = 2; i < 12; i++) frag[i] = 0x11;
        bool v = feedMAV(p, frag, sizeof(frag));
        CHECK(!v, "12-byte fragment of a 263-byte frame is not accepted");
    }

    // 4) parseHeartbeat must zero-initialize its result on a short payload
    //    (previously returned an uninitialized struct).
    {
        MAVLinkPacket pkt;
        memset(&pkt, 0xAA, sizeof(pkt));  // fill with junk
        pkt.len = 5;                      // below the 9 bytes heartbeat needs
        pkt.msgid = MAVLINK_MSG_ID_HEARTBEAT;

        MAVLinkParser p;
        MAVLinkHeartbeat hb = p.parseHeartbeat(&pkt);
        CHECK(hb.type == 0 && hb.autopilot == 0 && hb.base_mode == 0 &&
                  hb.custom_mode == 0 && hb.system_status == 0 && hb.mavlink_version == 0,
              "parseHeartbeat zero-inits on short payload");
    }
}

int main() {
    printf("== SkySweep32 host parser tests ==\n");
    testCRSF();
    testMAVLink();
    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
