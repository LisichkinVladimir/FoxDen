#ifndef bluetooth_h
#define bluetooth_h

#include <NimBLEDevice.h> 

#include "main.h"
#include "arduino_secrets.h"

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define WIFI_SSID_CHARACTERISTIC_UUID "feb5483e-36e1-4688-b7f5-ea07361b26a8"
#define WIFI_PASSWORD_CHARACTERISTIC_UUID "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"

#define BLUETOOTH_SERVER_NAME "FOXDEN_ESP32"

void initBluetooth(void);

#endif