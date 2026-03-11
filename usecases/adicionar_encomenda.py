from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from utils import logger
from repositories.interfaces import EncomendaRepository

logging = logger(__name__)

async def adicionar_encomenda(update: Update, context: ContextTypes.DEFAULT_TYPE, repository: EncomendaRepository):
    chat_id = update.effective_chat.id
    owner = update.effective_user.first_name

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

    encomenda, success = repository.create(chat_id=chat_id, item=item, data=data_db, dono=owner)

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

