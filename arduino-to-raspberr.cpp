#include <WiFi.h>
#include <PubSubClient.h>

// Configuración de red WiFi
const char* ssid = "iPhone de Ivan";         // Cambia esto por el nombre de tu red WiFi
const char* password = "mrchuki69"; // Cambia esto por la contraseña de tu red WiFi

// Configuración del broker MQTT
const char* mqtt_server = "broker.hivemq.com"; // Broker público HiveMQ
const int mqtt_port = 1883;                   // Puerto MQTT estándar sin TLS
const char* mqtt_topic = "test/arduino";      // Tema MQTT de prueba

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mensaje recibido en el tema: ");
  Serial.println(topic);
  Serial.print("Mensaje: ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect() {
  // Intentar reconectar mientras no esté conectado
  while (!client.connected()) {
    Serial.print("Intentando conectar al broker MQTT...");
    if (client.connect("ArduinoClient")) { // Nombre del cliente MQTT
      Serial.println("Conectado!");
      client.subscribe(mqtt_topic); // Suscribirse al tema de prueba
    } else {
      Serial.print("Fallo, rc=");
      Serial.print(client.state());
      Serial.println(" Intentando de nuevo en 5 segundos...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Publicar un mensaje cada 10 segundos
  static unsigned long lastMsg = 0;
  unsigned long now = millis();
  if (now - lastMsg > 10000) {
    lastMsg = now;
    String message = "Hola desde Arduino!";
    Serial.print("Publicando mensaje: ");
    Serial.println(message);
    client.publish(mqtt_topic, message.c_str());
  }
}