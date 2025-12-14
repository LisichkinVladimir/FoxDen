#ifndef bluetooth_h
#define bluetooth_h

#include <NimBLEDevice.h> 

#include "main.h"

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

#define BLUETOOTH_SERVER_NAME "FOXDEN_ESP32"

void initBluetooth(void);
void checkBluetoothConnected(void);

#endif