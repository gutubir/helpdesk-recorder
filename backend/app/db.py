"""Banco de dados (SQLite, biblioteca padrão).

Escolhido para o MVP: não precisa instalar nada no PC da empresa. Todo acesso
passa por esta classe, então trocar para PostgreSQL depois é reescrever só
este arquivo.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

STATUS_RECEBIDO = "recebido"
STATUS_TRANSCREVENDO = "transcrevendo"
STATUS_TRANSCRITO = "transcrito"
STATUS_ERRO = "erro"
STATUS_VALIDOS = {STATUS_RECEBIDO, STATUS_TRANSCREVENDO, STATUS_TRANSCRITO, STATUS_ERRO}

SCHEMA = """
CREATE TABLE IF NOT EXISTS atendimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_em TEXT NOT NULL,
    inicio TEXT,
    duracao_segundos REAL,
    status TEXT NOT NULL DEFAULT 'recebido',
    erro TEXT,
    pasta TEXT,
    meta TEXT
);
CREATE TABLE IF NOT EXISTS segmentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    atendimento_id INTEGER NOT NULL REFERENCES atendimentos(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL,
    falante TEXT NOT NULL,
    inicio REAL NOT NULL,
    fim REAL NOT NULL,
    texto TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_segmentos_atendimento
    ON segmentos(atendimento_id, ordem);
"""


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        # Uma conexão por operação: seguro para uso entre threads (rotas + tarefas
        # em segundo plano).
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _linha(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        if d.get("meta"):
            d["meta"] = json.loads(d["meta"])
        else:
            d["meta"] = {}
        return d

    # -- atendimentos ----------------------------------------------------
    def criar_atendimento(
        self,
        inicio: Optional[str] = None,
        duracao_segundos: Optional[float] = None,
        meta: Optional[dict] = None,
    ) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO atendimentos (criado_em, inicio, duracao_segundos, meta) "
                "VALUES (?, ?, ?, ?)",
                (_agora(), inicio, duracao_segundos, json.dumps(meta or {}, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def definir_pasta(self, atendimento_id: int, pasta: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE atendimentos SET pasta=? WHERE id=?", (pasta, atendimento_id))

    def definir_duracao(self, atendimento_id: int, duracao: float) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE atendimentos SET duracao_segundos=? WHERE id=?",
                (duracao, atendimento_id),
            )

    def definir_status(self, atendimento_id: int, status: str, erro: Optional[str] = None) -> None:
        if status not in STATUS_VALIDOS:
            raise ValueError(f"status inválido: {status}")
        with self._conn() as c:
            c.execute(
                "UPDATE atendimentos SET status=?, erro=? WHERE id=?",
                (status, erro, atendimento_id),
            )

    def marcar_interrompidos(self) -> int:
        """Na inicialização: nada pode estar em andamento, então o que ficou
        como 'recebido' ou 'transcrevendo' foi interrompido (queda, reinício)."""
        with self._conn() as c:
            cur = c.execute(
                "UPDATE atendimentos SET status=?, erro=? WHERE status IN (?, ?)",
                (STATUS_ERRO, "Processamento interrompido (servidor reiniciou)",
                 STATUS_RECEBIDO, STATUS_TRANSCREVENDO),
            )
            return cur.rowcount

    def obter(self, atendimento_id: int) -> Optional[dict[str, Any]]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM atendimentos WHERE id=?", (atendimento_id,)).fetchone()
        return self._linha(row) if row else None

    def listar(self, limite: int = 50, deslocamento: int = 0) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM atendimentos ORDER BY id DESC LIMIT ? OFFSET ?",
                (limite, deslocamento),
            ).fetchall()
        return [self._linha(r) for r in rows]

    def excluir(self, atendimento_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM atendimentos WHERE id=?", (atendimento_id,))

    # -- segmentos (transcrição por turnos) ------------------------------
    def substituir_segmentos(self, atendimento_id: int, turnos: list[dict[str, Any]]) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM segmentos WHERE atendimento_id=?", (atendimento_id,))
            c.executemany(
                "INSERT INTO segmentos (atendimento_id, ordem, falante, inicio, fim, texto) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (atendimento_id, i, t["falante"], t["inicio"], t["fim"], t["texto"])
                    for i, t in enumerate(turnos)
                ],
            )

    def listar_segmentos(self, atendimento_id: int) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT falante, inicio, fim, texto FROM segmentos "
                "WHERE atendimento_id=? ORDER BY ordem",
                (atendimento_id,),
            ).fetchall()
        return [dict(r) for r in rows]
