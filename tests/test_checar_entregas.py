import os
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TIME_ZONE", "America/Sao_Paulo")

from usecases import checar_entregas

from tests.helpers import make_context
from repositories.in_memory_encomenda_repository import InMemoryEncomendaRepository

pytestmark = pytest.mark.asyncio


@patch("usecases.checar_encomendas_job.datetime")
async def test_deve_buscar_entregas_de_amanha_e_enviar_alerta(datetime_mock):
    data_atual = datetime(2026, 3, 11, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    datetime_mock.now.return_value = data_atual
    repository = InMemoryEncomendaRepository()
    repository.seed(item="Teclado")
    context = make_context()

    await checar_entregas(context, repository)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="🚨 ALERTA DE ENTREGA 🚨\n\n📦 'Teclado' tá previsto pra chegar AMANHÃ (12/03/2026)!\n\nFiquem espertos pra receber o carteiro.",
    )


@patch("usecases.checar_encomendas_job.datetime")
async def test_deve_continuar_mesmo_se_um_envio_falhar(datetime_mock):
    datetime_mock.now.return_value = datetime(2026, 3, 11, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    repository = InMemoryEncomendaRepository()
    repository.seed(chat_id=1, item="Teclado")
    repository.seed(chat_id=2, item="Mouse")
    send_message = AsyncMock(side_effect=[Exception("falhou"), None])
    context = make_context(send_message=send_message)

    await checar_entregas(context, repository)

    assert context.bot.send_message.await_count == 2
