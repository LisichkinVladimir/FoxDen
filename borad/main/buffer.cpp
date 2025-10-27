#include "buffer.h"
#include "rest_api.h"

// Очередь импульсов
QueueHandle_t pulseQueue = NULL;
TaskHandle_t taskHandle = NULL;

// Время последней записи в очередь
SemaphoreHandle_t queueMutex;
volatile long lastQueuePut = 0;

// Процедура подготовки двнных для отправкичерез WiFi на REST сервер
static void SenderTask(void *pvParameters) {
  #ifdef DEBUG_MODE  
  Serial.printf("Инициализация работы с буфером данных\n");
  #endif
  char* mac_address = NULL;
  Pulse p;
  while(1) {
    vTaskDelay(pdMS_TO_TICKS(1000));
    // Получить время последного помещения данных в очередь
    long last_queue_access = 0;
    UBaseType_t queueSize = uxQueueMessagesWaiting(pulseQueue);
    if (xSemaphoreTake(queueMutex, PULSE_MAX_DELAY) == pdTRUE) {
      last_queue_access = lastQueuePut;
      xSemaphoreGive(queueMutex);
    }
    if (queueSize >= MAX_PULSE_SIZE_WHEN_SEND || (queueSize > 0 && last_queue_access > 0 && millis() - last_queue_access > MAX_PULSE_TIME_WHEN_SEND)) {
      // Подключение к Wifi
      if (initWeb(mac_address))
      {
        // Самый простой и рекомендуемый способ создать динамический массив
        std::vector<Pulse> pulseArray;
        while (xQueueReceive(pulseQueue, &p, PULSE_MAX_DELAY) == pdTRUE) {
          #ifdef DEBUG_MODE  
          Serial.printf("Данные в очереди для pin %d отправляются на Web сервер\n", p.pin);
          #endif
          pulseArray.push_back(p);
        }
        // Отправить данные через интернет
        if (pulseArray.size() > 0)
          sentData2Web(mac_address, pulseArray);
      }
    }
  }
  #ifdef DEBUG_MODE  
  Serial.printf("Ошибочное завершение процесса работы с буфером данных\n");
  #endif
  vTaskDelete(taskHandle);
}

void initBuffer(void) {
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
    queueMutex = xSemaphoreCreateBinary();

    // Запуск задачи с динамическим выделением памяти в куче, с размером стека 4кБ, приоритетом 1
    BaseType_t status = xTaskCreate(SenderTask, "SendTask", 4096, NULL, 1, &taskHandle);
    #ifdef DEBUG_MODE  
    if (status != pdPASS)
      Serial.printf("ERROR. Ошибка создания задания %d\n", status);
    else
      Serial.printf("Задание на оправку данных создано\n");
    #endif
  }
}

// Сохранить факт передачи показания в массив и инициализировать событие передачи данных по WiFi на сервер
void putData2Buffer(int pin) {
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
    if (xSemaphoreTake(queueMutex, PULSE_MAX_DELAY) == pdTRUE) {
      lastQueuePut = millis();
      xSemaphoreGive(queueMutex);
    }
  }
  else {
    #ifdef DEBUG_MODE  
    Serial.printf("ERROR. Ошибка записи в очередь %d pin %d\n", status, pin);
    #endif
  }
}