#include "web_wifi.h"

// MAC адрес устройства
char MacAddress[18] = {0};
bool isReadMac = false;

bool readMacAddress() {
  WiFi.mode(WIFI_STA);
  WiFi.STA.begin();
  uint8_t uMacAddress[6] = {0};
  esp_err_t ret = esp_wifi_get_mac(WIFI_IF_STA, uMacAddress);
  bool result = ret == ESP_OK;
  if (ret != ESP_OK)
    memset(uMacAddress, 0, sizeof(uMacAddress));
  sprintf(MacAddress, "%02x:%02x:%02x:%02x:%02x:%02x", 
    uMacAddress[0], uMacAddress[1], uMacAddress[2],
    uMacAddress[3], uMacAddress[4], uMacAddress[5]);
  for (byte i = 0; i < sizeof(MacAddress); ++i) 
    MacAddress[i] = static_cast<char>(std::toupper(static_cast<unsigned char>(MacAddress[i])));
  #ifdef DEBUG_MODE
  Serial.printf("ESP32 MAC Address: %s\n", MacAddress);
  #endif
  isReadMac = result;
  return result;
}

unsigned long connectTime = 0;
bool isWIFIConnect = false;

void Disconnect(void) {
  if (WiFi.isConnected()) {
    #ifdef DEBUG_MODE  
    Serial.println("WiFi Disconnecting");
    #endif
    WiFi.setAutoReconnect(false);
    WiFi.disconnect(true, true);
    while (WiFi.isConnected()) delay(5);
    #ifdef DEBUG_MODE  
    Serial.println("WiFi Disconnected");
    #endif
    delay(5000);
  }
  WiFi.mode(WIFI_OFF);  
}

void StartConnecting(void) {
  Disconnect();
  #ifdef DEBUG_MODE  
  Serial.printf("Попытка подключения к Wi-Fi сети в течении %.1f секунд\n", (1.0*WIFI_TIMEOUT)/1000);
  #endif

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);
  connectTime = millis();
  #ifdef DEBUG_MODE  
  Serial.printf("Запуск WiFi.begin\n");
  #endif
  delay(2000);
  #ifdef SHOW_NETWORKS
  int n = WiFi.scanNetworks();
  Serial.println("scan done");
  if (n == 0) {
      Serial.println("no networks found");
  } else {
    Serial.printf("Networks found %d\n", n);
    for(byte i = 0; i < n; ++i) {
      Serial.printf("wifi(%d): %s\n", i, WiFi.SSID(i));
    }
  }
  #endif
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  #ifdef DEBUG_MODE  
  Serial.printf("Ожидание подключения\n");
  #endif
} 

const char* getStatus2Sting(wl_status_t status) {
  switch (status) {
    case WL_NO_SHIELD: return "WL_NO_SHIELD";
    case WL_IDLE_STATUS: return "WL_IDLE_STATUS";
    case WL_NO_SSID_AVAIL: return "WL_NO_SSID_AVAIL";
    case WL_SCAN_COMPLETED: return "WL_SCAN_COMPLETED";
    case WL_CONNECTED: return "WL_CONNECTED";
    case WL_CONNECT_FAILED: return "WL_CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "WL_CONNECTION_LOST";
    case WL_DISCONNECTED: return "WL_DISCONNECTED";
  }
}

void printStatus(void) {
  Serial.println("[WiFi] status:");
  switch(WiFi.status()) {
      case WL_NO_SSID_AVAIL:
        Serial.println("[WiFi] SSID not found");
        break;
      case WL_CONNECT_FAILED:
        Serial.println("[WiFi] Failed - WiFi not connected! Reason: WL_CONNECT_FAILED");
        break;
      case WL_CONNECTION_LOST:
        Serial.println("[WiFi] Connection was lost");
        break;
      case WL_SCAN_COMPLETED:
        Serial.println("[WiFi] Scan is completed");
        break;
      case WL_DISCONNECTED:
        Serial.println("[WiFi] WiFi is disconnected");
        break;
      case WL_CONNECTED:
        Serial.print("[WiFi] WiFi is connected. IP address: ");
        Serial.println(WiFi.localIP());
        break;
      default:
        Serial.print("[WiFi] WiFi Status: ");
        Serial.println(WiFi.status());
        break;
  }
}

