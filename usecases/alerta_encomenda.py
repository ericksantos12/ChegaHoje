from telegram import Update
from telegram.ext import ContextTypes

from usecases.checar_encomendas_job import checar_entregas
from repositories.interfaces import EncomendaRepository


async def testar_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE, repository: EncomendaRepository):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚙️ forçando a checagem de entregas de amanhã agr..."
    )
    await checar_entregas(context, repository=repository)
