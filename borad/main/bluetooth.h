#ifndef bluetooth_h
#define bluetooth_h

#include <string>
#include <stdexcept>
#include <NimBLEDevice.h> 

#include "main.h"
#include "debug.h"
#include "arduino_secrets.h"
#include "rest_api.h"
#include "web_wifi.h"

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define WIFI_SSID_CHARACTERISTIC_UUID "feb5483e-36e1-4688-b7f5-ea07361b26a8"
#define WIFI_PASSWORD_CHARACTERISTIC_UUID "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"
#define SERVER_NAME_UUID "3c7925e8-badf-4d38-aab6-5e930db08008"
#define ESP_MAC_ADDRESS "a52070f7-802e-486c-9412-6aff410d5d0a"
#define LAST_LOG "ed421260-05f6-11f1-b4ac-0800200c9a66"

#define BLUETOOTH_SERVER_NAME "FOXDEN_ESP32"

struct FBLECharacteristic {
  const char* uuid;
  const char* description;
  const char* preference_name;
};

static FBLECharacteristic BLECharacteristics[] = {
  { WIFI_SSID_CHARACTERISTIC_UUID, "WIFI SSID", "WIFI_SSID"},
  { WIFI_PASSWORD_CHARACTERISTIC_UUID, "WIFI Password", "WIFI_PASSWORD"},
  { SERVER_NAME_UUID, "Web server name", "SERVER_NAME"},
  { ESP_MAC_ADDRESS, "ESP32 MAC address", NULL},
  { LAST_LOG, "Last log message", NULL}
};

class FBLECharacteristics {
public:
  static void outOfRange(void) {
    DebugOutputLn("Invalid Characteristic uuid", ERROR_LOG);
    throw std::invalid_argument("Invalid Characteristic uuid");
  }

  static void setValue(const char* uuid, const std::string value) {
    if (strcmp(uuid, WIFI_SSID_CHARACTERISTIC_UUID) == 0)
      WIFI_SSID = value;
    else if (strcmp(uuid, WIFI_PASSWORD_CHARACTERISTIC_UUID) == 0)
      WIFI_PASSWORD = value;
    else if (strcmp(uuid, SERVER_NAME_UUID) == 0)
      SERVER_NAME = value;
  }
  
  static const std::string getValue(const char* uuid) {
    if (strcmp(uuid, WIFI_SSID_CHARACTERISTIC_UUID) == 0)
      return WIFI_SSID;
    else if (strcmp(uuid, WIFI_PASSWORD_CHARACTERISTIC_UUID) == 0)
      return WIFI_PASSWORD;
    else if (strcmp(uuid, SERVER_NAME_UUID) == 0)
      return SERVER_NAME;
    else if (strcmp(uuid, ESP_MAC_ADDRESS) == 0) {
      return initMacSHA256();
    }
    else if (strcmp(uuid, LAST_LOG) == 0) {
      return getLastMessage();
    } else {
      Serial.printf("Invalid Characteristic getValue\n");
      outOfRange();
    }
  }

  static const char* getPreferenceName(const char* uuid) {
    for(int i = 0; i < sizeof(BLECharacteristics)/sizeof(FBLECharacteristic); i++)
      if (strcmp(BLECharacteristics[i].uuid, uuid) == 0)
        return BLECharacteristics[i].preference_name;
    Serial.printf("Invalid Characteristic getName\n");
    outOfRange();
  }

};

void initBluetooth(void);

#endif