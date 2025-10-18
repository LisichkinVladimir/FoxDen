#include <WiFi.h>
#include <esp_wifi.h>
#include "web.h"
#include "main.h"
#include "pulse_led.h"

// MAC адрес устройства
static uint8_t MacAddress[6] = {0};
bool is_read_mac = false;

bool readMacAddress() {
  WiFi.mode(WIFI_STA);
  WiFi.STA.begin();
  esp_err_t ret = esp_wifi_get_mac(WIFI_IF_STA, MacAddress);
  bool result = ret == ESP_OK;
  if (ret != ESP_OK)
    memset(MacAddress, 0, sizeof(MacAddress));
  #ifdef DEBUG_MODE  
  Serial.print("ESP32 Board MAC Address: ");
  Serial.printf("%02x:%02x:%02x:%02x:%02x:%02x\n",
                MacAddress[0], MacAddress[1], MacAddress[2],
                MacAddress[3], MacAddress[4], MacAddress[5]);
  #endif
  WiFi.mode(WIFI_OFF);
  return result;
}

// Очередь импульсов
QueueHandle_t pulseQueue = NULL;

// Процедура отправки данных через WiFi на REST сервер
static void SenderTask(void *pvParameters) {
  #ifdef DEBUG_MODE  
  Serial.printf("Инициализация процесса отравки данных\n");
  #endif
  Pulse* p;
  while(1) {
    portBASE_TYPE status = xQueueReceive(pulseQueue, p, PULSE_MAX_DELAY);
  }
}

void initWeb(void) {
  // TODO
  return;
  if (pulseQueue!= NULL) {
    pulseQueue = xQueueCreate(MAX_PULSE_SIZE, sizeof(Pulse));  
    // Запуск задачи с динамическим выделением памяти в куче, с размером стека 4кБ, приоритетом 5
    xTaskCreate(SenderTask, "SendRask", 4096, NULL, 5, NULL);
  }
}

// Сохранить факт передачи показания в массив и инициализировать событие передачи данных по WiFi на сервер
void sendData2Web(int pin) {
  // Включим светодиод
  turnOnLed();
  #ifdef DEBUG_MODE  
  Serial.printf("запись в очередь +10 литров pin %d\n", pin);
  #endif
  // TODO
  /*Pulse* p = new Pulse;
  p->time_millis = millis();
  p->pin = pin;
  BaseType_t status = xQueueSendToBack(pulseQueue, &p, PULSE_MAX_DELAY);
  if (status != pdPASS) {
    #ifdef DEBUG_MODE  
    Serial.printf("ошибка записи в очередь %d pin %d\n", status, pin);
    #endif
  }*/
}