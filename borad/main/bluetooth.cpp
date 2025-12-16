#include "bluetooth.h"

static NimBLEServer* pServer;
bool BluetoothConnected = false;

/**  None of these are required as they will be handled by the library with defaults. **
 **                       Remove as you see fit for your needs                        */
class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo) override {
    #ifdef DEBUG_MODE  
    Serial.printf("Client address: %s\n", connInfo.getAddress().toString().c_str());
    #endif
    /**
      *  We can use the connection handle here to ask for different connection parameters.
      *  Args: connection handle, min connection interval, max connection interval
      *  latency, supervision timeout.
      *  Units; Min/Max Intervals: 1.25 millisecond increments.
      *  Latency: number of intervals allowed to skip.
      *  Timeout: 10 millisecond increments.
      */
    pServer->updateConnParams(connInfo.getConnHandle(), 24, 48, 0, 180);
  }

  void onDisconnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo, int reason) override {
    #ifdef DEBUG_MODE
    Serial.printf("Client disconnected - start advertising\n");
    #endif
    NimBLEDevice::startAdvertising();
  }

  void onMTUChange(uint16_t MTU, NimBLEConnInfo& connInfo) override {
    #ifdef DEBUG_MODE
    Serial.printf("MTU updated: %u for connection ID: %u\n", MTU, connInfo.getConnHandle());
    #endif
  }

  /********************* Security handled here *********************/
  uint32_t onPassKeyDisplay() override {
    #ifdef DEBUG_MODE
    Serial.printf("Server Passkey Display\n");
    #endif
    /**
      * This should return a random 6 digit number for security
      *  or make your own static passkey as done here.
      */
    return 123456;
  }

  void onConfirmPassKey(NimBLEConnInfo& connInfo, uint32_t pass_key) override {
    #ifdef DEBUG_MODE
    Serial.printf("The passkey YES/NO number: %" PRIu32 "\n", pass_key);
    #endif
    /** Inject false if passkeys don't match. */
    NimBLEDevice::injectConfirmPasskey(connInfo, true);
  }

  void onAuthenticationComplete(NimBLEConnInfo& connInfo) override {
    /** Check that encryption was successful, if not we disconnect the client */
    if (!connInfo.isEncrypted()) {
        NimBLEDevice::getServer()->disconnect(connInfo.getConnHandle());
        #ifdef DEBUG_MODE
        Serial.printf("Encrypt connection failed - disconnecting client\n");
        #endif
        return;
    }

    #ifdef DEBUG_MODE
    Serial.printf("Secured connection to: %s\n", connInfo.getAddress().toString().c_str());
    #endif
  }
} serverCallbacks;

/** Handler class for characteristic actions */
class CharacteristicCallbacks : public NimBLECharacteristicCallbacks {
    void onRead(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo) override {
        Serial.printf("%s : onRead(), value: %s\n",
                      pCharacteristic->getUUID().toString().c_str(),
                      pCharacteristic->getValue().c_str());
    }

    void onWrite(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo) override {
        Serial.printf("%s : onWrite(), value: %s\n",
                      pCharacteristic->getUUID().toString().c_str(),
                      pCharacteristic->getValue().c_str());
        FBLECharacteristics::setValue(pCharacteristic->getUUID().toString(), pCharacteristic->getValue());
    }

    /**
     *  The value returned in code is the NimBLE host return code.
     */
    void onStatus(NimBLECharacteristic* pCharacteristic, int code) override {
        Serial.printf("Notification/Indication return code: %d, %s\n", code, NimBLEUtils::returnCodeToString(code));
    }

