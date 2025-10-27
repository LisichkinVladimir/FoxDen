#include "rest_api.h"

void sentData2Web(char* mac_address, std::vector<Pulse> pulseArray) {
  #ifdef DEBUG_MODE  
  Serial.printf("Отправка в Web массива из %d данных для устройства с mac адресом %s\n", pulseArray.size(), mac_address);
  return;
  #endif
  HTTPClient http;

  http.begin(SERVER_NAME);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  String httpRequestData = "mac_address=";

  int httpResponseCode = http.POST(httpRequestData);

  Serial.print("HTTP Response code: ");
  Serial.println(httpResponseCode);
  if (httpResponseCode > 0) {
    String response = http.getString();
    #ifdef DEBUG_MODE
    Serial.println("Server Response:");
    Serial.println(response);
    #endif
  } 
  else {
    #ifdef DEBUG_MODE
    Serial.print("Error on sending POST: ");
    Serial.println(httpResponseCode);
    #endif
  }
  http.end();
}
