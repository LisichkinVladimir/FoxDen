#include "rest_api.h"

std::unordered_map<std::string, std::string> mac_hash;

void generateSHA256(char* mac_address) {
  #ifdef DEBUG_MODE
  Serial.printf("Генерация MAC hash %s\n", mac_address);
  #endif

  std::vector<uint8_t> hash(32);

	mbedtls_md_context_t ctx;
	mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

  mbedtls_md_init(&ctx);
	mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 0);
	mbedtls_md_starts(&ctx);
	mbedtls_md_update(&ctx, (const unsigned char*)mac_address, 17);
	mbedtls_md_finish(&ctx, hash.data());
	mbedtls_md_free(&ctx);

  char hash_address[65] = {0};
  char twoByte[2];
  for(int i = 0, j = 0; i < hash.size(); i++, j+=2) {
    sprintf(twoByte, "%02x", hash[i]);
    hash_address[j] = twoByte[0];
    hash_address[j + 1] = twoByte[1];
  }
  for (int i = 0; i < hash.size()*2; ++i) 
    hash_address[i] = static_cast<char>(std::tolower(static_cast<unsigned char>(hash_address[i])));
  #ifdef DEBUG_MODE
  Serial.printf("MAC hash сгенерирован %s\n", hash_address);
  #endif
  mac_hash[mac_address] = hash_address;
}

bool isConnect = false;
std::string access_token = "";
std::map<int, int> pin_id;

bool connect2Web(char* mac_address) {
  #ifdef DEBUG_MODE
  Serial.print("Start connect2Web\n");
  Serial.printf("MAC address %s\n", mac_address);
  #endif

  if (mac_address == NULL) {
    #ifdef DEBUG_MODE  
    Serial.print("mac_address == NULL\n");
    #endif
    return false;
  }

  if (!mac_hash.contains(mac_address))
    generateSHA256(mac_address);
  std::string hash = mac_hash[mac_address];
  #ifdef DEBUG_MODE
  Serial.printf("MAC hash %s\n", hash.c_str());
  #endif
  
  WiFiClient client;
  HTTPClient http;  
  std::string server = std::string(SERVER_NAME) + "connect_device";
  if (!http.begin(client, server.c_str())) {
    #ifdef DEBUG_MODE
    Serial.printf("Error begin http connection to %s", server.c_str());
    #endif
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  std::string httpRequestData = "{\"mac_address\": \"" + hash + "\"}";

  int httpResponseCode = http.POST(httpRequestData.c_str());
  #ifdef DEBUG_MODE
  Serial.printf("HTTP from %s code: %d\n", server.c_str(), httpResponseCode);  
  #endif

  String payload;
  if (httpResponseCode > 0) {
    payload = client.readString();
    #ifdef DEBUG_MODE
    Serial.printf("Responce: %s\n", payload.c_str());
    #endif
  }

  client.stop();
  http.end();

  if (httpResponseCode != HTTP_CODE_OK) {
    #ifdef DEBUG_MODE
    Serial.print("Error on sending POST\n");
    #endif
    return false;
  }
  
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    #ifdef DEBUG_MODE
    Serial.printf("DeserializeJson failed: %s\n", error.f_str());
    #endif
    return false;
  }  
  #ifdef DEBUG_MODE
  Serial.print("DeserializeJson parsed succesfully\n");
  #endif
  // Получить сессионный ключ
  if (!doc.containsKey("result")) {
    #ifdef DEBUG_MODE
    Serial.printf("No result in payload");
    #endif
    return false;
  }
  if (doc["result"].containsKey("access_token")) {
    access_token = std::string(doc["result"]["access_token"]);
    #ifdef DEBUG_MODE
    Serial.printf("Access token %s\n", access_token.c_str());
    #endif
  }  else {
    #ifdef DEBUG_MODE
    Serial.print("No access token in payload\n");
    #endif
    return false;
  }
  // Получить список ID устройств (для каждого пина)
  if (doc["result"].containsKey("devices")) {
    JsonDocument devices = doc["result"]["devices"];
    #ifdef DEBUG_MODE
    String jsonString;
    serializeJson(devices, jsonString);    
    Serial.printf("Devices %s count: %d\n", jsonString.c_str(), devices.size());
    #endif
    pin_id.clear();
    for(int i = 0; i < devices.size(); i++) {
      int id = devices[i]["id"];
      int pin = devices[i]["pin"];
      #ifdef DEBUG_MODE
      Serial.printf("Id=%d pin=%d\n", id, pin);
      #endif
      pin_id[pin] = id;
    }
    isConnect = true;
  } else {
    #ifdef DEBUG_MODE
    Serial.printf("No device list in payload");
    #endif
    return false;
  }

  return true;
}

