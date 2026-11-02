# -*- coding: utf-8 -*-
"""Gera o flows.json do Node-RED (Dashboard 2.0) da Parte 2 do CardioIA Fase 3.

O arquivo e gerado por script para evitar erros de sintaxe e manter os IDs
estaveis entre versoes. Saida: 03_entrega/src/parte2_fog_cloud/node_red/flows.json
"""
import json, sys

PREFIXO = "cardioia/grupo55/paciente01"
BROKER_HOST = "broker.hivemq.com"
BROKER_PORTA = "1883"

TAB = "cardioia_f3_tab"

def no(**kw):
    return kw

FUNC_NORMALIZAR = r"""// Normaliza a amostra publicada pelo ESP32 em <prefixo>/sinais e distribui
// para graficos, medidores, tabela e avaliacao de limites.
// Saidas: 1 grafico bpm | 2 grafico temperatura | 3 medidor temp | 4 medidor umidade | 5 medidor bpm | 6 tabela | 7 avaliacao
const p = msg.payload;
if (!p || typeof p !== 'object') { node.warn('payload invalido: ' + JSON.stringify(msg.payload)); return null; }
const agoraMs = Date.now();
// Carimbo de tempo do dispositivo (epoca Unix via NTP). Se for relativo (sem NTP), usa a hora de chegada.
const tsMs = (typeof p.ts === 'number' && !p.tsrel && p.ts > 1700000000) ? p.ts * 1000 : agoraMs;
const amostra = {
    disp: p.disp || 'desconhecido',
    seq: Number(p.seq) || 0,
    ts: tsMs,
    tsrel: !!p.tsrel,
    temp: Number(p.temp),
    umid: Number(p.umid),
    bpm: Number(p.bpm) || 0,
    mov: Number(p.mov) === 1,
    mascara: Number(p.alertas) || 0,
    origem: p.origem || 'rt',
    recebidoEm: agoraMs
};
flow.set('ultimaAmostra', amostra);
node.status({ fill: amostra.origem === 'sync' ? 'yellow' : 'green', shape: 'dot', text: 'seq ' + amostra.seq + ' (' + amostra.origem + ') bpm ' + amostra.bpm + ' temp ' + amostra.temp.toFixed(1) });

// Historico das ultimas 12 amostras para a tabela (mais recente primeiro)
const hist = flow.get('historico') || [];
hist.unshift({
    hora: new Date(tsMs).toLocaleTimeString('pt-BR'),
    seq: amostra.seq,
    bpm: amostra.bpm,
    temp_c: amostra.temp.toFixed(1),
    umid_pct: amostra.umid.toFixed(0),
    movimento: amostra.mov ? 'sim' : 'nao',
    alertas_disp: amostra.mascara,
    origem: amostra.origem
});
while (hist.length > 12) hist.pop();
flow.set('historico', hist);

const mBpm   = { payload: amostra.bpm,  topic: 'Frequencia cardiaca', timestamp: tsMs };
const mTemp  = { payload: amostra.temp, topic: 'Temperatura', timestamp: tsMs };
const mGTemp = { payload: amostra.temp };
const mGUmid = { payload: amostra.umid };
const mGBpm  = { payload: amostra.bpm };
const mTab   = { payload: hist };
const mAval  = { payload: amostra };
return [mBpm, mTemp, mGTemp, mGUmid, mGBpm, mTab, mAval];
"""

FUNC_LIMITES = r"""// Limites de alerta definidos pelo grupo (camada Fog). Justificativa no relatorio da Parte 2.
// Ausencia de movimento: 600 s (10 min) em producao. O dispositivo (Edge) usa 60 s no modo
// de demonstracao e informa o alerta pela mascara; o Fog aceita os dois.
const limites = {
    bpmMax: 120,       // acima: taquicardia
    bpmMin: 50,        // abaixo (com bpm > 0): bradicardia
    tempMax: 38.0,     // acima: febre
    tempMin: 35.0,     // abaixo: hipotermia
    semMovimentoS: 600 // segundos sem movimento
};
flow.set('limites', limites);
flow.set('historico', []);
flow.set('alertasAtivos', []);
node.status({ fill: 'blue', shape: 'ring', text: 'limites definidos' });
msg.payload = limites;
return msg;
"""

