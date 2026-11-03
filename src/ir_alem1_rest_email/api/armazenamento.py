"""
CardioIA, Fase 3, Ir Além 1: armazenamento das amostras recebidas pela API.

Autor: Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55. Data: 31/10/2026.

Armazenamento em memória por paciente (deque com capacidade limitada, como o
buffer circular do firmware), com espelho opcional em CSV para auditoria. Para
produção, a mesma interface seria implementada sobre um banco de séries
temporais (InfluxDB) ou relacional; aqui o objetivo é a clareza do fluxo.
"""
from __future__ import annotations

import csv
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from .config import API, ConfigApi
from .modelos import Alerta, SinalArmazenado, SinalVital

CSV_CABECALHO = ["id", "recebido_em", "instante", "disp", "seq", "ts", "tsrel", "temp", "umid", "bpm", "mov",
                 "alertas_disp", "origem", "alertas_avaliados", "email_enviado"]


class Armazenamento:
    def __init__(self, cfg: ConfigApi = API):
        self.cfg = cfg
        self._por_paciente: dict[str, deque[SinalArmazenado]] = defaultdict(lambda: deque(maxlen=cfg.capacidade_por_paciente))
        self._ultimo_movimento: dict[str, datetime] = {}
        self._proximo_id = 1
        self._lock = Lock()
        if cfg.gravar_csv:
            self._preparar_csv(cfg.arquivo_csv)

    # ------------------------------------------------------------------ escrita
    def registrar(self, sinal: SinalVital, alertas: list[Alerta], recebido_em: Optional[datetime] = None,
                  email_enviado: bool = False) -> SinalArmazenado:
        recebido_em = recebido_em or datetime.now(timezone.utc)
        with self._lock:
            item = SinalArmazenado(id=self._proximo_id, recebido_em=recebido_em, instante=sinal.instante(recebido_em),
                                   sinal=sinal, alertas_avaliados=alertas, email_enviado=email_enviado)
            self._proximo_id += 1
            self._por_paciente[sinal.disp].append(item)
            if sinal.mov:
                self._ultimo_movimento[sinal.disp] = item.instante
            if self.cfg.gravar_csv:
                self._gravar_csv(item)
            return item

    def atualizar_movimento(self, sinal: SinalVital, recebido_em: Optional[datetime] = None) -> Optional[datetime]:
        """Atualiza e devolve o instante do último movimento conhecido do paciente (antes de avaliar o risco)."""
        instante = sinal.instante(recebido_em)
        with self._lock:
            if sinal.mov:
                self._ultimo_movimento[sinal.disp] = instante
            return self._ultimo_movimento.get(sinal.disp)

    def marcar_email(self, item_id: int, disp: str) -> None:
        with self._lock:
            for item in self._por_paciente.get(disp, ()):
                if item.id == item_id:
                    item.email_enviado = True
                    return

    # ------------------------------------------------------------------ leitura
    def listar(self, disp: Optional[str] = None, limite: int = 100, apenas_alertas: bool = False) -> list[SinalArmazenado]:
        with self._lock:
            # .get evita criar um paciente vazio no defaultdict ao consultar um disp inexistente
            fontes = [self._por_paciente.get(disp, ())] if disp else list(self._por_paciente.values())
            itens = [i for fila in fontes for i in fila]
        if apenas_alertas:
            itens = [i for i in itens if i.alertas_avaliados]
        itens.sort(key=lambda i: (i.instante, i.id))
        return itens[-limite:]

    def ultima(self, disp: str) -> Optional[SinalArmazenado]:
        with self._lock:
            fila = self._por_paciente.get(disp)
            return fila[-1] if fila else None

    def pacientes(self) -> list[str]:
        with self._lock:
            return sorted(self._por_paciente.keys())

    def total(self, disp: Optional[str] = None) -> int:
        with self._lock:
            if disp:
                return len(self._por_paciente.get(disp, ()))
            return sum(len(f) for f in self._por_paciente.values())

    def ultimo_movimento(self, disp: str) -> Optional[datetime]:
        with self._lock:
            return self._ultimo_movimento.get(disp)

    def limpar(self) -> None:
        with self._lock:
            self._por_paciente.clear()
            self._ultimo_movimento.clear()
            self._proximo_id = 1

    # ------------------------------------------------------------------ csv
    @staticmethod
    def _preparar_csv(caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        if not caminho.exists():
            with open(caminho, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_CABECALHO)

    def _gravar_csv(self, item: SinalArmazenado) -> None:
        s = item.sinal
        try:
            with open(self.cfg.arquivo_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    item.id, item.recebido_em.isoformat(), item.instante.isoformat(), s.disp, s.seq, s.ts, s.tsrel,
                    s.temp, s.umid, s.bpm, s.mov, s.alertas, s.origem,
                    ";".join(a.tipo for a in item.alertas_avaliados), int(item.email_enviado),
                ])
        except OSError:
            pass  # o CSV é espelho de auditoria; a API continua funcionando em memória
