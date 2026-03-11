import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from usecases.remover_encomenda import remover_encomenda

from tests.helpers import make_context, make_row, make_update


class RemoverEncomendaTests(IsolatedAsyncioTestCase):
    async def test_deve_avisar_quando_lista_estiver_vazia(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = []
        update = make_update()
        context = make_context()

        await remover_encomenda(update, context, repository)

        repository.remove.assert_not_called()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="a lista já tá vazia, não tem nada pra remover!",
        )

    async def test_deve_exigir_numero_da_encomenda(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = [make_row(encomenda_id=1, item="Teclado")]
        update = make_update()
        context = make_context(args=[])

        await remover_encomenda(update, context, repository)

        repository.remove.assert_not_called()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="opa, faltou dizer o número da encomenda! usa: /remover [número] (olha o /listar pra saber)",
        )

    async def test_deve_validar_que_indice_e_numerico(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = [make_row(encomenda_id=1, item="Teclado")]
        update = make_update()
        context = make_context(args=["abc"])

        await remover_encomenda(update, context, repository)

        repository.remove.assert_not_called()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="tem que ser número, po! ex: /remover 1",
        )

    async def test_deve_validar_que_indice_existe_na_lista(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = [make_row(encomenda_id=1, item="Teclado")]
        update = make_update()
        context = make_context(args=["2"])

        await remover_encomenda(update, context, repository)

        repository.remove.assert_not_called()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="tá viajando? só tem 1 itens na lista. digita um número válido.",
        )

    async def test_deve_avisar_quando_repositorio_nao_remover(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = [make_row(encomenda_id=5, item="Teclado")]
        repository.remove.return_value = False
        update = make_update()
        context = make_context(args=["1"])

        await remover_encomenda(update, context, repository)

        repository.remove.assert_called_once_with(encomenda_id=5)
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="deu ruim ao remover a encomenda. tenta de novo mais tarde por favor",
        )

    async def test_deve_remover_item_pelo_indice_informado(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = [
            make_row(encomenda_id=5, item="Teclado"),
            make_row(encomenda_id=8, item="Mouse"),
        ]
        repository.remove.return_value = True
        update = make_update()
        context = make_context(args=["2"])

        await remover_encomenda(update, context, repository)

        repository.remove.assert_called_once_with(encomenda_id=8)
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="🗑️ mandou pro ralo!\n\no pacote 📦 'Mouse' foi removido da lista com sucesso.",
        )