FUNC_AVALIAR = r"""// Avaliacao dos limites na camada Fog (Node-RED) combinada com a avaliacao feita
// no dispositivo (Edge, bitmask em "alertas"). Saidas: 1 painel | 2 notificacao | 3 texto
const LIM = flow.get('limites') || { bpmMax: 120, bpmMin: 50, tempMax: 38.0, tempMin: 35.0, semMovimentoS: 600 };
const a = msg.payload;
const tipos = [];
if (a.bpm > LIM.bpmMax) tipos.push('taquicardia');
if (a.bpm > 0 && a.bpm < LIM.bpmMin) tipos.push('bradicardia');
if (!isNaN(a.temp) && a.temp > LIM.tempMax) tipos.push('febre');
if (!isNaN(a.temp) && a.temp < LIM.tempMin) tipos.push('hipotermia');

// Ausencia de movimento avaliada no Fog pelo instante do ultimo movimento recebido
let ultimoMov = flow.get('ultimoMovimentoMs') || 0;
if (a.mov) { ultimoMov = a.ts; flow.set('ultimoMovimentoMs', ultimoMov); }
if (ultimoMov && (a.ts - ultimoMov) > LIM.semMovimentoS * 1000) tipos.push('sem_movimento');

// Alertas ja avaliados no dispositivo (bits: 1 taquicardia, 2 bradicardia, 4 febre, 8 hipotermia, 16 sem_movimento)
const nomes = ['taquicardia', 'bradicardia', 'febre', 'hipotermia', 'sem_movimento'];
nomes.forEach((n, i) => { if ((a.mascara & (1 << i)) && !tipos.includes(n)) tipos.push(n); });

const ativo = tipos.length > 0;
const hora = new Date(a.ts).toLocaleTimeString('pt-BR');
const resumo = 'bpm ' + a.bpm + ' | ' + a.temp.toFixed(1) + ' C | umid ' + a.umid.toFixed(0) + '% | mov ' + (a.mov ? 'sim' : 'nao');
const texto = ativo ? (tipos.join(', ') + ' | ' + resumo) : resumo;
const cor = ativo ? '#c62828' : '#2e7d32';
node.status({ fill: ativo ? 'red' : 'green', shape: 'dot', text: ativo ? tipos.join(', ') : 'normal' });

const painel = { payload: { ativo, texto, cor, tipos, hora, origem: a.origem, seq: a.seq } };

// Notificacao apenas quando surge um tipo novo de alerta em tempo real (evita repetir a cada 5 s)
const anteriores = flow.get('alertasAtivos') || [];
const novos = tipos.filter(t => !anteriores.includes(t));
flow.set('alertasAtivos', tipos);
let notif = null;
if (novos.length && a.origem === 'rt') {
    notif = { payload: 'Paciente 01: ' + novos.join(', ') + ' (bpm ' + a.bpm + ', ' + a.temp.toFixed(1) + ' C) as ' + hora };
}
const txt = { payload: ativo ? (hora + ': ' + tipos.join(', ')) : 'nenhum alerta ativo (' + hora + ')' };
return [painel, notif, txt];
"""

FUNC_ESTADO = r"""// Estado do dispositivo publicado em <prefixo>/estado (mensagem retida) e testamento (LWT).
const e = msg.payload || {};
const estado = String(e.estado || 'desconhecido');
const cores = { online: '#2e7d32', sincronizando: '#f9a825', offline: '#757575', offline_inesperado: '#c62828' };
const hora = e.ts ? new Date(e.ts * 1000).toLocaleTimeString('pt-BR') : new Date().toLocaleTimeString('pt-BR');
let texto = estado.toUpperCase() + ' | ' + hora;
if (e.pendentes !== undefined) texto += ' | pendentes ' + e.pendentes + '/' + e.capacidade;
if (e.publicadas !== undefined) texto += ' | publicadas ' + e.publicadas;
if (e.descartadas !== undefined) texto += ' | descartadas ' + e.descartadas;
if (e.rssi !== undefined) texto += ' | RSSI ' + e.rssi + ' dBm';
if (e.heap !== undefined) texto += ' | heap livre ' + Math.round(e.heap / 1024) + ' KB';
flow.set('estadoDispositivo', estado);
node.status({ fill: estado === 'online' ? 'green' : (estado === 'sincronizando' ? 'yellow' : 'red'), shape: 'dot', text: estado });
return { payload: { estado, texto, cor: cores[estado] || '#757575', disp: e.disp || '' } };
"""

