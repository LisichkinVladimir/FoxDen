#ifndef debug_h
#define debug_h

#include <iostream>
#include <string>
#include <vector>
#include <WString.h>

#define DEBUG_MODE

enum log_type {INFO_LOG, ERROR_LOG, NOT_LOG};

std::string getLastMessage(void);
std::string getLastError(void);

void DebugOutput(const char *message, log_type type = INFO_LOG);
void DebugOutputLn(const char *message, log_type type = INFO_LOG);
void DebugOutput(const String &message, log_type type = INFO_LOG);
void DebugOutputLn(const String &message, log_type type = INFO_LOG);
void DebugOutput(const std::string &message, log_type type = INFO_LOG);
void DebugOutputLn(const std::string &message, log_type type = INFO_LOG);

void DebugOutputf(const char *format, ...);
void DebugOutputE(const char *format, ...);

#endif