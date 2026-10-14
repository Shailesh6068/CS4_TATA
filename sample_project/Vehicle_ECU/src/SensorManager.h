#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <stdint.h>

struct SensorDevice {
    uint16_t sensor_id;
    int16_t last_reading;
};

class SensorManager {
public:
    SensorManager();
    ~SensorManager();

    bool initialize();
    int16_t readCoolantTemperature();
    int16_t readThrottlePosition();
    void setSensorTag(const char* tag);

    // [EDUCATIONAL TEST CASE: CWE-476 Potential Null Pointer Dereference]
    int16_t readUnverifiedSensor();

private:
    bool m_isReady;
    SensorDevice* m_unverifiedSensor;
    char m_sensorTag[16];
};

#endif // SENSOR_MANAGER_H
