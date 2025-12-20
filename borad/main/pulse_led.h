#ifndef pulse_led_h
#define pulse_led_h

#include <inttypes.h>
#include <Arduino.h>

#include "main.h"

// Пин светодиода
#if defined(ARDUINO_SUPER_MINI_ESP32C3)
  static const uint8_t ledPin = BUILTIN_LED;
#else
  static const uint8_t ledPin = 8;          
#endif
#define DELAY 1500
#define MAX_LED_SIZE 50
#define LED_MAX_DELAY 200

void initLed(void);
void turnOnLed(int delay = DELAY, int count = 1);

#endif