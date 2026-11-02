"""Testes de ponta a ponta da API REST (CardioIA, Fase 3, Ir Além 1) com o TestClient do FastAPI."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api import main as api_main
from api.armazenamento import Armazenamento
from api.config import ConfigApi, ConfigEmail
from api.notificacao import Notificador

BASE_TS = int(datetime(2026, 10, 31, 15, 0, 0, tzinfo=timezone.utc).timestamp())


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    """API isolada: armazenamento novo sem CSV e notificador simulado com log temporário."""
    monkeypatch.setattr(api_main, "armazenamento", Armazenamento(ConfigApi(gravar_csv=False)))
    monkeypatch.setattr(api_main, "notificador", Notificador(ConfigEmail(modo="simulado", intervalo_minimo_s=600,
                                                                          destinatarios=("c@exemplo.local",),
                                                                          arquivo_log=tmp_path / "e.log")))
    return TestClient(api_main.app)


def amostra(seq, bpm=72, temp=36.6, mov=1, passo_s=5, alertas=0):
    return {"disp": "cardioia-g55-p01", "seq": seq, "ts": BASE_TS + seq * passo_s, "tsrel": 0, "temp": temp,
            "umid": 45.0, "bpm": bpm, "mov": mov, "alertas": alertas, "origem": "teste"}


def test_saude(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "ok" and corpo["email_modo"] == "simulado" and corpo["limites"]["bpm_maximo"] == 120


def test_post_normal_sem_alerta_e_consulta(cliente):
    r = cliente.post("/sinais", json=amostra(1))
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["alertas"] == [] and corpo["email_enviado"] is False and corpo["mensagem"] == "sem alerta"
    lista = cliente.get("/sinais", params={"disp": "cardioia-g55-p01"}).json()
    assert len(lista) == 1 and lista[0]["sinal"]["seq"] == 1
    assert lista[0]["instante"].startswith("2026-10-31T15:00:05")


def test_post_taquicardia_gera_alerta_e_email_uma_vez(cliente):
    r1 = cliente.post("/sinais", json=amostra(1, bpm=140)).json()
    r2 = cliente.post("/sinais", json=amostra(2, bpm=142)).json()
    assert [a["tipo"] for a in r1["alertas"]] == ["taquicardia"] and r1["email_enviado"] is True
    assert [a["tipo"] for a in r2["alertas"]] == ["taquicardia"] and r2["email_enviado"] is False
    notif = cliente.get("/notificacoes").json()
    assert len(notif) == 1 and "taquicardia" in notif[0]["assunto"]
    alertas = cliente.get("/alertas").json()
    assert len(alertas) == 2


def test_ausencia_de_movimento_pelo_historico(cliente):
    cliente.post("/sinais", json=amostra(1, mov=1))
    # 125 amostras paradas com passo de 5 s = 625 s depois do ultimo movimento
    ultimo = None
    for seq in range(2, 127):
        ultimo = cliente.post("/sinais", json=amostra(seq, mov=0)).json()
    assert [a["tipo"] for a in ultimo["alertas"]] == ["sem_movimento"]
    resumo = cliente.get("/pacientes/cardioia-g55-p01/resumo").json()
    assert "sem_movimento" in resumo["alertas_ativos"] and resumo["total_amostras"] == 126


def test_lote_ordena_por_tempo(cliente):
    lote = [amostra(3, temp=38.4, alertas=4), amostra(1), amostra(2)]
    r = cliente.post("/sinais/lote", json=lote)
    assert r.status_code == 200
    assert r.json() == {"recebidas": 3, "com_alerta": 1, "emails_enviados": 1}
    seqs = [i["sinal"]["seq"] for i in cliente.get("/sinais").json()]
    assert seqs == [1, 2, 3]


def test_validacao_rejeita_payload_invalido(cliente):
    assert cliente.post("/sinais", json={"bpm": 999}).status_code == 422
    assert cliente.post("/sinais", json={"origem": "desconhecida"}).status_code == 422
    assert cliente.post("/sinais/lote", json=[]).status_code == 400


def test_ultimo_e_404_sem_dados(cliente):
    assert cliente.get("/sinais/ultimo", params={"disp": "ninguem"}).status_code == 404
    cliente.post("/sinais", json=amostra(1))
    assert cliente.get("/sinais/ultimo", params={"disp": "cardioia-g55-p01"}).json()["sinal"]["seq"] == 1


def test_carimbo_relativo_usa_hora_de_chegada(cliente):
    payload = amostra(1)
    payload.update({"ts": 4, "tsrel": 1})
    r = cliente.post("/sinais", json=payload).json()
    assert r["instante"].startswith(str(datetime.now(timezone.utc).year))


def test_limpar(cliente):
    cliente.post("/sinais", json=amostra(1))
    assert cliente.delete("/sinais").json() == {"status": "limpo"}
    assert cliente.get("/sinais").json() == []
