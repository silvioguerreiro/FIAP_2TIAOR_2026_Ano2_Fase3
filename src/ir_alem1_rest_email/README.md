# Ir Além 1: comunicação automatizada com REST e e-mail

Projeto CardioIA, Fase 3, Grupo 55. Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR.

API REST em Python (FastAPI) que recebe os sinais vitais do wearable CardioIA, aplica a lógica de verificação de risco (taquicardia, bradicardia, febre, hipotermia, ausência de movimento e supervisão de dispositivo silencioso) e aciona uma automação de e-mail em caso de alerta. Acompanham um cliente REST que simula o dispositivo e consome a API, uma ponte MQTT que liga o ESP32 da Parte 2 à API, um fluxo Node-RED de integração e testes automatizados.

## Estrutura

```
src/ir_alem1_rest_email/
├── api/
│   ├── main.py            # endpoints FastAPI (POST /sinais, GET /sinais, /alertas, /notificacoes, /pacientes/{disp}/resumo)
│   ├── modelos.py         # modelos Pydantic (mesmo JSON publicado pelo ESP32 via MQTT)
│   ├── risco.py           # regras de risco explicitas e testaveis
│   ├── notificacao.py     # automacao de e-mail (simulado, SMTP local ou SMTP real) com anti-spam
│   ├── armazenamento.py   # historico em memoria por paciente com espelho CSV
│   └── config.py          # limites e parametros via .env
├── cliente/
│   ├── cliente_rest.py    # envia leituras simuladas em 4 cenarios e consome os endpoints
│   └── ponte_mqtt_api.py  # assina o topico MQTT do ESP32 e encaminha para POST /sinais
├── node_red/
│   └── flows_integracao_api.json  # aba Node-RED: mqtt in -> http request POST /sinais -> debug
├── tests/                 # 35 testes (regras de risco, e-mail, API ponta a ponta)
├── requirements.txt
├── .env.example           # modelo de configuracao (o .env nao e versionado)
└── README.md
```

## Fluxo

1. O dispositivo (ou o cliente simulado, ou a ponte MQTT, ou o Node-RED) envia `POST /sinais` com o JSON da amostra: `disp`, `seq`, `ts`, `tsrel`, `temp`, `umid`, `bpm`, `mov`, `alertas`, `origem`.
2. A API determina o instante efetivo da amostra (carimbo NTP ou hora de chegada), atualiza o instante do último movimento do paciente e aplica as regras de `risco.py`, combinando-as com a máscara de alertas avaliada no próprio ESP32.
3. Se houver alerta, `notificacao.py` monta o e-mail (assunto com gravidade e tipos, corpo com pseudônimo, instante, alertas e sinais) e o envia ou simula. Uma política anti-spam impede repetir o mesmo tipo de alerta para o mesmo paciente antes de 10 minutos (`EMAIL_INTERVALO_MINIMO_S`), o que evita fadiga de alarmes.
4. A amostra é armazenada com a avaliação e o indicador de e-mail, e fica disponível em `GET /sinais`, `GET /sinais/ultimo`, `GET /alertas`, `GET /pacientes/{disp}/resumo` (que acrescenta a supervisão `sem_dados` quando o dispositivo está em silêncio) e `GET /notificacoes`.

## Regras de risco

| Regra | Condição | Gravidade |
|---|---|---|
| taquicardia | bpm acima de 120 | alta |
| bradicardia | bpm abaixo de 50, com bpm maior que zero (zero é ausência de leitura) | alta |
| febre | temperatura acima de 38,0 C | média |
| hipotermia | temperatura abaixo de 35,0 C | alta |
| sem_movimento | mais de 600 s desde o último movimento conhecido do paciente | alta |
| sem_dados | nenhuma amostra há mais de 300 s (avaliada no resumo do paciente) | média |

Os limites são os mesmos do firmware e do Node-RED e podem ser alterados no `.env`.

## Como executar

```bash
cd src/ir_alem1_rest_email
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # opcional; o padrao e e-mail simulado

# 1. API (documentacao interativa em http://127.0.0.1:8000/docs)
uvicorn api.main:app --host 127.0.0.1 --port 8000

# 2. Em outro terminal: cliente que simula o wearable e consome a API
python -m cliente.cliente_rest --url http://127.0.0.1:8000

# 3. Testes
python -m pytest -v
```

Os e-mails simulados ficam em `logs/emails_simulados.log` e as amostras em `dados/sinais_recebidos.csv` (ambos fora do versionamento). Para entregar a um servidor SMTP de depuração local: `pip install aiosmtpd`, `python -m aiosmtpd -n -l localhost:1025` e `EMAIL_MODO=local` no `.env`. Para um servidor real: `EMAIL_MODO=smtp` com `SMTP_SERVIDOR`, `SMTP_PORTA`, `SMTP_USUARIO` e `SMTP_SENHA` no `.env` (STARTTLS); credenciais nunca entram no código nem no repositório.

## Integração com o fluxo MQTT da Parte 2

Duas opções, com o projeto da Parte 2 publicando no Wokwi:

```bash
# A) ponte em Python: assina o topico do ESP32 e encaminha para a API
python -m cliente.ponte_mqtt_api --broker broker.hivemq.com --porta 1883 \
    --topico cardioia/grupo55/paciente01/sinais --api http://127.0.0.1:8000
```

B) importar `node_red/flows_integracao_api.json` no Node-RED (aba independente, pode coexistir com o fluxo do dashboard): o nó `http request` faz `POST /sinais` para cada amostra recebida e o `debug` mostra a resposta da API com os alertas e o indicador de e-mail. O arquivo é gerado por `scripts/gerar_flow_integracao_api.py`.

## Evidências

Em `assets/evidencias/ir_alem1/`: saída do cliente REST (151 amostras, 20 com alerta, 3 e-mails: taquicardia, febre e ausência de movimento), e-mails simulados, log do servidor, saída da ponte MQTT com o simulador de mensagens do firmware (16 amostras encaminhadas, e-mails de taquicardia e febre), CSV das amostras recebidas, captura do Node-RED encaminhando para a API com o painel de debug e a saída dos 35 testes.

Limitações declaradas: validação feita com o cliente simulado, com o simulador MQTT e com um broker local; a execução contra o broker público com o ESP32 real no Wokwi exige a API acessível na máquina onde roda a ponte ou o Node-RED, e não foi executada nesta entrega. O envio real por SMTP não foi executado (modo simulado), por decisão de não depender de credenciais.
