#ifndef buffer_h
#define buffer_h

#include <vector>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <freertos/projdefs.h>
#include <freertos/portmacro.h>

#include "main.h"
#include "pulse_led.h"

struct Pulse {
  long time_millis;
  int pin;
};

#define MAX_PULSE_SIZE 100
#define PULSE_MAX_DELAY 200
#define MAX_PULSE_SIZE_WHEN_SEND 2
#define MAX_PULSE_TIME_WHEN_SEND 60*1000*30

void initBuffer(void);
void putData2Buffer(int pin);

#endif