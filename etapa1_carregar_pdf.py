"""Etapa 1 — PDF -> texto limpo -> tabelas DOCUMENTOS e DOCUMENTO_PAGINAS.

Uso:
    python etapa1_carregar_pdf.py
"""

from rag_chat import config
from rag_chat.db import oracle_sim
from rag_chat.ingest import pdf_loader

TITULO = "Normas gerais para credenciamento e acesso ao Sesc (2ª edição, vigência 2026)"


def main() -> None:
    conn = oracle_sim.conectar(config.ORACLE_SIM_PATH)

    # O hash identifica o conteúdo do arquivo. Rodar de novo com o mesmo PDF
    # não duplica nada; um PDF novo (outra versão) gera um novo documento.
    hash_pdf = pdf_loader.hash_arquivo(config.PDF_NORMAS)
    existente = oracle_sim.buscar_documento_por_hash(conn, hash_pdf)
    if existente:
        print(f"Documento já carregado (id={existente['id']}). Nada a fazer.")
        documento_id = existente["id"]
    else:
        paginas = pdf_loader.extrair_paginas(config.PDF_NORMAS)
        documento_id = oracle_sim.inserir_documento(
            conn,
            titulo=TITULO,
            arquivo=config.PDF_NORMAS.name,
            hash_sha256=hash_pdf,
            paginas=paginas,
        )
        print(f"Documento gravado (id={documento_id}) com {len(paginas)} páginas.")

    paginas = oracle_sim.listar_paginas(conn, documento_id)
    total_caracteres = sum(len(p["texto"]) for p in paginas)
    vazias = [p["pagina"] for p in paginas if len(p["texto"]) < 40]
    print(f"Total de caracteres: {total_caracteres:,}".replace(",", "."))
    print(f"Páginas quase vazias (capas de capítulo): {vazias}")

    amostra = paginas[22]  # página 23: validade do credenciamento
    print(f"\n--- Amostra: página {amostra['pagina']} ---\n{amostra['texto'][:900]}")


if __name__ == "__main__":
    main()
