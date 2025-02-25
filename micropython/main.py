import network
import time
import machine
import ssd1306
import dht
from machine import Pin, I2C, PWM, ADC
from umqtt.simple import MQTTClient
import config

import ujson
import random
import urequests  # for making http requests to our flask api

# wifi settings
SSID = config.SSID
PASSWORD = config.PASSWORD

# ubidots mqtt settings
TOKEN = config.TOKEN
DEVICE = "sensorverse-32"
MQTT_CLIENT_ID = f"esp32glitchhunters"
MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_PORT = 1883
MQTT_USER = TOKEN
MQTT_PASSWORD = ""
MQTT_TOPIC_PUB = f"/v2.0/devices/{DEVICE}"

# flask mongodb api settings
FLASK_API_URL = config.FLASK_API_URL
API_KEY = config.API_KEY

# pin setup
# sensors
dht1_pin = Pin(4)
dht2_pin = Pin(15)
dht1 = dht.DHT11(dht1_pin)
dht2 = dht.DHT11(dht2_pin)

trig_pin = Pin(27, Pin.OUT)
echo_pin = Pin(14, Pin.IN)

pir_pin = Pin(33, Pin.IN)

ldr_pin = ADC(Pin(32))
ldr_pin.atten(ADC.ATTN_11DB)  # full voltage range (0-3.3v)

# actuators
servo = PWM(Pin(25), freq=50)
relay = Pin(23, Pin.OUT)
buzzer = PWM(Pin(26), freq=1000, duty=0)

rgb_red = PWM(Pin(19), freq=1000, duty=0)
rgb_green = PWM(Pin(18), freq=1000, duty=0)
rgb_blue = PWM(Pin(5), freq=1000, duty=0)

# oled display
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# built-in led for status indication
led = Pin(2, Pin.OUT)

# global mqtt client
mqtt_client = None

# global variables to store sensor readings
sensor_data = {
    "DHT-1-Temp": 0,
    "DHT-1-Humid": 0,
    "DHT-2-Temp": 0,
    "DHT-2-Humid": 0,
    "Ultrasonic-Distance": 0,
    "Pir-Motion": 0,
    "LDR-Intensity": 0
}

# global variables to track actuator states
actuator_states = {
    "servo-angle": 90,
    "relay": 0,
    "buzzer": 0,
    "rgb-red": 0,
    "rgb-green": 0,
    "rgb-blue": 0
}

# oled display screen control
current_screen = 0
screen_change_time = time.time()

# connect to wifi network
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    
    print("Connecting to WiFi...", end="")
    oled.fill(0)
    oled.text("Connecting to", 0, 0)
    oled.text("WiFi...", 0, 10)
    oled.show()
    
    timeout = 0
    while not wlan.isconnected() and timeout < 20:
        print(".", end="")
        time.sleep(1)
        timeout += 1
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"\nWiFi Connected: {ip}")
        oled.fill(0)
        oled.text("WiFi Connected", 0, 0)
        oled.text(ip, 0, 10)
        oled.show()
        time.sleep(2)
        return True
    else:
        print("\nWiFi Connection Failed")
        oled.fill(0)
        oled.text("WiFi Connection", 0, 0)
        oled.text("Failed!", 0, 10)
        oled.show()
        time.sleep(2)
        return False

# make sure wifi is still connected
def check_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print("⚠️ wifi disconnected! trying to reconnect...")
        return connect_wifi()
    return True

