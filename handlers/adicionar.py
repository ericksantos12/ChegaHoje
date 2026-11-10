"""Fluxo do /adicionar: comando rápido, conversa guiada quando falta algo e botão de desfazer.

- `/adicionar fone amanhã` salva direto.
- `/adicionar` (ou só item, ou só data) abre uma conversa que pergunta o que falta.
  A data pode vir pelos botões de atalho ou digitada. `/cancelar` sai.
- Em grupos com privacy mode o bot só recebe comandos e respostas às mensagens dele,
  por isso as perguntas usam ForceReply (a resposta da pessoa vira reply pro bot).
- A conversa é por (chat, usuário): duas pessoas adicionando no mesmo grupo não se misturam.
"""

from __future__ import annotations

import functools
import warnings
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

from config import Settings
from services import (
    MSG_BOTAO_NAO_EH_TEU,
    MSG_CANCELADO,
    MSG_DIGITA_DATA,
    MSG_ERRO_REMOVER,
    MSG_ERRO_SALVAR,
    MSG_ITEM_VAZIO,
    MSG_JA_SAIU,
    MSG_PERGUNTA_ITEM,
    MSG_TIMEOUT,
    EntradaInvalida,
    data_hoje,
    interpretar_data,
    mensagem_desfeito,
    mensagem_item_adicionado,
    mensagem_pergunta_data,
    separar_item_e_data,
)
from utils import get_logger

if TYPE_CHECKING:
    from datetime import date

    from repositories.interfaces import EncomendaRepository

log = get_logger(__name__)

ESPERANDO_ITEM, ESPERANDO_DATA = range(2)
FIM = ConversationHandler.END
TEMPO_LIMITE_CONVERSA = 5 * 60  # segundos

CB_ATALHO = "add:dias:"  # + quantidade de dias a partir de hoje
CB_DIGITAR = "add:digitar"
CB_CANCELAR = "add:cancelar"
CB_PREFIXO_CONVERSA = "add:"
CB_DESFAZER = "desfazer:"  # + id da encomenda

ATALHOS_DATA = [[("hoje", 0), ("amanhã", 1)], [("em 2 dias", 2), ("em 1 semana", 7)]]

# CallbackQueryHandler dentro de ConversationHandler com per_message=False é exatamente o que
# queremos (a conversa é por chat+usuário, não por mensagem); o aviso do PTB não se aplica.
warnings.filterwarnings("ignore", message=r"If 'per_message=False'", category=PTBUserWarning)


# ---------- helpers ----------


def teclado_atalhos_data() -> InlineKeyboardMarkup:
    linhas = [
        [InlineKeyboardButton(rotulo, callback_data=f"{CB_ATALHO}{dias}") for rotulo, dias in linha]
        for linha in ATALHOS_DATA
    ]
    linhas.append(
        [
            InlineKeyboardButton("✍️ digitar data", callback_data=CB_DIGITAR),
            InlineKeyboardButton("❌ cancelar", callback_data=CB_CANCELAR),
        ]
    )
    return InlineKeyboardMarkup(linhas)


