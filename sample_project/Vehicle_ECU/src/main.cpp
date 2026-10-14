#include "../include/config.h"
#include "SensorManager.h"
#include "CANInterface.h"
#include "EngineController.h"
#include <stdio.h>

int main() {
    printf("[ECU BOOT] Starting Vehicle ECU Controller %s...\n", ECU_FIRMWARE_VERSION);

    SensorManager sensors;
    if (!sensors.initialize()) {
        printf("[ERROR] SensorManager initialization failed!\n");
        return 1;
    }

    CANInterface can;
    if (!can.initialize()) {
        printf("[ERROR] CANInterface initialization failed!\n");
        return 1;
    }

    EngineController engine(&sensors, &can);
    engine.startEngine();
    engine.updateEngineCycle();

    printf("[ECU OK] System cycle active.\n");
    return 0;
}