# handle incoming mqtt messages
def mqtt_callback(topic, msg):
    global actuator_states
    try:
        topic_str = topic.decode('utf-8')
        msg_str = msg.decode('utf-8')
        print(f"📥 received mqtt: {topic_str} - {msg_str}")
        
        # parse commands - works with both v1.6 and v2.0 topic formats
        topic_parts = topic_str.split('/')
        
        # extract actuator name from topic
        if len(topic_parts) >= 5 and topic_parts[-1] == "lv":
            # find actuator name - it's the second-to-last part in the topic
            actuator_name = topic_parts[-2]
            
            # convert message to float then to appropriate value
            try:
                value = float(msg_str)
                
                print(f"⚡ processing actuator: {actuator_name} with value: {value}")
                
                if actuator_name == "servo-angle":
                    actuator_states["servo-angle"] = int(value)
                    update_servo(int(value))
                    print(f"✅ servo updated to {int(value)} degrees")
                    
                elif actuator_name == "relay":
                    relay_value = 1 if value >= 0.5 else 0
                    actuator_states["relay"] = relay_value
                    update_relay(relay_value)
                    print(f"✅ relay updated to {relay_value}")
                    
                elif actuator_name == "buzzer":
                    buzzer_value = int(value)
                    actuator_states["buzzer"] = buzzer_value
                    update_buzzer(buzzer_value)
                    print(f"✅ buzzer updated to {buzzer_value}%")
                    
                elif actuator_name == "rgb-red":
                    rgb_value = int(value)
                    actuator_states["rgb-red"] = rgb_value
                    update_rgb()
                    print(f"✅ rgb red updated to {rgb_value}")
                    
                elif actuator_name == "rgb-green":
                    rgb_value = int(value)
                    actuator_states["rgb-green"] = rgb_value
                    update_rgb()
                    print(f"✅ rgb green updated to {rgb_value}")
                    
                elif actuator_name == "rgb-blue":
                    rgb_value = int(value)
                    actuator_states["rgb-blue"] = rgb_value
                    update_rgb()
                    print(f"✅ rgb blue updated to {rgb_value}")
                
                # update oled immediately to show the change
                update_oled()
                
            except ValueError as e:
                print(f"❌ couldn't convert message to number: {e}")
                
    except Exception as e:
        print(f"❌ error in mqtt callback: {e}")

# connect to mqtt broker with error handling
def connect_mqtt():
    global mqtt_client
    
    oled.fill(0)
    oled.text("Connecting to", 0, 0)
    oled.text("MQTT broker...", 0, 10)
    oled.show()
    
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, keepalive=30)
        client.set_callback(mqtt_callback)
        client.connect()
        mqtt_client = client
        
        # subscribe to actuator topics - support both v1.6 and v2.0 formats
        actuator_names = ["servo-angle", "relay", "buzzer", "rgb-red", "rgb-green", "rgb-blue"]
        
        for name in actuator_names:
            # subscribe to v1.6 format
            topic_v1 = f"/v1.6/devices/{DEVICE}/{name}/lv"
            client.subscribe(topic_v1.encode())
            print(f"Subscribed to: {topic_v1}")
            
            # also subscribe to v2.0 format in case ubidots sends that
            topic_v2 = f"/v2.0/devices/{DEVICE}/{name}/lv"
            client.subscribe(topic_v2.encode())
            print(f"Subscribed to: {topic_v2}")

        print("✅ mqtt connected")
        oled.fill(0)
        oled.text("MQTT Connected", 0, 0)
        oled.show()
        time.sleep(1)

        return True
    except Exception as e:
        print(f"❌ mqtt connection error: {e}")
        oled.fill(0)
        oled.text("MQTT Error:", 0, 0)
        oled.text(str(e)[:16], 0, 15)
        oled.show()
        time.sleep(2)
        return False

# check if mqtt is still connected
def check_mqtt():
    global mqtt_client
    
    if mqtt_client is None:
        return connect_mqtt()
    
    try:
        # ping to check connection
        mqtt_client.ping()
        return True
    except:
        print("⚠️ mqtt disconnected! reconnecting...")
        try:
            mqtt_client.disconnect()
        except:
            pass
        mqtt_client = None
        return connect_mqtt()

# read dht11 temperature/humidity sensor
def read_dht(sensor):
    try:
        # dht11 needs at least 1 second between readings
        sensor.measure()
        # wait a bit for reliable reading
        time.sleep_ms(50)
        temp = sensor.temperature()
        hum = sensor.humidity()
        if temp == 0 and hum == 0:
            # dht11 sometimes returns 0,0 which is probably an error
            return None, None
        return temp, hum
    except OSError as e:
        print(f"DHT sensor error: {e}")
        return None, None

# measure distance with ultrasonic sensor
def measure_distance():
    try:
        # send trigger pulse
        trig_pin.off()
        time.sleep_us(2)
        trig_pin.on()
        time.sleep_us(10)
        trig_pin.off()
        
        # wait for echo with timeout (30ms)
        timeout_start = time.ticks_ms()
        while echo_pin.value() == 0:
            if time.ticks_diff(time.ticks_ms(), timeout_start) > 30:
                return -1
        
        start = time.ticks_us()
        
        # wait for echo to end with timeout (30ms)
        timeout_start = time.ticks_ms()
        while echo_pin.value() == 1:
            if time.ticks_diff(time.ticks_ms(), timeout_start) > 30:
                return -1
        
        end = time.ticks_us()
        
        # calculate distance in cm
        duration = time.ticks_diff(end, start)
        distance = (duration * 0.0343) / 2
        
        if distance < 0 or distance > 400:
            return -1
            
        return distance
    except Exception as e:
        print(f"ultrasonic error: {e}")
        return -1

