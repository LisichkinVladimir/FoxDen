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

// Время последней записи в очередь
SemaphoreHandle_t queue_mutex;
volatile long last_queue_put = 0;

// Процедура отправки данных через WiFi на REST сервер
static void SenderTask(void *pvParameters) {
  #ifdef DEBUG_MODE  
  Serial.printf("Инициализация процесса отравки данных\n");
  #endif
  Pulse p;
  while(1) {
    vTaskDelay(pdMS_TO_TICKS(1000));
    // Получить время последного помещения данных в очередь
    long last_queue_access = 0;
    UBaseType_t queueSize = uxQueueMessagesWaiting(pulseQueue);
    if (xSemaphoreTake(queue_mutex, PULSE_MAX_DELAY) == pdTRUE) {
      last_queue_access = last_queue_put;
      xSemaphoreGive(queue_mutex);
    }
    if (queueSize >= MAX_PULSE_SIZE_WHEN_SEND || (queueSize > 0 && last_queue_access > 0 && millis() - last_queue_access > MAX_PULSE_TIME_WHEN_SEND)) {      
      if (!is_read_mac)
        readMacAddress();
      // TODO Инициализация Wifi
      while (xQueueReceive(pulseQueue, &p, PULSE_MAX_DELAY) == pdTRUE) {
        #ifdef DEBUG_MODE  
        Serial.printf("Данные в очереди для pin %d отправляются на Web сервер\n", p.pin);
        #endif
        // TODO отправить данные через интернет
      }
    }
  }
}

void initWeb(void) {
  if (pulseQueue == NULL) {
    // Создание очереди
    pulseQueue = xQueueCreate(MAX_PULSE_SIZE, sizeof(Pulse));
    #ifdef DEBUG_MODE  
    if (pulseQueue == NULL)
      Serial.printf("ERROR. Ошибка создания очереди\n");
    else
      Serial.printf("Очередь создана\n");
    #endif

    // Создание семафора для переменной когда последний раз была запись в очередь
    queue_mutex = xSemaphoreCreateBinary();

    // Запуск задачи с динамическим выделением памяти в куче, с размером стека 4кБ, приоритетом 1
    BaseType_t status = xTaskCreate(SenderTask, "SendTask", 4096, NULL, 1, NULL);
    #ifdef DEBUG_MODE  
    if (status != pdPASS)
      Serial.printf("ERROR. Ошибка создания задания %d\n", status);
    else
      Serial.printf("Задание на оправку данных создано\n");
    #endif
  }
}

// Сохранить факт передачи показания в массив и инициализировать событие передачи данных по WiFi на сервер
void sendData2Web(int pin) {
  // Включим светодиод
  turnOnLed();
  #ifdef DEBUG_MODE  
  Serial.printf("Запись в очередь +10 литров pin %d\n", pin);
  #endif

  Pulse p;
  p.time_millis = millis();
  p.pin = pin;
  BaseType_t status = xQueueSendToBack(pulseQueue, &p, PULSE_MAX_DELAY);
  if (status == pdPASS) {
    if (xSemaphoreTake(queue_mutex, PULSE_MAX_DELAY) == pdTRUE) {
      last_queue_put = millis();
      xSemaphoreGive(queue_mutex);
    }
  }
  else {
    #ifdef DEBUG_MODE  
    Serial.printf("ERROR. Ошибка записи в очередь %d pin %d\n", status, pin);
    #endif
  }
}