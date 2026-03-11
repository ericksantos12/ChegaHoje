from telegram import Update
from telegram.ext import ContextTypes

from repositories.interfaces import EncomendaRepository


async def remover_encomenda(update: Update, context: ContextTypes.DEFAULT_TYPE, repository: EncomendaRepository):
    chat_id = update.effective_chat.id

    rows = repository.get_by_chat_id(chat_id=chat_id)

    if not rows:
        await context.bot.send_message(
            chat_id=chat_id,
            text="a lista já tá vazia, não tem nada pra remover!"
        )
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="opa, faltou dizer o número da encomenda! usa: /remover [número] (olha o /listar pra saber)"
        )
        return

    try:
        indice = int(context.args[0])
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="tem que ser número, po! ex: /remover 1"
        )
        return

    if indice < 1 or indice > len(rows):
        quantidade = len(rows)
        sufixo = "item" if quantidade == 1 else "itens"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"tá viajando? só tem {quantidade} {sufixo} na lista. digita um número válido."
        )
        return

    item_selecionado = rows[indice - 1]
    id_db = item_selecionado.id
    nome_item = item_selecionado.item

    is_removed = repository.remove(encomenda_id=id_db)

    if not is_removed:
        await context.bot.send_message(
            chat_id=chat_id,
            text="deu ruim ao remover a encomenda. tenta de novo mais tarde por favor"
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🗑️ mandou pro ralo!\n\no pacote 📦 '{nome_item}' foi removido da lista com sucesso."
    )
