"""Regras de negócio das encomendas: sem Telegram e sem banco, fácil de testar."""

from collections.abc import Sequence
from datetime import date, datetime, timedelta, tzinfo
from typing import TypeVar

from services.erros import EntradaInvalida

FORMATO_DATA = "%d/%m/%Y"

MSG_LISTA_VAZIA_REMOVER = "a lista já tá vazia, não tem nada pra remover!"
MSG_FALTOU_NUMERO = "opa, faltou dizer o número da encomenda! usa: /remover [número] (olha o /listar pra saber)"
MSG_NAO_EH_NUMERO = "tem que ser número, po! ex: /remover 1"

T = TypeVar("T")


def selecionar_por_indice(encomendas: Sequence[T], indice: str | None) -> T:
    """Escolhe a encomenda pela posição 1-based mostrada no /listar."""
    if not encomendas:
        raise EntradaInvalida(MSG_LISTA_VAZIA_REMOVER)

    if indice is None or not indice.strip():
        raise EntradaInvalida(MSG_FALTOU_NUMERO)

    try:
        numero = int(indice)
    except ValueError:
        raise EntradaInvalida(MSG_NAO_EH_NUMERO) from None

    if numero < 1 or numero > len(encomendas):
        raise EntradaInvalida(f"tá viajando? só tem {len(encomendas)} itens na lista. digita um número válido.")

    return encomendas[numero - 1]


def data_hoje(agora: datetime, tz: tzinfo) -> date:
    """Data de hoje no fuso `tz`. `agora` precisa ter fuso (aware)."""
    if agora.tzinfo is None:
        raise ValueError("agora precisa ter tzinfo")
    return agora.astimezone(tz).date()


def data_amanha(agora: datetime, tz: tzinfo) -> date:
    """Data de amanhã no fuso `tz`. `agora` precisa ter fuso (aware)."""
    return data_hoje(agora, tz) + timedelta(days=1)


def formatar_data(data: date) -> str:
    """Data no padrão br (dd/mm/aaaa) pra mostrar no chat."""
    return data.strftime(FORMATO_DATA)
