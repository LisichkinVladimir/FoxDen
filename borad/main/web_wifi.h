#ifndef web_wifi_h
#define web_wifi_h

#include <vector>
#include <stdlib.h>
#include <time.h>
#include <WiFi.h>
#include <WiFiType.h>
#include <WiFiSTA.h>
#include <WiFiGeneric.h>
#include <esp_wifi.h>
#include <esp_wifi_types_generic.h>
#include <esp_sntp.h>
#include <freertos/task.h>
#include <freertos/projdefs.h>

#include "arduino_secrets.h"

#include "main.h"
#include "tz.h"

#define WIFI_TIMEOUT 60000   // 1 minutes
#undef SHOW_NETWORKS
#define CURRENT_TZ TZ_Europe_Moscow

bool initWeb(char** mac_address, tm** timeinfo, unsigned long** synchTime);
void Disconnect(void);

#endif