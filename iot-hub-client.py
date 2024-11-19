import json
import random
import sys
import time

from sense_hat import SenseHat
from azure.iot.device import IoTHubDeviceClient, Message

# Azure IoT Hub Connection String (provided as a script argument)
AUX_CONNECTION_STRING = sys.argv[1]

# Initialize SenseHat
sense = SenseHat()

# Thresholds for joystick button actions
JOYSTICK_ACTIONS = {
    "up": "Red Wine",
    "down": "White Wine",
    "left": "Rose Wine",
    "middle": "Stop music"
}

# SENSOR DATA STRUCTURE
sensor_data = {}

# METHODS TO GET SENSOR VALUES
def get_sensor_temperature():
    temperature = sense.get_temperature()
    return round(temperature, 2)

def get_sensor_light():
    # Simulated light sensor (as SenseHat doesn't have one natively)
    # Replace with actual photodiode code if available
    light_level = random.randint(0, 100)
    return light_level

def get_joystick_action():
    for event in sense.stick.get_events():
        if event.action == "pressed" and event.direction in JOYSTICK_ACTIONS:
            return JOYSTICK_ACTIONS[event.direction]
    return "No Action"

# VALIDATE CONNECTION STRING
def aux_validate_connection_string():
    if not AUX_CONNECTION_STRING.startswith('HostName='):
        print("ERROR  - YOUR IoT HUB CONNECTION STRING IS NOT VALID")
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
            # Collect sensor data
            temperature = get_sensor_temperature()
            light_level = get_sensor_light()
            product_selection = get_joystick_action()

            # Store data in structure
            sensor_data['temperature'] = temperature
            sensor_data['light'] = light_level
            sensor_data['product_selection'] = product_selection

            # Convert to JSON
            json_sensor_data = json.dumps(sensor_data)

            # Create Azure IoT Message
            azure_iot_message = Message(json_sensor_data)

            # Add custom property if temperature exceeds threshold
            azure_iot_message.custom_properties["temperature_alert"] = "true" if temperature > 30 else "false"

            # Set message encoding
            azure_iot_message.content_encoding = 'utf-8'
            azure_iot_message.content_type = 'application/json'

            # Send the message
            print(f"Sending message: {azure_iot_message}")
            client.send_message(azure_iot_message)
            print("Message successfully sent")

            # Wait for a second
            time.sleep(1)

    except KeyboardInterrupt:
        print("IoTHubClient sample stopped")
    finally:
        sense.clear()

if __name__ == '__main__':
    iothub_client_telemetry_sample_run()