bool sendData2Web(char* mac_address, tm* timeinfo, unsigned long* synchTime, std::vector<Pulse> pulseArray) {
  #ifdef DEBUG_MODE  
  Serial.printf("Отправка в Web массива из %d данных для устройства с mac адресом %s\n", pulseArray.size(), mac_address);  
  #endif

  if (mac_address == NULL) {
    #ifdef DEBUG_MODE  
    Serial.print("mac_address == NULL\n");
    #endif
    return false;
  }

  if (timeinfo == NULL) {
    #ifdef DEBUG_MODE  
    Serial.print("timeinfo == NULL\n");
    #endif
    return false;
  }

  if (synchTime == NULL) {
    #ifdef DEBUG_MODE  
    Serial.print("synchTime == NULL\n");
    #endif
    return false;
  }

  int connectAttempt = 0;
  while (!isConnect && connectAttempt < CONNECT_ATTEMPT) {    
    connect2Web(mac_address);
    vTaskDelay(pdMS_TO_TICKS(1000));
    connectAttempt++;
  }
  if (!isConnect) {
    #ifdef DEBUG_MODE  
    Serial.print("Ошибка подключения\n");  
    #endif
    return false;
  }

  // Используя сессионный ключ послать данные SERVER_NAME + "send_device_data"
  WiFiClient client;
  HTTPClient http;  
  std::string server = std::string(SERVER_NAME) + "add_device_changes";
  if (!http.begin(client, server.c_str())) {
    #ifdef DEBUG_MODE
    Serial.printf("Error begin http connection to %s\n", server.c_str());
    #endif
    return false;
  }
  #ifdef DEBUG_MODE
  Serial.printf("Сonnection to %s\n", server.c_str());
  #endif
  std::string authorization = "Bearer " + access_token;
  http.addHeader("Authorization", authorization.c_str());
  http.addHeader("Content-Type", "application/json");

  bool is_success = true;

  for (int i = 0; i < pulseArray.size(); i++) {
    // {"device_id": "1", "moment": "2012-04-21T18:25:43Z" }
    unsigned long curr_millis = pulseArray[i].time_millis - *synchTime;
    time_t timestamp = mktime(timeinfo);
    timestamp += curr_millis / 1000;
    struct tm *pulse_timeinfo = gmtime(&timestamp);
    char buffer[80] = {0};
    // Example format: YYYY-MM-DD HH:MM:SS UTC
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", pulse_timeinfo);
    #ifdef DEBUG_MODE  
    Serial.printf("Время когда произошло срабатывание геркона: %s\n", buffer);
    #endif

    std::string httpRequestData = "{\"device_id\": \"" + std::to_string(pin_id[pulseArray[i].pin]) + "\", ";
    httpRequestData = httpRequestData + "\"moment\": \"" + buffer + "\"}";
    #ifdef DEBUG_MODE  
    Serial.printf("httpRequestData: %s\n", httpRequestData.c_str());
    #endif

    int httpResponseCode = http.POST(httpRequestData.c_str());
    #ifdef DEBUG_MODE
    Serial.printf("HTTP from %s code: %d\n", server.c_str(), httpResponseCode);  
    #endif

    String payload;
    if (httpResponseCode > 0) {
      payload = client.readString();
      #ifdef DEBUG_MODE
      Serial.printf("Responce: %s\n", payload.c_str());
      #endif
    }

    if (httpResponseCode != HTTP_CODE_OK) {
      #ifdef DEBUG_MODE
      Serial.print("Error on sending POST\n");
      #endif
    }
    is_success = is_success & httpResponseCode == HTTP_CODE_OK;
  }
  client.stop();
  http.end();

  return is_success;
}
