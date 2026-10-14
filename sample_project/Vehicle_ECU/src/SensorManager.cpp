#include "SensorManager.h"
#include <string.h>

SensorManager::SensorManager() : m_isReady(false), m_unverifiedSensor(nullptr) {
    memset(m_sensorTag, 0, sizeof(m_sensorTag));
}

SensorManager::~SensorManager() {}

bool SensorManager::initialize() {
    m_isReady = true;
    return true;
}

int16_t SensorManager::readCoolantTemperature() {
    // Normal nominal engine coolant temp: 85 deg C
    return 85;
}

int16_t SensorManager::readThrottlePosition() {
    return 25; // 25% open
}

// [EDUCATIONAL TEST CASE: MISRA C:2012 Rule 21.6 / CWE-120 Unsafe strcpy]
void SensorManager::setSensorTag(const char* tag) {
    if (tag != nullptr) {
        // Unbounded string copy into 16-byte fixed buffer
        strcpy(m_sensorTag, tag);
    }
}

// [EDUCATIONAL TEST CASE: CWE-476 Null Pointer Dereference]
int16_t SensorManager::readUnverifiedSensor() {
    // Pointer is accessed directly without checking m_unverifiedSensor != nullptr
    return m_unverifiedSensor->last_reading;
}
