import json
import os
import sys
import traceback

from telegram.constants import ParseMode

from utils.logger import logger

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

from repositories.SAEncomenda import SAEncomenda

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

async def adicionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    owner = update.effective_user.first_name
    encomenda_repo = SAEncomenda()

    texto_comando = ' '.join(context.args)
    if not texto_comando or '-' not in texto_comando:
        await context.bot.send_message(
            chat_id=chat_id,
            text="opa, formato errado! usa assim: /adicionar nome do pacote - dd/mm/aaaa"
        )
        return

    partes = texto_comando.split('-')
    item = partes[0].strip()
    data_str = partes[1].strip()

    try:
        data_obj = datetime.strptime(data_str, '%d/%m/%Y')
        data_db = data_obj.date()
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="opa, data zoada! usa o formato certinho: dd/mm/aaaa (ex: 15/03/2026)"
        )
        return

    encomenda, success = encomenda_repo.create(chat_id=chat_id, item=item, data=data_db, dono=owner)

    if not success:
        await context.bot.send_message(
            chat_id=chat_id,
            text="deu ruim ao salvar a encomenda. e a parte mais engraçada é que eu nem sei o porquê, tente de novo mais tarde por favor"
        )
        return

    logging.debug(f"Nova encomenda criada: {encomenda.__dict__}")
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"===== ITEM ADICIONADO =====\n\nPACOTE:\n📦 {item}\n\nPREVISÃO DE ENTREGA:\n📅 {data_str}"
    )


async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    encomenda_repo = SAEncomenda()

    rows = encomenda_repo.get_by_chat_id(chat_id=chat_id)

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


async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    encomenda_repo = SAEncomenda()

    rows = encomenda_repo.get_by_chat_id(chat_id=chat_id)

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
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"tá viajando? só tem {len(rows)} itens na lista. digita um número válido."
        )
        return

    item_selecionado = rows[indice - 1]
    id_db = item_selecionado.id
    nome_item = item_selecionado.item

    is_removed = encomenda_repo.remove(encomenda_id=id_db)

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


async def checar_entregas(context: ContextTypes.DEFAULT_TYPE):
    print("cheguei na rotina diária de checar entregas...")
    # busca pelo formato YYYY-MM-DD pq eh assim q ta no banco
    fuso_sp = ZoneInfo(os.getenv("TIME_ZONE", "America/Sao_Paulo"))
    agora_sp = datetime.now(fuso_sp)
    amanha_db = (agora_sp + timedelta(days=1)).strftime('%Y-%m-%d')
    amanha_br = (agora_sp + timedelta(days=1)).strftime('%d/%m/%Y')
    encomendas_repo = SAEncomenda()

    rows = encomendas_repo.get_by_date(date=amanha_db)
    print(rows)
    for row in rows:
        chat_id = row.chat_id
        item = row.item
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚨 ALERTA DE ENTREGA 🚨\n\n📦 '{item}' tá previsto pra chegar AMANHÃ ({amanha_br})!\n\nFiquem espertos pra receber o carteiro."
            )
        except Exception as e:
            logging.error(f"erro ao mandar msg pro chat {chat_id}: {e}")


async def testar_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚙️ forçando a checagem de entregas de amanhã agr..."
    )
    await checar_entregas(context)


if __name__ == '__main__':
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logging.error("token não encontrado nas variáveis de ambiente.")
        sys.exit(1)

    app = ApplicationBuilder().token(token).build()

    # handlers dos comandos
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('adicionar', adicionar))
    app.add_handler(CommandHandler('listar', listar))
    app.add_handler(CommandHandler('remover', remover))
    app.add_handler(CommandHandler('testar_alerta', testar_alerta))

    app.add_error_handler(error_handler)

    # rotina diária pra avisar das encomendas
    # roda todo dia as 08:00 no fuso de SP
    fuso_sp = ZoneInfo("America/Sao_Paulo")
    horario_aviso = time(hour=8, minute=0, second=0, tzinfo=fuso_sp)
    app.job_queue.run_daily(checar_entregas, time=horario_aviso)

    app.run_polling()