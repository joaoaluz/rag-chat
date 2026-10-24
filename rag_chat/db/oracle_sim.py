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
    """
    CREATE TABLE IF NOT EXISTS DOCUMENTO_CHUNKS (
        id            INTEGER PRIMARY KEY,
        documento_id  NUMBER        NOT NULL REFERENCES DOCUMENTOS(id),
        chunk_idx     NUMBER        NOT NULL,
        capitulo      VARCHAR2(200) NOT NULL,
        secao         VARCHAR2(300) NOT NULL,
        pagina_inicio NUMBER        NOT NULL,
        pagina_fim    NUMBER        NOT NULL,
        texto         CLOB          NOT NULL,
        UNIQUE (documento_id, chunk_idx)
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


def ultimo_documento(conn: sqlite3.Connection):
    return conn.execute("SELECT * FROM DOCUMENTOS ORDER BY id DESC LIMIT 1").fetchone()


def substituir_chunks(conn: sqlite3.Connection, documento_id: int, chunks: list) -> None:
    """Apaga os chunks antigos do documento e grava os novos.

    Chunking é barato e a gente vai ajustar os parâmetros várias vezes;
    por isso refazemos tudo a cada execução em vez de tentar atualizar.
    """
    with conn:
        conn.execute("DELETE FROM DOCUMENTO_CHUNKS WHERE documento_id = :doc", {"doc": documento_id})
        conn.executemany(
            """
            INSERT INTO DOCUMENTO_CHUNKS
                (documento_id, chunk_idx, capitulo, secao, pagina_inicio, pagina_fim, texto)
            VALUES (:doc, :idx, :capitulo, :secao, :pag_ini, :pag_fim, :texto)
            """,
            [
                {
                    "doc": documento_id,
                    "idx": idx,
                    "capitulo": c.capitulo,
                    "secao": c.secao,
                    "pag_ini": c.pagina_inicio,
                    "pag_fim": c.pagina_fim,
                    "texto": c.texto,
                }
                for idx, c in enumerate(chunks)
            ],
        )


def listar_chunks(conn: sqlite3.Connection, documento_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM DOCUMENTO_CHUNKS WHERE documento_id = :doc ORDER BY chunk_idx",
        {"doc": documento_id},
    ).fetchall()
