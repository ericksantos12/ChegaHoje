from datetime import date
from typing import Optional, Protocol

from db.models.encomenda import Encomenda


class EncomendaRepository(Protocol):
    """Contrato de acesso a dados de encomendas.

    Implementações não devem lançar exceções de banco: em caso de erro,
    registram no log e retornam o valor de falha documentado.
    Os objetos retornados ficam desanexados da sessão (somente leitura).
    """

    def create(
        self,
        chat_id: int,
        item: str,
        data: date,
        dono: str = "Sem dono",
    ) -> Optional[Encomenda]:
        """Retorna a encomenda criada, ou None em caso de erro."""
        ...

    def remove(self, chat_id: int, encomenda_id: int) -> bool:
        """Remove a encomenda se ela pertencer ao chat. True se removeu."""
        ...

    def get_by_chat_id(self, chat_id: int) -> list[Encomenda]:
        """Encomendas do chat ordenadas por (data, id). [] em caso de erro."""
        ...

    def get_by_date(self, data: date) -> list[Encomenda]:
        """Encomendas de todos os chats com a data informada. [] em caso de erro."""
        ...

    def remove_before(self, data: date) -> int:
        """Remove encomendas com data anterior a `data`. Retorna quantas removeu (0 em erro)."""
        ...