    /** Peer subscribed to notifications/indications */
    void onSubscribe(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo, uint16_t subValue) override {
        std::string str  = "Client ID: ";
        str             += connInfo.getConnHandle();
        str             += " Address: ";
        str             += connInfo.getAddress().toString();
        if (subValue == 0) {
            str += " Unsubscribed to ";
        } else if (subValue == 1) {
            str += " Subscribed to notifications for ";
        } else if (subValue == 2) {
            str += " Subscribed to indications for ";
        } else if (subValue == 3) {
            str += " Subscribed to notifications and indications for ";
        }
        str += std::string(pCharacteristic->getUUID());

        Serial.printf("%s\n", str.c_str());
    }
} chrCallbacks;

/** Handler class for descriptor actions */
class DescriptorCallbacks : public NimBLEDescriptorCallbacks {
    void onWrite(NimBLEDescriptor* pDescriptor, NimBLEConnInfo& connInfo) override {
        std::string dscVal = pDescriptor->getValue();
        Serial.printf("Descriptor written value: %s\n", dscVal.c_str());
    }

    void onRead(NimBLEDescriptor* pDescriptor, NimBLEConnInfo& connInfo) override {
        Serial.printf("%s Descriptor read %s\n", pDescriptor->getUUID().toString().c_str(), pDescriptor->getValue().c_str());
    }
} dscCallbacks; 

void initBluetooth(void) {
    Serial.printf("Запуск Bluetooth Server\n");

    NimBLEDevice::init(BLUETOOTH_SERVER_NAME);

    /**
     * Set the IO capabilities of the device, each option will trigger a different pairing method.
     *  BLE_HS_IO_DISPLAY_ONLY    - Passkey pairing
     *  BLE_HS_IO_DISPLAY_YESNO   - Numeric comparison pairing
     *  BLE_HS_IO_NO_INPUT_OUTPUT - DEFAULT setting - just works pairing
     */
    // NimBLEDevice::setSecurityIOCap(BLE_HS_IO_DISPLAY_ONLY); // use passkey
    // NimBLEDevice::setSecurityIOCap(BLE_HS_IO_DISPLAY_YESNO); //use numeric comparison

    /**
     *  2 different ways to set security - both calls achieve the same result.
     *  no bonding, no man in the middle protection, BLE secure connections.
     *
     *  These are the default values, only shown here for demonstration.
     */
    // NimBLEDevice::setSecurityAuth(false, false, true);
    // NimBLEDevice::setSecurityAuth(BLE_SM_PAIR_AUTHREQ_BOND | BLE_SM_PAIR_AUTHREQ_MITM | BLE_SM_PAIR_AUTHREQ_SC);

    pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(&serverCallbacks);

    NimBLEService* pService = pServer->createService(SERVICE_UUID);

    FBLECharacteristics vCharacteristics = {
        { WIFI_SSID_CHARACTERISTIC_UUID, "WIFI SSID" },
        { WIFI_PASSWORD_CHARACTERISTIC_UUID, "WIFI Password"},
        { SERVER_NAME_UUID, "Web server name"}
    };

    for (byte i = 0; i < vCharacteristics.size(); ++i) {
      FBLECharacteristic& characteristic = vCharacteristics[i];
      NimBLECharacteristic* pCharacteristic = pService->createCharacteristic(characteristic.uuid, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE);
      pCharacteristic->setValue(FBLECharacteristics::getValue(characteristic.uuid));
      pCharacteristic->setCallbacks(&chrCallbacks);
      NimBLEDescriptor* pDescription = pCharacteristic->createDescriptor(BLEUUID((uint16_t)0x2901));
      pDescription->setValue(characteristic.description.c_str());
      //pDescription->setCallbacks(&chrCallbacks);
    }

    /** Start the services when finished creating all Characteristics and Descriptors */
    pService->start();

    /** Create an advertising instance and add the services to the advertised data */
    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->setName("FoxDen Bluetooth");
    pAdvertising->addServiceUUID(pService->getUUID());
    /**
     *  If your device is battery powered you may consider setting scan response
     *  to false as it will extend battery life at the expense of less data sent.
     */
    pAdvertising->enableScanResponse(true);
    pAdvertising->start();

    Serial.printf("Advertising Started\n"); 
}