FUNC_ALERTA_DISP = r"""// Ultimo estado de alerta publicado pelo proprio dispositivo (retido em <prefixo>/alertas).
const p = msg.payload || {};
const hora = p.ts ? new Date(p.ts * 1000).toLocaleTimeString('pt-BR') : '';
if (p.ativo) {
    msg.payload = hora + ': ' + (p.tipos || '').split(',').join(', ') + ' (bpm ' + p.bpm + ', ' + Number(p.temp).toFixed(1) + ' C, seq ' + p.seq + ')';
} else {
    msg.payload = 'sem alerta no dispositivo' + (hora ? ' (' + hora + ')' : '');
}
return msg;
"""

TEMPLATE_PAINEL = r"""<template>
    <div class="cardioia-painel" :style="{ background: (msg.payload && msg.payload.cor) || '#9e9e9e' }">
        <div class="titulo">{{ msg.payload && msg.payload.ativo ? 'ALERTA ATIVO' : 'SITUACAO NORMAL' }}</div>
        <div class="texto">{{ (msg.payload && msg.payload.texto) || 'aguardando dados do dispositivo...' }}</div>
        <div class="rodape">
            atualizado {{ msg.payload && msg.payload.hora }} | amostra {{ msg.payload && msg.payload.seq }}
            <span v-if="msg.payload && msg.payload.origem === 'sync'"> | sincronizada do buffer do dispositivo</span>
        </div>
    </div>
</template>
<style>
.cardioia-painel { color: #fff; padding: 14px 18px; border-radius: 6px; width: 100%; }
.cardioia-painel .titulo { font-size: 1rem; font-weight: 700; letter-spacing: .06em; }
.cardioia-painel .texto { font-size: 1.35rem; margin-top: 4px; }
.cardioia-painel .rodape { font-size: .85rem; opacity: .9; margin-top: 6px; }
</style>
"""

TEMPLATE_ESTADO = r"""<template>
    <div class="cardioia-estado" :style="{ borderLeft: '10px solid ' + ((msg.payload && msg.payload.cor) || '#9e9e9e') }">
        <span class="bolinha" :style="{ background: (msg.payload && msg.payload.cor) || '#9e9e9e' }"></span>
        <span class="texto">{{ (msg.payload && msg.payload.texto) || 'sem estado recebido do dispositivo' }}</span>
        <span class="disp" v-if="msg.payload && msg.payload.disp"> | {{ msg.payload.disp }}</span>
    </div>
</template>
<style>
.cardioia-estado { padding: 10px 14px; border-radius: 6px; background: #f5f5f5; width: 100%; font-size: 1rem; }
.cardioia-estado .bolinha { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 10px; vertical-align: middle; }
.cardioia-estado .disp { color: #616161; }
</style>
"""

nodes = []

# ---- Configuracao ---------------------------------------------------------
nodes.append(no(id=TAB, type="tab", label="CardioIA Fase 3 - Monitoramento (Fog/Cloud)", disabled=False,
                info="Fluxo da Parte 2 da Fase 3 do CardioIA (Grupo 55). Recebe via MQTT as amostras do wearable simulado (ESP32 no Wokwi), normaliza, avalia os limites de alerta na camada Fog e alimenta o dashboard (Dashboard 2.0).", env=[]))
nodes.append(no(id="cfg_broker_cardioia", type="mqtt-broker", name="Broker MQTT (HiveMQ publico)", broker=BROKER_HOST, port=BROKER_PORTA,
                clientid="cardioia-nodered-g55", autoConnect=True, usetls=False, protocolVersion="4", keepalive=60, cleansession=True,
                autoUnsubscribe=True, birthTopic="", birthQos="0", birthRetain="false", birthPayload="", birthMsg={},
                closeTopic="", closeQos="0", closeRetain="false", closePayload="", closeMsg={},
                willTopic="", willQos="0", willRetain="false", willPayload="", willMsg={}, userProps="", sessionExpiry=""))
