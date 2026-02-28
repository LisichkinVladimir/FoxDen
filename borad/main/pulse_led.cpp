#include "pulse_led.h"

struct Led {
  int delay;
  int count;
};

void initLed(void) {
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);
}

void led_task_exec(void *pvParameters) {
  Led *pl = (Led *)pvParameters;
  vTaskDelay(pdMS_TO_TICKS(pl->delay));
  digitalWrite(ledPin, HIGH);
  #ifdef DEBUG_MODE_PULSE
  Serial.print("LED выключен\n");
  #endif
  while (pl->count-- > 1) {
    // Помигаем
    #ifdef DEBUG_MODE_PULSE
    Serial.print("Мигаем\n");
    #endif
    vTaskDelay(pdMS_TO_TICKS(DELAY));
    // Включаем
    digitalWrite(ledPin, LOW);
    vTaskDelay(pdMS_TO_TICKS(DELAY/2));
    // Выключаем
    digitalWrite(ledPin, HIGH);
  }
  delete pl;
  vTaskDelete(NULL);
}

void turnOnLed(int delay, int count) {
  Led* pl = new Led;
  pl->delay = delay;
  pl->count = count;
  BaseType_t status = xTaskCreate(led_task_exec, "led_task_exec", 1024, pl, 1, NULL);  
  if (status == pdPASS) {
    digitalWrite(ledPin, LOW);
    #ifdef DEBUG_MODE_PULSE
    Serial.printf("LED включен. Задание на мигание создано. dalay = %d\n", pl->delay);
    #endif
  }
  #ifdef DEBUG_MODE_PULSE
  else 
    Serial.printf("ERROR. Ошибка создания задания LED %d\n", status);
  #endif
}
