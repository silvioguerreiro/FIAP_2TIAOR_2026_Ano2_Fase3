"""Figuras dos relatorios da Fase 3 (CardioIA): diagrama de blocos, maquina de
estados e arquitetura Edge/Fog/Cloud. Desenho manual com matplotlib para
controle total do layout (nomes de arquivo em ASCII)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

AZUL = "#1f4e79"; AZUL_CLARO = "#dbe8f5"; VERDE = "#2e7d32"; VERDE_CLARO = "#e3f2e6"
LARANJA = "#b85c00"; LARANJA_CLARO = "#fdebd3"; CINZA = "#444444"; CINZA_CLARO = "#f2f2f2"
ROXO = "#5e35b1"; ROXO_CLARO = "#ece6f7"; VERMELHO = "#b71c1c"; VERMELHO_CLARO = "#fbe4e4"
plt.rcParams["font.family"] = "DejaVu Sans"


def caixa(ax, x, y, w, h, titulo, corpo="", cor=AZUL, fundo=AZUL_CLARO, ts=10.5, cs=8.6, lw=1.4, estilo="round,pad=0.02,rounding_size=0.12"):
    p = FancyBboxPatch((x, y), w, h, boxstyle=estilo, linewidth=lw, edgecolor=cor, facecolor=fundo, zorder=2)
    ax.add_patch(p)
    if corpo:
        ax.text(x + w / 2, y + h - 0.16, titulo, ha="center", va="top", fontsize=ts, fontweight="bold", color=cor, zorder=3)
        ax.text(x + w / 2, y + h / 2 - 0.12, corpo, ha="center", va="center", fontsize=cs, color="#222222", zorder=3, linespacing=1.35)
    else:
        ax.text(x + w / 2, y + h / 2, titulo, ha="center", va="center", fontsize=ts, fontweight="bold", color=cor, zorder=3)
    return (x, y, w, h)


def regiao(ax, x, y, w, h, titulo, cor, fundo, ts=11, direita=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.2", linewidth=1.2, edgecolor=cor, facecolor=fundo, zorder=1, linestyle="--")
    ax.add_patch(p)
    if direita:
        ax.text(x + w - 0.18, y + h - 0.14, titulo, ha="right", va="top", fontsize=ts, fontweight="bold", color=cor, zorder=3)
    else:
        ax.text(x + 0.18, y + h - 0.14, titulo, ha="left", va="top", fontsize=ts, fontweight="bold", color=cor, zorder=3)


def seta(ax, p0, p1, texto="", cor=CINZA, curva=0.0, ls="-", lw=1.5, pos=0.5, desloc=(0, 0.14), fs=8.2, estilo="-|>"):
    a = FancyArrowPatch(p0, p1, arrowstyle=estilo, mutation_scale=14, linewidth=lw, color=cor, connectionstyle=f"arc3,rad={curva}", linestyle=ls, zorder=4, shrinkA=2, shrinkB=2)
    ax.add_patch(a)
    if texto:
        xm = p0[0] + (p1[0] - p0[0]) * pos + desloc[0]
        ym = p0[1] + (p1[1] - p0[1]) * pos + desloc[1]
        # deslocamento perpendicular para arcos
        if curva:
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            xm += dy * curva * 0.5
            ym += -dx * curva * 0.5
        ax.text(xm, ym, texto, ha="center", va="center", fontsize=fs, color=cor, zorder=5,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none", alpha=0.95))


def novo(w, h):
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


# ---------------------------------------------------------------------------
# Figura 1: diagrama de blocos do dispositivo (Parte 1)
# ---------------------------------------------------------------------------
fig, ax = novo(13.5, 7.6)
regiao(ax, 0.3, 0.4, 3.0, 6.8, "Sensores simulados (Wokwi)", VERDE, VERDE_CLARO)
caixa(ax, 0.55, 5.55, 2.5, 1.25, "DHT22", "temperatura e umidade\nleitura a cada 5 s (minimo 2 s)\nGPIO 15", cor=VERDE, fundo="white")
caixa(ax, 0.55, 3.95, 2.5, 1.25, "Botao de pressao", "cada pressao = 1 batimento\nbpm pela media dos intervalos\nGPIO 4, interrupcao", cor=VERDE, fundo="white")
caixa(ax, 0.55, 2.35, 2.5, 1.25, "MPU6050", "aceleracao em 3 eixos\nmovimento por variacao do vetor\nI2C (GPIO 21 e 22)", cor=VERDE, fundo="white")
caixa(ax, 0.55, 0.7, 2.5, 1.25, "Chave deslizante", "Wi-Fi simulado (booleano)\nHIGH = conectado\nGPIO 18", cor=VERDE, fundo="white")

regiao(ax, 3.7, 0.4, 6.0, 6.8, "ESP32: processamento e armazenamento local (Edge)", AZUL, AZUL_CLARO)
caixa(ax, 3.95, 5.1, 2.6, 1.6, "Coleta (a cada 5 s)", "amostra de 16 bytes:\nts, temperatura, umidade,\nbpm, movimento, alertas", cor=AZUL, fundo="white")
caixa(ax, 6.85, 5.1, 2.6, 1.6, "Avaliacao local", "bpm > 120 ou bpm < 50\ntemp > 38 C ou temp < 35 C\nsem movimento acima do limite", cor=AZUL, fundo="white")
caixa(ax, 3.95, 2.85, 2.6, 1.5, "Maquina de estados", "ONLINE: envia em tempo real\n(LED verde aceso, GPIO 25)\nOFFLINE: armazena localmente", cor=AZUL, fundo="white")
caixa(ax, 6.85, 2.85, 2.6, 1.5, "Buffer circular (RAM)", "3.000 amostras x 16 B = 48 KB\ncerca de 4 h 10 min offline\nsobrescreve a mais antiga e conta", cor=AZUL, fundo="white")
caixa(ax, 3.95, 0.7, 2.6, 1.45, "SPIFFS (opcional)", "/pendentes.csv, flag USAR_SPIFFS\nvolatil no Wokwi; persistente\nem chip real (limite de 1 MB)", cor=AZUL, fundo="white")
caixa(ax, 6.85, 0.7, 2.6, 1.45, "Dimensionamento", "5 s por amostra = 720 por hora\n3.000 amostras = 4 h 10 min\n48 KB de 320 KB de RAM (15%)", cor=AZUL, fundo="white")

regiao(ax, 10.1, 4.0, 3.1, 3.2, "Atuadores locais", VERMELHO, VERMELHO_CLARO)
caixa(ax, 10.35, 5.75, 2.6, 1.0, "LED vermelho (GPIO 26)", "aceso enquanto houver alerta", cor=VERMELHO, fundo="white", ts=9.5)
caixa(ax, 10.35, 4.3, 2.6, 1.0, "Buzzer (GPIO 27)", "bip de 200 ms por amostra em alerta", cor=VERMELHO, fundo="white", ts=9.5)

regiao(ax, 10.1, 0.4, 3.1, 3.2, "Saida para a nuvem (Parte 1)", LARANJA, LARANJA_CLARO)
caixa(ax, 10.35, 0.75, 2.6, 2.2, "Monitor serial (115200)", "nuvem simulada: uma linha CSV\npor amostra\n\nts_s,temp_c,umid_pct,\nbpm,mov,alertas\n\nprefixos [ONLINE] e [SYNC]", cor=LARANJA, fundo="white", ts=9.5)

# sensores -> coleta
seta(ax, (3.05, 6.17), (3.95, 6.1))
seta(ax, (3.05, 4.57), (3.95, 5.7))
seta(ax, (3.05, 2.97), (3.95, 5.3), curva=-0.25)
seta(ax, (3.05, 1.32), (3.95, 3.3), curva=-0.2, texto="estado da\nconexao", pos=0.35, desloc=(0.25, -0.1), fs=7.6)
# coleta -> avaliacao -> estado
seta(ax, (6.55, 5.9), (6.85, 5.9), texto="amostra")
seta(ax, (8.15, 5.1), (5.5, 4.35), curva=0.15, texto="amostra com alertas", pos=0.5, desloc=(0.3, -0.12))
# avaliacao -> atuadores
seta(ax, (9.45, 6.1), (10.35, 6.25), texto="alerta", fs=8)
seta(ax, (9.45, 5.6), (10.35, 4.8))
# estado -> buffer / serial
seta(ax, (6.55, 3.6), (6.85, 3.6), texto="OFFLINE", fs=8)
seta(ax, (6.55, 3.0), (10.35, 2.3), curva=0.1, texto="ONLINE: envio imediato", pos=0.5, desloc=(0.0, 0.0), fs=8)
seta(ax, (9.45, 3.4), (10.35, 2.75), texto="ao voltar ONLINE: SYNC dos\npendentes em ordem cronologica,\ndepois limpa o buffer", pos=0.35, desloc=(0.35, 0.72), fs=7.6)
seta(ax, (6.85, 2.95), (6.3, 2.15), ls="--", texto="espelho\n(flag)", fs=7.6, desloc=(-0.45, 0.0), estilo="<|-|>")
fig.savefig("fig_p1_diagrama_blocos.png", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figura 2: maquina de estados online/offline (Parte 1)
# ---------------------------------------------------------------------------
fig, ax = novo(13.5, 6.2)
off = caixa(ax, 0.6, 1.6, 3.7, 3.0, "OFFLINE", "a cada 5 s: coleta a amostra,\navalia os limites e aciona LED e buzzer;\narmazena no buffer circular em RAM\n(e no SPIFFS, se habilitado);\nbuffer cheio: descarta a mais antiga\ne incrementa o contador de descartes", cor=VERMELHO, fundo=VERMELHO_CLARO, ts=12, cs=8.8)
syn = caixa(ax, 4.9, 1.6, 3.7, 3.0, "SINCRONIZANDO", "percorre o buffer da amostra mais antiga\na mais recente; imprime o cabecalho e\numa linha CSV por amostra com o prefixo\n[SYNC]; limpa o buffer e atualiza os\ncontadores (sincronizadas, descartadas);\na coleta nao e interrompida", cor=LARANJA, fundo=LARANJA_CLARO, ts=12, cs=8.8)
onl = caixa(ax, 9.2, 1.6, 3.7, 3.0, "ONLINE", "a cada 5 s: coleta a amostra,\navalia os limites e aciona LED e buzzer;\nenvia a linha CSV imediatamente pela\nserial com o prefixo [ONLINE];\nLED verde aceso; linha [BUFFER]\nde status a cada 30 s", cor=VERDE, fundo=VERDE_CLARO, ts=12, cs=8.8)
# estado inicial
ax.add_patch(plt.Circle((2.45, 5.6), 0.13, color="black", zorder=4))
seta(ax, (2.45, 5.45), (2.45, 4.6), texto="chave desligada no boot", fs=8.5, desloc=(1.2, 0.0))
seta(ax, (2.6, 5.6), (11.05, 4.6), curva=-0.12, texto="chave ligada no boot", fs=8.5, pos=0.55, desloc=(0, 0.0))
# transicoes
seta(ax, (4.3, 3.1), (4.9, 3.1), texto="chave ligada e\nbuffer com pendentes", fs=8.3, desloc=(0, 0.55))
seta(ax, (8.6, 3.1), (9.2, 3.1), texto="todas as pendentes\nenviadas; buffer limpo", fs=8.3, desloc=(0, 0.55))
seta(ax, (4.3, 1.9), (9.2, 1.9), curva=0.25, texto="chave ligada e buffer vazio", fs=8.5, pos=0.5, desloc=(0, 0.0))
seta(ax, (9.2, 1.65), (4.3, 1.65), curva=-0.45, texto="chave desligada (conexao perdida): continua coletando", fs=8.5, pos=0.5, desloc=(0, 0.0), cor=VERMELHO)
ax.text(6.75, 5.85, "Eventos: a chave deslizante (GPIO 18) e lida a cada iteracao do loop; a transicao OFFLINE para ONLINE dispara a sincronizacao antes de retomar o envio em tempo real.", ha="center", va="center", fontsize=8.6, color=CINZA)
fig.savefig("fig_p1_maquina_estados.png", facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figura 3: arquitetura Edge, Fog e Cloud (Parte 2)
# ---------------------------------------------------------------------------
fig, ax = novo(13.5, 8.2)
# Cloud (topo)
regiao(ax, 0.3, 5.75, 12.9, 2.25, "Cloud: servicos na internet", ROXO, ROXO_CLARO)
caixa(ax, 0.55, 5.95, 2.4, 1.5, "Servidores NTP", "pool.ntp.org\ntime.google.com\n(fuso UTC-4)", cor=ROXO, fundo="white", ts=10, cs=8.4)
caixa(ax, 3.2, 5.95, 2.9, 1.5, "Broker MQTT", "HiveMQ Cloud: TLS 8883,\nusuario e senha em config.h\nou broker.hivemq.com:1883\n(publico, so demonstracao)", cor=ROXO, fundo="white", ts=10.5, cs=8.2)
caixa(ax, 6.6, 5.95, 3.0, 1.5, "InfluxDB e Grafana Cloud", "opcionais: historico e\nvisualizacao avancada\n(nao implementados)", cor=ROXO, fundo="white", ts=10, cs=8.4)
caixa(ax, 10.0, 5.95, 2.95, 1.5, "API REST (Ir Alem 1)", "opcional: Python, recebe\nsinais por HTTP, verifica\nrisco e dispara e-mail", cor=ROXO, fundo="white", ts=10, cs=8.4)
# Fog (meio, so a direita)
regiao(ax, 6.4, 3.15, 6.8, 2.25, "Fog: processamento proximo ao uso", AZUL, AZUL_CLARO, direita=True)
caixa(ax, 6.65, 3.3, 3.95, 1.75, "Node-RED 4.1 (computador local)", "mqtt in (3 topicos, JSON), normalizacao,\nlimites no deploy, avaliacao Fog combinada\ncom a do dispositivo, historico de 12 amostras;\nDashboard 2.0: graficos de bpm e temperatura,\nmedidores, painel de alerta com cor,\nnotificacao, tabela e estado do enlace", cor=AZUL, fundo="white", ts=10, cs=7.9)
caixa(ax, 10.9, 3.3, 2.05, 1.75, "Navegador", "profissional de saude\nlocalhost:1880/dashboard\natualizacao em tempo real", cor=AZUL, fundo="white", ts=10, cs=8.0)
# Edge (base)
regiao(ax, 0.3, 0.35, 12.9, 2.5, "Edge: dispositivo vestivel", VERDE, VERDE_CLARO)
caixa(ax, 0.55, 0.6, 2.35, 1.85, "Sensores", "DHT22 (temp., umidade)\nbotao de batimentos\nMPU6050 (movimento)\nchave: queda do enlace", cor=VERDE, fundo="white", ts=10, cs=8.2)
caixa(ax, 3.2, 0.6, 2.9, 1.85, "ESP32 (firmware)", "coleta a cada 5 s, carimbo NTP\navaliacao local dos limites\nWi-Fi Wokwi-GUEST + MQTT\n(PubSubClient), JSON compacto,\ntestamento e reconexao", cor=VERDE, fundo="white", ts=10.5, cs=8.0)
caixa(ax, 6.6, 1.6, 6.35, 0.85, "Atuadores locais", "LED vermelho e buzzer: alerta imediato mesmo sem conexao; LED verde: online", cor=VERDE, fundo="white", ts=9.8, cs=8.0)
caixa(ax, 6.6, 0.6, 6.35, 0.85, "Resiliencia offline", "buffer circular de 3.000 amostras (20 B cada, 60 KB, 4 h 10 min de autonomia);\nao religar, sincroniza pelo MQTT em ordem cronologica, com origem sync e carimbo original", cor=VERDE, fundo="white", ts=9.8, cs=8.0)
# setas
seta(ax, (2.9, 1.5), (3.2, 1.5))
seta(ax, (6.1, 2.0), (6.6, 2.0), texto="alerta", fs=7.8, desloc=(0, 0.2))
seta(ax, (6.1, 1.0), (6.6, 1.0), estilo="<|-|>")
seta(ax, (4.65, 2.45), (4.65, 5.95), texto="MQTT publish\n.../sinais, .../alertas, .../estado\nTCP 1883 ou TLS 8883\n1 mensagem JSON a cada 5 s", fs=8.0, desloc=(1.05, 0.0), cor=VERDE, lw=1.8)
seta(ax, (3.35, 2.45), (2.5, 5.95), ls="--", lw=1.0, texto="hora NTP", fs=7.8, desloc=(-0.55, 0.0))
seta(ax, (6.1, 6.5), (7.6, 5.05), texto="MQTT subscribe\ncardioia/grupo55/paciente01/#", fs=8.0, pos=0.5, desloc=(-1.0, -0.05), cor=ROXO, lw=1.8)
seta(ax, (8.9, 5.05), (8.3, 5.95), ls="--", lw=1.0, texto="HTTP\n(opcional)", fs=7.6, desloc=(0.5, 0.1))
seta(ax, (10.3, 5.05), (11.2, 5.95), ls="--", lw=1.0, texto="HTTP POST\n(opcional)", fs=7.6, desloc=(0.6, 0.0))
seta(ax, (10.6, 4.2), (10.9, 4.2))
ax.text(6.75, 0.12, "Fluxo principal: a borda coleta, decide e armazena; o broker na nuvem distribui; o Node-RED (fog) normaliza, avalia e exibe. Tracejado: integracoes opcionais.", ha="center", va="center", fontsize=8.4, color=CINZA)
fig.savefig("fig_p2_arquitetura_edge_fog_cloud.png", facecolor="white")
plt.close(fig)
print("ok")
