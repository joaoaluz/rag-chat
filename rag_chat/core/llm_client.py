"""Cliente do Llama: ponto único por onde o projeto chama o modelo.

Envia o prompt já no template do Llama 3 (veja llama_prompt.py) com
`raw: true`, para o Ollama não aplicar o template dele por cima.
Para trocar de servidor (llama.cpp, gateway de inferência com fila), só
este arquivo muda.

Equivalente no llama.cpp: POST /completion com
{"prompt": ..., "stream": true, "n_predict": ..., "stop": [...]}.
"""

import json
import urllib.request
from collections.abc import Iterator

from rag_chat.core.llama_prompt import EOT


class LlamaIndisponivel(RuntimeError):
    pass


class LlamaClient:
    def __init__(self, base_url: str, modelo: str, contexto_tokens: int = 4096):
        self.base_url = base_url.rstrip("/")
        self.modelo = modelo
        # O Ollama usa por padrão uma janela de contexto pequena (2048 ou 4096 tokens,
        # dependendo da versão) e CORTA o começo do prompt em silêncio quando passa disso.
        # No RAG o começo do prompt são as instruções e os trechos: perder isso é grave.
        self.contexto_tokens = contexto_tokens

    def gerar(self, prompt: str, max_tokens: int = 512, temperatura: float = 0.1) -> Iterator[str]:
        """Gera a resposta em streaming, devolvendo os pedaços de texto conforme chegam."""
        corpo = {
            "model": self.modelo,
            "prompt": prompt,
            "raw": True,
            "stream": True,
            "options": {
                # Temperatura baixa: em RAG queremos fidelidade aos trechos, não criatividade.
                "temperature": temperatura,
                "num_predict": max_tokens,
                "num_ctx": self.contexto_tokens,
                "stop": [EOT],
            },
        }
        requisicao = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            resposta = urllib.request.urlopen(requisicao, timeout=300)
        except OSError as erro:
            raise LlamaIndisponivel(
                f"Não consegui falar com o Llama em {self.base_url} ({erro}). "
                f"O Ollama está rodando? Teste com: ollama run {self.modelo}"
            ) from erro

        # O Ollama responde uma linha JSON por pedaço (NDJSON): {"response": "...", "done": false}
        with resposta:
            for linha in resposta:
                if not linha.strip():
                    continue
                evento = json.loads(linha)
                if evento.get("error"):
                    raise LlamaIndisponivel(evento["error"])
                if evento.get("response"):
                    yield evento["response"]
                if evento.get("done"):
                    break
