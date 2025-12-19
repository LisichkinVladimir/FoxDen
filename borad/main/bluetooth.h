#ifndef bluetooth_h
#define bluetooth_h

#include <vector>
#include <string>
#include <stdexcept>
#include <NimBLEDevice.h> 

#include "main.h"
#include "arduino_secrets.h"

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define WIFI_SSID_CHARACTERISTIC_UUID "feb5483e-36e1-4688-b7f5-ea07361b26a8"
#define WIFI_PASSWORD_CHARACTERISTIC_UUID "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"
#define SERVER_NAME_UUID "3c7925e8-badf-4d38-aab6-5e930db08008"

#define BLUETOOTH_SERVER_NAME "FOXDEN_ESP32"

struct FBLECharacteristic {
  std::string uuid;
  std::string description;
};

class FBLECharacteristics : public std::vector<FBLECharacteristic> {
public:
  using std::vector<FBLECharacteristic>::vector;

  static void setValue(const std::string uuid, const std::string value) {
    if (uuid == WIFI_SSID_CHARACTERISTIC_UUID)
      WIFI_SSID = value;
    else if (uuid == WIFI_PASSWORD_CHARACTERISTIC_UUID) 
      WIFI_PASSWORD = value;
    else if (uuid == SERVER_NAME_UUID) 
      SERVER_NAME = value;
  }
  
  static const std::string getValue(const std::string uuid) {
    if (uuid == WIFI_SSID_CHARACTERISTIC_UUID)
      return WIFI_SSID;
    else if (uuid == WIFI_PASSWORD_CHARACTERISTIC_UUID)
      return WIFI_PASSWORD;
    else if (uuid == SERVER_NAME_UUID)
      return SERVER_NAME;
    else
      throw std::invalid_argument("Invalid Characteristic uuid");
  }

  static const char* getName(const std::string uuid) {
    if (uuid == WIFI_SSID_CHARACTERISTIC_UUID)
      return "WIFI_SSID";
    else if (uuid == WIFI_PASSWORD_CHARACTERISTIC_UUID)
      return "WIFI_PASSWORD";
    else if (uuid == SERVER_NAME_UUID)
      return "SERVER_NAME";
    else
      throw std::invalid_argument("Invalid Characteristic uuid");
  }
};

void initBluetooth(void);

#endif