#pragma once
#include "Arduino.h"

#define WL_IDLE_STATUS 0
#define WL_CONNECTED 3
#define WL_DISCONNECTED 6
#define WIFI_STA 1

class WiFiClass {
 public:
  int begin(const char*, const char* = nullptr) { return status(); }
  int status() { return fil::wifi_up() ? WL_CONNECTED : WL_DISCONNECTED; }
  IPAddress localIP() { return IPAddress(); }
  bool reconnect() { return fil::wifi_up(); }
  bool disconnect(bool = false) { return true; }
  bool setAutoReconnect(bool) { return true; }
  bool mode(int) { return true; }
  bool isConnected() { return fil::wifi_up(); }
};
extern WiFiClass WiFi;
