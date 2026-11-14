"""Etapa 4 — o RAG completo: pergunta -> busca -> prompt -> Llama -> resposta.

Uso:
    python etapa4_perguntar.py "Qual a validade da credencial plena?"
    python etapa4_perguntar.py --mostrar-prompt "Qual a validade da credencial plena?"

--mostrar-prompt imprime o texto exato enviado ao Llama, com os tokens
especiais do template, e não chama o modelo.
"""

import argparse
import sys

from rag_chat import config
from rag_chat.core import llama_prompt, prompt
from rag_chat.core.embeddings import criar_embedder
from rag_chat.core.llm_client import LlamaClient, LlamaIndisponivel
from rag_chat.core.vector_store import VectorStore

K = 4  # quantos trechos vão para o prompt


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("pergunta", nargs="+")
    args.add_argument("--mostrar-prompt", action="store_true")
    opcoes = args.parse_args()
    pergunta = " ".join(opcoes.pergunta)

    # 1. Busca
    embedder = criar_embedder()
    store = VectorStore(config.QDRANT_PATH, f"{config.QDRANT_COLECAO_BASE}__{embedder.nome}")
    resultados = store.buscar(embedder.vetorizar_consulta(pergunta), k=K)

    # 2. Prompt no template do Llama 3
    mensagens = prompt.montar_mensagens(pergunta, resultados)
    texto_prompt = llama_prompt.formatar(mensagens, incluir_bos=False)

    if opcoes.mostrar_prompt:
        print(llama_prompt.BOS + texto_prompt)  # o BOS é posto pelo servidor; mostramos para ficar completo
        tokens = len(texto_prompt) // 4  # estimativa grosseira: ~4 caracteres por token
        print(f"\n--- ~{tokens} tokens de prompt; janela configurada: {config.LLAMA_CONTEXTO_TOKENS} ---")
        return

    # 3. Geração em streaming
    llama = LlamaClient(config.LLAMA_URL, config.LLAMA_MODELO, config.LLAMA_CONTEXTO_TOKENS)
    print(f"❓ {pergunta}\n")
    try:
        for pedaco in llama.gerar(texto_prompt):
            print(pedaco, end="", flush=True)
    except LlamaIndisponivel as erro:
        sys.exit(f"\n{erro}")

    print("\n\nFontes:")
    for f in prompt.fontes(resultados):
        print(f"  {f}")


if __name__ == "__main__":
    main()
