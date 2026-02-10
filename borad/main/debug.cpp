#include <HardwareSerial.h>
#include "debug.h"

static SemaphoreHandle_t lastMessageMutex = NULL;
std::string last_message = "";
std::string last_error = "";

std::string getLastMessage(void) {
  if (lastMessageMutex != NULL && xSemaphoreTake(lastMessageMutex, 200) == pdTRUE) {
      std::string result = last_message;
      xSemaphoreGive(lastMessageMutex);
      return result;
    }
  else {
    Serial.println("lastMessageMutex is not initialized or locked");
    return std::string();
  }
}

std::string getLastError(void) {
  if (lastMessageMutex != NULL && xSemaphoreTake(lastMessageMutex, 200) == pdTRUE) {
      std::string result = last_error;
      xSemaphoreGive(lastMessageMutex);
      return result;
    }
  else {
    Serial.println("lastMessageMutex is not initialized or locked");
    return std::string();
  }
}

void setLastMessage(std::string message, log_type type = INFO_LOG) {
  if (type == NOT_LOG)
    return;  
  if (lastMessageMutex == NULL) {
    lastMessageMutex = xSemaphoreCreateBinary();
    xSemaphoreGive(lastMessageMutex); // Make it available    
  }
  if (lastMessageMutex != NULL) {
    if (xSemaphoreTake(lastMessageMutex, 200) == pdTRUE) {
      if (type == INFO_LOG)
        last_message = message;
      else
        last_error = message;
      xSemaphoreGive(lastMessageMutex);
    } else
      Serial.println("lastMessageMutex is locked");
  } else
    Serial.println("lastMessageMutex is not initialized"); 
}

void DebugOutput(const char *message, log_type type) {
  #ifdef DEBUG_MODE  
  Serial.print(message);
  setLastMessage(message, type);
  #endif
}

void DebugOutputLn(const char *message, log_type type) {
  #ifdef DEBUG_MODE  
  Serial.println(message);
  setLastMessage(message, type);
  #endif
}

void DebugOutput(const String &message, log_type type) {
  #ifdef DEBUG_MODE  
  Serial.print(message);
  setLastMessage(message.c_str(), type);
  #endif
}

void DebugOutputLn(const String &message, log_type type) {
  #ifdef DEBUG_MODE  
  Serial.println(message);
  setLastMessage(message.c_str(), type);
  #endif
}

void DebugOutput(const std::string &message, log_type type) {
  #ifdef DEBUG_MODE  
  Serial.print(message.c_str());
  setLastMessage(message, type);
  #endif
}

void DebugOutputLn(const std::string &message, log_type type) {
  #ifdef DEBUG_MODE  
  Serial.println(message.c_str());
  setLastMessage(message, type);
  #endif
};

void DebugOutputf(const char *format, ...) {
  #ifdef DEBUG_MODE
  va_list args;
  va_start(args, format);

  int size = vsnprintf(nullptr, 0, format, args);
  va_end(args);

  if (size < 0)
    return;
  
  std::vector<char> buffer(size + 1); // Create a buffer of the correct size
  va_start(args, format);
  vsnprintf(buffer.data(), buffer.size(), format, args);
  va_end(args);

  std::string s(buffer.begin(), buffer.end());
  Serial.print(s.c_str());
  setLastMessage(s, INFO_LOG);

  #endif  
}

void DebugOutputE(const char *format, ...) {
  #ifdef DEBUG_MODE
  va_list args;
  va_start(args, format);

  int size = vsnprintf(nullptr, 0, format, args);
  va_end(args);

  if (size < 0)
    return;
  
  std::vector<char> buffer(size + 1); // Create a buffer of the correct size
  va_start(args, format);
  vsnprintf(buffer.data(), buffer.size(), format, args);
  va_end(args);

  std::string s(buffer.begin(), buffer.end());
  Serial.print(s.c_str());
  setLastMessage(s, ERROR_LOG);

  #endif  
}
