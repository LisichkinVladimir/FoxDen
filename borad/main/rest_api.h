#ifndef rest_api_h
#define rest_api_h

#include <vector>
#include <HTTPClient.h>

#include "buffer.h"

#define SERVER_NAME "http://localhost:5000/"

void sentData2Web(std::vector<Pulse> pulseArray);

#endif
