"""
CardioIA, Fase 3, Ir Além 1: cliente REST que envia leituras simuladas e consome a API.

Projeto : CardioIA (FIAP, curso de Inteligência Artificial, Ano 2)
Autor   : Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55
Data    : 31/10/2026

Simula o wearable publicando na API (biblioteca requests) em quatro cenários
encadeados: repouso normal, taquicardia, febre e ausência de movimento. Depois
consome os endpoints de consulta (histórico, último sinal, resumo do paciente,
alertas e notificações) e imprime um resumo. Uso:

    python -m cliente.cliente_rest --url http://127.0.0.1:8000 --intervalo 0.2

O intervalo entre envios é curto para a demonstração; o dispositivo real
publica a cada 5 s. O carimbo de tempo é simulado com passo de 5 s por amostra
para que a regra de ausência de movimento (600 s) possa ser exercitada.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timezone

import requests

DISP = "cardioia-g55-p01"


def amostra(seq: int, ts: int, temp: float, bpm: int, mov: int, umid: float = 45.0, alertas: int = 0) -> dict:
    return {"disp": DISP, "seq": seq, "ts": ts, "tsrel": 0, "temp": round(temp, 2), "umid": round(umid, 1),
            "bpm": bpm, "mov": mov, "alertas": alertas, "origem": "cliente"}


def cenarios(inicio: int, aleatorio: random.Random) -> list[tuple[str, dict]]:
    """Gera a sequência de amostras (nome do cenário, payload) com passo de 5 s."""
    seq, ts, saida = 0, inicio, []

    def proxima(nome, temp, bpm, mov, alertas=0):
        nonlocal seq, ts
        seq += 1
        ts += 5
        saida.append((nome, amostra(seq, ts, temp, bpm, mov, 40 + aleatorio.random() * 10, alertas)))

    for _ in range(6):                       # repouso normal: 36,4 a 36,8 C, 62 a 78 bpm, movimento ocasional
        proxima("normal", 36.4 + aleatorio.random() * 0.4, aleatorio.randint(62, 78), 1 if aleatorio.random() < 0.5 else 0)
    for bpm in (118, 131, 146, 152, 149, 140, 124, 110):   # episódio de taquicardia
        proxima("taquicardia", 36.7, bpm, 1, alertas=0x01 if bpm > 120 else 0)
    for temp in (37.4, 37.9, 38.2, 38.6, 38.8, 38.5):      # febre em evolução
        proxima("febre", temp, aleatorio.randint(88, 98), 0, alertas=0x04 if temp > 38.0 else 0)
    proxima("movimento", 37.9, 84, 1)                     # último movimento registrado
    for i in range(130):                                   # 130 x 5 s = 650 s parado: ausência de movimento
        proxima("imovel", 37.6 - min(i, 40) * 0.01, aleatorio.randint(70, 80), 0)
    return saida


def executar(url: str, intervalo: float, semente: int) -> int:
    aleatorio = random.Random(semente)
    inicio = int(datetime.now(timezone.utc).timestamp()) - 5 * 160
    sessao = requests.Session()
    saude = sessao.get(f"{url}/saude", timeout=5).json()
    print(f"API {saude['versao']} em {url} | e-mail em modo {saude['email_modo']} | limites {saude['limites']}")

    enviados, com_alerta, emails = 0, 0, 0
    ultimo_cenario = None
    for nome, payload in cenarios(inicio, aleatorio):
        resp = sessao.post(f"{url}/sinais", json=payload, timeout=5)
        resp.raise_for_status()
        corpo = resp.json()
        enviados += 1
        if corpo["alertas"]:
            com_alerta += 1
        if corpo["email_enviado"]:
            emails += 1
        if nome != ultimo_cenario or corpo["alertas"] or corpo["email_enviado"]:
            tipos = ", ".join(a["tipo"] for a in corpo["alertas"]) or "nenhum"
            print(f"[{nome:11s}] seq={payload['seq']:3d} bpm={payload['bpm']:3d} temp={payload['temp']:5.2f} mov={payload['mov']}"
                  f" -> alertas: {tipos}{' | E-MAIL ENVIADO' if corpo['email_enviado'] else ''}")
        ultimo_cenario = nome
        time.sleep(intervalo)

    print("\nConsultas à API:")
    ultimo = sessao.get(f"{url}/sinais/ultimo", params={"disp": DISP}, timeout=5).json()
    print(f"  GET /sinais/ultimo      -> seq {ultimo['sinal']['seq']}, alertas {[a['tipo'] for a in ultimo['alertas_avaliados']]}")
    hist = sessao.get(f"{url}/sinais", params={"disp": DISP, "limite": 1000}, timeout=5).json()
    print(f"  GET /sinais             -> {len(hist)} amostras armazenadas")
    alertas = sessao.get(f"{url}/alertas", params={"disp": DISP, "limite": 1000}, timeout=5).json()
    print(f"  GET /alertas            -> {len(alertas)} amostras com alerta")
    resumo = sessao.get(f"{url}/pacientes/{DISP}/resumo", timeout=5).json()
    print(f"  GET /pacientes/.../resumo -> total {resumo['total_amostras']}, alertas ativos {resumo['alertas_ativos']}")
    notif = sessao.get(f"{url}/notificacoes", timeout=5).json()
    print(f"  GET /notificacoes       -> {len(notif)} e-mails gerados:")
    for n in notif:
        print(f"      {n['enviado_em'][:19]} [{n['modo']}] {n['assunto']} (entregue={n['entregue']})")
    print(f"\nResumo: {enviados} amostras enviadas, {com_alerta} com alerta, {emails} e-mails disparados.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Cliente REST do CardioIA (Ir Alem 1)")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--intervalo", type=float, default=0.2, help="segundos entre envios (demonstracao)")
    p.add_argument("--semente", type=int, default=55)
    args = p.parse_args(argv)
    try:
        return executar(args.url.rstrip("/"), args.intervalo, args.semente)
    except requests.RequestException as erro:
        print(f"erro ao falar com a API em {args.url}: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
