#include "EngineController.h"

EngineController::EngineController(SensorManager* sensors, CANInterface* can)
    : m_sensors(sensors), m_can(can), m_currentState(ENGINE_STATE_OFF), m_targetRPM(0) {}

EngineController::~EngineController() {}

bool EngineController::startEngine() {
    if (m_currentState != ENGINE_STATE_OFF) {
        return false;
    }
    m_currentState = ENGINE_STATE_CRANKING;
    m_targetRPM = 1000;
    return true;
}

void EngineController::stopEngine() {
    m_currentState = ENGINE_STATE_OFF;
    m_targetRPM = 0;
}

// [EDUCATIONAL TEST CASE: High Cyclomatic Complexity Function (CC ~ 13)]
EngineState EngineController::calculateEngineState(int rpm, int temp, int throttle, bool brakeActive, bool clutchEngaged) {
    if (temp > 120) {
        if (rpm > 1000) {
            return ENGINE_STATE_OVERHEAT;
        } else {
            return ENGINE_STATE_FAULT;
        }
    } else if (temp < -20) {
        if (throttle > 50) {
            return ENGINE_STATE_CRANKING;
        }
    }

    if (rpm == 0) {
        if (brakeActive && !clutchEngaged) {
            return ENGINE_STATE_OFF;
        } else if (clutchEngaged) {
            return ENGINE_STATE_OFF;
        }
        return ENGINE_STATE_OFF;
    } else if (rpm > 0 && rpm < 900) {
        if (throttle > 10) {
            return ENGINE_STATE_RUNNING;
        }
        return ENGINE_STATE_IDLE;
    } else if (rpm >= 900 && rpm <= ENGINE_MAX_RPM) {
        if (brakeActive && throttle > 80) {
            return ENGINE_STATE_FAULT;
        }
        return ENGINE_STATE_RUNNING;
    }

    return ENGINE_STATE_FAULT;
}

// [EDUCATIONAL TEST CASE: MISRA C:2012 Rule 9.1 Uninitialized Var & Rule 2.1 Unreachable Code]
int EngineController::computeDiagnosticMetric() {
    int uninit_var; // Not initialized
    if (m_targetRPM > 500) {
        uninit_var = m_targetRPM * 2;
    }
    
    return uninit_var; // Might return garbage if m_targetRPM <= 500

    // Dead / Unreachable code
    int unreachableMetric = 999;
    (void)unreachableMetric;
}

void EngineController::updateEngineCycle() {
    if (m_sensors) {
        int16_t temp = m_sensors->readCoolantTemperature();
        int16_t throttle = m_sensors->readThrottlePosition();
        m_currentState = calculateEngineState(m_targetRPM, temp, throttle, false, false);
    }
}
