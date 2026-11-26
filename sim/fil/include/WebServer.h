#pragma once
#include <map>
#include <vector>

#include "Arduino.h"

class WebServer {
 public:
  explicit WebServer(int port = 80) : port_(port) {}
  void on(const char* uri, std::function<void()> handler) { routes_[uri] = handler; }
  void begin() {}
  void handleClient();
  void sendHeader(const String& name, const String& value, bool first = false) {
    (void)first;
    headers_.push_back({name.s, value.s});
  }
  void send(int code, const char* content_type, const String& body);
  void send(int code, const String& content_type, const String& body) {
    send(code, content_type.c_str(), body);
  }
  void send(int code) { send(code, "text/plain", String("")); }
  String uri() const { return String(pending_); }

  // FIL control: queue a request to be served by the next handleClient().
  static void queue_request(const std::string& uri);

 private:
  int port_;
  std::map<std::string, std::function<void()>> routes_;
  std::vector<std::pair<std::string, std::string>> headers_;
  std::string pending_;
};
