import os
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TIME_ZONE", "America/Sao_Paulo")

from usecases.checar_encomendas_job import checar_entregas

from tests.helpers import make_context, make_row


class ChecarEntregasTests(IsolatedAsyncioTestCase):
    @patch("usecases.checar_encomendas_job.datetime")
    async def test_deve_buscar_entregas_de_amanha_e_enviar_alerta(self, datetime_mock):
        data_atual = datetime(2026, 3, 11, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        datetime_mock.now.return_value = data_atual
        repository = Mock()
        repository.get_by_date.return_value = [make_row(item="Teclado")]
        context = make_context()

        await checar_entregas(context, repository)

        repository.get_by_date.assert_called_once_with(date="2026-03-12")
        context.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="🚨 ALERTA DE ENTREGA 🚨\n\n📦 'Teclado' tá previsto pra chegar AMANHÃ (12/03/2026)!\n\nFiquem espertos pra receber o carteiro.",
        )

    @patch("usecases.checar_encomendas_job.datetime")
    async def test_deve_continuar_mesmo_se_um_envio_falhar(self, datetime_mock):
        datetime_mock.now.return_value = datetime(2026, 3, 11, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        repository = Mock()
        repository.get_by_date.return_value = [
            make_row(chat_id=1, item="Teclado"),
            make_row(chat_id=2, item="Mouse"),
        ]
        send_message = AsyncMock(side_effect=[Exception("falhou"), None])
        context = make_context(send_message=send_message)

        await checar_entregas(context, repository)

        self.assertEqual(context.bot.send_message.await_count, 2)