def teclado_desfazer(encomenda_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ desfazer", callback_data=f"{CB_DESFAZER}{encomenda_id}")]])


def _hoje(settings: Settings) -> date:
    return data_hoje(datetime.now(settings.time_zone), settings.time_zone)


def _chave_rascunho(update: Update) -> str:
    # user_data é por usuário em TODOS os chats; a chave separa conversas em chats diferentes
    return f"adicionar:{update.effective_chat.id}"


def _rascunho(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_chave_rascunho(update), {})


async def _encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Limpa o rascunho e tira os botões de data que ainda estiverem na tela."""
    rascunho = context.user_data.pop(_chave_rascunho(update), {})
    mensagem_teclado = rascunho.get("mensagem_teclado")
    if mensagem_teclado is not None:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id, message_id=mensagem_teclado, reply_markup=None
            )
        except TelegramError:
            pass  # mensagem apagada ou já sem botões
    return FIM


async def _enviar(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str, **kwargs):
    return await context.bot.send_message(chat_id=update.effective_chat.id, text=texto, **kwargs)


async def _perguntar(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str, exemplo: str) -> None:
    """Pergunta com ForceReply direcionado (selective) só pra quem tá adicionando."""
    resposta_forcada = ForceReply(selective=True, input_field_placeholder=exemplo)
    if update.callback_query is None and update.effective_message is not None:
        # respondendo à mensagem da pessoa, o selective mira nela
        await _enviar(
            update,
            context,
            texto,
            reply_markup=resposta_forcada,
            reply_parameters=ReplyParameters(
                message_id=update.effective_message.message_id, allow_sending_without_reply=True
            ),
        )
        return
    # veio de botão: não tem mensagem da pessoa pra responder, então menciona ela
    await _enviar(
        update,
        context,
        f"{update.effective_user.mention_html()} {texto}",
        reply_markup=resposta_forcada,
        parse_mode=ParseMode.HTML,
    )


async def _perguntar_data(update: Update, context: ContextTypes.DEFAULT_TYPE, item: str) -> int:
    mensagem = await _enviar(update, context, mensagem_pergunta_data(item), reply_markup=teclado_atalhos_data())
    _rascunho(update, context)["mensagem_teclado"] = mensagem.message_id
    return ESPERANDO_DATA


async def _salvar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    repository: EncomendaRepository,
    item: str,
    data: date,
) -> int:
    await _encerrar(update, context)
    usuario = update.effective_user
    dono = usuario.first_name if usuario else "Sem dono"

    encomenda = repository.create(chat_id=update.effective_chat.id, item=item, data=data, dono=dono)
    if encomenda is None:
        await _enviar(update, context, MSG_ERRO_SALVAR)
        return FIM

    log.debug("Nova encomenda criada: id=%s chat_id=%s data=%s", encomenda.id, encomenda.chat_id, data)
    await _enviar(update, context, mensagem_item_adicionado(item, data), reply_markup=teclado_desfazer(encomenda.id))
    return FIM


# ---------- passos da conversa ----------


async def adicionar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> int:
    """/adicionar [item] [data] — salva direto se veio tudo, senão pergunta o que falta."""
    await _encerrar(update, context)  # reentrada: descarta conversa anterior desse chat
    try:
        item, data = separar_item_e_data(" ".join(context.args or []), _hoje(settings))
    except EntradaInvalida as e:
        await _enviar(update, context, e.mensagem)
        return FIM

    if item and data:
        return await _salvar(update, context, repository, item, data)

    rascunho = _rascunho(update, context)
    rascunho["data"] = data
    if not item:
        await _perguntar(update, context, MSG_PERGUNTA_ITEM, "ex: fone bluetooth")
        return ESPERANDO_ITEM

    rascunho["item"] = item
    return await _perguntar_data(update, context, item)


async def receber_item(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> int:
    """Resposta à pergunta do item. Aceita também 'item data' de uma vez."""
    try:
        item, data = separar_item_e_data(update.effective_message.text or "", _hoje(settings))
    except EntradaInvalida as e:
        await _enviar(update, context, e.mensagem)
        return ESPERANDO_ITEM

    rascunho = _rascunho(update, context)
    data = data or rascunho.get("data")
    if not item:
        rascunho["data"] = data
        await _perguntar(update, context, MSG_ITEM_VAZIO, "ex: fone bluetooth")
        return ESPERANDO_ITEM

    if data:
        return await _salvar(update, context, repository, item, data)

    rascunho["item"] = item
    return await _perguntar_data(update, context, item)


async def receber_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> int:
    """Data digitada (resposta ao ForceReply ou mensagem direta no privado)."""
    try:
        data = interpretar_data(update.effective_message.text or "", _hoje(settings))
    except EntradaInvalida as e:
        await _perguntar(update, context, e.mensagem, "ex: 15/03, sexta, em 5 dias")
        return ESPERANDO_DATA
    return await _salvar(update, context, repository, _rascunho(update, context)["item"], data)


async def botao_atalho(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
    settings: Settings,
) -> int:
    query = update.callback_query
    await query.answer()
    dias = int(query.data.removeprefix(CB_ATALHO))
    data = _hoje(settings) + timedelta(days=dias)
    return await _salvar(update, context, repository, _rascunho(update, context)["item"], data)


async def botao_digitar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await _perguntar(update, context, MSG_DIGITA_DATA, "ex: 15/03, sexta, em 5 dias")
    return ESPERANDO_DATA


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/cancelar ou botão ❌."""
    if update.callback_query is not None:
        await update.callback_query.answer()
    await _encerrar(update, context)
    await _enviar(update, context, MSG_CANCELADO)
    return FIM


async def tempo_esgotado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _encerrar(update, context)
    await _enviar(update, context, MSG_TIMEOUT)


async def botao_sem_conversa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botão da conversa apertado por outra pessoa ou depois que a conversa acabou."""
    await update.callback_query.answer(MSG_BOTAO_NAO_EH_TEU)


# ---------- desfazer ----------


async def desfazer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    repository: EncomendaRepository,
) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    encomenda_id = int(query.data.removeprefix(CB_DESFAZER))

    encomenda = next((e for e in repository.get_by_chat_id(chat_id=chat_id) if e.id == encomenda_id), None)
    if encomenda is None:
        await query.answer(MSG_JA_SAIU)
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if not repository.remove(chat_id=chat_id, encomenda_id=encomenda_id):
        await query.answer(MSG_ERRO_REMOVER, show_alert=True)
        return

    await query.answer()
    await query.edit_message_text(mensagem_desfeito(encomenda.item))


# ---------- montagem ----------


def criar_handlers_adicionar(*, repository: EncomendaRepository, settings: Settings) -> list:
    """Handlers do /adicionar, na ordem em que devem ser registrados."""

    def com_deps(callback):
        return functools.partial(callback, repository=repository, settings=settings)

    texto = filters.TEXT & ~filters.COMMAND
    conversa = ConversationHandler(
        entry_points=[CommandHandler("adicionar", com_deps(adicionar))],
        states={
            ESPERANDO_ITEM: [MessageHandler(texto, com_deps(receber_item))],
            ESPERANDO_DATA: [
                CallbackQueryHandler(com_deps(botao_atalho), pattern=rf"^{CB_ATALHO}\d+$"),
                CallbackQueryHandler(botao_digitar, pattern=rf"^{CB_DIGITAR}$"),
                MessageHandler(texto, com_deps(receber_data)),
            ],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, tempo_esgotado)],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            CallbackQueryHandler(cancelar, pattern=rf"^{CB_CANCELAR}$"),
        ],
        allow_reentry=True,
        conversation_timeout=TEMPO_LIMITE_CONVERSA,
        per_chat=True,
        per_user=True,
        per_message=False,
        name="adicionar",
    )
    return [
        conversa,
        # só chega aqui se o botão não pertence a uma conversa ativa de quem apertou
        CallbackQueryHandler(botao_sem_conversa, pattern=rf"^{CB_PREFIXO_CONVERSA}"),
        CallbackQueryHandler(functools.partial(desfazer, repository=repository), pattern=rf"^{CB_DESFAZER}\d+$"),
    ]
