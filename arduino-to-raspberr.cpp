#include <WiFi.h>
#include <PubSubClient.h>

// Configuración de red WiFi
const char* ssid = "iPhone de Claudia";  // Cambia esto por el nombre de tu red WiFi
const char* password = "claudiac";  // Cambia esto por la contraseña de tu red WiFi

// Configuración del broker MQTT
const char* mqtt_server = "broker.hivemq.com";  // Cambia esto con la IP de tu Raspberry Pi si usas un broker local
const int mqtt_port = 1883;  // Puerto MQTT estándar

WiFiClient espClient;
PubSubClient client(espClient);

// Pin al que está conectado el relé
const int relePin = 1;  // Cambia esto si estás utilizando otro pin

// Tema MQTT para controlar el ventilador
const char* mqtt_topic = "test-arduino";  // Tema en el que recibirás los comandos

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    attempts++;
    if (attempts > 20) {  // Si no se conecta en 10 segundos, detiene el intento.
      Serial.println(" No se pudo conectar a la red WiFi.");
      return;  // Sale de la función si no se conecta
    }
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Intentar reconectar mientras no esté conectado al broker MQTT
  while (!client.connected()) {
    Serial.print("Intentando conectar al broker MQTT...");
    if (client.connect("ArduinoClient")) {  // Nombre del cliente MQTT
      Serial.println("Conectado al broker!");
      client.subscribe(mqtt_topic);  // Suscribirse al tema de control del ventilador
    } else {
      Serial.print("Fallo, rc=");
      Serial.print(client.state());
      Serial.println(" Intentando de nuevo en 5 segundos...");
      delay(5000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  // Convertir el mensaje recibido a String
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("Mensaje recibido en el tema: ");
  Serial.println(topic);
  Serial.print("Mensaje: ");
  Serial.println(message);

  // Control del relé según el mensaje recibido
  if (message == "ON") {
    digitalWrite(relePin, HIGH);  // Encender el ventilador
    Serial.println("Ventilador ENCENDIDO");
  } else if (message == "OFF") {
    digitalWrite(relePin, LOW);   // Apagar el ventilador
    Serial.println("Ventilador APAGADO");
  }
}

void setup() {
  // Iniciar comunicación serie
  Serial.begin(115200);
  Serial.println("Iniciando sistema...");

  // Configurar el pin del relé como salida
  pinMode(relePin, OUTPUT);
  digitalWrite(relePin, LOW);  // Asegurarse de que el ventilador esté apagado al inicio

  // Conectar a la red WiFi
  setup_wifi();
  
  // Configurar el servidor MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);  // Configurar la función de callback para los mensajes recibidos

  // Intentar conectar al servidor MQTT
  reconnect();
}

void loop() {
  // Asegurarse de que el cliente MQTT está conectado
  if (!client.connected()) {
    reconnect();
  }

  // Hacer que el cliente MQTT procese mensajes pendientes
  client.loop();
}
