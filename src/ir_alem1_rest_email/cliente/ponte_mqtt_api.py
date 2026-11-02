"""
CardioIA, Fase 3, Ir Além 1: ponte MQTT para a API REST.

Projeto : CardioIA (FIAP, curso de Inteligência Artificial, Ano 2)
Autor   : Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55
Data    : 31/10/2026

Assina o tópico de sinais publicado pelo ESP32 da Parte 2 e encaminha cada
mensagem, sem conversão, para POST /sinais da API. É a integração entre o
fluxo MQTT (Fog/Cloud) e a automação REST e e-mail deste desafio, alternativa
ao nó "http request" do Node-RED (flows_integracao_api.json). Uso:

    python -m cliente.ponte_mqtt_api --broker broker.hivemq.com --porta 1883 \
        --topico cardioia/grupo55/paciente01/sinais --api http://127.0.0.1:8000

Para o HiveMQ Cloud: --porta 8883 --tls --usuario ... --senha ... (ou variáveis
MQTT_USUARIO e MQTT_SENHA, nunca no código).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import ssl
import sys
import time

import paho.mqtt.client as mqtt
import requests

log = logging.getLogger("cardioia.ponte")


def construir_cliente(args) -> mqtt.Client:
    # Sufixo aleatório: dois processos com o mesmo client_id derrubam um ao outro no broker.
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cardioia-ponte-api-g55-{secrets.token_hex(3)}",
                          clean_session=True)
    usuario = args.usuario or os.getenv("MQTT_USUARIO", "")
    senha = args.senha or os.getenv("MQTT_SENHA", "")
    if usuario:
        cliente.username_pw_set(usuario, senha)
    if args.tls:
        cliente.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    sessao = requests.Session()
    contador = {"ok": 0, "erro": 0}

    def ao_conectar(c, _userdata, _flags, codigo, _props=None):
        log.info("[MQTT] conectado a %s:%s (codigo %s); assinando %s", args.broker, args.porta, codigo, args.topico)
        c.subscribe(args.topico, qos=1)

    def ao_receber(_c, _userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            payload["origem"] = "ponte"
            r = sessao.post(f"{args.api}/sinais", json=payload, timeout=5)
            r.raise_for_status()
            corpo = r.json()
            contador["ok"] += 1
            tipos = ", ".join(a["tipo"] for a in corpo["alertas"]) or "nenhum"
            log.info("[PONTE] seq=%s -> API id=%s alertas=%s email=%s", payload.get("seq"), corpo["id"], tipos, corpo["email_enviado"])
        except (ValueError, requests.RequestException) as erro:
            contador["erro"] += 1
            log.error("[PONTE] falha ao encaminhar (%s): %s", msg.topic, erro)

    def ao_desconectar(_c, _userdata, _flags, codigo, _props=None):
        log.warning("[MQTT] desconectado (codigo %s); %s encaminhadas, %s erros", codigo, contador["ok"], contador["erro"])

    cliente.on_connect = ao_conectar
    cliente.on_message = ao_receber
    cliente.on_disconnect = ao_desconectar
    return cliente


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ponte MQTT -> API REST (CardioIA, Ir Alem 1)")
    p.add_argument("--broker", default="broker.hivemq.com")
    p.add_argument("--porta", type=int, default=1883)
    p.add_argument("--tls", action="store_true")
    p.add_argument("--usuario", default="")
    p.add_argument("--senha", default="")
    p.add_argument("--topico", default="cardioia/grupo55/paciente01/sinais")
    p.add_argument("--api", default="http://127.0.0.1:8000")
    p.add_argument("--duracao", type=float, default=0, help="segundos de execucao (0 = ate Ctrl+C)")
    args = p.parse_args(argv)
    args.api = args.api.rstrip("/")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cliente = construir_cliente(args)
    cliente.connect(args.broker, args.porta, keepalive=30)
    try:
        if args.duracao > 0:
            cliente.loop_start()
            time.sleep(args.duracao)
            cliente.loop_stop()
            cliente.disconnect()
        else:
            cliente.loop_forever()
    except KeyboardInterrupt:
        cliente.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
