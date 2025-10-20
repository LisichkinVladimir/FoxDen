#include "web.h"

// MAC адрес устройства
static uint8_t MacAddress[6] = {0};
bool isReadMac = false;

bool readMacAddress() {
  WiFi.mode(WIFI_STA);
  WiFi.STA.begin();
  esp_err_t ret = esp_wifi_get_mac(WIFI_IF_STA, MacAddress);
  bool result = ret == ESP_OK;
  if (ret != ESP_OK)
    memset(MacAddress, 0, sizeof(MacAddress));
  #ifdef DEBUG_MODE  
  Serial.print("ESP32 MAC Address: ");
  Serial.printf("%02x:%02x:%02x:%02x:%02x:%02x\n",
                MacAddress[0], MacAddress[1], MacAddress[2],
                MacAddress[3], MacAddress[4], MacAddress[5]);
  #endif
  WiFi.mode(WIFI_OFF);
  isReadMac = result;
  return result;
}

unsigned long connectTime = 0;
unsigned long etime = 0;
unsigned long dottime = 0;
bool isConnect = false;

void wifiDisconnect(void) {
  if (WiFi.isConnected()) {
    #ifdef DEBUG_MODE  
    Serial.println("WiFi Disconnecting");
    #endif
    WiFi.setAutoReconnect(false);
    WiFi.disconnect(true, true);
    while (WiFi.isConnected()) delay(5);
    #ifdef DEBUG_MODE  
    Serial.println("WiFi Disconnected");
    delay(5000);
    #endif
  }
  WiFi.mode(WIFI_OFF);  
}

void wifiStartConnecting(void) {
  wifiDisconnect();
  #ifdef DEBUG_MODE  
  Serial.printf("\nПопытка подключения к Wi-Fi сети в течении %.1f секунд\n", (1.0*WIFI_TIMEOUT)/1000);
  #endif

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);
  connectTime = millis();
  dottime = millis();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
} 

bool initWeb() {
  if (!isReadMac)
    readMacAddress();
  // TODO инициализация подключения по WiFi
  // TODO получение текущего времени через SNTP
  return true;
}

void sentData2Web(std::vector<Pulse> pulseArray) {
  #ifdef DEBUG_MODE  
  Serial.printf("Отправка в Web массива из %d данных\n", pulseArray.size());
  #endif
  // TODO
}