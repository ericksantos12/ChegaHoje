"""Handlers dos comandos do bot. Só fazem a ponte Telegram <-> services/repositório."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ContextTypes

from config import Settings
from handlers.jobs import checar_entregas
from services import (
    MSG_ERRO_REMOVER,
    MSG_ERRO_SALVAR,
    MSG_TESTAR_ALERTA,
    EntradaInvalida,
    data_hoje,
    mensagem_item_adicionado,
    mensagem_lista,
    mensagem_removido,
    mensagem_start,
    parse_adicionar,
    selecionar_por_indice,
)
from utils import get_logger

if TYPE_CHECKING:
    from repositories.interfaces import EncomendaRepository

log = get_logger(__name__)


async def _responder(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text=texto)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, *, settings: Settings) -> None:
    await _responder(update, context, mensagem_start(settings.alert_time))


async def adicionar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> None:
    chat_id = update.effective_chat.id
    usuario = update.effective_user
    dono = usuario.first_name if usuario else "Sem dono"

    hoje = data_hoje(datetime.now(settings.time_zone), settings.time_zone)
    try:
        item, data = parse_adicionar(" ".join(context.args or []), hoje)
    except EntradaInvalida as e:
        await _responder(update, context, e.mensagem)
        return

    encomenda = repository.create(chat_id=chat_id, item=item, data=data, dono=dono)
    if encomenda is None:
        await _responder(update, context, MSG_ERRO_SALVAR)
        return

    log.debug("Nova encomenda criada: id=%s chat_id=%s data=%s", encomenda.id, chat_id, data)
    await _responder(update, context, mensagem_item_adicionado(item, data))


async def listar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    chat_id = update.effective_chat.id
    encomendas = repository.get_by_chat_id(chat_id=chat_id)
    log.debug("%s encomendas encontradas para chat_id %s", len(encomendas), chat_id)
    await _responder(update, context, mensagem_lista(encomendas))


async def remover(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    chat_id = update.effective_chat.id
    encomendas = repository.get_by_chat_id(chat_id=chat_id)

    indice = context.args[0] if context.args else None
    try:
        encomenda = selecionar_por_indice(encomendas, indice)
    except EntradaInvalida as e:
        await _responder(update, context, e.mensagem)
        return

    if not repository.remove(chat_id=chat_id, encomenda_id=encomenda.id):
        await _responder(update, context, MSG_ERRO_REMOVER)
        return

    await _responder(update, context, mensagem_removido(encomenda.item))


async def testar_alerta(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> None:
    """Força a checagem diária. Só pro dev, porque manda alerta pra TODOS os chats."""
    chat_id = update.effective_chat.id
    if settings.developer_chat_id is None or chat_id != settings.developer_chat_id:
        log.info("/testar_alerta ignorado: chat %s não é o do dev", chat_id)
        return

    await _responder(update, context, MSG_TESTAR_ALERTA)
    await checar_entregas(context, repository=repository, settings=settings)
