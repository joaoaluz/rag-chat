"""Configurações centrais do projeto. Tudo que muda entre ambientes fica aqui."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Documento fonte da PoC
PDF_NORMAS = RAIZ / "data" / "raw" / "normas-credenciamento-sesc-2026.pdf"

# "Oracle" simulado: um arquivo SQLite com o mesmo esquema que usaríamos no Oracle
ORACLE_SIM_PATH = RAIZ / "data" / "oracle_sim.db"

# Modelo de linguagem / embeddings (Ollama hoje, gateway de inferência amanhã).
# O Ollama aceita o formato da API da OpenAI em /v1.
LLM_BASE_URL = "http://localhost:11434/v1"

# "tfidf" roda sem baixar modelo; "bge-m3" usa o modelo semântico via Ollama.
EMBEDDER = "tfidf"
TFIDF_MODELO_PATH = RAIZ / "data" / "tfidf.pkl"

QDRANT_PATH = RAIZ / "data" / "qdrant"
QDRANT_COLECAO_BASE = "normas_sesc"
