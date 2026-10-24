"""Simulação do banco Oracle usando SQLite.

Por que funciona como simulação:
- O SQLite aceita os nomes de tipo do Oracle (VARCHAR2, CLOB, NUMBER, TIMESTAMP).
- O sqlite3 e o driver do Oracle (python-oracledb) usam o mesmo estilo de
  parâmetro nomeado: `WHERE id = :id`. As consultas daqui funcionam nos dois.

Única diferença no DDL: no Oracle a chave seria
`id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY`; no SQLite usamos
`INTEGER PRIMARY KEY`, que tem o mesmo efeito (auto-incremento).
"""

import sqlite3
from pathlib import Path

DDL = [
    """
    CREATE TABLE IF NOT EXISTS DOCUMENTOS (
        id            INTEGER PRIMARY KEY,
        titulo        VARCHAR2(300) NOT NULL,
        arquivo       VARCHAR2(500) NOT NULL,
        hash_sha256   VARCHAR2(64)  NOT NULL UNIQUE,
        total_paginas NUMBER        NOT NULL,
        carregado_em  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS DOCUMENTO_PAGINAS (
        documento_id NUMBER NOT NULL REFERENCES DOCUMENTOS(id),
        pagina       NUMBER NOT NULL,
        texto        CLOB,
        PRIMARY KEY (documento_id, pagina)
    )
    """,
]


def conectar(caminho: Path) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for comando in DDL:
        conn.execute(comando)
    return conn


def buscar_documento_por_hash(conn: sqlite3.Connection, hash_sha256: str):
    return conn.execute(
        "SELECT * FROM DOCUMENTOS WHERE hash_sha256 = :hash",
        {"hash": hash_sha256},
    ).fetchone()


def inserir_documento(
    conn: sqlite3.Connection,
    titulo: str,
    arquivo: str,
    hash_sha256: str,
    paginas: list[str],
) -> int:
    """Grava o documento e suas páginas numa única transação."""
    with conn:
        cur = conn.execute(
            """
            INSERT INTO DOCUMENTOS (titulo, arquivo, hash_sha256, total_paginas)
            VALUES (:titulo, :arquivo, :hash, :total)
            """,
            {"titulo": titulo, "arquivo": arquivo, "hash": hash_sha256, "total": len(paginas)},
        )
        documento_id = cur.lastrowid
        conn.executemany(
            """
            INSERT INTO DOCUMENTO_PAGINAS (documento_id, pagina, texto)
            VALUES (:doc, :pagina, :texto)
            """,
            [
                {"doc": documento_id, "pagina": numero, "texto": texto}
                for numero, texto in enumerate(paginas, start=1)
            ],
        )
    return documento_id


def listar_paginas(conn: sqlite3.Connection, documento_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT pagina, texto FROM DOCUMENTO_PAGINAS
        WHERE documento_id = :doc
        ORDER BY pagina
        """,
        {"doc": documento_id},
    ).fetchall()
