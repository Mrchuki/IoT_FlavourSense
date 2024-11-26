import paho.mqtt.client as mqtt
import time

# Configuración del broker
broker = "broker.hivemq.com"
port = 1883
topic = "test-arduino"

# Crear cliente MQTT
client = mqtt.Client("RaspberryPiClient")

# Variables de control
is_connected = False

# Función de callback al conectar
def on_connect(client, userdata, flags, rc):
    global is_connected
    if rc == 0:
        print("Conectado exitosamente al broker.")
        is_connected = True
    else:
        print(f"Error al conectar: {rc}")
        is_connected = False

# Función de callback al desconectar
def on_disconnect(client, userdata, rc):
    global is_connected
    print("Desconectado del broker.")
    is_connected = False

# Función de callback al publicar
def on_publish(client, userdata, mid):
    print(f"Mensaje publicado exitosamente. ID del mensaje: {mid}")

# Configurar callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish

try:
    # Conectar al broker
    print("Conectando al broker...")
    client.connect(broker, port, keepalive=60)

    # Iniciar el bucle de red en segundo plano
    client.loop_start()

    # Publicar mensajes periódicamente
    while True:
        if is_connected:
            message = "ON"
            result = client.publish(topic, message, qos=1)
            status = result[0]
            if status == 0:
                print(f"Publicado correctamente en el tema `{topic}`: {message}")
            else:
                print(f"Error al publicar el mensaje en el tema `{topic}`")
        else:
            print("Esperando reconexión al broker...")

        time.sleep(2)  # Espaciar las publicaciones para evitar saturar el broker

except KeyboardInterrupt:
    print("\nPublicación detenida.")
finally:
    client.loop_stop()
    client.disconnect()
