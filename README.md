# 🌞 Digital Twin Renewable Energy Solar Farm

## 📘 Overview
The **Digital Twin Renewable Energy Solar Farm** is an IoT-based smart monitoring system designed to simulate and track the performance of solar panels in real-time. This project uses sensors connected to a microcontroller to measure voltage, current, and efficiency of solar panels, and mirrors the physical system’s behavior through a **Digital Twin dashboard**.

---

## ⚙️ Key Features

- **🔋 Real-Time Energy Monitoring**
  - Track individual solar panels' voltage and current.
  - Combine data from panels arranged in parallel and series configurations.

- **☁️ Blynk Cloud Dashboard**
  - Visualize live data such as voltage, current, and performance efficiency.
  - Get alerts for underperforming panels.

- **🌐 Local IP Web UI**
  - Access live panel data locally via ESP32/ESP8266 IP.
  - Simple and clean web interface for quick diagnostics.

- **📊 Digital Twin Visualization**
  - Mirror the physical solar farm's performance virtually.
  - Simulate operational conditions and system response.

---

## 🧠 System Architecture

**Components Used**
- ESP32 / ESP8266 microcontroller  
- 4 Solar Panels (6.9V each)  
- Voltage & Current Sensors (ACS712)  
- LED Indicators (Panel Status)  
- Blynk IoT Platform for Cloud Integration  
- HTML Web Interface for Local Access  

**Panel Configuration**
| Panels | Type | Connection | Description |
| ------- | ---- | ----------- | ------------ |
| A & B | Voltage Panels | Parallel | Combined voltage monitoring |
| C & D | Current Panels | Series | Current measurement and flow control |

---

## 🎥 Demonstration Videos

| Feature | Video File | Description |
| -------- | ----------- | ----------- |
| 🌤️ **Full Project Demo** | [`Digital Twin Solar Farm.mp4`](./Digital%20Twin%20Solar%20Farm.mp4) | Complete overview of the system, including sensors, dashboard, and monitoring. |
| ☁️ **Blynk Cloud Dashboard** | [`BLYNK.mov`](./BLYNK.mov) | Live visualization of solar panel performance through Blynk IoT Cloud. |
| 🌐 **Local IP Dashboard** | [`IP Web UI.mp4`](./IP%20Web%20UI.mp4) | Demonstration of the local ESP-based web monitoring interface. |
| 🧠 **Digital Twin Dashboard** | [`Solar Farm Dashboard.mp4`](./Solar%20Farm%20Dashboard.mp4) | Shows the digital twin’s visualization and real-time analytics. |

> 💡 You can click the video filenames above once uploaded to your GitHub repo to watch them directly in the browser.

---

## 🧩 How It Works

1. **Data Collection:**  
   Sensors measure voltage and current from panels A–D.
   
2. **Processing & Transmission:**  
   The ESP32 processes readings and sends data to:
   - **Blynk Cloud (Remote Monitoring)**
   - **Local Web UI (Real-Time Local Access)**

3. **Digital Twin Simulation:**  
   The web dashboard reflects the actual system’s performance dynamically, enabling predictive insights.

---

## 🚀 Setup Instructions

1. **Upload Code:**  
   Flash the `Solar_Farm.ino` file to your ESP32/ESP8266 using the Arduino IDE.

2. **Update Blynk Credentials:**  
   Replace the following in your code:
   ```cpp
   #define BLYNK_TEMPLATE_ID "Your_Template_ID"
   #define BLYNK_AUTH_TOKEN "Your_Auth_Token"
