"""
CardioIA, Fase 3, Ir Além 1: configuração da API REST e da automação de e-mail.

Projeto : CardioIA (FIAP, curso de Inteligência Artificial, Ano 2)
Autor   : Silvio Prestes Guerreiro Junior, RM 567958, turma 2TIAOR, Grupo 55
Data    : 31/10/2026

Todos os parâmetros podem ser sobrescritos por variáveis de ambiente (arquivo
.env na pasta do módulo; modelo em .env.example). Nenhuma credencial fica no
código: no modo de e-mail "simulado" (padrão) nada é enviado pela rede.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PASTA_MODULO = Path(__file__).resolve().parent.parent
load_dotenv(PASTA_MODULO / ".env")


def _int(nome: str, padrao: int) -> int:
    try:
        return int(os.getenv(nome, padrao))
    except ValueError:
        return padrao


def _float(nome: str, padrao: float) -> float:
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        return padrao


@dataclass(frozen=True)
class LimitesRisco:
    """Limites clínicos usados pelo módulo de risco (mesmos do firmware e do Node-RED)."""

    bpm_maximo: int = _int("LIMITE_BPM_MAXIMO", 120)          # acima: taquicardia
    bpm_minimo: int = _int("LIMITE_BPM_MINIMO", 50)           # abaixo (com bpm > 0): bradicardia
    temperatura_maxima: float = _float("LIMITE_TEMP_MAXIMA", 38.0)  # acima: febre
    temperatura_minima: float = _float("LIMITE_TEMP_MINIMA", 35.0)  # abaixo: hipotermia
    sem_movimento_s: int = _int("LIMITE_SEM_MOVIMENTO_S", 600)      # ausência de movimento
    sem_dados_s: int = _int("LIMITE_SEM_DADOS_S", 300)              # dispositivo silencioso


@dataclass(frozen=True)
class ConfigEmail:
    """Parâmetros da automação de e-mail.

    modo:
      simulado  registra o e-mail completo em arquivo de log e na memória (padrão);
      local     entrega a um servidor SMTP local de depuração (ex.: aiosmtpd em 1025);
      smtp      envia por um servidor SMTP real com STARTTLS e autenticação (.env).
    """

    modo: str = os.getenv("EMAIL_MODO", "simulado").strip().lower()
    servidor: str = os.getenv("SMTP_SERVIDOR", "localhost")
    porta: int = _int("SMTP_PORTA", 1025)
    usuario: str = os.getenv("SMTP_USUARIO", "")
    senha: str = os.getenv("SMTP_SENHA", "")
    usar_tls: bool = os.getenv("SMTP_TLS", "1") == "1"
    remetente: str = os.getenv("EMAIL_REMETENTE", "cardioia-alertas@exemplo.local")
    destinatarios: tuple[str, ...] = tuple(
        d.strip() for d in os.getenv("EMAIL_DESTINATARIOS", "equipe-clinica@exemplo.local").split(",") if d.strip()
    )
    intervalo_minimo_s: int = _int("EMAIL_INTERVALO_MINIMO_S", 600)  # anti-spam por paciente e tipo
    arquivo_log: Path = field(default_factory=lambda: PASTA_MODULO / "logs" / "emails_simulados.log")


@dataclass(frozen=True)
class ConfigApi:
    titulo: str = "CardioIA, Fase 3, Ir Além 1: API de sinais vitais"
    versao: str = "0.1.0"
    capacidade_por_paciente: int = _int("API_CAPACIDADE_POR_PACIENTE", 5000)
    arquivo_csv: Path = field(default_factory=lambda: PASTA_MODULO / "dados" / "sinais_recebidos.csv")
    gravar_csv: bool = os.getenv("API_GRAVAR_CSV", "1") == "1"


LIMITES = LimitesRisco()
EMAIL = ConfigEmail()
API = ConfigApi()
