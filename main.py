import json
import os
import sys
import traceback
import functools

from telegram.constants import ParseMode

from repositories.SAEncomenda import SAEncomenda
from usecases import adicionar_encomenda, listar_encomendas, remover_encomenda, testar_alerta, checar_entregas
from utils.logger import logger

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from datetime import time
from zoneinfo import ZoneInfo

load_dotenv()

logging = logger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f""" salve galera, sou um bot com o intuito de ajudar a anotar as encomendas que possuem previsão de chegar, pra dona luciene não ser pega de surpresa!
    
===== COMO USAR O BOT =====

➕ /adicionar [item] - [dd/mm/aaaa]
    ex: /adicionar liquidificador - 27/02/2026

📋 /listar
    mostra a lista com todas as encomendas salvas.

🗑️ /remover [número]
    tira uma encomenda da lista (olha o número no /listar).

⏰ todo dia às 08:00 eu vou avisar se tiver pacote chegando no dia seguinte!

Duvidas ou feedbacks só direcionar ao meu chefe @ericksantos12
"""

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logging.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096-character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {json.dumps(update_str, indent=2, ensure_ascii=False)}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {str(context.chat_data)}</pre>\n\n"
        f"<pre>context.user_data = {str(context.user_data)}</pre>\n\n"
        f"<pre>{tb_string}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=str(os.getenv("DEVELOPER_CHAT_ID")), text=message, parse_mode=ParseMode.HTML
    )

if __name__ == '__main__':
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logging.error("token não encontrado nas variáveis de ambiente.")
        sys.exit(1)

    app = ApplicationBuilder().token(token).build()

    repository = SAEncomenda()

    # handlers dos comandos
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('adicionar', functools.partial(adicionar_encomenda, repository=repository)))
    app.add_handler(CommandHandler('listar', functools.partial(listar_encomendas, repository=repository)))
    app.add_handler(CommandHandler('remover', functools.partial(remover_encomenda, repository=repository)))
    app.add_handler(CommandHandler('testar_alerta', functools.partial(testar_alerta, repository=repository)))

    app.add_error_handler(error_handler)

    # rotina diária pra avisar das encomendas
    # roda todo dia as 08:00 no fuso de SP
    fuso_sp = ZoneInfo("America/Sao_Paulo")
    horario_aviso = time(hour=8, minute=0, second=0, tzinfo=fuso_sp)
    app.job_queue.run_daily(functools.partial(checar_entregas, repository=repository), time=horario_aviso)

    app.run_polling()