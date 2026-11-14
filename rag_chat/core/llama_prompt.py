"""Template de chat do Llama 3 (vale para 3.1, 3.2 e 3.3).

Um LLM não recebe "mensagens": recebe um texto só. Os papéis (system, user,
assistant) são marcados com tokens especiais que o modelo aprendeu no
treino. Montar esse texto à mão deixa claro o que o modelo realmente vê:

    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    Você é um assistente...<|eot_id|><|start_header_id|>user<|end_header_id|>

    Pergunta...<|eot_id|><|start_header_id|>assistant<|end_header_id|>

O texto termina com o cabeçalho do assistant aberto: o modelo continua dali,
escreve a resposta e fecha com <|eot_id|> (por isso ele é o token de parada).
"""

from dataclasses import dataclass
from typing import Literal

BOS = "<|begin_of_text|>"
EOT = "<|eot_id|>"  # fim de turno; usado como stop
_CABECALHO = "<|start_header_id|>{papel}<|end_header_id|>\n\n"


@dataclass
class Mensagem:
    papel: Literal["system", "user", "assistant"]
    texto: str


def formatar(mensagens: list[Mensagem], incluir_bos: bool = True) -> str:
    """Converte as mensagens no texto que o Llama 3 espera.

    incluir_bos=False quando o servidor já acrescenta o <|begin_of_text|>
    sozinho na tokenização (llama.cpp e Ollama fazem isso); BOS duplicado
    piora as respostas.
    """
    partes = [BOS] if incluir_bos else []
    for m in mensagens:
        partes.append(_CABECALHO.format(papel=m.papel) + m.texto.strip() + EOT)
    partes.append(_CABECALHO.format(papel="assistant"))
    return "".join(partes)
