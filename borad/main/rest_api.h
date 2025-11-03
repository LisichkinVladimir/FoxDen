#ifndef rest_api_h
#define rest_api_h

#include <stdlib.h>
#include <vector>
#include <string>
#include <unordered_map>
#include <HTTPClient.h>
#include <WString.h>
#include <mbedtls/md.h>

#include "buffer.h"

#define SERVER_NAME "http://localhost:5000/"
#define CONNECT_ATTEMPT 2

void sendData2Web(char* mac_address, std::vector<Pulse> pulseArray);
void connect2Web(char* mac_address);

#endif
