import paho.mqtt.client as mqtt
import time

# Configuración del broker
broker = "localhost"  # Usa "localhost" si Mosquitto está en la misma Raspberry
port = 1883
topic = "test"  # Tema al que publicaremos

# Crear cliente MQTT
client = mqtt.Client()

# Conectar al broker
client.connect(broker, port, 60)

# Publicar mensajes periódicamente
try:
    while True:
        message = "Mensaje desde Raspberry Pi"
        client.publish(topic, message)
        print(f"Publicado: {message}")
        time.sleep(2)  # Publicar cada 2 segundos
except KeyboardInterrupt:
    print("\nPublicación detenida.")
finally:
    client.disconnect()
