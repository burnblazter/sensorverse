# Sensorverse 🌐  

A Smart IoT Sensor Network Project developed for **Samsung Innovation Campus Batch 6**  

## Overview 📊  

Sensorverse is an **IoT-powered sensor network** designed to collect and visualize environmental data using **ESP32, MongoDB, and Ubidots**. This project integrates multiple sensors and actuators, enabling real-time monitoring and control through cloud-based dashboards and APIs.  

## Features ⚡  

✅ **Comprehensive Sensor Network:**  
- 2x **DHT11** (Temperature & Humidity)  
- **HC-SR04** (Ultrasonic Distance Sensor)  
- **PIR Motion Sensor**  
- **LDR** (Light Intensity Sensor)  

✅ **Actuator Control:**  
- **Servo Motor** (Adjustable via API)  
- **Relay Module** (On/Off switching)  
- **RGB LED** (PWM-based color control)  
- **Buzzer** (Tone and alert system)  

✅ **Data Visualization & Storage:**  
- **Ubidots Dashboard** for real-time monitoring  
- **MongoDB** for historical data storage  
- **SSD1306 OLED Display** for local feedback  

✅ **Seamless API & Cloud Integration:**  
- **RESTful API** for data retrieval & control  
- **MQTT** for efficient IoT communication  
- **Secure HTTP Transmission**  

## Hardware Requirements 🔧  

- **ESP32** Development Board  
- **DHT11** Temperature & Humidity Sensors (2x)  
- **HC-SR04** Ultrasonic Sensor  
- **PIR Motion Sensor**  
- **LDR** (Light Dependent Resistor)  
- **SSD1306 OLED Display**  
- **Servo Motor**  
- **Relay Module**  
- **RGB LED**  
- **Buzzer**  
- **Breadboard & Jumper Wires**  

## Software Stack 💻  

**Microcontroller:**  
- **MicroPython** for ESP32  
- **MQTT & HTTP** for IoT communication  
- **Network Management**  

**Backend:**  
- **Express.js** for API  
- **MongoDB Atlas** for database  
- **RESTful API**  

**Cloud Services:**  
- **Ubidots IoT Platform** ([Live Dashboard](#ubidots-dashboard-🌍))  

## Installation & Setup 🛠️  

### 1️⃣ Hardware Setup  
- Connect all sensors and actuators to the **ESP32** following the wiring diagram.  
- Flash **MicroPython firmware** to ESP32.  
- Upload `main.py` to ESP32.  

### 2️⃣ Backend Setup  
```bash
git clone https://github.com/burnblazter/sensorverse.git
cd sensorverse
npm install
node server.js
```

### 3️⃣ Environment Configuration  
- Set up **MongoDB Atlas** for data storage.  
- Configure **Ubidots** for real-time monitoring.  
- Update credentials in the config file (`config.json`).  

## API Endpoints 🌐  

| Method | Endpoint                | Description |
|--------|-------------------------|-------------|
| **POST** | `/api/sensors` | Submit new sensor data |
| **GET**  | `/api/sensors` | Retrieve all sensor data |
| **GET**  | `/api/sensors/latest` | Get the latest sensor readings |
| **GET**  | `/api/health` | API health check |

## Ubidots Dashboard 🌍  

🔗 **Live Dashboard:** [View Sensor Data](https://stem.ubidots.com/app/dashboards/public/dashboard/M4-PHEVR1xYkPgXzGMQZlqk181G9xCaK1XlsggFJXzI?navbar=true&contextbar=true&datePicker=true&devicePicker=true&displayTitle=true)  

📸 **Dashboard Preview:**  
![Ubidots Dashboard](https://i.postimg.cc/fy0cRZPK/chrome-T422d-Hhj7p.png)  

## Contributors 🏆  
Glitch Hunters
👨‍💻 **Fael @burnblazter** (Lead Developer)  
👨‍💻 **Khanza @khanzaarezi**  
👨‍💻 **Cania @canai23**  
👨‍💻 **Vincent @vincentnc** 

## Learning Outcomes 📚  

Through this project, we gained experience in:  
✅ **IoT sensor integration** and real-time data collection  
✅ **MicroPython & ESP32** firmware development  
✅ **Cloud data storage** with **MongoDB Atlas**  
✅ **API development** using **Express.js**  
✅ **Network communication** via **MQTT & HTTP**  
✅ **Error handling & system reliability**  

## License 📝  

This project is licensed under the **MIT License** – see [LICENSE.md](LICENSE) for details.  

## Acknowledgments 🙏  

A big thank you to:  
- **Samsung Innovation Campus** for this opportunity  
- Our **mentors & instructors** for their guidance  
- The **open-source community** for valuable resources  


---  

🚀 **Made with ❤️ for Samsung Innovation Campus Batch 6** 🚀
