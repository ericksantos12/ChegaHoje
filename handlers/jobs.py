"""Rotinas agendadas no job_queue."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from telegram.ext import ContextTypes

from config import Settings
from services import data_amanha, data_hoje, mensagem_alerta
from utils import get_logger

if TYPE_CHECKING:
    from repositories.interfaces import EncomendaRepository

log = get_logger(__name__)


async def checar_entregas(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> None:
    """Avisa cada chat das encomendas previstas pra amanhã (no fuso configurado)."""
    amanha = data_amanha(datetime.now(settings.time_zone), settings.time_zone)
    encomendas = repository.get_by_date(amanha)
    log.info("checagem de entregas pra %s: %s encomendas", amanha, len(encomendas))

    for encomenda in encomendas:
        try:
            await context.bot.send_message(
                chat_id=encomenda.chat_id,
                text=mensagem_alerta(encomenda.item, amanha),
            )
        except Exception as e:
            log.error("erro ao mandar msg pro chat %s: %s", encomenda.chat_id, e)


async def limpar_encomendas_antigas(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> None:
    """Apaga encomendas com previsão anterior a hoje, pra lista não crescer pra sempre."""
    hoje = data_hoje(datetime.now(settings.time_zone), settings.time_zone)
    removidas = repository.remove_before(hoje)
    log.info("limpeza diária: %s encomendas antigas removidas (antes de %s)", removidas, hoje)
