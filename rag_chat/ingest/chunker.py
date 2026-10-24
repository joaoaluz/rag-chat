"""Chunking estrutural: capítulo -> seção -> parágrafos -> chunks.

Como a estrutura aparece no texto deste PDF:
- Capítulo: página de capa quase vazia ("Credenciamento", "Direitos e deveres").
- Seção: linha em MAIÚSCULAS, às vezes quebrada em duas
  ("CONDIÇÕES PARA EMISSÃO" + "DA CREDENCIAL PLENA").
- Parágrafo: as linhas vêm quebradas pela diagramação; juntamos de novo.

Cada chunk fica dentro de uma única seção (nunca mistura dois assuntos)
e leva junto o nome do capítulo, da seção e as páginas, para a citação.
"""

import re
from dataclasses import dataclass, field

# Capa, ficha técnica, sumário e contracapa não têm conteúdo útil para responder perguntas.
PAGINAS_IGNORADAS = {1, 2, 3, 8, 9, 65}
CAPITULO_INICIAL = "Resolução"  # página 4 vem antes da primeira capa
# Bloco de assinatura digital da resolução: nome em maiúsculas, CPF mascarado, certificado.
MARCA_ASSINATURA = "Assinado digitalmente por:"

MAX_CARACTERES = 1200  # ~300 tokens
SOBREPOSICAO = 200  # repete o final do chunk anterior no começo do próximo

_FIM_DE_FRASE = re.compile(r"(?<=[.;:!?])\s+")


@dataclass
class Paragrafo:
    texto: str
    pagina: int


@dataclass
class Secao:
    capitulo: str
    titulo: str
    paragrafos: list[Paragrafo] = field(default_factory=list)


@dataclass
class Chunk:
    capitulo: str
    secao: str
    pagina_inicio: int
    pagina_fim: int
    texto: str

    @property
    def texto_para_embedding(self) -> str:
        """O que será vetorizado: o texto com o "endereço" dele no documento.

        Um trecho como "A validade será de 24 meses" sozinho não diz de qual
        credencial está falando. Com o cabeçalho, o vetor carrega esse contexto.
        """
        return f"{self.capitulo} > {self.secao}\n{self.texto}"


def _eh_capa(texto: str) -> bool:
    return 0 < len(texto) < 80 and "." not in texto


def _eh_titulo(linha: str) -> bool:
    letras = [c for c in linha if c.isalpha()]
    return len(letras) >= 8 and sum(c.isupper() for c in letras) / len(letras) > 0.85


def _formatar_titulo(texto: str) -> str:
    texto = " ".join(texto.split()).rstrip(",").lower()
    texto = texto[0].upper() + texto[1:]
    return re.sub(r"\bsesc\b", "Sesc", texto)


def _inicia_paragrafo(linha: str, anterior: str) -> bool:
    return (
        linha.startswith(("- ", "→"))
        or anterior.endswith((".", ":", ";"))
        or anterior == "Observações"
        or linha == "Observações"
    )


def extrair_secoes(paginas: list[tuple[int, str]]) -> list[Secao]:
    """Percorre as páginas e devolve as seções com seus parágrafos remontados."""
    secoes: list[Secao] = []
    capitulo = CAPITULO_INICIAL
    atual = Secao(capitulo, capitulo)
    titulo_pendente: list[str] = []
    linha_anterior = ""

    def fechar_secao():
        if atual.paragrafos:
            secoes.append(atual)

    for numero, texto in paginas:
        if numero in PAGINAS_IGNORADAS or not texto:
            continue
        texto = texto.split(MARCA_ASSINATURA)[0].strip()
        if _eh_capa(texto):
            fechar_secao()
            capitulo = _formatar_titulo(texto.replace("\n", " "))
            atual = Secao(capitulo, capitulo)
            linha_anterior = ""
            continue

        for linha in texto.splitlines():
            if _eh_titulo(linha):
                titulo_pendente.append(linha)
                continue
            if titulo_pendente:
                fechar_secao()
                atual = Secao(capitulo, _formatar_titulo(" ".join(titulo_pendente)))
                titulo_pendente = []
                linha_anterior = ""

            if not atual.paragrafos or _inicia_paragrafo(linha, linha_anterior):
                atual.paragrafos.append(Paragrafo(linha, numero))
            else:
                atual.paragrafos[-1].texto += " " + linha
            linha_anterior = linha

    fechar_secao()
    return secoes


def _dividir_por_palavras(texto: str) -> list[str]:
    """Último recurso para textos sem pontuação (ex.: tabelas achatadas)."""
    partes, atual = [], ""
    for palavra in texto.split():
        if atual and len(atual) + 1 + len(palavra) > MAX_CARACTERES:
            partes.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    return partes + [atual] if atual else partes


def _unidades(secao: Secao) -> list[Paragrafo]:
    """Parágrafos que cabem num chunk; os longos demais são divididos
    por frase e, se ainda não couber, por palavras."""
    unidades = []
    for p in secao.paragrafos:
        if len(p.texto) <= MAX_CARACTERES:
            unidades.append(p)
            continue
        for frase in _FIM_DE_FRASE.split(p.texto):
            pedacos = [frase] if len(frase) <= MAX_CARACTERES else _dividir_por_palavras(frase)
            unidades.extend(Paragrafo(t, p.pagina) for t in pedacos)
    return unidades


def fatiar_secao(secao: Secao) -> list[Chunk]:
    """Empacota parágrafos em chunks de até MAX_CARACTERES, com sobreposição."""
    chunks: list[Chunk] = []
    grupo: list[Paragrafo] = []

    def emitir():
        chunks.append(
            Chunk(
                capitulo=secao.capitulo,
                secao=secao.titulo,
                pagina_inicio=grupo[0].pagina,
                pagina_fim=grupo[-1].pagina,
                texto="\n".join(p.texto for p in grupo),
            )
        )

    for unidade in _unidades(secao):
        tamanho_atual = sum(len(p.texto) + 1 for p in grupo)
        if grupo and tamanho_atual + len(unidade.texto) > MAX_CARACTERES:
            emitir()
            # Sobreposição: leva os últimos parágrafos (até SOBREPOSICAO caracteres)
            # para o próximo chunk, assim uma ideia na fronteira não se perde.
            reaproveitar: list[Paragrafo] = []
            for p in reversed(grupo):
                if sum(len(x.texto) for x in reaproveitar) + len(p.texto) > SOBREPOSICAO:
                    break
                reaproveitar.insert(0, p)
            # Se a sobreposição + a próxima unidade estourar o limite, começa sem ela.
            if sum(len(p.texto) + 1 for p in reaproveitar) + len(unidade.texto) > MAX_CARACTERES:
                reaproveitar = []
            grupo = reaproveitar
        grupo.append(unidade)

    if grupo:
        emitir()
    return chunks


def fatiar(paginas: list[tuple[int, str]]) -> list[Chunk]:
    return [chunk for secao in extrair_secoes(paginas) for chunk in fatiar_secao(secao)]
