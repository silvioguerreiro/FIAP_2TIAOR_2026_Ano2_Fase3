#!/usr/bin/env python3
"""
CardioIA, Fase 3, Ir Além 2: extrai as séries temporais reais do protótipo a partir dos logs de evidência.

Autor: Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55. Data: 31/10/2026.

Lê os logs do monitor serial das Partes 1 e 2 (assets/evidencias) e grava dois CSVs em
src/ir_alem2_ia_series/dados/ com uma linha por amostra do dispositivo:
    ts, temp_c, umid_pct, bpm, mov, alertas, origem
Parte 1: linhas [ONLINE] e [OFFLINE] com CSV (as linhas [SYNC] repetem as amostras offline e são ignoradas).
Parte 2: linhas [ONLINE] com JSON e [OFFLINE] com pares chave=valor (as amostras "sync" repetem as offline).

Uso: python3 scripts/extrair_series_prototipo.py
"""
import csv
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOG_P1 = RAIZ / "assets/evidencias/parte1/log_serial_parte1_wokwi_2026-10-30.txt"
LOG_P2 = RAIZ / "assets/evidencias/parte2/log_serial_parte2_wokwi_2026-10-30.txt"
SAIDA = RAIZ / "src/ir_alem2_ia_series/dados"
SAIDA.mkdir(parents=True, exist_ok=True)
CAMPOS = ["ts", "temp_c", "umid_pct", "bpm", "mov", "alertas", "origem"]


def parte1():
    linhas = []
    padrao = re.compile(r"^\[(ONLINE|OFFLINE)\] (\d+),([\d.]+),([\d.]+),(\d+),(\d),(\d+)")
    for l in LOG_P1.read_text(encoding="utf-8").splitlines():
        m = padrao.match(l)
        if m:
            estado, ts, temp, umid, bpm, mov, al = m.groups()
            linhas.append(dict(ts=int(ts), temp_c=float(temp), umid_pct=float(umid), bpm=int(bpm), mov=int(mov),
                               alertas=int(al), origem="online" if estado == "ONLINE" else "offline"))
    linhas.sort(key=lambda r: r["ts"])
    return linhas


def parte2():
    linhas = []
    for l in LOG_P2.read_text(encoding="utf-8").splitlines():
        if l.startswith("[ONLINE] cardioia/") and "<- {" in l:
            j = json.loads(l.split("<- ", 1)[1])
            if j.get("origem") == "sync":
                continue
            linhas.append(dict(ts=int(j["ts"]), temp_c=float(j["temp"]), umid_pct=float(j["umid"]), bpm=int(j["bpm"]),
                               mov=int(j["mov"]), alertas=int(j["alertas"]), origem="online"))
        elif l.startswith("[OFFLINE] seq="):
            kv = dict(re.findall(r"(\w+)=([\d.]+)", l.split("|")[0]))
            linhas.append(dict(ts=int(kv["ts"]), temp_c=float(kv["temp"]), umid_pct=float(kv["umid"]), bpm=int(kv["bpm"]),
                               mov=int(kv["mov"]), alertas=int(kv["alertas"]), origem="offline"))
    # o log resumiu trechos repetitivos entre parenteses; as amostras existentes bastam para a demonstracao
    vistos, unicos = set(), []
    for r in sorted(linhas, key=lambda r: r["ts"]):
        if r["ts"] not in vistos:
            vistos.add(r["ts"]); unicos.append(r)
    return unicos


for nome, dados in (("prototipo_parte1_2026-10-30.csv", parte1()), ("prototipo_parte2_2026-10-30.csv", parte2())):
    with open(SAIDA / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(dados)
    print(f"{nome}: {len(dados)} amostras")
