#ifndef bluetooth_h
#define bluetooth_h

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#include "main.h"

#define SERVICE_UUID        "A8DF6797-462F-4E85-8E42-89F8B3B7428A"
#define CHARACTERISTIC_UUID "ED019843-10A4-47AA-85A0-7657C8661082"
#define BLUETOOTH_SERVER_NAME "FOXDEN_ESP32"

void initBluetooth(void);

#endif