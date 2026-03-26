import pytest

from usecases import remover_encomenda

from tests.helpers import make_context, make_update
from repositories.in_memory_encomenda_repository import InMemoryEncomendaRepository

pytestmark = pytest.mark.asyncio


async def test_deve_avisar_quando_lista_estiver_vazia():
    repository = InMemoryEncomendaRepository()
    update = make_update()
    context = make_context()

    await remover_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="a lista já tá vazia, não tem nada pra remover!",
    )


async def test_deve_exigir_numero_da_encomenda():
    repository = InMemoryEncomendaRepository()
    repository.seed(item="Teclado")
    update = make_update()
    context = make_context(args=[])

    await remover_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="opa, faltou dizer o número da encomenda! usa: /remover [número] (olha o /listar pra saber)",
    )


async def test_deve_validar_que_indice_e_numerico():
    repository = InMemoryEncomendaRepository()
    repository.seed(item="Teclado")
    update = make_update()
    context = make_context(args=["abc"])

    await remover_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="tem que ser número, po! ex: /remover 1",
    )


async def test_deve_validar_que_indice_existe_na_lista():
    repository = InMemoryEncomendaRepository()
    repository.seed(item="Teclado")
    update = make_update()
    context = make_context(args=["2"])

    await remover_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="tá viajando? só tem 1 item na lista. digita um número válido.",
    )


async def test_deve_avisar_quando_repositorio_nao_remover():
    repository = InMemoryEncomendaRepository()
    row = repository.seed(item="Teclado")
    repository.fail_on_remove_ids.add(row.id)
    update = make_update()
    context = make_context(args=["1"])

    await remover_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="deu ruim ao remover a encomenda. tenta de novo mais tarde por favor",
    )


async def test_deve_remover_item_pelo_indice_informado():
    repository = InMemoryEncomendaRepository()
    repository.seed(item="Teclado")
    repository.seed(item="Mouse")
    update = make_update()
    context = make_context(args=["2"])

    await remover_encomenda(update, context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="🗑️ mandou pro ralo!\n\no pacote 📦 'Mouse' foi removido da lista com sucesso.",
    )