nodes.append(no(id="ui_base_cardioia", type="ui-base", name="CardioIA", path="/dashboard", appIcon="", includeClientData=True,
                acceptsClientConfig=["ui-notification", "ui-control"], showPathInSidebar=False, headerContent="page",
                navigationStyle="default", titleBarStyle="default", showReconnectNotification=True, notificationDisplayTime=1,
                showDisconnectNotification=True, allowInstall=False))
nodes.append(no(id="ui_theme_cardioia", type="ui-theme", name="Tema CardioIA",
                colors={"surface": "#ffffff", "primary": "#c62828", "bgPage": "#f4f5f7", "groupBg": "#ffffff", "groupOutline": "#d9d9e0"},
                sizes={"density": "default", "pagePadding": "12px", "groupGap": "12px", "groupBorderRadius": "4px", "widgetGap": "12px"}))
nodes.append(no(id="ui_page_paciente01", type="ui-page", name="Paciente 01 - Monitoramento continuo", ui="ui_base_cardioia", path="/paciente01",
                icon="heart-pulse", layout="grid", theme="ui_theme_cardioia",
                breakpoints=[{"name": "Default", "px": 0, "cols": 3}, {"name": "Tablet", "px": 576, "cols": 6},
                             {"name": "Small Desktop", "px": 768, "cols": 9}, {"name": "Desktop", "px": 1024, "cols": 12}],
                tabs=[], order=1, className="", visible="true", disabled="false"))

def grupo(id_, nome, ordem, largura=12, altura=1):
    return no(id=id_, type="ui-group", name=nome, page="ui_page_paciente01", width=str(largura), height=str(altura), order=ordem,
              showTitle=True, className="", visible="true", disabled="false", groupType="default", tab="")

nodes += [
    grupo("grp_estado", "Estado do dispositivo (Edge) e do enlace", 1),
    grupo("grp_alerta", "Alertas (limites avaliados no Fog e no dispositivo)", 2),
    grupo("grp_graficos", "Sinais vitais em tempo real", 3),
    grupo("grp_medidores", "Medidores", 4),
    grupo("grp_tabela", "Ultimas amostras recebidas", 5),
]

# ---- Entrada MQTT ---------------------------------------------------------
def mqtt_in(id_, nome, topico, x, y, wires):
    return no(id=id_, type="mqtt in", z=TAB, name=nome, topic=topico, qos="0", datatype="json", broker="cfg_broker_cardioia",
              nl=False, rap=True, rh=0, inputs=0, x=x, y=y, wires=[wires])

nodes.append(no(id="cmt_entrada", type="comment", z=TAB, name="1. Entrada: assinaturas MQTT (JSON publicado pelo ESP32)",
                info="Topicos: " + PREFIXO + "/sinais (uma mensagem por amostra), /alertas (retida) e /estado (retida, com testamento).", x=250, y=40, wires=[]))
nodes.append(mqtt_in("mqtt_in_sinais", "MQTT sinais", PREFIXO + "/sinais", 160, 180, ["fn_normalizar", "dbg_sinais"]))
nodes.append(mqtt_in("mqtt_in_alertas", "MQTT alertas", PREFIXO + "/alertas", 160, 700, ["fn_alerta_disp", "dbg_alertas"]))
nodes.append(mqtt_in("mqtt_in_estado", "MQTT estado", PREFIXO + "/estado", 160, 820, ["fn_estado", "dbg_estado"]))

nodes.append(no(id="dbg_sinais", type="debug", z=TAB, name="debug sinais", active=True, tosidebar=True, console=False, tostatus=False,
                complete="payload", targetType="msg", statusVal="", statusType="auto", x=450, y=120, wires=[]))
nodes.append(no(id="dbg_alertas", type="debug", z=TAB, name="debug alertas", active=True, tosidebar=True, console=False, tostatus=False,
                complete="payload", targetType="msg", statusVal="", statusType="auto", x=450, y=760, wires=[]))
nodes.append(no(id="dbg_estado", type="debug", z=TAB, name="debug estado", active=True, tosidebar=True, console=False, tostatus=False,
                complete="payload", targetType="msg", statusVal="", statusType="auto", x=450, y=880, wires=[]))

# ---- Processamento (Fog) --------------------------------------------------
nodes.append(no(id="cmt_fog", type="comment", z=TAB, name="2. Processamento na camada Fog: normalizacao, limites e historico",
                info="Os limites ficam em flow.limites (definidos no deploy). A funcao de avaliacao combina a avaliacao local do dispositivo (bitmask) com a avaliacao do Fog.", x=720, y=40, wires=[]))
