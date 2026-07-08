import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Callable, Any

from dotenv import load_dotenv

load_dotenv()

#Variaveis de configuração do diretório e arquivo de armazenamento simulado dos alertas
ALERTS_FILE = Path("data") / "alerts.jsonl"

#Variavel de configuração do webhook do Google Chat, para envio de notificações
GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")

#Observabilidade em IA: mede a latência de execução de uma função executada pelo Agente, 
#retornando o resultado e o tempo gasto em milissegundos
def measure_latency_ms(function: Callable, *args) -> tuple[Any, float]:
    start = time.perf_counter()
    result = function(*args)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return result, latency_ms

#Consulta os alertas recentes no "banco de dados" simulado 
# retorna os últimos N alertas
def get_alerts_from_database(limit: int = 5) -> list[dict]:
    """
    Simula uma consulta ao MongoDB/STH.
    Para a demo, os alertas estão em data/alerts.jsonl.
    """

    if not ALERTS_FILE.exists():
        return []

    lines = ALERTS_FILE.read_text(encoding="utf-8").splitlines()
    alerts = []

    for line in lines[-limit:]:
        try:
            alerts.append(json.loads(line))
        except Exception:
            pass

    return alerts

#Simula uma chamada para uma LLM, que gera um resumo do alerta atual
def call_llm_to_generate_summary(current_alert: dict, recent_alerts: list) -> str:
    """
    Simula uma chamada para uma LLM.
    Em produção, aqui entraria OpenAI, Gemini, Azure OpenAI, Bedrock etc.
    """

    device_id = current_alert.get("deviceId")
    metric = current_alert.get("metric")
    severity = current_alert.get("severity")
    
    #Envia para LLM o current_alert com os dados avgValue, maxValue, outOfRangeReadings, etc.
    #Para gerar um resumo do alerta atual
    #return call_llm(current_alert)    

    #Resposta/Resumo simulado recebido pela LLM, com base no alerta atual
    return f"""🚨 Alert Edge IoT

            Dispositivo: {device_id}
            Métrica: {metric}
            Severidade: {severity}

            Detectado padrão anormal nas leituras de temperatura.

            Contexto:
            - Média da janela: {current_alert.get("avgValue")}°C
            - Valor máximo: {current_alert.get("maxValue")}°C
            - Leituras fora da faixa: {current_alert.get("criticalReadings")}/{current_alert.get("windowSize")}
            - Latência da decisão na borda: {current_alert.get("edgeDecisionLatencyMs")} ms

            Possível causa:
            Falha no sensor, problema de calibração, alimentação ou conexão física.

            Ação recomendada:
            Verificar o sensor, a alimentação, o cabeamento e a calibração antes de confiar nas próximas leituras.
            """.strip()

#Observabilidade em IA: estima o número de tokens que seriam consumidos ao enviar o resumo para uma LLM
def estimate_tokens(text: str) -> int:
    return round(len(text.split()) * 1.3)

#Função para o Agente de IA enviar notificação para o Google Chat, caso a URL do webhook esteja configurada.
def send_notification_to_google_chat(message: str) -> None:

    payload = json.dumps({"text": message}).encode("utf-8")

    request = urllib.request.Request(
        GOOGLE_CHAT_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )

    try:
        urllib.request.urlopen(request, timeout=10)
        print("\n✅ Message sent to Google Chat")
    except Exception as error:
        print("\n❌ Failed to send Google Chat notification")
        print(f"error={error}")

#Função principal que processa o alerta recebido, chamando a LLM e envia notificação
def handle_alert_event(current_alert: dict) -> None:

    agent_start = time.perf_counter()

    recent_alerts, database_latency_ms = measure_latency_ms(
        get_alerts_from_database,
        5,
    )

    summary, llm_latency_ms = measure_latency_ms(
        call_llm_to_generate_summary,
        current_alert,
        recent_alerts,
    )

    _, notification_latency_ms = measure_latency_ms(
        send_notification_to_google_chat,
        summary,
    )

    total_agent_latency_ms = round(
        (time.perf_counter() - agent_start) * 1000,
        2,
    )

    estimated_tokens = estimate_tokens(summary)
    
    #Relatorio de observabilidade do Agente de IA, incluindo latências e estimativa de tokens consumidos
    #Futuramente ser enviado para um sistema de monitoramento, como Prometheus, Grafana ou OpenTelemetry
    #Avaliar Custo de Tokens, Latência e Performance do Agente de IA
    print("\n--- Agent observability ---")
    print(f"databaseLatencyMs={database_latency_ms}")
    print(f"llmLatencyMs={llm_latency_ms}")
    print(f"notificationLatencyMs={notification_latency_ms}")
    print(f"totalAgentLatencyMs={total_agent_latency_ms}")
    print(f"estimatedTokens={estimated_tokens}")