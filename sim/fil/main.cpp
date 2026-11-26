// FIL driver loop: line-oriented command protocol on stdin, events on stdout.
//   ADC <pin> <raw>   set the value analogRead(pin) returns
//   TIME <ms>         set millis()
//   WIFI <0|1>        Wi-Fi link state seen by WiFi.status()/Blynk
//   SETUP             call the sketch's setup()
//   LOOP              call the sketch's loop() once
//   GET <uri>         queue an HTTP GET, then call loop() once (served by handleClient)
// Every command is answered by its events followed by a line "END".
#include <iostream>
#include <sstream>
#include <string>

#include "Arduino.h"
#include "WebServer.h"

void setup();
void loop();

int main() {
  std::ios::sync_with_stdio(true);
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string cmd;
    in >> cmd;
    if (cmd == "ADC") {
      int pin, raw;
      in >> pin >> raw;
      fil::set_adc(pin, raw);
    } else if (cmd == "TIME") {
      unsigned long ms;
      in >> ms;
      fil::set_millis(ms);
    } else if (cmd == "WIFI") {
      int up;
      in >> up;
      fil::set_wifi(up != 0);
    } else if (cmd == "SETUP") {
      setup();
    } else if (cmd == "LOOP") {
      loop();
    } else if (cmd == "GET") {
      std::string uri;
      in >> uri;
      WebServer::queue_request(uri);
      loop();
    } else if (cmd == "QUIT") {
      break;
    } else if (!cmd.empty()) {
      fil::emit("ERROR\tunknown command %s\n", cmd.c_str());
    }
    fil::emit("END\n");
    fflush(stdout);
  }
  return 0;
}
