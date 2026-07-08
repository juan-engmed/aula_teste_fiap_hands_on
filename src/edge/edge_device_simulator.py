import json
import os
import random
import statistics
import time
from collections import deque
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


load_dotenv()

DEVICE_ID = "edge-device-001"

#Variaveis de configuração do MQTT Broker e do tópico de alertas
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_ALERTS = os.getenv("MQTT_TOPIC_ALERTS", "alerts/edge/detected")

#Variaveis de configuração do tamanho da janela e do número total de leituras
WINDOW_SIZE = 10
TOTAL_READINGS = 20

#Variaveis de configuração da faixa válida de temperatura e dos critérios para detecção de padrão de falha
VALID_MIN_TEMP = 20.0
VALID_MAX_TEMP = 35.0
MAX_AVG_TEMP = 60.0
MAX_OUT_OF_RANGE_RATIO = 0.40

#Simula a geração de leituras de temperatura, com valores normais e anômalos
def generate_temperature(index: int) -> float:
    if index < 10:
        return round(random.uniform(24.0, 28.0), 2)

    return round(random.uniform(179.0, 200.0), 2)


#Verifica se a leitura de temperatura está fora da faixa válida definida
def is_temperature_out_of_range(temperature: float) -> bool:
    return temperature < VALID_MIN_TEMP or temperature > VALID_MAX_TEMP


#Inteligencia na Edge: analisa a janela de leituras de temperatura
def analyze_temperature_window(temperature_window: deque) -> dict:
    readings = list(temperature_window)

    out_of_range_readings = 0

    for temperature in readings:
        if is_temperature_out_of_range(temperature):
            out_of_range_readings += 1

    out_of_range_ratio = round(
        out_of_range_readings / len(readings),
        2,
    )

    return {
        "avgValue": round(statistics.mean(readings), 2),
        "maxValue": round(max(readings), 2),
        "outOfRangeReadings": out_of_range_readings,
        "outOfRangeRatio": out_of_range_ratio,
        "windowSize": len(readings),
    }

#Verifica se a janela de leituras apresenta padrão de falha, baseado em critérios definidos
def has_failure_pattern(window_analysis: dict) -> bool:
    return (
        window_analysis["windowSize"] == WINDOW_SIZE
        and window_analysis["avgValue"] > MAX_AVG_TEMP
        and window_analysis["outOfRangeRatio"] >= MAX_OUT_OF_RANGE_RATIO
    )

# Cria um evento padronizado de alerta a partir da análise da janela local.
# Esse payload será publicado via MQTT e consumido pelo ingestion_service.
def build_alert_event(window_analysis: dict) -> dict:
    return {
        "eventType": "EdgeAnomalyDetected",
        "deviceId": DEVICE_ID,
        "metric": "temperature",
        "severity": "HIGH",
        "probableCause": "SENSOR_FAILURE",
        "avgValue": window_analysis["avgValue"],
        "maxValue": window_analysis["maxValue"],
        "outOfRangeReadings": window_analysis["outOfRangeReadings"],
        "windowSize": window_analysis["windowSize"],
        "outOfRangeRatio": window_analysis["outOfRangeRatio"],
        "detectedAt": datetime.now(timezone.utc).isoformat(),
    }

#Publica o alerta no tópico MQTT definido, permitindo que outros serviços ou sistema
#possam receber e processar o alerta
def publish_alert(event: dict) -> None:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{DEVICE_ID}-publisher",
    )

    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    payload = json.dumps(event)

    client.publish(
        topic=MQTT_TOPIC_ALERTS,
        payload=payload,
        qos=1,
    ).wait_for_publish()

    client.loop_stop()
    client.disconnect()

    print(f"\n🚨 MQTT alert sent → {MQTT_TOPIC_ALERTS}")
    print(payload)


#Exibe o resultado da simulação de redução de tráfego com a utilização da Edge Computing,
#comparando o número de mensagens enviadas para a nuvem no modo "cloud-only" versus o modo "edge"
def print_edge_result(total_readings: int) -> None:
    cloud_only_messages = total_readings
    edge_messages = 1

    traffic_reduction = round(
        (1 - edge_messages / cloud_only_messages) * 100,
        2,
    )

    print("\n" + "=" * 48)
    print("📊 RESULTADO NA EDGE")
    print("=" * 48)
    print(f"Leituras geradas           : {total_readings}")
    print(f"Mensagens no cloud-only    : {cloud_only_messages}")
    print(f"Mensagens no modo edge     : {edge_messages}")
    print(f"Redução de tráfego         : {traffic_reduction}%")
    print(f"Local da decisão           : EDGE")
    print("=" * 48)

#Função principal que simula a coleta de leituras de temperatura,
#análise na Edge e envio de alertas via MQTT
def main() -> None:
    temperature_window = deque(maxlen=WINDOW_SIZE)

    print(f"Starting edge simulator: {DEVICE_ID}\n")

    for index in range(TOTAL_READINGS):
        
        # Simula a coleta de leitura de temperatura a cada segundo
        temperature = generate_temperature(index)
        temperature_window.append(temperature)

        #Analisa a janela de leituras para verificar se há padrão de falha
        window_analysis = analyze_temperature_window(temperature_window)

        status = (
            "OUT_OF_RANGE"
            if is_temperature_out_of_range(temperature)
            else "OK"
        )

        print(
            f"reading={index + 1:02d} "
            f"temp={temperature:.2f}°C "
            f"status={status} "
            f"avg={window_analysis['avgValue']:.2f}°C "
            f"outOfRangeRatio={window_analysis['outOfRangeRatio']:.2f}"
        )

        #Verifica se há padrão de falha na janela de leituras e publica o alerta no MQTT
        if has_failure_pattern(window_analysis):
            event = build_alert_event(window_analysis)
            publish_alert(event)
            print_edge_result(total_readings=index + 1)
            return

        time.sleep(1)

    print("\nNo alert detected.")


if __name__ == "__main__":
    main()