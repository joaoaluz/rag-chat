"""Etapa 3a — chunks do "Oracle" -> vetores -> Qdrant.

Uso (depois das etapas 1 e 2):
    python etapa3_indexar.py
"""

from rag_chat import config
from rag_chat.core.embeddings import criar_embedder
from rag_chat.core.vector_store import VectorStore
from rag_chat.db import oracle_sim
from rag_chat.ingest.chunker import texto_para_embedding


def main() -> None:
    conn = oracle_sim.conectar(config.ORACLE_SIM_PATH)
    documento = oracle_sim.ultimo_documento(conn)
    chunks = oracle_sim.listar_chunks(conn, documento["id"]) if documento else []
    if not chunks:
        raise SystemExit("Nenhum chunk encontrado. Rode antes as etapas 1 e 2.")

    embedder = criar_embedder()
    textos = [texto_para_embedding(c["capitulo"], c["secao"], c["texto"]) for c in chunks]
    print(f"Vetorizando {len(textos)} chunks com '{embedder.nome}'...")
    vetores = embedder.vetorizar_documentos(textos)
    print(f"Cada vetor tem {len(vetores[0])} dimensões.")

    store = VectorStore(config.QDRANT_PATH, f"{config.QDRANT_COLECAO_BASE}__{embedder.nome}")
    store.recriar_colecao(len(vetores[0]))
    store.indexar(
        ids=[c["id"] for c in chunks],
        vetores=vetores,
        payloads=[
            {
                "documento_id": c["documento_id"],
                "chunk_idx": c["chunk_idx"],
                "capitulo": c["capitulo"],
                "secao": c["secao"],
                "pagina_inicio": c["pagina_inicio"],
                "pagina_fim": c["pagina_fim"],
                "texto": c["texto"],
            }
            for c in chunks
        ],
    )
    print(f"Coleção '{store.colecao}' com {store.total()} pontos.")


if __name__ == "__main__":
    main()
