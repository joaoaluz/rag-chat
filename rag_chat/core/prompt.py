"""Montagem do prompt de RAG: instruções + trechos recuperados + pergunta.

É aqui que o "Augmented" do RAG acontece. Três escolhas importantes:

1. As regras ficam no system: responder só com base nos trechos, admitir
   quando não sabe e citar as fontes. É o que reduz a alucinação.
2. Os trechos são numerados [1], [2]... com seção e página, para o modelo
   conseguir citar e a gente conseguir conferir.
3. Os trechos vão na mensagem do user, logo antes da pergunta: modelos
   pequenos prestam mais atenção no que está perto do fim do prompt.
"""

from rag_chat.core.llama_prompt import Mensagem
from rag_chat.core.vector_store import Resultado

SYSTEM = """Você é o assistente de atendimento do Sesc e responde dúvidas sobre credenciamento \
com base nas "Normas gerais para credenciamento e acesso ao Sesc" (vigência 2026).

Regras:
- Use SOMENTE as informações dos trechos fornecidos. Não use conhecimento próprio.
- Se os trechos não trouxerem a resposta, diga: "Não encontrei essa informação nas normas." \
e sugira procurar a Central de Atendimento de uma unidade do Sesc.
- Cite a fonte de cada informação com o número do trecho, como [1] ou [2].
- Responda em português do Brasil, de forma curta e direta, em no máximo 5 frases.
- Não invente valores, prazos ou documentos."""


def _paginas(payload: dict) -> str:
    ini, fim = payload["pagina_inicio"], payload["pagina_fim"]
    return f"p. {ini}" if ini == fim else f"p. {ini}-{fim}"


def formatar_trechos(resultados: list[Resultado]) -> str:
    blocos = []
    for n, r in enumerate(resultados, start=1):
        p = r.payload
        blocos.append(f"[{n}] {p['capitulo']} > {p['secao']} ({_paginas(p)})\n{p['texto']}")
    return "\n\n".join(blocos)


def montar_mensagens(pergunta: str, resultados: list[Resultado]) -> list[Mensagem]:
    usuario = f"""Trechos das normas:

{formatar_trechos(resultados)}

Pergunta: {pergunta}"""
    return [Mensagem("system", SYSTEM), Mensagem("user", usuario)]


def fontes(resultados: list[Resultado]) -> list[str]:
    """Lista legível das fontes, para mostrar abaixo da resposta."""
    return [f"[{n}] {r.payload['secao']} ({_paginas(r.payload)})" for n, r in enumerate(resultados, start=1)]
