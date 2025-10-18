#ifndef web_h
#define web_h

struct Pulse {
  long time_millis;
  int pin;
};

#define MAX_PULSE_SIZE 100
#define PULSE_MAX_DELAY 200

void initWeb(void);
void sendData2Web(int pin);

#endif