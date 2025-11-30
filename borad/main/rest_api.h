#ifndef rest_api_h
#define rest_api_h

#include <stdlib.h>
#include <vector>
#include <map>
#include <string>
#include <unordered_map>
#include <HTTPClient.h>
#include <WString.h>
#include <mbedtls/md.h>
#include <ArduinoJson.h>
#include <WiFiClient.h>

#include "buffer.h"

#define SERVER_NAME "http://192.168.1.14:5000/"
#define CONNECT_ATTEMPT 2

bool sendData2Web(char* mac_address, std::vector<Pulse> pulseArray);
bool connect2Web(char* mac_address);

#endif