void waitConnecting() {
  // Инициализация подключения по WiFi
  StartConnecting();
  #ifdef DEBUG_MODE
  unsigned long etime = 0;
  int step = 1;
  #endif
  do {
    vTaskDelay(pdMS_TO_TICKS(1500));
    wl_status_t status = WiFi.status();
    if (status == WL_CONNECTED) {
      etime = millis() - connectTime;
      #ifdef DEBUG_MODE
      Serial.print("WiFi is connected with IP address: ");
      Serial.println(WiFi.localIP());
      Serial.printf("Подключено после %u ms\n", etime);
      #endif
      isWIFIConnect = true;
      break;
    }
    #ifdef DEBUG_MODE
    Serial.printf("WiFi Не подключено %d статус(%d) %s\n", step++, status, getStatus2Sting(status)); 
    #endif
  } while (millis() - connectTime <= WIFI_TIMEOUT);
  if (!isWIFIConnect) {
      #ifdef DEBUG_MODE
      Serial.printf("Не подключено после %.1f секунд\n", (1.0*WIFI_TIMEOUT)/1000);
      printStatus();
      #endif
  }
}

unsigned long synchronizationTime = 0;
bool isSynchronized = false;
bool sntpFinish = false;
SemaphoreHandle_t synchronizationMutex;
struct tm curr_timeinfo;

void sntp_notification(struct timeval *tv)
{
  char strftime_buf[20] = {0};
  localtime_r(&tv->tv_sec, &curr_timeinfo);
  if (xSemaphoreTake(synchronizationMutex, 200) == pdTRUE) {
    if (curr_timeinfo.tm_year < (1970 - 1900)) {
      isSynchronized = false;
      #ifdef DEBUG_MODE  
      Serial.printf("Синхронизация времени не удалась!\n");
      #endif
    } else {
      // Post time event
      // eventLoopPost(RE_TIME_EVENTS, RE_TIME_SNTP_SYNC_OK, nullptr, 0, portMAX_DELAY);
      isSynchronized = true;
      synchronizationTime = millis();
      #ifdef DEBUG_MODE  
      strftime(strftime_buf, sizeof(strftime_buf), "%d.%m.%Y %H:%M:%S", &curr_timeinfo);
      Serial.printf("Синхронизация времени завершена, текущее время: %s\n", strftime_buf);
      #endif
    };
    sntpFinish = true;
    xSemaphoreGive(synchronizationMutex);
  }
}

// SNTP-синхронизация времени
void setDateTime() {
  #ifdef DEBUG_MODE  
  Serial.printf("Запуск синхронизации времени\n");
  #endif
  setenv("TZ", CURRENT_TZ, 1);
  tzset();
  sntpFinish = false;
  unsigned long synchronizationStart = millis();
  // Создание семафора
  synchronizationMutex = xSemaphoreCreateBinary();
  // Запускаем синхронизацию времени по SNTP протоколу
  sntp_setoperatingmode(SNTP_OPMODE_POLL);
  sntp_set_time_sync_notification_cb(sntp_notification);
  sntp_setservername(0, "pool.ntp.org");
  sntp_setservername(1, "time.nist.gov");
  sntp_setservername(2, "time.google.com");
  sntp_setservername(3, "time.windows.com");
  sntp_init();
  #ifdef DEBUG_MODE
  int step = 1; 
  #endif
  while (true) {
    if (xSemaphoreTake(synchronizationMutex, 200) == pdTRUE) {
      if (sntpFinish || millis() - synchronizationStart > WIFI_TIMEOUT)
        break;
      #ifdef DEBUG_MODE  
      Serial.printf("Ожидание синхронихации времени %d\n", step++);
      #endif
    }
    xSemaphoreGive(synchronizationMutex);
    vTaskDelay(pdMS_TO_TICKS(1500));
  }
  vSemaphoreDelete(synchronizationMutex);
  #ifdef DEBUG_MODE
  if (!isSynchronized)
    Serial.printf("Не произошла синхронихация времени после %.1f секунд\n", (1.0*WIFI_TIMEOUT)/1000);
  else
    Serial.print("Ожидание завершено\n");
  #endif
}

bool initWeb(char** mac_address, tm** timeinfo, unsigned long** synchTime) {
  #ifdef DEBUG_MODE
  Serial.println("initWeb");
  #endif
  if (!isReadMac)
    readMacAddress();
  waitConnecting();
  if (isWIFIConnect)
    if (!isSynchronized)
      setDateTime();
  *mac_address = MacAddress;
  *timeinfo = &curr_timeinfo;
  *synchTime = &synchronizationTime;
  return isReadMac && isWIFIConnect && isSynchronized;
}