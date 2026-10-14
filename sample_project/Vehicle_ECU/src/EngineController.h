#ifndef ENGINE_CONTROLLER_H
#define ENGINE_CONTROLLER_H

#include "../include/config.h"
#include "SensorManager.h"
#include "CANInterface.h"

class EngineController {
public:
    EngineController(SensorManager* sensors, CANInterface* can);
    ~EngineController();

    bool startEngine();
    void stopEngine();
    void updateEngineCycle();
    
    // [EDUCATIONAL TEST CASE: High Cyclomatic Complexity Function]
    EngineState calculateEngineState(int rpm, int temp, int throttle, bool brakeActive, bool clutchEngaged);

    // [EDUCATIONAL TEST CASE: MISRA C:2012 Rule 9.1 Uninitialized Variable & Dead Code]
    int computeDiagnosticMetric();

private:
    SensorManager* m_sensors;
    CANInterface* m_can;
    EngineState m_currentState;
    int m_targetRPM;
};

#endif // ENGINE_CONTROLLER_H
