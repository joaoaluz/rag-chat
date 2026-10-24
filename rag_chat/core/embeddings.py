"""Embeddings: texto -> vetor.

Duas implementações com a mesma interface, para trocar uma pela outra
mudando só `config.EMBEDDER`:

- TfidfEmbedder: vetor de "quais palavras aparecem e quanto". Não entende
  significado ("carteirinha" e "credencial" são palavras diferentes), mas roda
  em qualquer lugar sem baixar modelo. Serve para montar o fluxo agora.
- OllamaEmbedder: vetor semântico do bge-m3, servido pelo Ollama (ou pelo
  gateway de inferência) no formato da API da OpenAI (/v1/embeddings).

Regra de ouro: o mesmo embedder que indexou os documentos tem que vetorizar
a pergunta. Vetores de modelos diferentes não são comparáveis.
"""

import json
import pickle
import urllib.request
from pathlib import Path
from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer


class Embedder(Protocol):
    nome: str

    def dimensao(self) -> int: ...
    def vetorizar_documentos(self, textos: list[str]) -> list[list[float]]: ...
    def vetorizar_consulta(self, texto: str) -> list[float]: ...


class TfidfEmbedder:
    """TF-IDF com n-gramas de caracteres.

    TF (term frequency): quanto um termo aparece no chunk.
    IDF (inverse document frequency): termos raros no documento todo pesam mais;
    "sesc" aparece em quase todo chunk e quase não ajuda a diferenciar.

    Usamos pedaços de 3 a 5 letras ("dep", "depe", "depen"...) em vez de
    palavras inteiras: assim "dependente" e "dependentes" compartilham quase
    tudo, o que compensa a falta de um stemmer para português.

    Diferente de um modelo pronto, o TF-IDF precisa "aprender" o vocabulário
    dos documentos (fit). Esse vocabulário é salvo em disco para que a busca
    use exatamente o mesmo.
    """

    nome = "tfidf"

    def __init__(self, caminho_modelo: Path):
        self.caminho_modelo = caminho_modelo
        self._vetorizador: TfidfVectorizer | None = None
        if caminho_modelo.exists():
            self._vetorizador = pickle.loads(caminho_modelo.read_bytes())

    def _exigir_treinado(self) -> TfidfVectorizer:
        if self._vetorizador is None:
            raise RuntimeError("TF-IDF ainda não foi treinado. Rode a indexação (etapa 3) antes.")
        return self._vetorizador

    def dimensao(self) -> int:
        return len(self._exigir_treinado().vocabulary_)

    def vetorizar_documentos(self, textos: list[str]) -> list[list[float]]:
        self._vetorizador = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            strip_accents="unicode",
            lowercase=True,
            sublinear_tf=True,
            max_features=8192,
        )
        matriz = self._vetorizador.fit_transform(textos)
        self.caminho_modelo.parent.mkdir(parents=True, exist_ok=True)
        self.caminho_modelo.write_bytes(pickle.dumps(self._vetorizador))
        return matriz.toarray().tolist()

    def vetorizar_consulta(self, texto: str) -> list[float]:
        return self._exigir_treinado().transform([texto]).toarray()[0].tolist()


class OllamaEmbedder:
    """Embeddings semânticos via endpoint compatível com a OpenAI.

    Aponta para o Ollama local hoje; para o gateway de inferência amanhã,
    trocando só a base_url.
    """

    def __init__(self, base_url: str, modelo: str, api_key: str = "rag-chat"):
        self.base_url = base_url.rstrip("/")
        self.modelo = modelo
        self.api_key = api_key
        self.nome = modelo.replace(":", "-")
        self._dim: int | None = None

    def _post(self, entradas: list[str]) -> list[list[float]]:
        requisicao = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps({"model": self.modelo, "input": entradas}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(requisicao, timeout=120) as resposta:
            dados = json.load(resposta)["data"]
        return [item["embedding"] for item in sorted(dados, key=lambda d: d["index"])]

    def dimensao(self) -> int:
        if self._dim is None:
            self._dim = len(self._post(["teste"])[0])
        return self._dim

    def vetorizar_documentos(self, textos: list[str]) -> list[list[float]]:
        vetores = []
        for i in range(0, len(textos), 16):  # lotes pequenos para não estourar memória
            vetores.extend(self._post(textos[i : i + 16]))
        return vetores

    def vetorizar_consulta(self, texto: str) -> list[float]:
        return self._post([texto])[0]


def criar_embedder() -> Embedder:
    from rag_chat import config

    if config.EMBEDDER == "tfidf":
        return TfidfEmbedder(config.TFIDF_MODELO_PATH)
    return OllamaEmbedder(config.LLM_BASE_URL, config.EMBEDDER)
