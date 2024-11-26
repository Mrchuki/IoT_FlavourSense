"""
Este script controla una Raspberry Pi equipada con un Sense HAT para enviar datos de sensores a Azure IoT Hub
y reaccionar a comandos recibidos desde la nube. Las principales funciones del script son:

1. **Recolección de datos:**
   - La Raspberry Pi mide la temperatura y los niveles de luz utilizando los sensores del Sense HAT.
   - También detecta la selección del usuario a través del joystick del Sense HAT, mapeando direcciones
     (arriba, abajo, derecha) a tipos de vino: "Red Wine", "White Wine" y "Rosé Wine".
   - Todos estos datos se estructuran en formato JSON y se envían a Azure IoT Hub.

2. **Visualización local:**
   - Según la selección del joystick, se muestran notas musicales en la matriz LED del Sense HAT,
     con colores específicos para cada tipo de vino:
       * "Red Wine" → Corchea roja
       * "White Wine" → Blanca blanca
       * "Rosé Wine" → Semicorchea rosa
   - La intensidad de las notas se puede ajustar (más brillante o menos brillante) mediante comandos
     enviados desde Azure.

3. **Reacción a comandos de Azure:**
   - Comandos posibles y sus efectos:
     - `"Fan ON"`: Llama al script auxiliar `raspberry-to-arduino.py` para activar un ventilador.
     - `"Fan OFF"`: Apaga el ventilador.
     - `"Increase Brightness"`: Aumenta la intensidad de las notas en la matriz LED.
     - `"Decrease Brightness"`: Reduce la intensidad de las notas en la matriz LED.
     - `"Temperature Low"`: Indicación recibida, pero sin acción implementada por ahora.

4. **Intercambio de datos:**
   - Los datos se envían a Azure IoT Hub en tiempo real, en mensajes codificados en JSON.
   - Azure procesa estos datos y puede devolver comandos que la Raspberry Pi ejecuta.
   - Este flujo permite una interacción bidireccional entre la Raspberry Pi y Azure.

El script también asegura la limpieza de los recursos GPIO y la matriz LED al finalizar la ejecución.
"""

import json
import sys
import time
from sense_hat import SenseHat
from azure.iot.device import IoTHubDeviceClient, Message
import RPi.GPIO as GPIO
import subprocess  # Para llamar al script auxiliar

# Azure IoT Hub Connection String
AUX_CONNECTION_STRING = sys.argv[1]

# Initialize SenseHat
sense = SenseHat()

# GPIO Setup
GPIO.setmode(GPIO.BCM)

# SENSOR DATA STRUCTURE
sensor_data = {}

# MAP JOYSTICK INPUT TO WINE TYPE
WINE_SELECTION = {
    "up": "Red Wine",
    "down": "White Wine",
    "right": "Rosé Wine",
}

# METHODS TO GET SENSOR VALUES
def get_sensor_temperature():
    return round(sense.get_temperature(), 2)

def get_sensor_light():
    humidity = sense.get_humidity()
    return "Low Light" if humidity < 50 else "High Light"

def get_sensor_joystick():
    for event in sense.stick.get_events():
        if event.action == "pressed":
            if event.direction in WINE_SELECTION:
                return WINE_SELECTION[event.direction]
            elif event.direction == "left":
                return "Noise Detected"
    return "No Selection"

# DISPLAY NOTES ON LED MATRIX
def display_note(note, intensity=1):
    colors = {
        "Red Wine": [139 * intensity, 0, 0],
        "Rosé Wine": [255 * intensity, 182 * intensity, 193 * intensity],
        "White Wine": [255 * intensity, 255 * intensity, 255 * intensity],
    }
    if note in colors:
        color = colors[note]
        matrix = [
            color if (x + y) % 2 == 0 else [0, 0, 0]
            for x in range(8) for y in range(8)
        ]
        sense.set_pixels(matrix)

# VALIDATE CONNECTION STRING
def aux_validate_connection_string():
    if not AUX_CONNECTION_STRING.startswith('HostName='):
        print("ERROR - YOUR IoT HUB CONNECTION STRING IS NOT VALID")
        sys.exit()

# INITIALIZE CLIENT
def aux_iothub_client_init():
    client = IoTHubDeviceClient.create_from_connection_string(AUX_CONNECTION_STRING)
    return client

# HANDLE INCOMING COMMANDS
def handle_command(client):
    while True:
        message = client.receive_message()  # Blocking call
        payload = json.loads(message.data)
        command = payload.get("command", None)

        if command == "Fan ON":
            print("Command received: Fan ON")
            #subprocess.run(["python3", "raspberry-to-arduino.py --ON"])
            subprocess.run(["python3", "raspberry-to-arduino.py"])
# aquñi hay q ver si le metemos otro script para off o que
        elif command == "Fan OFF":
            print("Command received: Fan OFF")
            subprocess.run(["python3", "raspberry-to-arduino.py"])

        elif command == "Increase Brightness":
            print("Command received: Increase Brightness")
            display_note(sensor_data.get('joystick_action', 'No Selection'), intensity=2)

        elif command == "Decrease Brightness":
            print("Command received: Decrease Brightness")
            display_note(sensor_data.get('joystick_action', 'No Selection'), intensity=0.5)

        elif command == "Temperature Low":
            print("Command received: Temperature Low - To be implemented.")

# MAIN SCRIPT
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

            # Update displayed note
            if joystick_action in WINE_SELECTION.values():
                display_note(joystick_action)

            # STORING SENSOR VALUES IN DATA STRUCTURE
            sensor_data.update({
                'temperature': temperature,
                'light': light,
                'joystick_action': joystick_action,
            })

            # SENDING DATA TO AZURE
            json_sensor_data = json.dumps(sensor_data)
            azure_iot_message = Message(json_sensor_data)
            azure_iot_message.content_encoding = 'utf-8'
            azure_iot_message.content_type = 'application/json'
            print(f"Sending message: {azure_iot_message}")
            client.send_message(azure_iot_message)
            print("Message successfully sent")

            time.sleep(1)

    except KeyboardInterrupt:
        print("IoTHubClient sample stopped")
    finally:
        GPIO.cleanup()
        sense.clear()

if __name__ == '__main__':
    iothub_client_telemetry_sample_run()

