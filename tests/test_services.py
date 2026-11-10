import html
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from services import (
    EntradaInvalida,
    data_hoje,
    mensagem_erro,
    mensagem_lista,
    mensagem_start,
    selecionar_por_indice,
)
from services.encomendas import (
    MSG_FALTOU_NUMERO,
    MSG_LISTA_VAZIA_REMOVER,
    MSG_NAO_EH_NUMERO,
)

HOJE = date(2026, 11, 10)
SP = ZoneInfo("America/Sao_Paulo")


# ---------- selecionar_por_indice ----------

ITENS = ["a", "b", "c"]


@pytest.mark.parametrize("indice, esperado", [("1", "a"), ("3", "c"), (" 2 ", "b")])
def test_selecionar_valido(indice, esperado):
    assert selecionar_por_indice(ITENS, indice) == esperado


def test_selecionar_lista_vazia():
    with pytest.raises(EntradaInvalida) as e:
        selecionar_por_indice([], "1")
    assert e.value.mensagem == MSG_LISTA_VAZIA_REMOVER


@pytest.mark.parametrize("indice", [None, "", "  "])
def test_selecionar_sem_numero(indice):
    with pytest.raises(EntradaInvalida) as e:
        selecionar_por_indice(ITENS, indice)
    assert e.value.mensagem == MSG_FALTOU_NUMERO


@pytest.mark.parametrize("indice", ["um", "1.5", "1a"])
def test_selecionar_nao_numerico(indice):
    with pytest.raises(EntradaInvalida) as e:
        selecionar_por_indice(ITENS, indice)
    assert e.value.mensagem == MSG_NAO_EH_NUMERO


@pytest.mark.parametrize("indice", ["0", "4", "-1"])
def test_selecionar_fora_do_intervalo(indice):
    with pytest.raises(EntradaInvalida) as e:
        selecionar_por_indice(ITENS, indice)
    assert e.value.mensagem == "tá viajando? só tem 3 itens na lista. digita um número válido."


# ---------- datas ----------


def test_hoje_no_meio_do_dia():
    assert data_hoje(datetime(2026, 11, 10, 12, 0, tzinfo=SP), SP) == date(2026, 11, 10)


def test_hoje_usa_o_fuso_e_nao_utc():
    # 01:30 UTC do dia 11 ainda é 22:30 do dia 10 em SP
    agora = datetime(2026, 11, 11, 1, 30, tzinfo=UTC)
    assert data_hoje(agora, SP) == date(2026, 11, 10)
    assert data_hoje(agora, UTC) == date(2026, 11, 11)


def test_datas_recusam_datetime_sem_fuso():
    with pytest.raises(ValueError):
        data_hoje(datetime(2026, 11, 10, 12, 0), SP)


# ---------- mensagens ----------


class _Enc:
    def __init__(self, item, data):
        self.item = item
        self.data = data


def test_mensagem_lista():
    texto = mensagem_lista([_Enc("fone", date(2026, 12, 1)), _Enc("Wi-Fi", date(2026, 12, 2))])
    assert texto.startswith("===== ENCOMENDAS =====")
    assert "1. 📦 fone\n    📅 Previsão: 01/12/2026" in texto
    assert "2. 📦 Wi-Fi\n    📅 Previsão: 02/12/2026" in texto


def test_mensagem_lista_vazia():
    assert mensagem_lista([]) == "❌ Lista Vazia"


def test_mensagem_erro_escapa_html():
    texto = mensagem_erro("<update>", "{}", "{}", "File <stdin>, a & b")
    assert "&lt;update&gt;" in texto
    assert "File &lt;stdin&gt;, a &amp; b" in texto
    assert "<stdin>" not in texto


def test_mensagem_erro_corta_e_mantem_fim_do_traceback():
    traceback = "linha inútil <x>\n" * 1000 + "ValueError: o erro de verdade <aqui>"
    texto = mensagem_erro("u" * 10_000, "{}", "{}", traceback)
    assert len(texto) <= 4096
    assert texto.endswith(html.escape("ValueError: o erro de verdade <aqui>") + "</pre>")
    # o corte não pode deixar entidade html pela metade
    corpo_tb = texto.rsplit("<pre>", 1)[1].removesuffix("</pre>")
    assert corpo_tb.startswith("…")
    trecho = html.unescape(corpo_tb[1:])
    assert traceback.endswith(trecho)
    assert html.escape(trecho) == corpo_tb[1:]


def test_mensagem_erro_curta_nao_corta():
    texto = mensagem_erro("u", "{}", "{}", "tb curto")
    assert "…" not in texto
    assert texto.endswith("<pre>tb curto</pre>")


def test_mensagem_start_usa_horario_configurado():
    texto = mensagem_start(time(7, 30))
    assert "todo dia às 07:30 eu vou avisar" in texto
    assert "/testar_alerta" not in texto
