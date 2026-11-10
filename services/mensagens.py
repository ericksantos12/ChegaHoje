"""Textos que o bot manda no chat."""

import html
from collections.abc import Iterable
from datetime import date, time
from typing import Protocol

from services.encomendas import formatar_data

LIMITE_MENSAGEM_TELEGRAM = 4096

MSG_LISTA_VAZIA = "❌ Lista Vazia"
MSG_ERRO_SALVAR = (
    "deu ruim ao salvar a encomenda. e a parte mais engraçada é que eu nem sei o porquê, "
    "tente de novo mais tarde por favor"
)
MSG_ERRO_REMOVER = "deu ruim ao remover a encomenda. tenta de novo mais tarde por favor"
MSG_TESTAR_ALERTA = "⚙️ forçando a checagem de entregas de amanhã agr..."

# fluxo guiado do /adicionar
MSG_PERGUNTA_ITEM = "qual o pacote? 📦"
MSG_ITEM_VAZIO = "o nome do pacote não pode ser vazio, manda de novo 📦"
MSG_DIGITA_DATA = "manda a data aí 📅 (ex: 15/03, amanhã, sexta, em 5 dias)"
MSG_CANCELADO = "beleza, cancelei ❌"
MSG_TIMEOUT = "⏰ demorou demais, cancelei o /adicionar. manda de novo quando quiser"
MSG_BOTAO_NAO_EH_TEU = "esse botão não é pra você (ou já expirou) 👀"

# botões de desfazer / remover
MSG_JA_SAIU = "esse já não tá mais na lista"


class _ItemComData(Protocol):
    item: str
    data: date


def mensagem_start(horario_alerta: time) -> str:
    saudacao = (
        " salve galera, sou um bot com o intuito de ajudar a anotar as encomendas que possuem "
        "previsão de chegar, pra dona luciene não ser pega de surpresa!"
    )
    return f"""{saudacao}

===== COMO USAR O BOT =====

➕ /adicionar [item] [quando]
    ex: /adicionar liquidificador 27/02
        /adicionar fone bluetooth amanhã
        /adicionar Wi-Fi mesh sexta
        /adicionar teclado em 5 dias
    ou manda só /adicionar que eu vou perguntando.
    (só aceito data de hoje pra frente)

📋 /listar
    mostra a lista com todas as encomendas salvas.

🗑️ /remover [número]
    tira uma encomenda da lista (ou usa os botões do /listar).

⏰ todo dia às {horario_alerta:%H:%M} eu vou avisar se tiver pacote chegando no dia seguinte!

Duvidas ou feedbacks só direcionar ao meu chefe @ericksantos12
"""


def mensagem_lista(encomendas: Iterable[_ItemComData]) -> str:
    linhas = [
        f"{indice}. 📦 {encomenda.item}\n    📅 Previsão: {formatar_data(encomenda.data)}\n\n"
        for indice, encomenda in enumerate(encomendas, start=1)
    ]
    if not linhas:
        return MSG_LISTA_VAZIA
    return "===== ENCOMENDAS =====\n\n" + "".join(linhas)


def mensagem_item_adicionado(item: str, data: date) -> str:
    return f"===== ITEM ADICIONADO =====\n\nPACOTE:\n📦 {item}\n\nPREVISÃO DE ENTREGA:\n📅 {formatar_data(data)}"


def mensagem_pergunta_data(item: str) -> str:
    return f"📦 {item}\n\ne chega quando? escolhe aí ou responde com a data (ex: 15/03, sexta, em 5 dias)"


def mensagem_desfeito(item: str) -> str:
    return f"↩️ desfeito! o pacote 📦 '{item}' saiu da lista."


def mensagem_confirmar_remocao(item: str, data: date) -> str:
    return f"tirar 📦 '{item}' ({formatar_data(data)}) da lista mesmo?"


def mensagem_removido(item: str) -> str:
    return f"🗑️ mandou pro ralo!\n\no pacote 📦 '{item}' foi removido da lista com sucesso."


def mensagem_alerta(item: str, data: date) -> str:
    return (
        f"🚨 ALERTA DE ENTREGA 🚨\n\n📦 '{item}' tá previsto pra chegar AMANHÃ ({formatar_data(data)})!"
        "\n\nFiquem espertos pra receber o carteiro."
    )


_CORTE = "…"


def _escapar_limitado(texto: str, limite: int, manter_fim: bool = False) -> str:
    """html.escape no texto, cortando pra caber em `limite` sem quebrar entidades (&lt; etc)."""
    escapado = html.escape(texto)
    if len(escapado) <= limite:
        return escapado

    # html.escape troca caractere por caractere, então dá pra cortar por caractere original
    pedacos = [html.escape(c) for c in texto]
    if manter_fim:
        pedacos.reverse()

    orcamento = max(limite - len(_CORTE), 0)
    mantidos: list[str] = []
    for pedaco in pedacos:
        if len(pedaco) > orcamento:
            break
        mantidos.append(pedaco)
        orcamento -= len(pedaco)

    if manter_fim:
        return _CORTE + "".join(reversed(mantidos))
    return "".join(mantidos) + _CORTE


def mensagem_erro(
    update: str,
    chat_data: str,
    user_data: str,
    traceback: str,
    limite: int = LIMITE_MENSAGEM_TELEGRAM,
) -> str:
    """Relatório de erro pro dev em HTML, escapado e cabendo no limite do Telegram.

    O contexto (update, chat_data, user_data) é cortado no fim; o traceback é cortado
    no começo, porque a parte útil (a exceção) fica no final.
    """
    modelo = (
        "An exception was raised while handling an update\n"
        "<pre>update = {update}</pre>\n\n"
        "<pre>context.chat_data = {chat_data}</pre>\n\n"
        "<pre>context.user_data = {user_data}</pre>\n\n"
        "<pre>{traceback}</pre>"
    )
    contexto = {
        "update": _escapar_limitado(update, limite // 4),
        "chat_data": _escapar_limitado(chat_data, limite // 16),
        "user_data": _escapar_limitado(user_data, limite // 16),
    }
    sobra = limite - len(modelo.format(traceback="", **contexto))
    return modelo.format(traceback=_escapar_limitado(traceback, sobra, manter_fim=True), **contexto)
