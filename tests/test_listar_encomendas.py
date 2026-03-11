import os
from datetime import date
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from usecases.listar_encomendas import listar_encomendas

from tests.helpers import make_context, make_row, make_update


class ListarEncomendasTests(IsolatedAsyncioTestCase):
    async def test_deve_avisar_quando_lista_estiver_vazia(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = []
        update = make_update()
        context = make_context()

        await listar_encomendas(update, context, repository)

        repository.get_by_chat_id.assert_called_once_with(chat_id=123)
        context.bot.send_message.assert_awaited_once_with(chat_id=123, text="❌ Lista Vazia")

    async def test_deve_listar_encomendas_formatadas(self):
        repository = Mock()
        repository.get_by_chat_id.return_value = [
            make_row(encomenda_id=1, item="Teclado", delivery_date=date(2026, 3, 12)),
            make_row(encomenda_id=2, item="Mouse", delivery_date=date(2026, 3, 13)),
        ]
        update = make_update()
        context = make_context()

        await listar_encomendas(update, context, repository)

        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="===== ENCOMENDAS =====\n\n"
            "1. 📦 Teclado\n    📅 Previsão: 12/03/2026\n\n"
            "2. 📦 Mouse\n    📅 Previsão: 13/03/2026\n\n",
        )
