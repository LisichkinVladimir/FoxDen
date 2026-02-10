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
};

static FBLECharacteristic BLECharacteristics[] = {
  { WIFI_SSID_CHARACTERISTIC_UUID, "WIFI SSID" },
  { WIFI_PASSWORD_CHARACTERISTIC_UUID, "WIFI Password"},
  { SERVER_NAME_UUID, "Web server name"},
  { ESP_MAC_ADDRESS, "ESP32 MAC address"},
  { LAST_LOG, "Last log message"}
};

class FBLECharacteristics {
public:
  static void outOfRange(void) {
    DebugOutputLn("Invalid Characteristic uuid", ERROR_LOG);
    throw std::invalid_argument("Invalid Characteristic uuid");
  }

  static void setValue(const char* uuid, const std::string value) {
    if (uuid == WIFI_SSID_CHARACTERISTIC_UUID)
      WIFI_SSID = value;
    else if (uuid == WIFI_PASSWORD_CHARACTERISTIC_UUID)
      WIFI_PASSWORD = value;
    else if (uuid == SERVER_NAME_UUID)
      SERVER_NAME = value;
  }
  
  static const std::string getValue(const char* uuid) {
    if (uuid == WIFI_SSID_CHARACTERISTIC_UUID)
      return WIFI_SSID;
    else if (uuid == WIFI_PASSWORD_CHARACTERISTIC_UUID)
      return WIFI_PASSWORD;
    else if (uuid == SERVER_NAME_UUID)
      return SERVER_NAME;
    else if (uuid == ESP_MAC_ADDRESS) {
      std::string mac_address = initMacSHA256();
      return mac_address;
    }
    else if (uuid == LAST_LOG) {
      return getLastMessage();
    } else
      outOfRange();
  }

  static const char* getName(const char* uuid) {
    for(int i = 0; i < sizeof(BLECharacteristics)/sizeof(FBLECharacteristic); i++)
      if (BLECharacteristics[i].uuid == uuid)
        return BLECharacteristics[i].description;
    outOfRange();
  }

};

void initBluetooth(void);

#endif