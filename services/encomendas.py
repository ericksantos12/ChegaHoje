"""Regras de negócio das encomendas: sem Telegram e sem banco, fácil de testar."""

from collections.abc import Sequence
from datetime import date, datetime, tzinfo
from typing import TypeVar

from services.datas import separar_item_e_data
from services.erros import EntradaInvalida

FORMATO_DATA = "%d/%m/%Y"

MSG_LISTA_VAZIA_REMOVER = "a lista já tá vazia, não tem nada pra remover!"
MSG_FALTOU_NUMERO = "opa, faltou dizer o número da encomenda! usa: /remover [número] (olha o /listar pra saber)"
MSG_NAO_EH_NUMERO = "tem que ser número, po! ex: /remover 1"

MSG_EDITAR_USO = (
    "manda o número e o que mudar: /editar [número] [novo nome] [nova data]\n\n"
    "ex: /editar 2 sexta  (só a data)\n"
    "     /editar 2 fone azul  (só o nome)\n"
    "     /editar 2 fone azul 20/12  (os dois)"
)

T = TypeVar("T")


def selecionar_por_indice(encomendas: Sequence[T], indice: str | None, comando: str = "remover") -> T:
    """Escolhe a encomenda pela posição 1-based mostrada no /listar.

    `comando` ('remover', 'editar') só muda o texto das mensagens de erro.
    """
    if not encomendas:
        raise EntradaInvalida(f"a lista já tá vazia, não tem nada pra {comando}!")

    if indice is None or not indice.strip():
        raise EntradaInvalida(
            f"opa, faltou dizer o número da encomenda! usa: /{comando} [número] (olha o /listar pra saber)"
        )

    try:
        numero = int(indice)
    except ValueError:
        raise EntradaInvalida(f"tem que ser número, po! ex: /{comando} 1") from None

    if numero < 1 or numero > len(encomendas):
        raise EntradaInvalida(f"tá viajando? só tem {len(encomendas)} itens na lista. digita um número válido.")

    return encomendas[numero - 1]


def interpretar_edicao(texto: str, hoje: date) -> tuple[str | None, date | None]:
    """O que mudar numa encomenda: (novo_item, nova_data); None = não mexe.

    Usa a mesma regra do /adicionar (data no fim do texto):
    'sexta' muda só a data, 'fone azul' só o nome, 'fone azul 20/12' os dois.
    """
    if not texto or not texto.strip():
        raise EntradaInvalida(MSG_EDITAR_USO)
    item, data = separar_item_e_data(texto, hoje)
    return item or None, data


def data_hoje(agora: datetime, tz: tzinfo) -> date:
    """Data de hoje no fuso `tz`. `agora` precisa ter fuso (aware)."""
    if agora.tzinfo is None:
        raise ValueError("agora precisa ter tzinfo")
    return agora.astimezone(tz).date()


def formatar_data(data: date) -> str:
    """Data no padrão br (dd/mm/aaaa) pra mostrar no chat."""
    return data.strftime(FORMATO_DATA)
