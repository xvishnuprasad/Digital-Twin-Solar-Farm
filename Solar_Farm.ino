/***************************************************
 * Smart Energy Panel Monitor (6.9V Solar Panels)
 * Panels: A,B,C Voltage, D Current
 * LED: AB combined, C only
 ***************************************************/

#define BLYNK_TEMPLATE_ID ""
#define BLYNK_TEMPLATE_NAME "Solar Farm"
#define BLYNK_AUTH_TOKEN ""

#include <WiFi.h>
#include <WebServer.h>
#include <BlynkSimpleEsp32.h>

// Wi-Fi
char ssid[] = "Vishnu's24";
char pass[] = "223334444";

// Pins
#define VOLTAGE_A 34
#define VOLTAGE_B 35
#define VOLTAGE_C 32
#define CURRENT_D 33

#define RED_AB 14
#define YELLOW_AB 12
#define GREEN_AB 13

#define RED_CD 25
#define YELLOW_CD 26
#define GREEN_CD 27

BlynkTimer timer;
WebServer server(80);

// ---------------- Voltage & Current Reading ----------------
float readVoltage(int pin) {
  int raw = analogRead(pin);
  float voltage = (raw / 4095.0) * 10.0; // 6.9V panels, sensorMax 10V
  return voltage;
}

float readCurrent(int pin) {
  int raw = analogRead(pin);
  float voltage = (raw / 4095.0) * 5.0;
  float current = (voltage - 2.5) / 0.185; // ACS712 5A
  if(current < 0) current = 0; // ignore small negatives
  return current;
}

// ---------------- LED Control ----------------
String statusAB, statusC;

void updateLEDs(float voltageA, float voltageB, float voltageC) {
  // AB Combined
  float combinedAB = (voltageA + voltageB) / 2.0;
  if(combinedAB <= 1.0){
    digitalWrite(RED_AB,HIGH); digitalWrite(YELLOW_AB,LOW); digitalWrite(GREEN_AB,LOW);
    statusAB = "RED: No Voltage";
  } else if(combinedAB < 5.0){
    digitalWrite(RED_AB,LOW); digitalWrite(YELLOW_AB,HIGH); digitalWrite(GREEN_AB,LOW);
    statusAB = "YELLOW: Low Voltage";
  } else {
    digitalWrite(RED_AB,LOW); digitalWrite(YELLOW_AB,LOW); digitalWrite(GREEN_AB,HIGH);
    statusAB = "GREEN: Normal";
  }

  // C Only
  if(voltageC <= 1.0){
    digitalWrite(RED_CD,HIGH); digitalWrite(YELLOW_CD,LOW); digitalWrite(GREEN_CD,LOW);
    statusC = "RED: No Voltage";
  } else if(voltageC < 5.0){
    digitalWrite(RED_CD,LOW); digitalWrite(YELLOW_CD,HIGH); digitalWrite(GREEN_CD,LOW);
    statusC = "YELLOW: Low Voltage";
  } else {
    digitalWrite(RED_CD,LOW); digitalWrite(YELLOW_CD,LOW); digitalWrite(GREEN_CD,HIGH);
    statusC = "GREEN: Normal";
  }
}

// ---------------- Send Data ----------------
void sendData() {
  float voltageA = readVoltage(VOLTAGE_A);
  float voltageB = readVoltage(VOLTAGE_B);
  float voltageC = readVoltage(VOLTAGE_C);
  float currentD = readCurrent(CURRENT_D);

  Blynk.virtualWrite(V0, voltageA);
  Blynk.virtualWrite(V1, voltageB);
  Blynk.virtualWrite(V2, voltageC);
  Blynk.virtualWrite(V3, currentD);

  updateLEDs(voltageA, voltageB, voltageC);

  Blynk.virtualWrite(V4, statusAB);
  Blynk.virtualWrite(V5, statusC);

  Serial.printf("A: %.2f V | B: %.2f V | C: %.2f V | D Current: %.2f A\n", voltageA, voltageB, voltageC, currentD);
}

// ---------------- API ----------------
void handleAPI(){
  float voltageA = readVoltage(VOLTAGE_A);
  float voltageB = readVoltage(VOLTAGE_B);
  float voltageC = readVoltage(VOLTAGE_C);
  float currentD = readCurrent(CURRENT_D);

  String json = "{";
  json += "\"PanelA_Voltage\":" + String(voltageA,2) + ",";
  json += "\"PanelB_Voltage\":" + String(voltageB,2) + ",";
  json += "\"PanelC_Voltage\":" + String(voltageC,2) + ",";
  json += "\"PanelD_Current\":" + String(currentD,2) + ",";
  json += "\"Status_PanelAB\":\"" + statusAB + "\",";
  json += "\"Status_PanelC\":\"" + statusC + "\"";
  json += "}";

  server.send(200,"application/json",json);
}

// ---------------- Setup ----------------
void setup() {
  Serial.begin(115200);

  pinMode(RED_AB,OUTPUT); pinMode(YELLOW_AB,OUTPUT); pinMode(GREEN_AB,OUTPUT);
  pinMode(RED_CD,OUTPUT); pinMode(YELLOW_CD,OUTPUT); pinMode(GREEN_CD,OUTPUT);

  WiFi.begin(ssid,pass);
  Serial.print("Connecting WiFi");
  while(WiFi.status()!=WL_CONNECTED){delay(500); Serial.print(".");}
  Serial.println("\nWi-Fi Connected! IP: "); Serial.println(WiFi.localIP());

  Blynk.begin(BLYNK_AUTH_TOKEN,ssid,pass);

  server.on("/api",handleAPI);
  server.begin();
  Serial.println("API Ready");

  timer.setInterval(2000L, sendData);
}

// ---------------- Loop ----------------
void loop(){
  Blynk.run();
  timer.run();
  server.handleClient();
}

