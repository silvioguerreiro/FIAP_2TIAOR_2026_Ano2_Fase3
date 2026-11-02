"""Testes da automação de e-mail (CardioIA, Fase 3, Ir Além 1), em modo simulado."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from api.config import ConfigEmail
from api.modelos import Alerta, SinalVital
from api.notificacao import Notificador, montar_mensagem

AGORA = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)


def cfg_simulada(tmp_path: Path, intervalo: int = 600) -> ConfigEmail:
    return ConfigEmail(modo="simulado", destinatarios=("clinica@exemplo.local",), intervalo_minimo_s=intervalo,
                       arquivo_log=tmp_path / "emails.log")


def alerta(tipo="taquicardia", gravidade="alta"):
    return Alerta(tipo=tipo, gravidade=gravidade, descricao=f"{tipo} de teste", valor=1, limite=0)


def sinal(**campos):
    base = {"disp": "cardioia-g55-p01", "seq": 7, "ts": int(AGORA.timestamp()), "temp": 38.6, "umid": 50.0, "bpm": 140, "mov": 0}
    base.update(campos)
    return SinalVital(**base)


def test_mensagem_contem_pseudonimo_alertas_e_aviso(tmp_path):
    msg = montar_mensagem(sinal(), [alerta(), alerta("febre", "media")], AGORA, cfg_simulada(tmp_path))
    corpo = msg.get_content()
    assert msg["Subject"].startswith("[CardioIA] Alerta ALTA: taquicardia, febre")
    assert "cardioia-g55-p01" in corpo and "taquicardia" in corpo and "febre" in corpo
    assert "nao substitui a avaliacao de um profissional" in corpo
    assert "@" not in corpo.split("Paciente")[0]  # nenhum dado pessoal no cabecalho do corpo


def test_modo_simulado_registra_em_log_e_historico(tmp_path):
    n = Notificador(cfg_simulada(tmp_path))
    r = n.notificar(sinal(), [alerta()], AGORA, agora=AGORA)
    assert r is not None and r.entregue and r.modo == "simulado"
    assert len(n.historico) == 1
    texto = (tmp_path / "emails.log").read_text(encoding="utf-8")
    assert "Assunto: [CardioIA] Alerta ALTA: taquicardia" in texto


def test_intervalo_minimo_suprime_repeticao_do_mesmo_tipo(tmp_path):
    n = Notificador(cfg_simulada(tmp_path, intervalo=600))
    assert n.notificar(sinal(), [alerta()], AGORA, agora=AGORA) is not None
    assert n.notificar(sinal(seq=8), [alerta()], AGORA, agora=AGORA + timedelta(seconds=599)) is None
    assert n.notificar(sinal(seq=9), [alerta()], AGORA, agora=AGORA + timedelta(seconds=600)) is not None


def test_tipo_novo_dispara_mesmo_dentro_do_intervalo(tmp_path):
    n = Notificador(cfg_simulada(tmp_path))
    n.notificar(sinal(), [alerta()], AGORA, agora=AGORA)
    r = n.notificar(sinal(seq=8), [alerta(), alerta("febre", "media")], AGORA, agora=AGORA + timedelta(seconds=30))
    assert r is not None and "febre" in r.assunto and "taquicardia" not in r.assunto


def test_pacientes_diferentes_sao_independentes(tmp_path):
    n = Notificador(cfg_simulada(tmp_path))
    assert n.notificar(sinal(disp="p01"), [alerta()], AGORA, agora=AGORA) is not None
    assert n.notificar(sinal(disp="p02"), [alerta()], AGORA, agora=AGORA) is not None


def test_sem_alertas_nao_envia(tmp_path):
    n = Notificador(cfg_simulada(tmp_path))
    assert n.notificar(sinal(), [], AGORA, agora=AGORA) is None


def test_modo_local_sem_servidor_falha_sem_excecao(tmp_path):
    cfg = ConfigEmail(modo="local", servidor="127.0.0.1", porta=1, destinatarios=("x@exemplo.local",),
                      intervalo_minimo_s=0, arquivo_log=tmp_path / "e.log")
    r = Notificador(cfg).notificar(sinal(), [alerta()], AGORA, agora=AGORA)
    assert r is not None and r.entregue is False and r.detalhe.startswith("falha")