# read all sensor values
def read_sensors():
    global sensor_data
    
    try:
        # read first temperature/humidity sensor
        temp1, hum1 = read_dht(dht1)
        if temp1 is not None and hum1 is not None:
            sensor_data["DHT-1-Temp"] = temp1
            sensor_data["DHT-1-Humid"] = hum1
        
        # wait before reading second dht sensor
        time.sleep_ms(1000)  # dht11 needs at least 1 second between readings
        
        # read second temperature/humidity sensor
        temp2, hum2 = read_dht(dht2)
        if temp2 is not None and hum2 is not None:
            sensor_data["DHT-2-Temp"] = temp2
            sensor_data["DHT-2-Humid"] = hum2
        
        # read distance sensor
        distance = measure_distance()
        if distance >= 0:
            sensor_data["Ultrasonic-Distance"] = distance
        
        # read motion sensor
        sensor_data["Pir-Motion"] = pir_pin.value()
        
        # read light sensor
        sensor_data["LDR-Intensity"] = ldr_pin.read()
        
        print("📊 sensor readings:")
        print(f"DHT1: {sensor_data['DHT-1-Temp']}°C, {sensor_data['DHT-1-Humid']}%")
        print(f"DHT2: {sensor_data['DHT-2-Temp']}°C, {sensor_data['DHT-2-Humid']}%")
        print(f"Distance: {sensor_data['Ultrasonic-Distance']:.1f} cm")
        print(f"Motion: {sensor_data['Pir-Motion']}")
        print(f"Light: {sensor_data['LDR-Intensity']}")
        
        return True
    except Exception as e:
        print(f"❌ error reading sensors: {e}")
        return False

# send sensor data to ubidots cloud
def send_to_ubidots():
    led.off()
    
    if not check_wifi() or not check_mqtt():
        return False
    
    try:
        # prepare json payload
        payload = ujson.dumps(sensor_data)
        
        oled.fill(0)
        oled.text("Sending data to", 0, 0)
        oled.text("Ubidots...", 0, 10)
        oled.show()
        
        # publish to ubidots
        mqtt_client.publish(MQTT_TOPIC_PUB, payload.encode())
        
        print("✅ data sent to ubidots via mqtt")
        led.on()  # turn on led to show successful send
        
        # show success message
        oled.fill(0)
        oled.text("Ubidots data", 0, 20)
        oled.text("sent!", 0, 30)
        oled.show()
        time.sleep(1)
        
        return True
    except Exception as e:
        print(f"❌ mqtt publish error: {e}")
        led.off()
        
        # show error message
        oled.fill(0)
        oled.text("Ubidots send", 0, 20)
        oled.text("failed!", 0, 30)
        oled.show()
        time.sleep(1)
        
        return False

# send sensor data to our flask api with mongodb backend
def send_to_mongodb_api():
    led.off()
    
    if not check_wifi():
        return False
    
    try:
        # prepare data for mongodb api
        # add timestamp and device info
        mongo_data = sensor_data.copy()
        mongo_data["device_id"] = DEVICE
        mongo_data["timestamp"] = time.time()
        
        # include actuator states in the data
        mongo_data["actuators"] = actuator_states
        
        payload = ujson.dumps(mongo_data)
        
        # show sending status
        oled.fill(0)
        oled.text("Sending data to", 0, 0)
        oled.text("MongoDB...", 0, 10)
        oled.show()
        
        # set headers with api key
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY
        }
        
        # send http post request to flask api
        try:
            response = urequests.post(
                FLASK_API_URL,
                data=payload,
                headers=headers
            )
            
            # try to get response content
            try:
                response_text = response.text()  # try as method first
            except TypeError:
                try:
                    response_text = response.text  # try as property
                except:
                    response_text = "No response text available"
            
            # figure out if request was successful
            success = False
            try:
                # different versions of urequests have different attributes
                if hasattr(response, 'status_code'):
                    success = 200 <= response.status_code < 300
                elif hasattr(response, 'status'):
                    success = 200 <= response.status < 300
                else:
                    # if we can't check status, assume it worked
                    success = True
            except:
                # if any error occurs, assume it failed
                success = False
            
            if success:
                print(f"✅ data sent to mongodb api: {response_text}")
                led.on()  # turn on led to show successful send
                
                # show success message
                oled.fill(0)
                oled.text("MongoDB data", 0, 20)
                oled.text("sent!", 0, 30)
                oled.show()
                time.sleep(1)
                
                try:
                    response.close()
                except:
                    pass
                return True
            else:
                print(f"❌ mongodb api error: {response_text}")
                
                # show error message
                oled.fill(0)
                oled.text("MongoDB error:", 0, 20)
                oled.text(str(response_text)[:16], 0, 30)  # truncate to fit screen
                oled.show()
                time.sleep(1)
                
                try:
                    response.close()
                except:
                    pass
                return False
        
        except Exception as e:
            print(f"❌ request error: {e}")
            
            # show error message
            oled.fill(0)
            oled.text("Request error:", 0, 20)
            oled.text(str(e)[:16], 0, 30)  # truncate to fit screen
            oled.show()
            time.sleep(1)
            
            return False
            
    except Exception as e:
        print(f"❌ mongodb api error: {e}")
        led.off()
        
        # show error message
        oled.fill(0)
        oled.text("MongoDB error:", 0, 20)
        oled.text(str(e)[:16], 0, 30)  # truncate to fit screen
        oled.show()
        time.sleep(1)
        
        return False

