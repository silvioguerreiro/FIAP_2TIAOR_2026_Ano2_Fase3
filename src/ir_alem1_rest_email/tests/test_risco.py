"""Testes do módulo de verificação de risco (CardioIA, Fase 3, Ir Além 1)."""
from datetime import datetime, timedelta, timezone

import pytest

from api import risco
from api.config import LimitesRisco
from api.modelos import SinalVital

LIM = LimitesRisco()
AGORA = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)


def sinal(**campos) -> SinalVital:
    base = {"disp": "teste", "seq": 1, "ts": int(AGORA.timestamp()), "temp": 36.6, "umid": 45.0, "bpm": 72, "mov": 1}
    base.update(campos)
    return SinalVital(**base)


def tipos(alertas):
    return [a.tipo for a in alertas]


def test_amostra_normal_nao_gera_alerta():
    assert risco.avaliar(sinal(), {"instante": AGORA, "ultimo_movimento": AGORA}) == []


@pytest.mark.parametrize("bpm,esperado", [(120, []), (121, ["taquicardia"]), (150, ["taquicardia"])])
def test_taquicardia_no_limite(bpm, esperado):
    assert tipos(risco.avaliar(sinal(bpm=bpm), {"instante": AGORA, "ultimo_movimento": AGORA})) == esperado


@pytest.mark.parametrize("bpm,esperado", [(50, []), (49, ["bradicardia"]), (30, ["bradicardia"])])
def test_bradicardia_no_limite(bpm, esperado):
    assert tipos(risco.avaliar(sinal(bpm=bpm), {"instante": AGORA, "ultimo_movimento": AGORA})) == esperado


def test_bpm_zero_e_ausencia_de_leitura_nao_bradicardia():
    assert risco.avaliar(sinal(bpm=0), {"instante": AGORA, "ultimo_movimento": AGORA}) == []


@pytest.mark.parametrize("temp,esperado", [(38.0, []), (38.1, ["febre"]), (35.0, []), (34.9, ["hipotermia"])])
def test_febre_e_hipotermia_nos_limites(temp, esperado):
    assert tipos(risco.avaliar(sinal(temp=temp), {"instante": AGORA, "ultimo_movimento": AGORA})) == esperado


def test_temperatura_ausente_nao_gera_alerta_termico():
    assert risco.avaliar(sinal(temp=None), {"instante": AGORA, "ultimo_movimento": AGORA}) == []


def test_sem_movimento_depende_do_tempo_parado():
    ctx_curto = {"instante": AGORA, "ultimo_movimento": AGORA - timedelta(seconds=LIM.sem_movimento_s)}
    ctx_longo = {"instante": AGORA, "ultimo_movimento": AGORA - timedelta(seconds=LIM.sem_movimento_s + 1)}
    assert risco.avaliar(sinal(mov=0), ctx_curto) == []
    assert tipos(risco.avaliar(sinal(mov=0), ctx_longo)) == ["sem_movimento"]


def test_sem_movimento_nao_dispara_sem_historico_nem_com_movimento_atual():
    assert risco.avaliar(sinal(mov=0), {"instante": AGORA, "ultimo_movimento": None}) == []
    ctx = {"instante": AGORA, "ultimo_movimento": AGORA - timedelta(hours=2)}
    assert risco.avaliar(sinal(mov=1), ctx) == []


def test_mascara_do_dispositivo_e_incorporada_sem_duplicar():
    # 0x01 taquicardia (ja detectada pelo valor) + 0x10 sem_movimento (so o dispositivo viu)
    alertas = risco.avaliar(sinal(bpm=140, alertas=0x11), {"instante": AGORA, "ultimo_movimento": AGORA})
    assert tipos(alertas) == ["taquicardia", "sem_movimento"]
    assert "dispositivo" in alertas[1].descricao


def test_multiplos_alertas_na_mesma_amostra():
    alertas = risco.avaliar(sinal(bpm=135, temp=38.9), {"instante": AGORA, "ultimo_movimento": AGORA})
    assert tipos(alertas) == ["taquicardia", "febre"]
    assert all(a.gravidade in {"alta", "media"} for a in alertas)


def test_limites_personalizados():
    lim = LimitesRisco(bpm_maximo=100)
    assert tipos(risco.avaliar(sinal(bpm=110), {"instante": AGORA, "ultimo_movimento": AGORA}, lim)) == ["taquicardia"]


def test_supervisao_sem_dados():
    assert risco.verificar_sem_dados(None, AGORA) is None
    assert risco.verificar_sem_dados(AGORA - timedelta(seconds=LIM.sem_dados_s), AGORA) is None
    a = risco.verificar_sem_dados(AGORA - timedelta(seconds=LIM.sem_dados_s + 1), AGORA)
    assert a is not None and a.tipo == "sem_dados"
