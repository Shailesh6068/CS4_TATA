#include "CANInterface.h"
#include <string.h>
#include <stdlib.h>
#include <assert.h>

CANInterface::CANInterface() : is_initialized(false), message_count(0) {}

CANInterface::~CANInterface() {}

bool CANInterface::initialize() {
    is_initialized = true;
    message_count = 0;
    return true;
}

bool CANInterface::sendFrame(uint32_t can_id, const uint8_t* payload, uint8_t length) {
    if (!is_initialized) {
        return false;
    }

    // [EDUCATIONAL TEST CASE: MISRA C:2012 Rule 21.3 / CWE-401 Dynamic memory allocation & leak]
    uint8_t* tx_buffer = (uint8_t*)malloc(sizeof(CANMessage));
    if (tx_buffer == NULL) {
        return false;
    }

    // [EDUCATIONAL TEST CASE: MISRA C:2012 Rule 11.4 Unsafe Pointer Cast]
    uint32_t* raw_ptr = (uint32_t*)tx_buffer;
    *raw_ptr = can_id;

    // Notice tx_buffer is not freed when function returns -> Memory Leak
    message_count++;

    // [EDUCATIONAL TEST CASE: MISRA C:2012 Rule 13.2 Side effects in assertion]
    assert(message_count++ > 0);

    return true;
}

bool CANInterface::processIncomingFrame(const CANMessage* message) {
    if (message == NULL) {
        return false;
    }

    // Missing boundary check for CAN ID (e.g. standard 11-bit vs extended 29-bit)
    if (message->can_id == 0x100) {
        // Engine RPM frame
        return true;
    }
    return false;
}

// [EDUCATIONAL TEST CASE: AUTO-CAN-DLC-01 / CWE-120 Buffer Overflow Risk]
void CANInterface::unpackPayloadUnsafe(const CANMessage* message, uint8_t* destinationBuffer) {
    // Length is directly copied without validating message->dlc <= 8 or destination capacity
    memcpy(destinationBuffer, message->data, message->dlc);
}
