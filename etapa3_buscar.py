"""Etapa 3b — pergunta -> vetor -> chunks mais parecidos.

Uso:
    python etapa3_buscar.py "Qual a validade da credencial plena?"
    python etapa3_buscar.py            # roda as perguntas de exemplo
"""

import sys

from rag_chat import config
from rag_chat.core.embeddings import criar_embedder
from rag_chat.core.vector_store import VectorStore

PERGUNTAS_EXEMPLO = [
    "Qual a validade da credencial plena?",
    "Quais documentos o comerciário precisa apresentar?",
    "Até que idade o filho pode ser dependente?",
    "Estou desempregado, ainda posso usar o Sesc?",
    "Meu filho pode tirar a carteirinha?",
    "Posso emprestar minha carteirinha para minha irmã?",
]


def buscar(store: VectorStore, embedder, pergunta: str, k: int = 3) -> None:
    print(f"\n❓ {pergunta}")
    for r in store.buscar(embedder.vetorizar_consulta(pergunta), k=k):
        p = r.payload
        paginas = f"p.{p['pagina_inicio']}" + (f"-{p['pagina_fim']}" if p["pagina_fim"] != p["pagina_inicio"] else "")
        inicio = p["texto"].replace("\n", " ")[:110]
        print(f"   {r.score:.2f}  {p['secao']} ({paginas})\n         {inicio}...")


def main() -> None:
    embedder = criar_embedder()
    store = VectorStore(config.QDRANT_PATH, f"{config.QDRANT_COLECAO_BASE}__{embedder.nome}")
    perguntas = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else PERGUNTAS_EXEMPLO
    for pergunta in perguntas:
        buscar(store, embedder, pergunta)


if __name__ == "__main__":
    main()