# control servo motor position
def update_servo(angle):
    try:
        # make sure angle is in valid range
        angle = max(0, min(180, angle))
        
        # convert angle to pwm duty cycle (50hz pwm)
        # most servos: 0° = 0.5ms pulse, 180° = 2.5ms pulse
        # at 50hz, period = 20ms
        
        # for esp32 with 10-bit resolution (0-1023)
        min_duty = 26   # 0.5ms/20ms * 1023 ≈ 26
        max_duty = 123  # 2.5ms/20ms * 1023 ≈ 123
        
        duty = min_duty + int((angle / 180) * (max_duty - min_duty))
        servo.duty(duty)
        
        print(f"🔄 servo angle set to {angle}° (duty={duty})")
    except Exception as e:
        print(f"❌ servo error: {e}")

# control relay on/off
def update_relay(status):
    try:
        relay.value(1 if status == 1 else 0)
        print(f"🔄 relay set to {status}")
    except Exception as e:
        print(f"❌ relay error: {e}")

# control buzzer volume/tone
def update_buzzer(value):
    try:
        # make sure value is between 0-100
        value = max(0, min(100, value))
        
        if value > 0:
            # convert 1-100 to duty 0-1023
            duty = int((value / 100) * 1023)
            buzzer.freq(1000)  # 1khz tone
            buzzer.duty(duty)
            print(f"🔄 buzzer set to {value}% (duty={duty})")
        else:
            buzzer.duty(0)  # turn off
            print("🔄 buzzer turned off")
    except Exception as e:
        print(f"❌ buzzer error: {e}")

# update rgb led color
def update_rgb():
    try:
        # get rgb values from state (0-255 range)
        r = max(0, min(255, actuator_states["rgb-red"]))
        g = max(0, min(255, actuator_states["rgb-green"]))
        b = max(0, min(255, actuator_states["rgb-blue"]))
        
        # convert rgb values (0-255) to pwm duty (0-1023)
        r_duty = int((r / 255) * 1023)
        g_duty = int((g / 255) * 1023)
        b_duty = int((b / 255) * 1023)
        
        # set pwm values
        rgb_red.duty(r_duty)
        rgb_green.duty(g_duty)
        rgb_blue.duty(b_duty)
        
        print(f"🔄 rgb led set to r:{r} g:{g} b:{b} (duties: {r_duty},{g_duty},{b_duty})")
    except Exception as e:
        print(f"❌ rgb led error: {e}")