nodes.append(no(id="inj_limites", type="inject", z=TAB, name="no deploy", props=[{"p": "payload"}], repeat="", crontab="", once=True,
                onceDelay=0.1, topic="", payload="", payloadType="date", x=160, y=460, wires=[["fn_limites"]]))
nodes.append(no(id="fn_limites", type="function", z=TAB, name="Definir limites de alerta", func=FUNC_LIMITES, outputs=1, timeout=0,
                noerr=0, initialize="", finalize="", libs=[], x=470, y=460, wires=[["dbg_limites"]]))
nodes.append(no(id="dbg_limites", type="debug", z=TAB, name="debug limites", active=False, tosidebar=True, console=False, tostatus=False,
                complete="payload", targetType="msg", statusVal="", statusType="auto", x=720, y=460, wires=[]))

nodes.append(no(id="fn_normalizar", type="function", z=TAB, name="Normalizar amostra", func=FUNC_NORMALIZAR, outputs=7, timeout=0,
                noerr=0, initialize="", finalize="", libs=[], x=480, y=240,
                wires=[["ui_chart_bpm"], ["ui_chart_temp"], ["ui_gauge_temp"], ["ui_gauge_umid"], ["ui_gauge_bpm"], ["ui_tabela"], ["fn_avaliar"]]))
nodes.append(no(id="fn_avaliar", type="function", z=TAB, name="Avaliar limites (Fog)", func=FUNC_AVALIAR, outputs=3, timeout=0,
                noerr=0, initialize="", finalize="", libs=[], x=740, y=580,
                wires=[["ui_painel_alerta"], ["ui_notificacao"], ["ui_texto_alerta"]]))
nodes.append(no(id="fn_estado", type="function", z=TAB, name="Estado do dispositivo", func=FUNC_ESTADO, outputs=1, timeout=0,
                noerr=0, initialize="", finalize="", libs=[], x=480, y=820, wires=[["ui_painel_estado"]]))
nodes.append(no(id="fn_alerta_disp", type="function", z=TAB, name="Alerta publicado pelo dispositivo", func=FUNC_ALERTA_DISP, outputs=1, timeout=0,
                noerr=0, initialize="", finalize="", libs=[], x=500, y=700, wires=[["ui_texto_alerta_disp"]]))

# ---- Dashboard -------------------------------------------------------------
nodes.append(no(id="cmt_dash", type="comment", z=TAB, name="3. Visualizacao: Dashboard 2.0 (@flowfuse/node-red-dashboard)",
                info="Pagina /dashboard/paciente01: graficos de bpm e temperatura, medidores, painel de alerta com cor, notificacao e tabela.", x=1180, y=40, wires=[]))

def chart(id_, nome, label, ordem, ymin, ymax, y):
    return no(id=id_, type="ui-chart", z=TAB, group="grp_graficos", name=nome, label=label, order=ordem, chartType="line",
              category="topic", categoryType="msg", xAxisLabel="hora", xAxisProperty="timestamp", xAxisPropertyType="msg",
              xAxisType="time", xAxisFormat="", xAxisFormatType="auto", xmin="", xmax="", yAxisLabel=label, yAxisProperty="payload",
              yAxisPropertyType="msg", ymin=str(ymin), ymax=str(ymax), bins=10, action="append", stackSeries=False, pointShape="circle",
              pointRadius=3, showLegend=True, removeOlder="30", removeOlderUnit="60", removeOlderPoints="",
              colors=["#c62828", "#1e88e5", "#FF7F0E", "#2CA02C", "#A347E1", "#D62728", "#FF9896", "#9467BD", "#C5B0D5"],
              textColor=["#666666"], textColorDefault=True, gridColor=["#e5e5e5"], gridColorDefault=True, width="6", height="7",
              className="", interpolation="linear", x=1100, y=y, wires=[[]])

nodes.append(chart("ui_chart_bpm", "Grafico bpm", "Frequencia cardiaca (bpm)", 1, 0, 200, 140))
nodes.append(chart("ui_chart_temp", "Grafico temperatura", "Temperatura (C)", 2, 20, 42, 200))

