"""Qdrant: guarda os vetores dos chunks e faz a busca por similaridade.

Na PoC usamos o modo local do qdrant-client (uma pasta em disco, sem
servidor). Para usar o Qdrant em Docker, troque `path=` por `url=`; o resto
do código não muda.

Cada embedder tem sua própria coleção (normas_sesc__tfidf,
normas_sesc__bge-m3), porque os vetores de modelos diferentes têm tamanhos e
"espaços" diferentes. Ter as duas lado a lado permite comparar resultados.
"""

from dataclasses import dataclass
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


@dataclass
class Resultado:
    score: float
    payload: dict


class VectorStore:
    def __init__(self, caminho: Path, colecao: str):
        self.cliente = QdrantClient(path=str(caminho))
        self.colecao = colecao

    def recriar_colecao(self, dimensao: int) -> None:
        if self.cliente.collection_exists(self.colecao):
            self.cliente.delete_collection(self.colecao)
        self.cliente.create_collection(
            self.colecao,
            vectors_config=VectorParams(size=dimensao, distance=Distance.COSINE),
        )

    def indexar(self, ids: list[int], vetores: list[list[float]], payloads: list[dict]) -> None:
        # O id do ponto é o id do chunk no Oracle: reindexar sobrescreve em vez de duplicar.
        self.cliente.upsert(
            self.colecao,
            points=[PointStruct(id=i, vector=v, payload=p) for i, v, p in zip(ids, vetores, payloads)],
        )

    def buscar(self, vetor: list[float], k: int = 4) -> list[Resultado]:
        resposta = self.cliente.query_points(self.colecao, query=vetor, limit=k, with_payload=True)
        return [Resultado(score=p.score, payload=p.payload) for p in resposta.points]

    def total(self) -> int:
        return self.cliente.count(self.colecao).count
