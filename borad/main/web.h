#ifndef web_h
#define web_h

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <freertos/projdefs.h>
#include <freertos/portmacro.h>
#include <WiFi.h>
#include <esp_wifi.h>

struct Pulse {
  long time_millis;
  int pin;
};

#define MAX_PULSE_SIZE 100
#define PULSE_MAX_DELAY 200
#define MAX_PULSE_SIZE_WHEN_SEND 2
#define MAX_PULSE_TIME_WHEN_SEND 60*1000*30

void initWeb(void);
void sendData2Web(int pin);

#endif