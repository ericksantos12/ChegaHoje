from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock


def make_update(chat_id: int = 123, user_name: str = "Erick") -> SimpleNamespace:
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_user=SimpleNamespace(first_name=user_name),
    )


def make_context(args: list[str] | None = None, send_message: AsyncMock | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        args=args or [],
        bot=SimpleNamespace(send_message=send_message or AsyncMock()),
    )


def make_row(
    encomenda_id: int = 1,
    chat_id: int = 123,
    item: str = "Pacote",
    delivery_date: date = date(2026, 3, 12),
) -> SimpleNamespace:
    return SimpleNamespace(id=encomenda_id, chat_id=chat_id, item=item, data=delivery_date)
