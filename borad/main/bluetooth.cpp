#include "bluetooth.h"

BLEServer *pServer;
BLEService *pService;
BLECharacteristic *pCharacteristic;

void initBluetooth(void) {
  #ifdef DEBUG_MODE  
  Serial.print("Инициализация Bluetooth\n");
  #endif
  BLEDevice::init(BLUETOOTH_SERVER_NAME);
  pServer = BLEDevice::createServer();
  if (pServer == NULL) {
    #ifdef DEBUG_MODE  
    Serial.print("createServer fail\n");
    #endif
    return;
  }
  pService = pServer->createService(SERVICE_UUID);
  if (pService == NULL) {
    #ifdef DEBUG_MODE  
    Serial.print("createService fail\n");
    #endif
    return;
  }
  pCharacteristic = pService->createCharacteristic(
    CHARACTERISTIC_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  #ifdef DEBUG_MODE  
  Serial.print("Bluetooth инициализирован\n");
  #endif
}