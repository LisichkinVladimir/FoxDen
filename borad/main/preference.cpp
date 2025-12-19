#include "preference.h"

Preferences foxden_settings;

void initPreference(void) {
  foxden_settings.begin("foxden_settings", false);
  WIFI_SSID = foxden_settings.getString("WIFI_SSID", WIFI_SSID.c_str()).c_str();
  WIFI_PASSWORD = foxden_settings.getString("WIFI_PASSWORD", WIFI_PASSWORD.c_str()).c_str();
  SERVER_NAME = foxden_settings.getString("SERVER_NAME", SERVER_NAME.c_str()).c_str();

  #ifdef DEBUG_MODE
  Serial.print("Init preferences:\n");
  Serial.printf("WIFI_SSID: %s\n", WIFI_SSID.c_str());
  Serial.printf("WIFI_PASSWORD: %s\n", WIFI_PASSWORD.c_str());
  Serial.printf("SERVER_NAME: %s\n", SERVER_NAME.c_str());
  #endif
}

void setPreference(const char *key, const std::string value) {
  foxden_settings.putString(key, value.c_str());
  #ifdef DEBUG_MODE
  Serial.printf("Set preference %s value %s\n", key, value.c_str());
  #endif
}