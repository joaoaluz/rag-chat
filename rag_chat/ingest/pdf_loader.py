"""Leitura e limpeza do PDF.

O texto extraído de um PDF diagramado (este foi feito no InDesign) vem com
"sujeira" de layout. Cada regra abaixo corrige um problema que aparece de
verdade neste documento:

  "| 23 |"                  -> número de página impresso no topo; removido
  "indepen -\\ndentemente"   -> palavra hifenizada na quebra de linha; juntada
  "T rabalhador"            -> espaço falso de kerning depois do "T"; removido
  "\\t\\x83 Foto recente"     -> marcador de lista em fonte especial; vira "- "
"""

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

_NUMERO_PAGINA = re.compile(r"^\s*\|\s*\d+\s*\|\s*$", re.MULTILINE)
_HIFENIZACAO = re.compile(r"(\w)\s*-\s*\n\s*(\w)")
_KERNING_T = re.compile(r"\bT (?=[a-záéíóúâêôãõç])")
_MARCADOR = re.compile(r"^[\t ]*\x83[\t ]*", re.MULTILINE)
_ESPACOS = re.compile(r"[ \t]+")


def hash_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def limpar_texto(texto: str) -> str:
    texto = _NUMERO_PAGINA.sub("", texto)
    texto = _HIFENIZACAO.sub(r"\1\2", texto)
    texto = _KERNING_T.sub("T", texto)
    texto = _MARCADOR.sub("- ", texto)
    texto = _ESPACOS.sub(" ", texto)
    # Mantemos as quebras de linha: na etapa de chunking elas ajudam a achar os títulos.
    linhas = [linha.strip() for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha)


def extrair_paginas(caminho: Path) -> list[str]:
    """Devolve o texto limpo de cada página, na ordem (índice 0 = página 1)."""
    leitor = PdfReader(caminho)
    return [limpar_texto(pagina.extract_text() or "") for pagina in leitor.pages]
