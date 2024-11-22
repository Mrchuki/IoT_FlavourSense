# SCRIPT PARA QUE LA RASPBERRYPI MANDE LAS MEDIDAS A AZURE. Tenemos la selección de productos y la detección de mucho ruido con el joystick, la temperatura
# y los niveveles de luz simulados con el sensor de humedad (solo 2 rangos: poca y mucha luz).

import json
import sys
import time
from sense_hat import SenseHat
from azure.iot.device import IoTHubDeviceClient, Message

# Azure IoT Hub Connection String
AUX_CONNECTION_STRING = sys.argv[1]

# Initialize SenseHat
sense = SenseHat()

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

# RUN THE SCRIPT
def iothub_client_telemetry_sample_run():
    try:
        aux_validate_connection_string()
        client = aux_iothub_client_init()

        print("IoT Hub Sensor Telemetry")
        print("Press Ctrl-C to exit")

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

            # ADDING A CUSTOM PROPERTY, which can trigger actions in Azure, such as sending alerts or logging the event. Lo dejo por si nos interesa.
            azure_iot_message.custom_properties["noise_alert"] = "true" if joystick_action == "Noise Detected" else "false"

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

if __name__ == '__main__':
    iothub_client_telemetry_sample_run()
