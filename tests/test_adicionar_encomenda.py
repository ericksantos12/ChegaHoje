import os
from datetime import date

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from usecases import adicionar_encomenda

from tests.helpers import make_context, make_update
from repositories.in_memory_encomenda_repository import InMemoryEncomendaRepository

pytestmark = pytest.mark.asyncio


async def test_deve_rejeitar_formato_invalido():
    repository = InMemoryEncomendaRepository()
    update = make_update()
    context = make_context(args=["pacote sem separador"])

    await adicionar_encomenda(update, context, repository)

    assert repository.get_by_chat_id(chat_id=123) == []
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="opa, formato errado! usa assim: /adicionar nome do pacote - dd/mm/aaaa",
    )


async def test_deve_rejeitar_data_invalida():
    repository = InMemoryEncomendaRepository()
    update = make_update()
    context = make_context(args=["Monitor", "-", "31/02/2026"])

    await adicionar_encomenda(update, context, repository)

    assert repository.get_by_chat_id(chat_id=123) == []
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="opa, data zoada! usa o formato certinho: dd/mm/aaaa (ex: 15/03/2026)",
    )


async def test_deve_salvar_encomenda_quando_comando_for_valido():
    repository = InMemoryEncomendaRepository()
    update = make_update(user_name="Ana")
    context = make_context(args=["Monitor", "Gamer", "-", "12/03/2026"])

    await adicionar_encomenda(update, context, repository)

    rows = repository.get_by_chat_id(chat_id=123)
    assert len(rows) == 1
    assert rows[0].item == "Monitor Gamer"
    assert rows[0].data == date(2026, 3, 12)
    assert rows[0].dono == "Ana"
    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="===== ITEM ADICIONADO =====\n\nPACOTE:\n📦 Monitor Gamer\n\nPREVISÃO DE ENTREGA:\n📅 12/03/2026",
    )


async def test_deve_avisar_quando_repositorio_falhar_ao_salvar():
    repository = InMemoryEncomendaRepository(fail_on_create=True)
    update = make_update()
    context = make_context(args=["Fone", "-", "12/03/2026"])

    await adicionar_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="deu ruim ao salvar a encomenda. e a parte mais engraçada é que eu nem sei o porquê, tente de novo mais tarde por favor",
    )
