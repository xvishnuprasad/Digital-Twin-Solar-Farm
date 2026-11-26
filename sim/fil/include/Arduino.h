// Host-side Arduino core shim for firmware-in-the-loop (FIL) testing.
// Implements only the API surface Solar_Farm.ino uses; every observable side effect
// (GPIO writes, Serial output, Blynk writes, HTTP responses) is emitted as a protocol
// line on stdout so the Python driver can compare it with the reference model.
#pragma once

#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <string>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1

class String {
 public:
  std::string s;
  String() {}
  String(const char* c) : s(c ? c : "") {}
  String(const std::string& x) : s(x) {}
  String(char c) : s(1, c) {}
  String(int v) : s(std::to_string(v)) {}
  String(unsigned int v) : s(std::to_string(v)) {}
  String(long v) : s(std::to_string(v)) {}
  String(unsigned long v) : s(std::to_string(v)) {}
  String(float v, unsigned char dec = 2) { fmt((double)v, dec); }
  String(double v, unsigned char dec = 2) { fmt(v, dec); }
  String& operator+=(const String& o) { s += o.s; return *this; }
  String& operator+=(const char* c) { s += c; return *this; }
  String& operator+=(char c) { s += c; return *this; }
  bool operator==(const String& o) const { return s == o.s; }
  bool operator==(const char* c) const { return s == c; }
  bool operator!=(const String& o) const { return s != o.s; }
  const char* c_str() const { return s.c_str(); }
  unsigned int length() const { return (unsigned int)s.size(); }
  int indexOf(const char* c) const { auto p = s.find(c); return p == std::string::npos ? -1 : (int)p; }
  friend String operator+(const String& a, const String& b) { return String(a.s + b.s); }
  friend String operator+(const char* a, const String& b) { return String(std::string(a) + b.s); }
  friend String operator+(const String& a, const char* b) { return String(a.s + b); }

 private:
  void fmt(double v, unsigned char dec) {
    char b[64];
    snprintf(b, sizeof b, "%*.*f", dec + 2, (int)dec, v);  // dtostrf(v, dec+2, dec)
    s = b;
  }
};

class IPAddress {
 public:
  String toString() const { return String("127.0.0.1"); }
};

class HardwareSerial {
 public:
  void begin(unsigned long) {}
  void print(const char* c);
  void print(const String& v) { print(v.c_str()); }
  void print(int v) { print(String(v)); }
  void print(float v) { print(String(v)); }
  void print(double v) { print(String(v)); }
  void print(const IPAddress& ip) { print(ip.toString()); }
  template <typename T> void println(const T& v) { print(v); print("\n"); }
  void println() { print("\n"); }
  int printf(const char* fmt, ...);
};
extern HardwareSerial Serial;

void pinMode(int pin, int mode);
void digitalWrite(int pin, int level);
int analogRead(int pin);
void delay(unsigned long ms);
unsigned long millis();

// ---- FIL control surface (used by main.cpp, not by the sketch) ----
namespace fil {
void emit(const char* fmt, ...);
void set_adc(int pin, int raw);
void set_millis(unsigned long ms);
void set_wifi(bool up);
bool wifi_up();
void flush_serial();
}  // namespace fil
