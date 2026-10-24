"""Configurações centrais do projeto. Tudo que muda entre ambientes fica aqui."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Documento fonte da PoC
PDF_NORMAS = RAIZ / "data" / "raw" / "normas-credenciamento-sesc-2026.pdf"

# "Oracle" simulado: um arquivo SQLite com o mesmo esquema que usaríamos no Oracle
ORACLE_SIM_PATH = RAIZ / "data" / "oracle_sim.db"
