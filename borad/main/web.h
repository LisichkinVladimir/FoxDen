#ifndef web_h
#define web_h

#include <vector>
#include <WiFi.h>
#include <esp_wifi.h>
#include <arduino_secrets.h>

#include "main.h"
#include "buffer.h"

#define WIFI_TIMEOUT 120000   // 2 minutes

bool initWeb();
void sentData2Web(std::vector<Pulse> pulseArray);

#endif