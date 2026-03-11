from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

from telegram.ext import ContextTypes

from repositories.interfaces import EncomendaRepository
from utils import logger

logging = logger(__name__)

async def checar_entregas(context: ContextTypes.DEFAULT_TYPE, repository: EncomendaRepository):
    # busca pelo formato YYYY-MM-DD pq eh assim q ta no banco
    fuso_sp = ZoneInfo(os.getenv("TIME_ZONE", "America/Sao_Paulo"))
    agora_sp = datetime.now(fuso_sp)
    amanha_db = (agora_sp + timedelta(days=1)).strftime('%Y-%m-%d')
    amanha_br = (agora_sp + timedelta(days=1)).strftime('%d/%m/%Y')

    rows = repository.get_by_date(date=amanha_db)
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