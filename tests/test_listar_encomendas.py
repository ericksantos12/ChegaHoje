import os
from datetime import date

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from usecases import listar_encomendas

from tests.helpers import make_context, make_update
from repositories.in_memory_encomenda_repository import InMemoryEncomendaRepository

pytestmark = pytest.mark.asyncio


async def test_deve_avisar_quando_lista_estiver_vazia():
    repository = InMemoryEncomendaRepository()
    update = make_update()
    context = make_context()

    await listar_encomendas(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(chat_id=123, text="❌ Lista Vazia")


async def test_deve_listar_encomendas_formatadas():
    repository = InMemoryEncomendaRepository()
    repository.seed(chat_id=123, item="Teclado", delivery_date=date(2026, 3, 12))
    repository.seed(chat_id=123, item="Mouse", delivery_date=date(2026, 3, 13))
    update = make_update()
    context = make_context()

    await listar_encomendas(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="===== ENCOMENDAS =====\n\n"
        "1. 📦 Teclado\n    📅 Previsão: 12/03/2026\n\n"
        "2. 📦 Mouse\n    📅 Previsão: 13/03/2026\n\n",
    )
