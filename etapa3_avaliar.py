"""Etapa 3c — mede a qualidade da busca com perguntas de resposta conhecida.

Para cada pergunta em avaliacao/perguntas.json, verifica se a seção certa
aparece entre os k primeiros resultados (métrica "acerto@k").
Rode com cada embedder e compare os números.

Uso:
    python etapa3_avaliar.py
"""

import json

from rag_chat import config
from rag_chat.core.embeddings import criar_embedder
from rag_chat.core.vector_store import VectorStore

K = 3


def main() -> None:
    casos = json.loads((config.RAIZ / "avaliacao" / "perguntas.json").read_text(encoding="utf-8"))
    embedder = criar_embedder()
    store = VectorStore(config.QDRANT_PATH, f"{config.QDRANT_COLECAO_BASE}__{embedder.nome}")

    acertos = 0
    for caso in casos:
        resultados = store.buscar(embedder.vetorizar_consulta(caso["pergunta"]), k=K)
        secoes = [r.payload["secao"] for r in resultados]
        if caso["secao_esperada"] in secoes:
            acertos += 1
            marca = f"✅ #{secoes.index(caso['secao_esperada']) + 1}"
        else:
            marca = "❌   "
        print(f"{marca}  {caso['pergunta']}")
        if marca.startswith("❌"):
            print(f"         esperado: {caso['secao_esperada']} · veio: {secoes[0]}")

    print(f"\nacerto@{K} com '{embedder.nome}': {acertos}/{len(casos)} ({acertos / len(casos):.0%})")


if __name__ == "__main__":
    main()
