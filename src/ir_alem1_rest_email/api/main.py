"""
CardioIA, Fase 3, Ir Além 1: API REST de sinais vitais com verificação de risco e e-mail.

Projeto : CardioIA (FIAP, curso de Inteligência Artificial, Ano 2)
Autor   : Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55
Data    : 31/10/2026

Fluxo: POST /sinais recebe uma amostra (mesmo JSON publicado pelo ESP32 via
MQTT), atualiza o contexto do paciente, aplica as regras de risco, dispara o
e-mail de alerta (simulado por padrão) e armazena. GET /sinais consulta o
histórico; GET /pacientes/{disp}/resumo devolve o estado atual, incluindo a
regra de supervisão "sem dados"; GET /notificacoes lista os e-mails gerados.

Execução: uvicorn api.main:app --reload   (documentação interativa em /docs)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from . import risco
from .armazenamento import Armazenamento
from .config import API, EMAIL, LIMITES
from .modelos import EmailRegistrado, RespostaEnvio, ResumoPaciente, SinalArmazenado, SinalVital
from .notificacao import Notificador

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cardioia.api")

app = FastAPI(title=API.titulo, version=API.versao,
              description="Recebe sinais vitais do wearable CardioIA, verifica risco e aciona e-mail de alerta. "
                          "Dados simulados; paciente identificado por pseudônimo.")
armazenamento = Armazenamento()
notificador = Notificador()


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


@app.get("/saude", tags=["operacao"])
def saude() -> dict:
    """Verificação de vida da API e configuração ativa (sem segredos)."""
    return {
        "status": "ok", "versao": API.versao, "amostras": armazenamento.total(), "pacientes": armazenamento.pacientes(),
        "limites": LIMITES.__dict__, "email_modo": EMAIL.modo, "email_destinatarios": list(EMAIL.destinatarios),
    }


@app.post("/sinais", response_model=RespostaEnvio, status_code=201, tags=["sinais"])
def receber_sinal(sinal: SinalVital) -> RespostaEnvio:
    """Recebe uma amostra, avalia o risco, dispara o e-mail se houver alerta novo e armazena."""
    recebido_em = agora_utc()
    instante = sinal.instante(recebido_em)
    ultimo_mov = armazenamento.atualizar_movimento(sinal, recebido_em)
    alertas = risco.avaliar(sinal, {"instante": instante, "ultimo_movimento": ultimo_mov})
    registro_email = notificador.notificar(sinal, alertas, instante, agora=recebido_em) if alertas else None
    item = armazenamento.registrar(sinal, alertas, recebido_em, email_enviado=registro_email is not None)
    if alertas:
        log.warning("[ALERTA] %s seq=%s: %s | e-mail %s", sinal.disp, sinal.seq, ", ".join(a.tipo for a in alertas),
                    "enviado" if registro_email else "suprimido (intervalo minimo)")
    else:
        log.info("[OK] %s seq=%s bpm=%s temp=%s", sinal.disp, sinal.seq, sinal.bpm, sinal.temp)
    mensagem = ("alerta: " + ", ".join(a.tipo for a in alertas)) if alertas else "sem alerta"
    return RespostaEnvio(id=item.id, instante=item.instante, alertas=alertas,
                         email_enviado=registro_email is not None, mensagem=mensagem)


@app.post("/sinais/lote", tags=["sinais"])
def receber_lote(sinais: list[SinalVital]) -> dict:
    """Recebe várias amostras de uma vez (por exemplo, a sincronização do buffer offline)."""
    if not sinais:
        raise HTTPException(status_code=400, detail="lote vazio")
    respostas = [receber_sinal(s) for s in sorted(sinais, key=lambda s: (s.ts or 0, s.seq))]
    return {"recebidas": len(respostas), "com_alerta": sum(1 for r in respostas if r.alertas),
            "emails_enviados": sum(1 for r in respostas if r.email_enviado)}


@app.get("/sinais", response_model=list[SinalArmazenado], tags=["sinais"])
def listar_sinais(disp: Optional[str] = Query(default=None, description="Filtra por dispositivo/paciente"),
                  limite: int = Query(default=100, ge=1, le=5000),
                  apenas_alertas: bool = Query(default=False)) -> list[SinalArmazenado]:
    """Consulta o histórico de amostras, em ordem cronológica."""
    return armazenamento.listar(disp, limite, apenas_alertas)


@app.get("/sinais/ultimo", response_model=SinalArmazenado, tags=["sinais"])
def ultimo_sinal(disp: str = Query(default="cardioia-g55-p01")) -> SinalArmazenado:
    item = armazenamento.ultima(disp)
    if item is None:
        raise HTTPException(status_code=404, detail=f"nenhuma amostra para {disp}")
    return item


@app.get("/pacientes", tags=["pacientes"])
def listar_pacientes() -> dict:
    return {"pacientes": armazenamento.pacientes()}


@app.get("/pacientes/{disp}/resumo", response_model=ResumoPaciente, tags=["pacientes"])
def resumo_paciente(disp: str) -> ResumoPaciente:
    """Estado atual do paciente: última amostra, alertas ativos e supervisão de silêncio do dispositivo."""
    ultima = armazenamento.ultima(disp)
    if ultima is None:
        raise HTTPException(status_code=404, detail=f"nenhuma amostra para {disp}")
    ativos = [a.tipo for a in ultima.alertas_avaliados]
    silencio = risco.verificar_sem_dados(ultima.recebido_em, agora_utc())
    if silencio:
        ativos.append(silencio.tipo)
    return ResumoPaciente(disp=disp, total_amostras=armazenamento.total(disp), ultima_amostra=ultima,
                          alertas_ativos=ativos, ultimo_movimento=armazenamento.ultimo_movimento(disp))


@app.get("/alertas", response_model=list[SinalArmazenado], tags=["alertas"])
def listar_alertas(disp: Optional[str] = None, limite: int = Query(default=100, ge=1, le=5000)) -> list[SinalArmazenado]:
    """Amostras que geraram ao menos um alerta."""
    return armazenamento.listar(disp, limite, apenas_alertas=True)


@app.get("/notificacoes", response_model=list[EmailRegistrado], tags=["alertas"])
def listar_notificacoes(limite: int = Query(default=50, ge=1, le=200)) -> list[EmailRegistrado]:
    """E-mails gerados pela automação (simulados ou enviados), do mais antigo ao mais recente."""
    return list(notificador.historico)[-limite:]


@app.delete("/sinais", tags=["operacao"])
def limpar() -> dict:
    """Limpa o armazenamento em memória (uso em testes e demonstrações)."""
    armazenamento.limpar()
    return {"status": "limpo"}
