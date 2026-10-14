#ifndef CAN_INTERFACE_H
#define CAN_INTERFACE_H

#include "../include/config.h"

class CANInterface {
public:
    CANInterface();
    ~CANInterface();

    bool initialize();
    bool sendFrame(uint32_t can_id, const uint8_t* payload, uint8_t length);
    bool processIncomingFrame(const CANMessage* message);
    
    // Insecure buffer unpack method for testing
    void unpackPayloadUnsafe(const CANMessage* message, uint8_t* destinationBuffer);

private:
    bool is_initialized;
    uint32_t message_count;
};

#endif // CAN_INTERFACE_H
