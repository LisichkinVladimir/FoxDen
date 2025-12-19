#ifndef rest_api_h
#define rest_api_h

#include <stdlib.h>
#include <vector>
#include <string>
#include <HTTPClient.h>
#include <WString.h>
#include <mbedtls/md.h>
#include <ArduinoJson.h>
#include <WiFiClient.h>

#include "buffer.h"
#include "arduino_secrets.h"

#define CONNECT_ATTEMPT 2

bool sendData2Web(char* mac_address, tm* timeinfo, unsigned long* synchTime, std::vector<Pulse> pulseArray);
bool connect2Web(char* mac_address);

#endif
