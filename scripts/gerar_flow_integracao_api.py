#!/usr/bin/env python3
"""
CardioIA, Fase 3, Ir Além 1: gera o fluxo Node-RED de integração com a API REST.

Autor: Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55. Data: 31/10/2026.

O fluxo é uma aba independente (pode ser importada junto com o fluxo da Parte 2):
mqtt in (sinais do ESP32) -> function (prepara a requisição) -> http request
(POST /sinais na API) -> function (resume a resposta) -> debug. Assim o Node-RED
(camada Fog) encaminha cada amostra do dispositivo para a API, que verifica o
risco e dispara o e-mail. Uso:

    python3 scripts/gerar_flow_integracao_api.py src/ir_alem1_rest_email/node_red/flows_integracao_api.json [broker] [porta] [url_api]
"""
import json
import sys

destino = sys.argv[1] if len(sys.argv) > 1 else "src/ir_alem1_rest_email/node_red/flows_integracao_api.json"
broker = sys.argv[2] if len(sys.argv) > 2 else "broker.hivemq.com"
porta = sys.argv[3] if len(sys.argv) > 3 else "1883"
url_api = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8000/sinais"

ABA = "ia1aba000000001"
BROKER = "ia1broker000001"

FUNC_PREPARAR = """// Prepara a requisicao para a API REST do Ir Alem 1.
// O payload publicado pelo ESP32 ja esta no formato aceito por POST /sinais;
// apenas garantimos o tipo e registramos a origem para rastreabilidade.
const p = msg.payload;
if (!p || typeof p !== 'object') { node.warn('payload invalido'); return null; }
msg.headers = { 'Content-Type': 'application/json' };
msg.payload = p;
node.status({ fill: 'blue', shape: 'dot', text: 'seq ' + p.seq + ' -> API' });
return msg;"""

FUNC_RESUMIR = """// Resume a resposta da API (201 com alertas e indicador de e-mail).
if (msg.statusCode !== 201) {
    node.status({ fill: 'red', shape: 'ring', text: 'HTTP ' + msg.statusCode });
    node.error('API respondeu ' + msg.statusCode + ': ' + JSON.stringify(msg.payload));
    return null;
}
const r = msg.payload;
const tipos = (r.alertas || []).map(a => a.tipo).join(', ') || 'nenhum';
node.status({ fill: r.alertas && r.alertas.length ? 'red' : 'green', shape: 'dot',
              text: 'id ' + r.id + ' | ' + tipos + (r.email_enviado ? ' | e-mail' : '') });
msg.payload = { id: r.id, instante: r.instante, alertas: tipos, email_enviado: r.email_enviado };
return msg;"""

nos = [
    {"id": ABA, "type": "tab", "label": "CardioIA Ir Alem 1 - Integracao com a API REST", "disabled": False,
     "info": "Encaminha cada amostra publicada pelo ESP32 (MQTT) para a API REST em Python, que verifica o risco e dispara o e-mail."},
    {"id": BROKER, "type": "mqtt-broker", "name": "Broker MQTT (integracao API)", "broker": broker, "port": porta,
     "clientid": "cardioia-nodered-api-g55", "autoConnect": True, "usetls": False, "protocolVersion": "4", "keepalive": "60",
     "cleansession": True, "autoUnsubscribe": True, "birthTopic": "", "birthQos": "0", "birthPayload": "",
     "closeTopic": "", "closeQos": "0", "closePayload": "", "willTopic": "", "willQos": "0", "willPayload": "",
     "userProps": "", "sessionExpiry": ""},
    {"id": "ia1comment00001", "type": "comment", "z": ABA, "name": "Ir Alem 1: ESP32 (MQTT) -> Node-RED -> API REST (FastAPI) -> verificacao de risco e e-mail",
     "info": "Pre-requisito: API em execucao (uvicorn api.main:app) em " + url_api, "x": 420, "y": 40, "wires": []},
    {"id": "ia1mqttin000001", "type": "mqtt in", "z": ABA, "name": "MQTT sinais (ESP32)", "topic": "cardioia/grupo55/paciente01/sinais",
     "qos": "1", "datatype": "json", "broker": BROKER, "nl": False, "rap": True, "rh": 0, "inputs": 0, "x": 150, "y": 120, "wires": [["ia1prep00000001"]]},
    {"id": "ia1prep00000001", "type": "function", "z": ABA, "name": "Preparar requisicao", "func": FUNC_PREPARAR, "outputs": 1,
     "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": 380, "y": 120, "wires": [["ia1http00000001"]]},
    {"id": "ia1http00000001", "type": "http request", "z": ABA, "name": "POST /sinais (API REST)", "method": "POST", "ret": "obj",
     "paytoqs": "ignore", "url": url_api, "tls": "", "persist": False, "proxy": "", "insecureHTTPParser": False,
     "authType": "", "senderr": False, "headers": [], "x": 620, "y": 120, "wires": [["ia1resumo000001"]]},
    {"id": "ia1resumo000001", "type": "function", "z": ABA, "name": "Resumir resposta", "func": FUNC_RESUMIR, "outputs": 1,
     "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": 850, "y": 120, "wires": [["ia1debug0000001"]]},
    {"id": "ia1debug0000001", "type": "debug", "z": ABA, "name": "debug resposta da API", "active": True, "tosidebar": True,
     "console": False, "tostatus": False, "complete": "payload", "targetType": "msg", "statusVal": "", "statusType": "auto",
     "x": 1080, "y": 120, "wires": []},
]

with open(destino, "w", encoding="utf-8") as f:
    json.dump(nos, f, ensure_ascii=False, indent=2)
print(f"gerado: {destino} ({len(nos)} nos; broker {broker}:{porta}; API {url_api})")
