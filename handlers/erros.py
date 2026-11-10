"""Handler global de erros: loga e manda o traceback pro dev."""

import json
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import Settings
from services import mensagem_erro
from utils import get_logger

log = get_logger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE, *, settings: Settings) -> None:
    # loga antes de tudo, pra aparecer mesmo se o resto quebrar
    log.error("Exception while handling an update:", exc_info=context.error)

    if settings.developer_chat_id is None:
        log.warning("DEVELOPER_CHAT_ID não configurado, erro ficou só no log")
        return

    tb_string = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
    update_obj = update.to_dict() if isinstance(update, Update) else str(update)
    mensagem = mensagem_erro(
        update=json.dumps(update_obj, indent=2, ensure_ascii=False, default=str),
        chat_data=str(context.chat_data),
        user_data=str(context.user_data),
        traceback=tb_string,
    )

    await context.bot.send_message(chat_id=settings.developer_chat_id, text=mensagem, parse_mode=ParseMode.HTML)