def gauge(id_, nome, titulo, unidades, ordem, vmin, vmax, segmentos, y):
    return no(id=id_, type="ui-gauge", z=TAB, name=nome, group="grp_medidores", order=ordem, value="payload", valueType="msg",
              width="4", height="4", gtype="gauge-half", gstyle="needle", title=titulo, alwaysShowTitle=False,
              floatingTitlePosition="top-left", units=unidades, icon="", prefix="", suffix="", segments=segmentos, min=vmin, max=vmax,
              sizeThickness=16, sizeGap=4, sizeKeyThickness=8, styleRounded=True, styleGlow=False, className="", x=1100, y=y, wires=[[]])

nodes.append(gauge("ui_gauge_temp", "Medidor temperatura", "Temperatura", "C", 1, 30, 42,
                   [{"from": 30, "color": "#1e88e5"}, {"from": 35, "color": "#43a047"}, {"from": 38, "color": "#e53935"}], 260))
nodes.append(gauge("ui_gauge_umid", "Medidor umidade", "Umidade", "%", 2, 0, 100,
                   [{"from": 0, "color": "#90caf9"}, {"from": 30, "color": "#43a047"}, {"from": 70, "color": "#fb8c00"}], 320))
nodes.append(gauge("ui_gauge_bpm", "Medidor bpm", "Frequencia cardiaca", "bpm", 3, 0, 200,
                   [{"from": 0, "color": "#e53935"}, {"from": 50, "color": "#43a047"}, {"from": 120, "color": "#e53935"}], 380))

nodes.append(no(id="ui_tabela", type="ui-table", z=TAB, group="grp_tabela", name="Tabela ultimas amostras", label="Ultimas 12 amostras (mais recente primeiro)",
                order=1, width="12", height="8", maxrows=12, passthru=False, autocols=True, showSearch=False, deselect=True,
                selectionType="none", columns=[], mobileBreakpoint="sm", mobileBreakpointType="defaults", action="replace", className="",
                x=1100, y=440, wires=[[]]))

nodes.append(no(id="ui_painel_alerta", type="ui-template", z=TAB, group="grp_alerta", page="", ui="", name="Painel de alerta (cor)",
                order=1, width="12", height="2", head="", format=TEMPLATE_PAINEL, storeOutMessages=True, passthru=True,
                resendOnRefresh=True, templateScope="local", className="", x=1100, y=540, wires=[[]]))
nodes.append(no(id="ui_notificacao", type="ui-notification", z=TAB, ui="ui_base_cardioia", name="Notificacao de alerta", position="top right",
                colorDefault=False, color="#c62828", displayTime="8", showCountdown=True, outputs=1, allowDismiss=True, dismissText="Fechar",
                allowConfirm=False, confirmText="Confirmar", raw=False, className="", x=1100, y=600, wires=[[]]))
nodes.append(no(id="ui_texto_alerta", type="ui-text", z=TAB, group="grp_alerta", order=2, width="6", height="1", name="Texto ultimo alerta (Fog)",
                label="Avaliacao Fog", format="{{msg.payload}}", layout="row-spread", style=False, font="", fontSize=16, color="#717171",
                wrapText=True, className="", value="payload", valueType="msg", x=1100, y=660, wires=[]))
nodes.append(no(id="ui_texto_alerta_disp", type="ui-text", z=TAB, group="grp_alerta", order=3, width="6", height="1", name="Texto alerta do dispositivo",
                label="Avaliacao no dispositivo (Edge)", format="{{msg.payload}}", layout="row-spread", style=False, font="", fontSize=16, color="#717171",
                wrapText=True, className="", value="payload", valueType="msg", x=1100, y=720, wires=[]))
nodes.append(no(id="ui_painel_estado", type="ui-template", z=TAB, group="grp_estado", page="", ui="", name="Painel de estado",
                order=1, width="12", height="1", head="", format=TEMPLATE_ESTADO, storeOutMessages=True, passthru=True,
                resendOnRefresh=True, templateScope="local", className="", x=1100, y=820, wires=[[]]))

saida = sys.argv[1] if len(sys.argv) > 1 else "flows.json"
with open(saida, "w", encoding="utf-8") as f:
    json.dump(nodes, f, ensure_ascii=False, indent=2)
print("gerado", saida, "com", len(nodes), "nos")
