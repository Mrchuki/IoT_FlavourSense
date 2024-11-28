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
from tkinter import StringVar  # Import necesario para las variables de Tkinter

# Azure IoT Hub Connection String
AUX_CONNECTION_STRING = "HostName=icaiiotflavoursense.azure-devices.net;DeviceId=SenseHat;SharedAccessKey=1zTmZeEfAeDwV7P7gf2ERKkiG1F/2mG79ou5RM8BYlA="

# MQTT Broker Configuración
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "test-arduino"

# Variables de control para MQTT
mqtt_client = mqtt.Client("RaspberryPiClient")
mqtt_connected = False

# Variables necesarias para la interfaz
temperature = StringVar(value="N/A")
light = StringVar(value="N/A")
joystick_action = StringVar(value="No Selection")
mqtt_status = StringVar(value="Disconnected")

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

# Función para crear la interfaz gráfica
def create_interface():
    import tkinter as tk
    from tkinter import Label, Canvas

    root = tk.Tk()
    root.title("FlavourSense")
    root.geometry("400x500")
    root.configure(bg="#fff5e6")  # Fondo de color crema

    # Encabezado
    header = Label(root, text="FlavourSense", font=("Serif", 24, "bold"), fg="#800020", bg="#fff5e6")
    header.pack(pady=10)

    # Ícono de la copa de vino
    canvas = Canvas(root, width=100, height=100, bg="#fff5e6", highlightthickness=0)
    canvas.pack()
    canvas.create_oval(20, 20, 80, 80, fill="#800020")  # Copa en color vino
    canvas.create_rectangle(45, 80, 55, 100, fill="#800020")  # Base de la copa

    # Sección de temperatura
    Label(root, text="Temperature:", font=("Arial", 14), bg="#fff5e6", anchor="w").pack(fill="x", padx=20)
    Label(root, textvariable=temperature, font=("Arial", 20, "bold"), bg="#f8e1e1", fg="#800020", anchor="center").pack(fill="x", padx=20, pady=5)

    # Estado de luz
    Label(root, text="Light Status:", font=("Arial", 14), bg="#fff5e6", anchor="w").pack(fill="x", padx=20)
    Label(root, textvariable=light, font=("Arial", 16, "bold"), bg="#fce5cd", fg="#ff4500", anchor="center").pack(fill="x", padx=20, pady=5)

    # Selección del joystick
    Label(root, text="Joystick Selection:", font=("Arial", 14), bg="#fff5e6", anchor="w").pack(fill="x", padx=20)
    Label(root, textvariable=joystick_action, font=("Arial", 16, "bold"), bg="#e6e6fa", fg="#800080", anchor="center").pack(fill="x", padx=20, pady=5)

    # Estado MQTT
    Label(root, text="MQTT Status:", font=("Arial", 14), bg="#fff5e6", anchor="w").pack(fill="x", padx=20)
    Label(root, textvariable=mqtt_status, font=("Arial", 16, "bold"), bg="#fafad2", fg="#ff8c00", anchor="center").pack(fill="x", padx=20, pady=5)

    root.mainloop()

# Función para ejecutar la interfaz gráfica en un hilo por separado y que así no bloquee el resto del código
def start_interface_thread():
    import threading
    threading.Thread(target=create_interface, daemon=True).start()

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        print("Conectado exitosamente al broker MQTT.")
        mqtt_connected = True
        mqtt_status.set("Connected")
    else:
        print(f"Error al conectar al broker MQTT: {rc}")
        mqtt_connected = False
        mqtt_status.set("Disconnected")

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

# MATRICES DE NOTAS MUSICALES
def get_note_matrix(note, intensity=1):
    black = [0, 0, 0]
    red = [int(139 * intensity), 0, 0]
    pink = [int(255 * intensity), int(182 * intensity), int(193 * intensity)]
    white = [int(255 * intensity), int(255 * intensity), int(255 * intensity)]

    corchea = [
        black, black, black, red, red, black, black, black,
        black, black, black, red, red, black, black, black,
        black, black, red, red, red, red, black, black,
        black, black, red, red, red, red, black, black,
        black, black, black, red, red, black, black, black,
        black, black, black, red, red, black, black, black,
        black, black, black, red, red, black, black, black,
        black, black, black, black, black, black, black, black,
    ]

    semicorchea = [
        black, black, pink, pink, black, black, black, black,
        black, black, pink, pink, black, black, black, black,
        black, pink, pink, pink, pink, black, black, black,
        black, pink, pink, pink, pink, black, black, black,
        black, black, pink, pink, pink, pink, black, black,
        black, black, pink, pink, pink, pink, black, black,
        black, black, black, pink, pink, black, black, black,
        black, black, black, black, black, black, black, black,
    ]

    blanca = [
        black, black, white, white, white, white, black, black,
        black, white, white, black, black, white, white, black,
        black, white, black, black, black, black, white, black,
        black, white, black, black, black, black, white, black,
        black, white, black, black, black, black, white, black,
        black, white, white, black, black, white, white, black,
        black, black, white, white, white, white, black, black,
        black, black, black, black, black, black, black, black,
    ]

    if note == "Red Wine":
        return corchea
    elif note == "Rosé Wine":
        return semicorchea
    elif note == "White Wine":
        return blanca
    else:
        return [black] * 64

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
        client = IoTHubDeviceClient.create_from_connection_string(AUX_CONNECTION_STRING)

        print("Conectando al broker MQTT...")
        mqtt_connect_with_retry()

        print("IoT Hub Sensor Telemetry and Command Listener")
        print("Press Ctrl-C to exit")

        threading.Thread(target=handle_command, args=(client,), daemon=True).start()

        while True:
            temp = get_sensor_temperature()
            light_status = get_sensor_light()
            joystick = get_sensor_joystick()

            if joystick in WINE_SELECTION.values():
                display_note(joystick)
              
            temperature.set(f"{temp}°C")
            light.set(light_status)
            joystick_action.set(joystick)

            sensor_data.update({
                'temperature': temp,
                'light': light_status,
                'joystick_action': joystick,
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
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        GPIO.cleanup()
        sense.clear()
        root.destroy()

if __name__ == '__main__':
   # Iniciar la interfaz gráfica
    start_interface_thread()
   
   # Fujo del programa
    iothub_client_telemetry_sample_run()
