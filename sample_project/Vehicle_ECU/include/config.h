#ifndef ECU_CONFIG_H
#define ECU_CONFIG_H

#include <stdint.h>

#define ECU_FIRMWARE_VERSION "v2.4.1-RC3"
#define MAX_CAN_PAYLOAD_SIZE 8
#define ENGINE_MAX_RPM 8000
#define THROTTLE_MAX_PERCENT 100

// [EDUCATIONAL TEST CASE: CWE-798 Hardcoded Diagnostic Secret Key]
#define DIAGNOSTIC_SEED_KEY "ECU_SEC_AUTH_KEY_2026_AUTOMOTIVE"

typedef struct {
    uint32_t can_id;
    uint8_t dlc;
    uint8_t data[MAX_CAN_PAYLOAD_SIZE];
} CANMessage;

typedef enum {
    ENGINE_STATE_OFF = 0,
    ENGINE_STATE_CRANKING,
    ENGINE_STATE_IDLE,
    ENGINE_STATE_RUNNING,
    ENGINE_STATE_OVERHEAT,
    ENGINE_STATE_FAULT
} EngineState;

#endif // ECU_CONFIG_H
