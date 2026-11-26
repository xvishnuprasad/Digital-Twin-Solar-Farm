// Implementation of the host-side Arduino/WiFi/WebServer/Blynk shim.
#include <map>
#include <string>

#include "Arduino.h"
#include "BlynkSimpleEsp32.h"
#include "WebServer.h"
#include "WiFi.h"

HardwareSerial Serial;
WiFiClass WiFi;
BlynkWifi Blynk;

namespace {
std::map<int, int> g_adc;
unsigned long g_millis = 0;
bool g_wifi = true;
std::string g_serial;  // partial Serial line
std::string g_pending_uri;
}  // namespace

namespace fil {
void emit(const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vprintf(fmt, ap);
  va_end(ap);
}
void set_adc(int pin, int raw) { g_adc[pin] = raw; }
void set_millis(unsigned long ms) { g_millis = ms; }
void set_wifi(bool up) { g_wifi = up; }
bool wifi_up() { return g_wifi; }
void flush_serial() {
  if (!g_serial.empty()) {
    emit("SERIAL\t%s\n", g_serial.c_str());
    g_serial.clear();
  }
}
}  // namespace fil

void HardwareSerial::print(const char* c) {
  for (const char* p = c; *p; ++p) {
    if (*p == '\n') {
      fil::emit("SERIAL\t%s\n", g_serial.c_str());
      g_serial.clear();
    } else if (*p != '\r') {
      if (g_serial.size() < 4096) g_serial += *p;  // bound runaway "....." loops
    }
  }
}

int HardwareSerial::printf(const char* fmt, ...) {
  char buf[512];
  va_list ap;
  va_start(ap, fmt);
  int n = vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  print(buf);
  return n;
}

void pinMode(int, int) {}
void digitalWrite(int pin, int level) { fil::emit("LED\t%d\t%d\n", pin, level ? 1 : 0); }
int analogRead(int pin) {
  auto it = g_adc.find(pin);
  return it == g_adc.end() ? 0 : it->second;
}
void delay(unsigned long ms) { g_millis += ms; }
unsigned long millis() { return g_millis; }

void WebServer::queue_request(const std::string& uri) { g_pending_uri = uri; }

void WebServer::handleClient() {
  if (g_pending_uri.empty()) return;
  pending_ = g_pending_uri;
  g_pending_uri.clear();
  headers_.clear();
  auto it = routes_.find(pending_);
  if (it != routes_.end()) {
    it->second();
  } else {
    send(404, "text/plain", String("Not found"));
  }
}

void WebServer::send(int code, const char* content_type, const String& body) {
  std::string hdr;
  for (auto& h : headers_) {
    if (!hdr.empty()) hdr += "\x1f";
    hdr += h.first + ": " + h.second;
  }
  headers_.clear();
  fil::emit("HTTP\t%d\t%s\t%s\t%s\n", code, content_type, hdr.c_str(), body.c_str());
}
