import json
import os
from datetime import datetime, timezone
from pathlib import Path
from ai_alert_agent import handle_alert_event

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


load_dotenv()

#Variaveis de configuração do MQTT Broker e do tópico de alertas
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_ALERTS = os.getenv("MQTT_TOPIC_ALERTS", "alerts/edge/detected")

#Variaveis de configuração do diretório e arquivo de armazenamento simulado dos alertas
DATA_DIR = Path("data")
ALERTS_FILE = DATA_DIR / "alerts.jsonl"

#Função para salvar o evento de alerta em um arquivo JSONL, simulando a persistência em um banco de dados
def save_event_to_jsonl(event: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    with ALERTS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

#Iot Agent: normaliza o evento recebido via MQTT, adicionando timestamp e metadados de armazenamento
def normalize_event(event: dict) -> dict:
    return {
        **event,
        "ingestedAt": datetime.now(timezone.utc).isoformat(),
        "storage": "jsonl-simulated-mongodb-sth",
    }

#Função de callback chamada quando o cliente MQTT se conecta ao Broker
def on_connect(
    client: mqtt.Client,
    userdata,
    flags,
    reason_code,
    properties,
) -> None:
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
    print(f"Subscribing to topic: {MQTT_TOPIC_ALERTS}\n")

    client.subscribe(MQTT_TOPIC_ALERTS, qos=1)

#Função de callback chamada quando uma mensagem MQTT é recebida.
def on_message(
    client: mqtt.Client,
    userdata,
    message: mqtt.MQTTMessage,
) -> None:
    payload = message.payload.decode("utf-8")

    print("\n📩 MQTT message received")
    print(f"topic={message.topic}")
    print(f"payload={payload}")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        print("Invalid JSON payload. Message ignored.")
        return

    # Papel simplificado de um IoT Agent:
    # interpreta a mensagem recebida via MQTT e adapta para o formato interno da aplicação.
    normalized_event = normalize_event(event)

    # Simula a persistência em MongoDB usando um arquivo JSONL.
    save_event_to_jsonl(normalized_event)

    # Aciona o AI Agent com o evento já normalizado e persistido.
    handle_alert_event(normalized_event)

    print(f"✅ Event saved to {ALERTS_FILE}")
    print("AI Agent processed the alert using recent context.\n")

#Função para criar o cliente MQTT, configurar callbacks e se conectar ao BrokerMQTT
def create_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="cloud-ingestion-service",
    )

    client.on_connect = on_connect
    client.on_message = on_message

    return client

#Função principal que inicia o serviço de ingestão MQTT,
#conectando-se ao Broker e aguardando mensagens
def main() -> None:
    client = create_mqtt_client()

    print("Starting MQTT ingestion service...")
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()