"""
CardioIA, Fase 3, Ir Além 1: automação de e-mail em caso de alerta.

Autor: Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55. Data: 31/10/2026.

Três modos, escolhidos por EMAIL_MODO (.env):
  simulado  (padrão) monta a mensagem completa (cabeçalhos e corpo) e a registra
            em logs/emails_simulados.log e na memória; nada sai pela rede. É o
            modo usado nas evidências e nos testes, pois não depende de credenciais.
  local     entrega a um servidor SMTP de depuração na própria máquina, por
            exemplo "python -m aiosmtpd -n -l localhost:1025", que imprime as
            mensagens recebidas no terminal.
  smtp      envia por um servidor real (Gmail, Outlook, etc.) com STARTTLS e
            autenticação; usuário e senha vêm apenas do .env.

Uma política anti-spam impede repetir o mesmo tipo de alerta para o mesmo
paciente antes de EMAIL_INTERVALO_MINIMO_S (padrão 10 min), como fazem os
sistemas de alarme clínico para evitar fadiga de alarmes.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from collections import deque
from datetime import datetime, timezone
from email.message import EmailMessage
from threading import Lock
from typing import Optional

from .config import EMAIL, ConfigEmail
from .modelos import Alerta, EmailRegistrado, SinalVital

log = logging.getLogger("cardioia.email")


def montar_mensagem(sinal: SinalVital, alertas: list[Alerta], instante: datetime, cfg: ConfigEmail) -> EmailMessage:
    """Monta o e-mail de alerta em texto simples, sem dados pessoais (apenas o pseudônimo)."""
    tipos = ", ".join(a.tipo for a in alertas)
    gravidade = "ALTA" if any(a.gravidade == "alta" for a in alertas) else "MEDIA"
    msg = EmailMessage()
    msg["From"] = cfg.remetente
    msg["To"] = ", ".join(cfg.destinatarios)
    msg["Subject"] = f"[CardioIA] Alerta {gravidade}: {tipos} ({sinal.disp})"
    linhas = [
        "CardioIA, monitoramento continuo (Fase 3, Ir Alem 1)",
        "",
        f"Paciente (pseudonimo): {sinal.disp}",
        f"Instante da amostra  : {instante.astimezone().strftime('%d/%m/%Y %H:%M:%S %Z')}",
        f"Sequencia            : {sinal.seq} (origem {sinal.origem})",
        "",
        "Alertas detectados:",
    ]
    for a in alertas:
        linhas.append(f"  - {a.tipo} ({a.gravidade}): {a.descricao}")
    temp = f"{sinal.temp:.1f} C" if sinal.temp is not None else "sem leitura"
    umid = f"{sinal.umid:.0f}%" if sinal.umid is not None else "sem leitura"
    linhas += [
        "",
        f"Sinais da amostra: bpm {sinal.bpm} | temperatura {temp} | umidade {umid} | movimento {'sim' if sinal.mov else 'nao'}",
        "",
        "Este aviso e gerado automaticamente por um prototipo academico com dados simulados;",
        "nao substitui a avaliacao de um profissional de saude.",
    ]
    msg.set_content("\n".join(linhas))
    return msg


class Notificador:
    """Envia (ou simula) e-mails de alerta com política anti-spam e histórico em memória."""

    def __init__(self, cfg: ConfigEmail = EMAIL, limite_historico: int = 200):
        self.cfg = cfg
        self._ultimo_envio: dict[tuple[str, str], datetime] = {}
        self.historico: deque[EmailRegistrado] = deque(maxlen=limite_historico)
        self._lock = Lock()
        self.cfg.arquivo_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ política
    def tipos_a_notificar(self, disp: str, alertas: list[Alerta], agora: datetime) -> list[Alerta]:
        """Filtra os alertas que ainda não foram notificados dentro do intervalo mínimo."""
        pendentes = []
        for a in alertas:
            chave = (disp, a.tipo)
            ultimo = self._ultimo_envio.get(chave)
            if ultimo is None or (agora - ultimo).total_seconds() >= self.cfg.intervalo_minimo_s:
                pendentes.append(a)
        return pendentes

    # ------------------------------------------------------------------ envio
    def notificar(self, sinal: SinalVital, alertas: list[Alerta], instante: datetime,
                  agora: Optional[datetime] = None) -> Optional[EmailRegistrado]:
        """Dispara o e-mail para os alertas novos; devolve o registro ou None se nada foi enviado."""
        agora = agora or datetime.now(timezone.utc)
        with self._lock:
            novos = self.tipos_a_notificar(sinal.disp, alertas, agora)
            if not novos:
                return None
            msg = montar_mensagem(sinal, novos, instante, self.cfg)
            entregue, detalhe = self._entregar(msg)
            for a in novos:
                self._ultimo_envio[(sinal.disp, a.tipo)] = agora
            registro = EmailRegistrado(
                enviado_em=agora, modo=self.cfg.modo, destinatarios=list(self.cfg.destinatarios),
                assunto=msg["Subject"], corpo=msg.get_content(), entregue=entregue, detalhe=detalhe,
            )
            self.historico.append(registro)
            self._registrar_em_arquivo(registro)
            return registro

    def _entregar(self, msg: EmailMessage) -> tuple[bool, str]:
        modo = self.cfg.modo
        if modo == "simulado":
            log.info("[EMAIL simulado] %s -> %s", msg["Subject"], msg["To"])
            return True, "registrado em log (modo simulado, nada enviado pela rede)"
        try:
            if modo == "local":
                with smtplib.SMTP(self.cfg.servidor, self.cfg.porta, timeout=10) as smtp:
                    smtp.send_message(msg)
                return True, f"entregue ao servidor SMTP local {self.cfg.servidor}:{self.cfg.porta}"
            if modo == "smtp":
                contexto = ssl.create_default_context()
                with smtplib.SMTP(self.cfg.servidor, self.cfg.porta, timeout=20) as smtp:
                    smtp.ehlo()
                    if self.cfg.usar_tls:
                        smtp.starttls(context=contexto)
                        smtp.ehlo()
                    if self.cfg.usuario:
                        smtp.login(self.cfg.usuario, self.cfg.senha)
                    smtp.send_message(msg)
                return True, f"enviado por {self.cfg.servidor}:{self.cfg.porta} (STARTTLS={self.cfg.usar_tls})"
            return False, f"modo de e-mail desconhecido: {modo}"
        except (OSError, smtplib.SMTPException) as erro:  # falha de rede ou de autenticação
            log.error("[EMAIL] falha no envio (%s): %s", modo, erro)
            return False, f"falha: {erro}"

    def _registrar_em_arquivo(self, r: EmailRegistrado) -> None:
        try:
            with open(self.cfg.arquivo_log, "a", encoding="utf-8") as f:
                f.write("=" * 78 + "\n")
                f.write(f"{r.enviado_em.isoformat()} | modo={r.modo} | entregue={r.entregue} | {r.detalhe}\n")
                f.write(f"Para: {', '.join(r.destinatarios)}\nAssunto: {r.assunto}\n\n{r.corpo}\n")
        except OSError as erro:
            log.error("[EMAIL] nao foi possivel gravar o log: %s", erro)
