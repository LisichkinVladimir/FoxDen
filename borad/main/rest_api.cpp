#include "rest_api.h"

bool isConnect = false;
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

void connect2Web(char* mac_address) {
  #ifdef DEBUG_MODE
  Serial.print("Start connect2Web\n");
  Serial.printf("MAC address %s\n", mac_address);
  #endif
  if (!mac_hash.contains(mac_address))
    generateSHA256(mac_address);
  std::string hash = mac_hash[mac_address];
  #ifdef DEBUG_MODE
  Serial.printf("MAC hash %s\n", hash.c_str());
  #endif

  HTTPClient http;

  std::string server = std::string(SERVER_NAME) + "connect_device";
  http.begin(server.c_str());
  http.addHeader("Content-Type", "application/json");
  std::string httpRequestData = "{\"mac_address\": \"" + hash + "\"}";

  int httpResponseCode = http.POST(httpRequestData.c_str());

  #ifdef DEBUG_MODE
  Serial.printf("HTTP Response from %s code: %d\n", server.c_str(), httpResponseCode);
  #endif
  if (httpResponseCode > 0) {
    String response = http.getString();
    #ifdef DEBUG_MODE
    Serial.printf("Server Response: %s\n", response);
    #endif
  } 
  else {
    #ifdef DEBUG_MODE
    Serial.print("Error on sending POST\n");
    #endif
  }
  http.end();
  // TODO 
  // Получить список ID устройств (для каждого пина)
  // Получить сессионный ключ
}

void sendData2Web(char* mac_address, std::vector<Pulse> pulseArray) {
  #ifdef DEBUG_MODE  
  Serial.printf("Отправка в Web массива из %d данных для устройства с mac адресом %s\n", pulseArray.size(), mac_address);  
  #endif

  int connectAttempt = 0;
  while (isConnect || connectAttempt < CONNECT_ATTEMPT) {    
    connect2Web(mac_address);
    vTaskDelay(pdMS_TO_TICKS(1000));
  }
  // TODO используя сессионный ключ послать данные SERVER_NAME + "send_device_data"
}
