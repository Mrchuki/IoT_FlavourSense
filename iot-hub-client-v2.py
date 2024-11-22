# SCRIPT PARA QUE LA RASPBERRYPI MANDE LAS MEDIDAS A AZURE. Tenemos la selección de productos y la detección de mucho ruido con el joystick, la temperatura
# y los niveles de luz simulados con el sensor de humedad (solo 2 rangos: poca y mucha luz).
# Además, este script escucha comandos desde Azure IoT Hub y actúa según las condiciones:
# - CUANDO LA TEMPERATURA SEA MUY ALTA & WHITE WINE, ENCENDEMOS EL VENTILADOR Y UN LED BLANCO
# - CUANDO LA TEMPERATURA SEA MUY BAJA & RED WINE, ENCENDEMOS EL VENTILADOR Y UN LED ROJO (AIRE CALIENTE)
# - CUANDO LA TEMPERATURA SEA INTERMEDIA & ROSÉ WINE, ENCENDEMOS EL VENTILADOR Y UN LED ROSA QUE INDICA TEMPERATURA IDEAL
# - También se reproducirá música según el tipo de vino seleccionado.

import json
import sys
import time
from sense_hat import SenseHat
from azure.iot.device import IoTHubDeviceClient, Message
import RPi.GPIO as GPIO

# Azure IoT Hub Connection String
AUX_CONNECTION_STRING = sys.argv[1]

# Initialize SenseHat
sense = SenseHat()

# GPIO Setup
GPIO.setmode(GPIO.BCM)
LED_WHITE = 17
LED_RED = 27
LED_PINK = 22
FAN = 23

GPIO.setup(LED_WHITE, GPIO.OUT)
GPIO.setup(LED_RED, GPIO.OUT)
GPIO.setup(LED_PINK, GPIO.OUT)
GPIO.setup(FAN, GPIO.OUT)

# SENSOR DATA STRUCTURE
sensor_data = {}

# MAP JOYSTICK INPUT TO WINE TYPE
WINE_SELECTION = {
    "up": "Red Wine",
    "down": "White Wine",
    "right": "Rosé Wine"
}

# METHODS TO GET SENSOR VALUES
def get_sensor_temperature():
    temperature = sense.get_temperature()
    return round(temperature, 2)

def get_sensor_light():
    # Simulate light levels using humidity sensor with two ranges
    humidity = sense.get_humidity()
    return "Low Light" if humidity < 50 else "High Light"

def get_sensor_joystick():
    # Interpret joystick direction
    for event in sense.stick.get_events():
        if event.action == "pressed":
            if event.direction in WINE_SELECTION:
                return WINE_SELECTION[event.direction]
            elif event.direction == "left":
                return "Noise Detected"
    return "No Selection"

# VALIDATE CONNECTION STRING
def aux_validate_connection_string():
    if not AUX_CONNECTION_STRING.startswith('HostName='):
        print("ERROR - YOUR IoT HUB CONNECTION STRING IS NOT VALID")
        print("FORMAT - HostName=your_iot_hub_name.azure-devices.net;DeviceId=your_device_name;SharedAccessKey=your_shared_access_key")
        sys.exit()

# INITIALIZE CLIENT
def aux_iothub_client_init():
    client = IoTHubDeviceClient.create_from_connection_string(AUX_CONNECTION_STRING)
    return client

# HANDLE INCOMING COMMANDS
def handle_command(client):
    while True:
        # Receive messages from Azure
        message = client.receive_message()  # Blocking call
        print("Message received:")
        print(message.data)
        payload = json.loads(message.data)

        # Get the temperature and wine type from the message
        temperature = payload.get("temperature", None)
        wine_type = payload.get("wine_type", None)

        # Perform actions based on conditions
        if temperature and wine_type:
            if temperature > 30 and wine_type == "White Wine":
                GPIO.output(LED_WHITE, GPIO.HIGH)
                GPIO.output(FAN, GPIO.HIGH)
                print("Condition: High temperature & White Wine - LED White & Fan ON")
                print("Playing: What a Wonderful World - Louis Armstrong")

            elif temperature < 15 and wine_type == "Red Wine":
                GPIO.output(LED_RED, GPIO.HIGH)
                GPIO.output(FAN, GPIO.HIGH)
                print("Condition: Low temperature & Red Wine - LED Red & Fan ON")
                print("Playing: At Last - Etta James")

            elif 15 <= temperature <= 30 and wine_type == "Rosé Wine":
                GPIO.output(LED_PINK, GPIO.HIGH)
                GPIO.output(FAN, GPIO.HIGH)
                print("Condition: Intermediate temperature & Rosé Wine - LED Pink & Fan ON")
                print("Playing: Blinding Lights - The Weeknd")

        # Reset outputs if no condition matches
        else:
            GPIO.output(LED_WHITE, GPIO.LOW)
            GPIO.output(LED_RED, GPIO.LOW)
            GPIO.output(LED_PINK, GPIO.LOW)
            GPIO.output(FAN, GPIO.LOW)

# RUN THE SCRIPT
def iothub_client_telemetry_sample_run():
    try:
        aux_validate_connection_string()
        client = aux_iothub_client_init()

        print("IoT Hub Sensor Telemetry and Command Listener")
        print("Press Ctrl-C to exit")

        # Start a separate thread to handle incoming messages
        import threading
        threading.Thread(target=handle_command, args=(client,), daemon=True).start()

        while True:
            # COLLECTING SENSOR VALUES
            temperature = get_sensor_temperature()
            light = get_sensor_light()
            joystick_action = get_sensor_joystick()

            # STORING SENSOR VALUES IN DATA STRUCTURE
            sensor_data['temperature'] = temperature
            sensor_data['light'] = light
            sensor_data['joystick_action'] = joystick_action

            # TRANSFORMING IT TO JSON
            json_sensor_data = json.dumps(sensor_data)

            # CREATING AN AZURE IOT MESSAGE OBJECT
            azure_iot_message = Message(json_sensor_data)

            # ADDING A CUSTOM PROPERTY. CREO QUE NO LO USAREMOS
            # azure_iot_message.custom_properties["noise_alert"] = "true" if joystick_action == "Noise Detected" else "false"

            # SETTING PROPER MESSAGE ENCODING
            azure_iot_message.content_encoding = 'utf-8'
            azure_iot_message.content_type = 'application/json'

            # SENDING THE MESSAGE
            print(f"Sending message: {azure_iot_message}")
            client.send_message(azure_iot_message)
            print("Message successfully sent")

            # SLEEPING FOR A SECOND BEFORE RESTARTING
            time.sleep(1)

    except KeyboardInterrupt:
        print("IoTHubClient sample stopped")
    finally:
        GPIO.cleanup()
        sense.clear()

if __name__ == '__main__':
    iothub_client_telemetry_sample_run()