# update info on the oled display
def update_oled():
    global current_screen, screen_change_time
    
    try:
        # rotate through screens every 3 seconds
        if time.time() - screen_change_time > 3:
            current_screen = (current_screen + 1) % 4  # 4 different screens
            screen_change_time = time.time()
        
        oled.fill(0)
        
        if current_screen == 0:
            # temperature and humidity screen
            oled.text("Temperature & Humidity", 0, 0)
            oled.text(f"DHT1: {sensor_data['DHT-1-Temp']}C", 0, 15)
            oled.text(f"      {sensor_data['DHT-1-Humid']}%", 0, 25)
            oled.text(f"DHT2: {sensor_data['DHT-2-Temp']}C", 0, 40)
            oled.text(f"      {sensor_data['DHT-2-Humid']}%", 0, 50)
        
        elif current_screen == 1:
            # distance, motion and light screen
            oled.text("Distance & Motion", 0, 0)
            oled.text(f"Dist: {sensor_data['Ultrasonic-Distance']:.1f} cm", 0, 15)
            oled.text(f"Motion: {'YES' if sensor_data['Pir-Motion'] else 'NO'}", 0, 30)
            oled.text(f"Light: {sensor_data['LDR-Intensity']}", 0, 45)
        
        elif current_screen == 2:
            # actuator status screen
            oled.text("Actuator States", 0, 0)
            oled.text(f"Servo: {actuator_states['servo-angle']}deg", 0, 15)
            oled.text(f"Relay: {'ON' if actuator_states['relay'] else 'OFF'}", 0, 25)
            oled.text(f"Buzzer: {actuator_states['buzzer']}%", 0, 35)
            oled.text(f"RGB: {actuator_states['rgb-red']},", 0, 45)
            oled.text(f"{actuator_states['rgb-green']},{actuator_states['rgb-blue']}", 0, 55)
        
        elif current_screen == 3:
            # connection status screen
            oled.text("Connection Status", 0, 0)
            wlan = network.WLAN(network.STA_IF)
            oled.text(f"WiFi: {'OK' if wlan.isconnected() else 'NO'}", 0, 15)
            oled.text(f"MQTT: {'OK' if mqtt_client else 'NO'}", 0, 25)
            oled.text(f"MongoDB: API", 0, 35)
            oled.text(f"Device: {DEVICE}", 0, 45)
        
        oled.show()
    except Exception as e:
        print(f"❌ oled error: {e}")

# check for new mqtt messages
def check_mqtt_messages():
    global mqtt_client
    
    if mqtt_client is not None:
        try:
            mqtt_client.check_msg()
        except Exception as e:
            print(f"❌ error checking mqtt messages: {e}")
            # try to reconnect on error
            mqtt_client = None
            connect_mqtt()
    
# main program loop
def main():
    # set actuators to default values
    update_servo(90)
    update_relay(0)
    update_buzzer(0)
    update_rgb()
    
    # show startup message
    oled.fill(0)
    oled.text("Sensorverse", 20, 10)
    oled.text("Starting...", 25, 30)
    oled.show()
    time.sleep(2)
    
    # connect to wifi - keep trying until successful
    if not connect_wifi():
        while True:
            if connect_wifi():
                break
            time.sleep(10)
    
    # connect to mqtt - keep trying until successful
    if not connect_mqtt():
        while True:
            if connect_mqtt():
                break
            time.sleep(10)
    
    # startup beep to show we're ready
    buzzer.duty(512)
    time.sleep(0.2)
    buzzer.duty(0)
    
    last_sensor_read = 0
    last_ubidots_send = 0
    last_mongodb_send = 0  # timer for mongodb api
    
    while True:
        try:
            current_time = time.time()
            
            # make sure connections are still active
            if not check_wifi() or not check_mqtt():
                time.sleep(5)
                continue
            
            # check for incoming control messages frequently
            check_mqtt_messages()
            
            # read sensors every 2 seconds
            if current_time - last_sensor_read >= 2:
                if read_sensors():
                    last_sensor_read = current_time
            
            # send data to ubidots every 10 seconds
            if current_time - last_ubidots_send >= 10:
                if send_to_ubidots():
                    last_ubidots_send = current_time
            
            # send data to mongodb every 60 seconds
            if current_time - last_mongodb_send >= 60:
                if send_to_mongodb_api():
                    last_mongodb_send = current_time
            
            # update display
            update_oled()
            
            # small delay to prevent hogging cpu
            time.sleep(0.1)
            
        except Exception as e:
            print(f"main loop error: {e}")
            oled.fill(0)
            oled.text("Error:", 0, 0)
            error_msg = str(e)
            # split message to fit on tiny screen
            for i in range(0, min(len(error_msg), 48), 16):
                oled.text(error_msg[i:i+16], 0, 15 + i//16*10)
            oled.show()
            time.sleep(5)

# start program with error handling
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("program terminated by user")
    except Exception as e:
        print(f"fatal error: {e}")
        oled.fill(0)
        oled.text("Fatal Error:", 0, 0)
        error_msg = str(e)
        # split error message to fit on screen
        for i in range(0, min(len(error_msg), 48), 16):
            oled.text(error_msg[i:i+16], 0, 15 + i//16*10)
        oled.show()
        
        # try to disconnect mqtt cleanly
        if mqtt_client is not None:
            try:
                mqtt_client.disconnect()
            except:
                pass
