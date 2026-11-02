"""
CardioIA, Fase 3, Ir Além 1: modelos de dados da API (Pydantic).

Autor: Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55. Data: 31/10/2026.

O formato segue o payload publicado pelo ESP32 em <prefixo>/sinais na Parte 2,
para que a mesma mensagem possa ser encaminhada à API sem conversão (ponte
MQTT ou nó http request do Node-RED). O paciente é um pseudônimo: nenhum dado
pessoal entra na API.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SinalVital(BaseModel):
    """Uma amostra de sinais vitais, como publicada pelo dispositivo."""

    disp: str = Field(default="cardioia-g55-p01", description="Identificador pseudônimo do dispositivo/paciente")
    seq: int = Field(default=0, ge=0, description="Número de sequência da amostra no dispositivo")
    ts: Optional[int] = Field(default=None, ge=0, description="Época Unix em segundos (NTP); ausente usa a hora de chegada")
    tsrel: int = Field(default=0, ge=0, le=1, description="1 se o carimbo é relativo ao boot (sem NTP)")
    temp: Optional[float] = Field(default=None, ge=-40, le=80, description="Temperatura em graus Celsius")
    umid: Optional[float] = Field(default=None, ge=0, le=100, description="Umidade relativa em por cento")
    bpm: int = Field(default=0, ge=0, le=400, description="Frequência cardíaca; 0 significa sem leitura")
    mov: int = Field(default=0, ge=0, le=1, description="1 se houve movimento na janela da amostra")
    alertas: int = Field(default=0, ge=0, le=255, description="Máscara de alertas avaliados no dispositivo")
    origem: str = Field(default="rt", description="rt (tempo real) ou sync (sincronização do buffer)")

    @field_validator("origem")
    @classmethod
    def _origem_valida(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"rt", "sync", "cliente", "ponte", "teste"}:
            raise ValueError("origem deve ser rt, sync, cliente, ponte ou teste")
        return v

    def instante(self, recebido_em: Optional[datetime] = None) -> datetime:
        """Instante efetivo da amostra: carimbo NTP quando confiável, senão a hora de chegada."""
        if self.ts is not None and not self.tsrel and self.ts > 1_700_000_000:
            return datetime.fromtimestamp(self.ts, tz=timezone.utc)
        return recebido_em or datetime.now(timezone.utc)


class Alerta(BaseModel):
    """Resultado de uma regra de risco aplicada a uma amostra."""

    tipo: str
    gravidade: str
    descricao: str
    valor: Optional[float] = None
    limite: Optional[float] = None


class SinalArmazenado(BaseModel):
    """Amostra como devolvida pela API, com o instante efetivo e a avaliação de risco."""

    id: int
    recebido_em: datetime
    instante: datetime
    sinal: SinalVital
    alertas_avaliados: list[Alerta] = []
    email_enviado: bool = False


class RespostaEnvio(BaseModel):
    id: int
    instante: datetime
    alertas: list[Alerta]
    email_enviado: bool
    mensagem: str


class ResumoPaciente(BaseModel):
    disp: str
    total_amostras: int
    ultima_amostra: Optional[SinalArmazenado]
    alertas_ativos: list[str]
    ultimo_movimento: Optional[datetime]


class EmailRegistrado(BaseModel):
    enviado_em: datetime
    modo: str
    destinatarios: list[str]
    assunto: str
    corpo: str
    entregue: bool
    detalhe: str = ""
