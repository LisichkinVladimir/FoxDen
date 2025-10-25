#include "pulse_led.h"

unsigned long delaytime = 0;

void initLed(void) {
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);
}

void turnOnLed(void) {
  delaytime = millis();
  digitalWrite(ledPin, LOW);
}

void turnOffLed(long delay) {
  if (delaytime > 0 && millis() - delaytime > delay)
    digitalWrite(ledPin, HIGH);
}