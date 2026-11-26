#pragma once
#include <vector>

#include "WiFi.h"

#define V0 0
#define V1 1
#define V2 2
#define V3 3
#define V4 4
#define V5 5
#define V6 6
#define V7 7
#define V8 8
#define V9 9
#define V10 10

class BlynkWifi {
 public:
  // Real Blynk.begin() blocks until Wi-Fi and the cloud are reachable.
  void begin(const char* auth, const char* ssid, const char* pass) {
    (void)ssid; (void)pass;
    config(auth);
    while (!fil::wifi_up()) delay(500);
    connected_ = true;
  }
  void config(const char* auth, const char* domain = "blynk.cloud", uint16_t port = 80) {
    (void)auth; (void)domain; (void)port;
    configured_ = true;
  }
  bool connect(unsigned long timeout = 18000) {
    (void)timeout;
    connected_ = configured_ && fil::wifi_up();
    return connected_;
  }
  bool connected() { return connected_ && fil::wifi_up(); }
  void run() {
    if (configured_ && !connected_ && fil::wifi_up()) connected_ = true;
  }
  void virtualWrite(int pin, float v) { if (connected()) fil::emit("BLYNK\t%d\t%.9g\n", pin, (double)v); }
  void virtualWrite(int pin, double v) { if (connected()) fil::emit("BLYNK\t%d\t%.9g\n", pin, v); }
  void virtualWrite(int pin, int v) { if (connected()) fil::emit("BLYNK\t%d\t%d\n", pin, v); }
  void virtualWrite(int pin, const String& v) { if (connected()) fil::emit("BLYNK\t%d\t%s\n", pin, v.c_str()); }
  void virtualWrite(int pin, const char* v) { virtualWrite(pin, String(v)); }

 private:
  bool configured_ = false;
  bool connected_ = false;
};
extern BlynkWifi Blynk;

class BlynkTimer {
 public:
  int setInterval(long ms, void (*cb)()) {
    timers_.push_back({ms, millis(), cb});
    return (int)timers_.size() - 1;
  }
  void run() {
    unsigned long now = millis();
    for (auto& t : timers_) {
      if (now - t.prev >= (unsigned long)t.interval) {
        t.prev += t.interval;
        t.cb();
      }
    }
  }

 private:
  struct T { long interval; unsigned long prev; void (*cb)(); };
  std::vector<T> timers_;
};
