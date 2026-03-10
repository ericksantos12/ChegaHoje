from datetime import date
from typing import Optional, Protocol

from db.models.encomenda import Encomenda


class EncomendaRepository(Protocol):

    def create(
        self,
        chat_id: int,
        item: str,
        data: date,
        dono: str = "Sem dono",
    ) -> tuple[Optional[Encomenda], bool]:
        """Returns (encomenda, created)."""
        ...

    def update(self, encomenda_id: int, **fields: object) -> bool:
        """Returns True when an existing row is updated."""
        ...

    def remove(self, encomenda_id: int) -> bool:
        """Returns True when an existing row is removed."""
        ...

    def get_by_chat_id(self, chat_id: int) -> list[Encomenda]:
        """Returns all encomendas for the given chat_id."""
        ...

    def get_by_date(self, date: str) -> list[Encomenda]:
        """Returns the encomenda with the given date, or None if not found."""
        ...