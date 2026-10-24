"""Etapa 2 — páginas do "Oracle" -> seções -> chunks -> tabela DOCUMENTO_CHUNKS.

Uso (depois da etapa 1):
    python etapa2_chunking.py
"""

from collections import Counter

from rag_chat import config
from rag_chat.db import oracle_sim
from rag_chat.ingest import chunker


def main() -> None:
    conn = oracle_sim.conectar(config.ORACLE_SIM_PATH)
    documento = oracle_sim.ultimo_documento(conn)
    if not documento:
        raise SystemExit("Nenhum documento carregado. Rode antes: python etapa1_carregar_pdf.py")

    paginas = [(p["pagina"], p["texto"]) for p in oracle_sim.listar_paginas(conn, documento["id"])]
    chunks = chunker.fatiar(paginas)
    oracle_sim.substituir_chunks(conn, documento["id"], chunks)

    tamanhos = [len(c.texto) for c in chunks]
    por_secao = Counter((c.capitulo, c.secao) for c in chunks)
    print(f"{len(chunks)} chunks em {len(por_secao)} seções")
    print(f"Tamanho (caracteres): mín {min(tamanhos)} · médio {sum(tamanhos) // len(tamanhos)} · máx {max(tamanhos)}\n")

    capitulo_atual = None
    for (capitulo, secao), qtd in por_secao.items():
        if capitulo != capitulo_atual:
            print(capitulo.upper())
            capitulo_atual = capitulo
        print(f"  {qtd:>2} chunk(s)  {secao}")

    exemplo = next(c for c in chunks if c.secao.startswith("Período de validade"))
    print(f"\n--- Exemplo (o que vai para o embedding) ---\n{exemplo.texto_para_embedding}")


if __name__ == "__main__":
    main()
