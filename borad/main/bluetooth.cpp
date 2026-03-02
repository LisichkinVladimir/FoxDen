#include "bluetooth.h"
#include "preference.h"

static NimBLEServer* pServer;
bool BluetoothConnected = false;

/**  None of these are required as they will be handled by the library with defaults. **
 **                       Remove as you see fit for your needs                        */
class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo) override {
    #ifdef DEBUG_MODE
    DebugOutputLn("Client address: " + connInfo.getAddress().toString(), NOT_LOG);
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
    DebugOutputLn("Client disconnected - start advertising", NOT_LOG);
    #endif
    NimBLEDevice::startAdvertising();
  }

  void onMTUChange(uint16_t MTU, NimBLEConnInfo& connInfo) override {
    #ifdef DEBUG_MODE
    std::string message = "MTU updated: " + std::to_string(MTU) + " for connection ID: " + std::to_string(connInfo.getConnHandle());
    DebugOutputLn(message, NOT_LOG);
    #endif
  }

  /********************* Security handled here *********************/
  uint32_t onPassKeyDisplay() override {
    #ifdef DEBUG_MODE
    DebugOutputLn("Server Passkey Display");
    #endif
    /**
      * This should return a random 6 digit number for security
      *  or make your own static passkey as done here.
      */
    return 123456;
  }

  void onConfirmPassKey(NimBLEConnInfo& connInfo, uint32_t pass_key) override {
    #ifdef DEBUG_MODE
    DebugOutputf("The passkey YES/NO number: %" PRIu32 "\n", pass_key);
    #endif
    /** Inject false if passkeys don't match. */
    NimBLEDevice::injectConfirmPasskey(connInfo, true);
  }

  void onAuthenticationComplete(NimBLEConnInfo& connInfo) override {
    /** Check that encryption was successful, if not we disconnect the client */
    if (!connInfo.isEncrypted()) {
        NimBLEDevice::getServer()->disconnect(connInfo.getConnHandle());
        #ifdef DEBUG_MODE
        DebugOutputE("Encrypt connection failed - disconnecting client\n");
        #endif
        return;
    }

    #ifdef DEBUG_MODE
    DebugOutputf("Secured connection to: %s\n", connInfo.getAddress().toString().c_str());
    #endif
  }
} serverCallbacks;

/** Handler class for characteristic actions */
class CharacteristicCallbacks : public NimBLECharacteristicCallbacks {
  void onRead(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo) override {
    std::string uuid = pCharacteristic->getUUID().toString();
    std::string value = pCharacteristic->getValue();
    if (uuid == LAST_LOG) {
      value = getLastMessage();
      pCharacteristic->setValue(value);
    }
    #ifdef DEBUG_MODE
    DebugOutputLn(uuid + " : onRead(), value: " + value, NOT_LOG);
    #endif  
  }

  void onWrite(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo) override {
    std::string uuid = pCharacteristic->getUUID().toString();
    std::string value = pCharacteristic->getValue();
    #ifdef DEBUG_MODE
    DebugOutputf("%s : onWrite(), value: %s\n", uuid.c_str(), value.c_str());
    #endif  
    FBLECharacteristics::setValue(uuid.c_str(), value);
    setPreference(FBLECharacteristics::getPreferenceName(uuid.c_str()), value);
  }

  /**
    *  The value returned in code is the NimBLE host return code.
    */
  void onStatus(NimBLECharacteristic* pCharacteristic, int code) override {
    #ifdef DEBUG_MODE
    DebugOutputf("Notification/Indication return code: %d, %s\n", code, NimBLEUtils::returnCodeToString(code));
    #endif  
  }

  /** Peer subscribed to notifications/indications */
  void onSubscribe(NimBLECharacteristic* pCharacteristic, NimBLEConnInfo& connInfo, uint16_t subValue) override {
    #ifdef DEBUG_MODE
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

    DebugOutputf("%s\n", str.c_str());
    #endif
  }
} chrCallbacks;

/** Handler class for descriptor actions */
class DescriptorCallbacks : public NimBLEDescriptorCallbacks {
  void onWrite(NimBLEDescriptor* pDescriptor, NimBLEConnInfo& connInfo) override {
    #ifdef DEBUG_MODE
    std::string dscVal = pDescriptor->getValue();
    DebugOutputf("Descriptor written value: %s\n", dscVal.c_str());
    #endif
  }

  void onRead(NimBLEDescriptor* pDescriptor, NimBLEConnInfo& connInfo) override {
    #ifdef DEBUG_MODE
    DebugOutputf("%s Descriptor read %s\n", pDescriptor->getUUID().toString().c_str(), pDescriptor->getValue().c_str());
    #endif
  }
} dscCallbacks; 

void initBluetooth(void) {
    #ifdef DEBUG_MODE
    DebugOutputLn("Запуск Bluetooth Server");
    #endif

    std::string mac_address = initMacSHA256();
    Disconnect();

    NimBLEDevice::init(BLUETOOTH_SERVER_NAME + mac_address);
    #ifdef DEBUG_MODE
    int power = NimBLEDevice::getPower();
    DebugOutputf("Bluetooth power %d\n", power);
    #endif
    NimBLEDevice::setPower(3); /** +3db */

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

    for (byte i = 0; i < sizeof(BLECharacteristics)/sizeof(FBLECharacteristic); ++i) {
      FBLECharacteristic& characteristic = BLECharacteristics[i];
      NimBLECharacteristic* pCharacteristic;
      if (characteristic.uuid == ESP_MAC_ADDRESS || characteristic.uuid == LAST_LOG)
        pCharacteristic = pService->createCharacteristic(characteristic.uuid, NIMBLE_PROPERTY::READ);
      else
        pCharacteristic = pService->createCharacteristic(characteristic.uuid, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE);
      pCharacteristic->setValue(FBLECharacteristics::getValue(characteristic.uuid));
      pCharacteristic->setCallbacks(&chrCallbacks);
      NimBLEDescriptor* pDescription = pCharacteristic->createDescriptor(BLEUUID((uint16_t)0x2901));
      pDescription->setValue(characteristic.description);
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

    #ifdef DEBUG_MODE
    DebugOutputLn("Advertising Started");
    #endif
}
