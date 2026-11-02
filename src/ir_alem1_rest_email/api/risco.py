"""
CardioIA, Fase 3, Ir Além 1: módulo de verificação de risco.

Autor: Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55. Data: 31/10/2026.

Regras explícitas e testáveis, com os mesmos limites do firmware (Parte 1) e do
fluxo Node-RED (Parte 2). Cada regra é uma função pura que recebe a amostra e
o contexto do paciente (instante do último movimento, instante da última
amostra) e devolve um Alerta ou None. A função avaliar() aplica todas as
regras e acrescenta os alertas que o próprio dispositivo já sinalizou na
máscara de bits, para que a decisão da borda não seja perdida na nuvem.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from .config import LIMITES, LimitesRisco
from .modelos import Alerta, SinalVital

# Bits da máscara "alertas" publicada pelo dispositivo (Partes 1 e 2).
BITS_DISPOSITIVO = {
    0x01: "taquicardia",
    0x02: "bradicardia",
    0x04: "febre",
    0x08: "hipotermia",
    0x10: "sem_movimento",
}

GRAVIDADE = {
    "taquicardia": "alta",
    "bradicardia": "alta",
    "febre": "media",
    "hipotermia": "alta",
    "sem_movimento": "alta",
    "sem_dados": "media",
}


def regra_taquicardia(s: SinalVital, _ctx: dict, lim: LimitesRisco) -> Optional[Alerta]:
    """Frequência cardíaca acima do limite superior."""
    if s.bpm > lim.bpm_maximo:
        return Alerta(tipo="taquicardia", gravidade=GRAVIDADE["taquicardia"], valor=s.bpm, limite=lim.bpm_maximo,
                      descricao=f"frequencia cardiaca de {s.bpm} bpm acima de {lim.bpm_maximo} bpm")
    return None


def regra_bradicardia(s: SinalVital, _ctx: dict, lim: LimitesRisco) -> Optional[Alerta]:
    """Frequência cardíaca abaixo do limite inferior. bpm igual a zero é ausência de leitura, não parada."""
    if 0 < s.bpm < lim.bpm_minimo:
        return Alerta(tipo="bradicardia", gravidade=GRAVIDADE["bradicardia"], valor=s.bpm, limite=lim.bpm_minimo,
                      descricao=f"frequencia cardiaca de {s.bpm} bpm abaixo de {lim.bpm_minimo} bpm")
    return None


def regra_febre(s: SinalVital, _ctx: dict, lim: LimitesRisco) -> Optional[Alerta]:
    """Temperatura acima do limite de febre."""
    if s.temp is not None and s.temp > lim.temperatura_maxima:
        return Alerta(tipo="febre", gravidade=GRAVIDADE["febre"], valor=s.temp, limite=lim.temperatura_maxima,
                      descricao=f"temperatura de {s.temp:.1f} C acima de {lim.temperatura_maxima:.1f} C")
    return None


def regra_hipotermia(s: SinalVital, _ctx: dict, lim: LimitesRisco) -> Optional[Alerta]:
    """Temperatura abaixo do limite de hipotermia."""
    if s.temp is not None and s.temp < lim.temperatura_minima:
        return Alerta(tipo="hipotermia", gravidade=GRAVIDADE["hipotermia"], valor=s.temp, limite=lim.temperatura_minima,
                      descricao=f"temperatura de {s.temp:.1f} C abaixo de {lim.temperatura_minima:.1f} C")
    return None


def regra_sem_movimento(s: SinalVital, ctx: dict, lim: LimitesRisco) -> Optional[Alerta]:
    """Ausência de movimento por mais tempo que o limite, medida pelo instante do último movimento.

    O contexto traz "instante" (instante desta amostra) e "ultimo_movimento" (instante
    do último movimento conhecido do paciente, já atualizado se esta amostra tem mov=1).
    Sem nenhum movimento conhecido ainda, a regra não dispara (evita falso alerta no início).
    """
    ultimo: Optional[datetime] = ctx.get("ultimo_movimento")
    agora: Optional[datetime] = ctx.get("instante")
    if s.mov or ultimo is None or agora is None:
        return None
    parado = (agora - ultimo).total_seconds()
    if parado > lim.sem_movimento_s:
        return Alerta(tipo="sem_movimento", gravidade=GRAVIDADE["sem_movimento"], valor=round(parado), limite=lim.sem_movimento_s,
                      descricao=f"sem movimento ha {int(parado)} s (limite {lim.sem_movimento_s} s)")
    return None


REGRAS: tuple[Callable[[SinalVital, dict, LimitesRisco], Optional[Alerta]], ...] = (
    regra_taquicardia,
    regra_bradicardia,
    regra_febre,
    regra_hipotermia,
    regra_sem_movimento,
)


def alertas_do_dispositivo(mascara: int) -> list[str]:
    """Traduz a máscara de bits publicada pelo ESP32 em nomes de alerta."""
    return [nome for bit, nome in BITS_DISPOSITIVO.items() if mascara & bit]


def avaliar(s: SinalVital, ctx: Optional[dict] = None, limites: LimitesRisco = LIMITES) -> list[Alerta]:
    """Aplica todas as regras e combina com a avaliação feita no dispositivo.

    Devolve a lista de alertas sem duplicatas, na ordem das regras. Um alerta
    sinalizado apenas pelo dispositivo (por exemplo, ausência de movimento
    avaliada na borda com a janela de demonstração) entra com a descrição
    "sinalizado pelo dispositivo".
    """
    ctx = ctx or {}
    encontrados: list[Alerta] = []
    tipos: set[str] = set()
    for regra in REGRAS:
        a = regra(s, ctx, limites)
        if a is not None and a.tipo not in tipos:
            encontrados.append(a)
            tipos.add(a.tipo)
    for nome in alertas_do_dispositivo(s.alertas):
        if nome not in tipos:
            encontrados.append(Alerta(tipo=nome, gravidade=GRAVIDADE.get(nome, "media"),
                                      descricao=f"{nome} sinalizado pelo dispositivo (mascara {s.alertas})"))
            tipos.add(nome)
    return encontrados


def verificar_sem_dados(ultima_amostra: Optional[datetime], agora: datetime, limites: LimitesRisco = LIMITES) -> Optional[Alerta]:
    """Regra de supervisão: dispositivo silencioso por mais tempo que o limite (avaliada sob demanda)."""
    if ultima_amostra is None:
        return None
    silencio = (agora - ultima_amostra).total_seconds()
    if silencio > limites.sem_dados_s:
        return Alerta(tipo="sem_dados", gravidade=GRAVIDADE["sem_dados"], valor=round(silencio), limite=limites.sem_dados_s,
                      descricao=f"nenhuma amostra ha {int(silencio)} s (limite {limites.sem_dados_s} s)")
    return None


def janela_segundos(limites: LimitesRisco = LIMITES) -> timedelta:
    return timedelta(seconds=limites.sem_movimento_s)
