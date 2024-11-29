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
import threading
import paho.mqtt.client as mqtt  # Para comunicación con Arduino
import RPi.GPIO as GPIO

# Azure IoT Hub Connection String
AUX_CONNECTION_STRING = "HostName=icaiiotflavoursense.azure-devices.net;DeviceId=SenseHat;SharedAccessKey=1zTmZeEfAeDwV7P7gf2ERKkiG1F/2mG79ou5RM8BYlA="

# MQTT Broker Configuración
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "test-arduino"

# Variables de control para MQTT
mqtt_client = mqtt.Client("RaspberryPiClient")
mqtt_connected = False

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

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        print("Conectado exitosamente al broker MQTT.")
        mqtt_connected = True
    else:
        print(f"Error al conectar al broker MQTT: {rc}")
        mqtt_connected = False

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    print("Desconectado del broker MQTT.")
    mqtt_connected = False

def on_publish(client, userdata, mid):
    print(f"Mensaje publicado exitosamente. ID del mensaje: {mid}")

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_publish = on_publish

# Reconexión periódica al broker MQTT
def mqtt_connect_with_retry():
    global mqtt_connected
    while not mqtt_connected:
        try:
            print("Intentando conectar al broker MQTT...")
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
            time.sleep(2)  # Espera antes de verificar el estado
        except Exception as e:
            print(f"Error al conectar al broker MQTT: {e}")
            time.sleep(5)  # Reintentar tras un breve retraso

# Métodos para controlar el Arduino vía MQTT
def send_to_arduino(message):
    if mqtt_connected:
        result = mqtt_client.publish(MQTT_TOPIC, message, qos=1, retain=True)
        if result.rc == 0:
            print(f"Mensaje enviado a Arduino: {message}")
        else:
            print(f"Error al enviar mensaje a Arduino: {result.rc}")
    else:
        print("No conectado al broker MQTT. No se pudo enviar el mensaje.")

# Métodos para obtener valores del Sense HAT
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

# Función para generar una onda sinusoidal
def generate_continuous_wave_matrix(amplitude, frequency, phase_shift, color):
    matrix = [[black for _ in range(8)] for _ in range(8)]
    prev_y = None  # Para unir puntos de forma continua

    for x in range(8):
        y_position = int(3.5 + amplitude * math.sin(frequency * x + phase_shift))
        matrix[y_position][x] = color
        if prev_y is not None and prev_y != y_position:
            step = 1 if y_position > prev_y else -1
            for intermediate_y in range(prev_y, y_position, step):
                matrix[intermediate_y][x] = color
        prev_y = y_position
    return matrix

# Función para mostrar una onda sinusoidal continuamente
def animate_continuous_wave(wave_settings, stop_flag):
    amplitude, frequency, color = wave_settings
    phase_shift = 0
    while not stop_flag[0]:
        wave_matrix = generate_continuous_wave_matrix(amplitude, frequency, phase_shift, color)
        flattened_matrix = [pixel for row in wave_matrix for pixel in row]
        sense.set_pixels(flattened_matrix)
        phase_shift += 0.5
        time.sleep(0.2)

# Función para mostrar una línea horizontal azul
def display_horizontal_line(color):
    matrix = [[black for _ in range(8)] for _ in range(8)]
    for x in range(8):
        matrix[3][x] = color  # Línea centrada
    flattened_matrix = [pixel for row in matrix for pixel in row]
    sense.set_pixels(flattened_matrix)

# DISPLAY NOTES ON LED MATRIX
def display_note(note, intensity=1):
    matrix = get_note_matrix(note, intensity)
    sense.set_pixels(matrix)

# HANDLE INCOMING COMMANDS FROM AZURE
def handle_command(client):
    while True:
        message = client.receive_message()
        payload = json.loads(message.data)
        command = payload.get("command", None)

        if command == "Fan ON":
            print("Command received: Fan ON")
            send_to_arduino("ON")

        elif command == "Fan OFF":
            print("Command received: Fan OFF")
            send_to_arduino("OFF")

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
        current_thread = None  # Control del hilo actual
        stop_flag = [False]  # Señal para detener el hilo de animación

       # Definición de colores
        black = [0, 0, 0]
        red = [255, 0, 0]  # Corchea - Red Wine
        pink = [200, 85, 160]  # Semicorchea - Rosé Wine
        white = [255, 255, 255]  # Blanca - White Wine
        blue = [0, 0, 255]  # Línea horizontal azul

        client = IoTHubDeviceClient.create_from_connection_string(AUX_CONNECTION_STRING)

        print("Conectando al broker MQTT...")
        mqtt_connect_with_retry()

        print("IoT Hub Sensor Telemetry and Command Listener")
        print("Press Ctrl-C to exit")

        threading.Thread(target=handle_command, args=(client,), daemon=True).start()

        while True:
            temperature = get_sensor_temperature()
            light = get_sensor_light()
            events = sense.stick.get_events()  # Captura los eventos del joystick
            for event in events:
                if event.action == "pressed":
                    if event.direction == "middle":
                        print("Joystick presionado en el centro.")
                        if current_thread:
                            stop_flag[0] = True
                            current_thread.join()
                        display_horizontal_line([0, 0, 255])  # Línea azul
                    elif event.direction in WINE_SELECTION:
                        wine = WINE_SELECTION[event.direction]
                        print(f"Seleccionado: {wine}")

                        if wine == "Red Wine":
                            wave_settings = (3, 0.8, red)
                        elif wine == "Rosé Wine":
                            wave_settings = (2, 1, pink)
                        elif wine == "White Wine":
                            wave_settings = (1, 1.2, white)

                        if current_thread:
                            stop_flag[0] = True
                            current_thread.join()
                        stop_flag = [False]
                        current_thread = threading.Thread(
                            target=animate_continuous_wave, args=(wave_settings, stop_flag)
                        )
                        current_thread.start()

            sensor_data.update({
                'temperature': temperature,
                'light': light,
            })

            json_sensor_data = json.dumps(sensor_data)
            azure_iot_message = Message(json_sensor_data)
            azure_iot_message.content_encoding = 'utf-8'
            azure_iot_message.content_type = 'application/json'
            client.send_message(azure_iot_message)
            print(f"Message sent: {azure_iot_message}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("IoTHubClient sample stopped")
    finally:
        stop_flag[0] = True  # Asegurarse de detener cualquier animación activa
        if current_thread:
            current_thread.join()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        GPIO.cleanup()
        sense.clear()

if __name__ == '__main__':
    iothub_client_telemetry_sample_run()
