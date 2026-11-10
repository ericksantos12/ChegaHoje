import functools
import logging as stdlib_logging
import sys
from datetime import time

from telegram.ext import ApplicationBuilder, CommandHandler

from config import ConfigError, get_settings
from db import create_session_factory
from handlers import (
    adicionar,
    checar_entregas,
    error_handler,
    limpar_encomendas_antigas,
    listar,
    remover,
    start,
    testar_alerta,
)
from repositories import SAEncomenda
from utils import get_logger

log = get_logger(__name__)

# limpeza das encomendas antigas, de madrugada no fuso configurado
HORARIO_LIMPEZA = time(hour=3, minute=0)


def main() -> None:
    try:
        settings = get_settings()
    except ConfigError as e:
        log.error("configuração inválida: %s", e)
        sys.exit(1)

    stdlib_logging.getLogger().setLevel(settings.log_level)
    # o httpx loga cada request em INFO, com o token do bot na URL
    stdlib_logging.getLogger("httpx").setLevel(stdlib_logging.WARNING)

    repository = SAEncomenda(create_session_factory(settings.database_url))
    deps = {"repository": repository, "settings": settings}

    app = ApplicationBuilder().token(settings.telegram_token).build()

    # handlers dos comandos
    app.add_handler(CommandHandler("start", functools.partial(start, settings=settings)))
    app.add_handler(CommandHandler("adicionar", functools.partial(adicionar, **deps)))
    app.add_handler(CommandHandler("listar", functools.partial(listar, repository=repository)))
    app.add_handler(CommandHandler("remover", functools.partial(remover, repository=repository)))
    # só responde no chat do dev (DEVELOPER_CHAT_ID)
    app.add_handler(CommandHandler("testar_alerta", functools.partial(testar_alerta, **deps)))

    app.add_error_handler(functools.partial(error_handler, settings=settings))

    # rotina diária pra avisar das encomendas de amanhã (ALERT_TIME no fuso TIME_ZONE)
    app.job_queue.run_daily(
        functools.partial(checar_entregas, **deps),
        time=settings.alert_time,
        name="checar_entregas",
    )
    # rotina diária pra apagar encomendas com data que já passou
    app.job_queue.run_daily(
        functools.partial(limpar_encomendas_antigas, **deps),
        time=HORARIO_LIMPEZA.replace(tzinfo=settings.time_zone),
        name="limpar_encomendas_antigas",
    )

    app.run_polling()


if __name__ == "__main__":
    main()
