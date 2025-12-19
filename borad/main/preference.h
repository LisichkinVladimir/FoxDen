#ifndef preference_h
#define preference_h

#include <string>
#include <Preferences.h>

#include "main.h"
#include "arduino_secrets.h"

void initPreference(void);
void setPreference(const char *key, const std::string value);

#endif