"""Regras de negócio das encomendas: sem Telegram e sem banco, fácil de testar."""
from collections.abc import Sequence
from datetime import date, datetime, timedelta, tzinfo
from typing import TypeVar

FORMATO_DATA = "%d/%m/%Y"

MSG_FORMATO_ERRADO = "opa, formato errado! usa assim: /adicionar nome do pacote - dd/mm/aaaa"
MSG_DATA_ZOADA = "opa, data zoada! usa o formato certinho: dd/mm/aaaa (ex: 15/03/2026)"
MSG_DATA_PASSADA = "eita, essa data já passou! só aceito data de hoje pra frente."

MSG_LISTA_VAZIA_REMOVER = "a lista já tá vazia, não tem nada pra remover!"
MSG_FALTOU_NUMERO = "opa, faltou dizer o número da encomenda! usa: /remover [número] (olha o /listar pra saber)"
MSG_NAO_EH_NUMERO = "tem que ser número, po! ex: /remover 1"

T = TypeVar("T")


class EntradaInvalida(ValueError):
    """Entrada do usuário inválida. `mensagem` é o texto pra responder no chat."""

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


def parse_adicionar(texto: str, hoje: date) -> tuple[str, date]:
    """Converte 'item - dd/mm/aaaa' em (item, data).

    Usa o último '-' como separador, então o item pode ter hífen ('Wi-Fi mesh - 10/12/2026').
    Datas no passado são recusadas; hoje é aceito.
    """
    if not texto or "-" not in texto:
        raise EntradaInvalida(MSG_FORMATO_ERRADO)

    item, data_str = (parte.strip() for parte in texto.rsplit("-", 1))
    if not item:
        raise EntradaInvalida(MSG_FORMATO_ERRADO)

    try:
        data = datetime.strptime(data_str, FORMATO_DATA).date()
    except ValueError:
        raise EntradaInvalida(MSG_DATA_ZOADA) from None

    if data < hoje:
        raise EntradaInvalida(MSG_DATA_PASSADA)

    return item, data


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
        raise EntradaInvalida(
            f"tá viajando? só tem {len(encomendas)} itens na lista. digita um número válido."
        )

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
