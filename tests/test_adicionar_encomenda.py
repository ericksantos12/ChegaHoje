import os
from datetime import date
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from usecases.adicionar_encomenda import adicionar_encomenda

from tests.helpers import make_context, make_update


class AdicionarEncomendaTests(IsolatedAsyncioTestCase):
    async def test_deve_rejeitar_formato_invalido(self):
        repository = Mock()
        update = make_update()
        context = make_context(args=["pacote sem separador"])

        await adicionar_encomenda(update, context, repository)

        repository.create.assert_not_called()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="opa, formato errado! usa assim: /adicionar nome do pacote - dd/mm/aaaa",
        )

    async def test_deve_rejeitar_data_invalida(self):
        repository = Mock()
        update = make_update()
        context = make_context(args=["Monitor", "-", "31/02/2026"])

        await adicionar_encomenda(update, context, repository)

        repository.create.assert_not_called()
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="opa, data zoada! usa o formato certinho: dd/mm/aaaa (ex: 15/03/2026)",
        )

    async def test_deve_salvar_encomenda_quando_comando_for_valido(self):
        repository = Mock()
        update = make_update(user_name="Ana")
        context = make_context(args=["Monitor", "Gamer", "-", "12/03/2026"])
        encomenda = SimpleNamespace(id=7, item="Monitor Gamer", data=date(2026, 3, 12), dono="Ana")
        repository.create.return_value = (encomenda, True)

        await adicionar_encomenda(update, context, repository)

        repository.create.assert_called_once_with(
            chat_id=123,
            item="Monitor Gamer",
            data=date(2026, 3, 12),
            dono="Ana",
        )
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="===== ITEM ADICIONADO =====\n\nPACOTE:\n📦 Monitor Gamer\n\nPREVISÃO DE ENTREGA:\n📅 12/03/2026",
        )

    async def test_deve_avisar_quando_repositorio_falhar_ao_salvar(self):
        repository = Mock()
        repository.create.return_value = (None, False)
        update = make_update()
        context = make_context(args=["Fone", "-", "12/03/2026"])

        await adicionar_encomenda(update, context, repository)

        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="deu ruim ao salvar a encomenda. e a parte mais engraçada é que eu nem sei o porquê, tente de novo mais tarde por favor",
        )
