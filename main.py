import logging
import os
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from db.init_db import init_db
from repositories.encomendas import SqlAlchemyEncomendaRepository

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

repo = SqlAlchemyEncomendaRepository()


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


async def adicionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

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
        data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="opa, data zoada! usa o formato certinho: dd/mm/aaaa (ex: 15/03/2026)"
        )
        return

    repo.add(chat_id=chat_id, item=item, data=data_obj)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"===== ITEM ADICIONADO =====\n\nPACOTE:\n📦 {item}\n\nPREVISÃO DE ENTREGA:\n📅 {data_str}"
    )


async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    rows = repo.list_by_chat(chat_id)

    if not rows:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Lista Vazia"
        )
        return

    mensagem = "===== ENCOMENDAS =====\n\n"
    for index, encomenda in enumerate(rows, start=1):
        data_br = encomenda.data.strftime('%d/%m/%Y')
        mensagem += f"{index}. 📦 {encomenda.item}\n    📅 Previsão: {data_br}\n\n"

    await context.bot.send_message(
        chat_id=chat_id,
        text=mensagem
    )


async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    rows = repo.list_by_chat(chat_id)

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

    encomenda_selecionada = rows[indice - 1]
    repo.remove_by_id(encomenda_selecionada.id)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🗑️ mandou pro ralo!\n\no pacote 📦 '{encomenda_selecionada.item}' foi removido da lista com sucesso."
    )


async def checar_entregas(context: ContextTypes.DEFAULT_TYPE):
    amanha = (datetime.now() + timedelta(days=1)).date()
    amanha_br = amanha.strftime('%d/%m/%Y')

    rows = repo.list_by_date(amanha)

    for encomenda in rows:
        try:
            await context.bot.send_message(
                chat_id=encomenda.chat_id,
                text=f"🚨 ALERTA DE ENTREGA 🚨\n\n📦 '{encomenda.item}' tá previsto pra chegar AMANHÃ ({amanha_br})!\n\nFiquem espertos pra receber o carteiro."
            )
        except Exception as e:
            logging.error(f"erro ao mandar msg pro chat {encomenda.chat_id}: {e}")


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

    # prepara o banco de dados antes do bot ligar
    init_db()

    app = ApplicationBuilder().token(token).build()

    # handlers dos comandos
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('adicionar', adicionar))
    app.add_handler(CommandHandler('listar', listar))
    app.add_handler(CommandHandler('remover', remover))
    app.add_handler(CommandHandler('testar_alerta', testar_alerta))

    # rotina diária pra avisar das encomendas
    # roda todo dia as 08:00 no fuso de SP
    fuso_sp = ZoneInfo("America/Sao_Paulo")
    horario_aviso = time(hour=8, minute=0, second=0, tzinfo=fuso_sp)
    app.job_queue.run_daily(checar_entregas, time=horario_aviso)

    app.run_polling()