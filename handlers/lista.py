"""/listar com um botão 🗑️ por encomenda (com confirmação antes de apagar)."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from services import (
    MSG_ERRO_REMOVER,
    MSG_JA_SAIU,
    mensagem_confirmar_remocao,
    mensagem_lista,
)
from utils import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from repositories.interfaces import EncomendaRepository

log = get_logger(__name__)

CB_REMOVER = "rm:"  # + id: pede confirmação
CB_REMOVER_SIM = "rmsim:"  # + id: remove de vez
CB_REMOVER_NAO = "rmnao"  # volta pra lista

MAX_BOTOES = 50  # o Telegram limita o tamanho do teclado; acima disso, /remover N
TAMANHO_ROTULO = 28


def _rotulo(indice: int, item: str) -> str:
    if len(item) > TAMANHO_ROTULO:
        item = item[: TAMANHO_ROTULO - 1] + "…"
    return f"🗑️ {indice}. {item}"


def teclado_lista(encomendas: Sequence) -> InlineKeyboardMarkup | None:
    if not encomendas:
        return None
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(_rotulo(indice, e.item), callback_data=f"{CB_REMOVER}{e.id}")]
            for indice, e in enumerate(encomendas[:MAX_BOTOES], start=1)
        ]
    )


def teclado_confirmacao(encomenda_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ sim, tira", callback_data=f"{CB_REMOVER_SIM}{encomenda_id}"),
                InlineKeyboardButton("❌ não", callback_data=CB_REMOVER_NAO),
            ]
        ]
    )


async def _editar(query, texto: str, teclado: InlineKeyboardMarkup | None) -> None:
    try:
        await query.edit_message_text(texto, reply_markup=teclado)
    except BadRequest as e:
        # apertar duas vezes gera "message is not modified"; não é erro de verdade
        if "not modified" not in str(e).lower():
            raise


async def _mostrar_lista(query, repository: EncomendaRepository, chat_id: int) -> None:
    encomendas = repository.get_by_chat_id(chat_id=chat_id)
    await _editar(query, mensagem_lista(encomendas), teclado_lista(encomendas))


def _buscar(repository: EncomendaRepository, chat_id: int, encomenda_id: int):
    return next((e for e in repository.get_by_chat_id(chat_id=chat_id) if e.id == encomenda_id), None)


async def listar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    chat_id = update.effective_chat.id
    encomendas = repository.get_by_chat_id(chat_id=chat_id)
    log.debug("%s encomendas encontradas para chat_id %s", len(encomendas), chat_id)
    await context.bot.send_message(
        chat_id=chat_id, text=mensagem_lista(encomendas), reply_markup=teclado_lista(encomendas)
    )


async def botao_remover(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    encomenda = _buscar(repository, chat_id, int(query.data.removeprefix(CB_REMOVER)))
    if encomenda is None:
        await query.answer(MSG_JA_SAIU)
        await _mostrar_lista(query, repository, chat_id)
        return

    await query.answer()
    await _editar(query, mensagem_confirmar_remocao(encomenda.item, encomenda.data), teclado_confirmacao(encomenda.id))


async def botao_remover_sim(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    encomenda = _buscar(repository, chat_id, int(query.data.removeprefix(CB_REMOVER_SIM)))
    if encomenda is None:
        await query.answer(MSG_JA_SAIU)
    elif repository.remove(chat_id=chat_id, encomenda_id=encomenda.id):
        await query.answer(f"🗑️ '{encomenda.item}' saiu da lista"[:200])
    else:
        await query.answer(MSG_ERRO_REMOVER, show_alert=True)
    await _mostrar_lista(query, repository, chat_id)


async def botao_remover_nao(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    await update.callback_query.answer()
    await _mostrar_lista(update.callback_query, repository, update.effective_chat.id)


def criar_handlers_lista(*, repository: EncomendaRepository) -> list:
    def com_repo(callback):
        return functools.partial(callback, repository=repository)

    return [
        CommandHandler("listar", com_repo(listar)),
        CallbackQueryHandler(com_repo(botao_remover), pattern=rf"^{CB_REMOVER}\d+$"),
        CallbackQueryHandler(com_repo(botao_remover_sim), pattern=rf"^{CB_REMOVER_SIM}\d+$"),
        CallbackQueryHandler(com_repo(botao_remover_nao), pattern=rf"^{CB_REMOVER_NAO}$"),
    ]
