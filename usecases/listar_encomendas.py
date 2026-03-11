from telegram import Update
from telegram.ext import ContextTypes

from repositories.interfaces import EncomendaRepository
from utils import logger

logging = logger(__name__)

async def listar_encomendas(update: Update, context: ContextTypes.DEFAULT_TYPE, repository: EncomendaRepository):
    chat_id = update.effective_chat.id

    rows = repository.get_by_chat_id(chat_id=chat_id)

    if not rows:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Lista Vazia"
        )
        return
    logging.debug("Encomendas encontradas para chat_id %d: %s", chat_id, [row.__dict__ for row in rows])
    mensagem = "===== ENCOMENDAS =====\n\n"
    for index, row in enumerate(rows):
        item = row.item
        # converte de volta pro padrao br pra mostrar na tela
        data_br = row.data.strftime('%d/%m/%Y')
        mensagem += f"{index + 1}. 📦 {item}\n    📅 Previsão: {data_br}\n\n"

    await context.bot.send_message(
        chat_id=chat_id,
        text=mensagem
    )