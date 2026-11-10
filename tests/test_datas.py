from datetime import date

import pytest

from services import (
    MSG_DATA_NAO_ENTENDI,
    MSG_DATA_PASSADA,
    MSG_DATA_ZOADA,
    EntradaInvalida,
    interpretar_data,
    separar_item_e_data,
)

HOJE = date(2026, 11, 10)  # terça-feira


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        # formato antigo continua valendo
        ("liquidificador - 27/12/2026", ("liquidificador", date(2026, 12, 27))),
        ("Wi-Fi mesh - 10/12/2026", ("Wi-Fi mesh", date(2026, 12, 10))),
        ("fone-10/12/2026", ("fone", date(2026, 12, 10))),
        # sem hífen, sem ano
        ("fone bluetooth 15/03", ("fone bluetooth", date(2027, 3, 15))),
        ("livro, dia 20/11", ("livro", date(2026, 11, 20))),
        ("cadeira 20.12.27", ("cadeira", date(2027, 12, 20))),
        ("cabo de 2/3 metros 15/03", ("cabo de 2/3 metros", date(2027, 3, 15))),
        # relativas
        ("Café hoje", ("Café", HOJE)),
        ("caixa pra hoje", ("caixa", HOJE)),
        ("liquidificador amanhã", ("liquidificador", date(2026, 11, 11))),
        ("liquidificador AMANHA", ("liquidificador", date(2026, 11, 11))),
        ("panela depois de amanhã", ("panela", date(2026, 11, 12))),
        ("teclado em 5 dias", ("teclado", date(2026, 11, 15))),
        ("tênis em uma semana", ("tênis", date(2026, 11, 17))),
        ("mouse daqui a 2 semanas", ("mouse", date(2026, 11, 24))),
        # dias da semana: próxima ocorrência depois de hoje
        ("Wi-Fi mesh sexta", ("Wi-Fi mesh", date(2026, 11, 13))),
        ("Ônibus de brinquedo SEXTA-FEIRA", ("Ônibus de brinquedo", date(2026, 11, 13))),
        ("mesa na próxima terça-feira", ("mesa", date(2026, 11, 17))),
        ("vaso segunda", ("vaso", date(2026, 11, 16))),
    ],
)
def test_separa_item_e_data(texto, esperado):
    assert separar_item_e_data(texto, HOJE) == esperado


@pytest.mark.parametrize("texto", ["pacote", "Hoje Café", "pao 5", "fone 15-03-2027", ""])
def test_sem_data_no_fim_devolve_none(texto):
    assert separar_item_e_data(texto, HOJE) == (texto.strip(), None)


@pytest.mark.parametrize(("texto", "esperado"), [("amanhã", date(2026, 11, 11)), ("15/03", date(2027, 3, 15))])
def test_so_data_devolve_item_vazio(texto, esperado):
    assert separar_item_e_data(texto, HOJE) == ("", esperado)


def test_dia_da_semana_igual_a_hoje_vai_pra_semana_que_vem():
    assert separar_item_e_data("x terça", HOJE) == ("x", date(2026, 11, 17))


def test_sem_ano_data_antiga_vai_pro_ano_que_vem():
    assert separar_item_e_data("x 15/03", HOJE)[1] == date(2027, 3, 15)


@pytest.mark.parametrize("texto", ["x 9/11", "x 01/10", "x 01/01/2025", "x 09/11/2026"])
def test_data_passada_recusada(texto):
    with pytest.raises(EntradaInvalida) as e:
        separar_item_e_data(texto, HOJE)
    assert e.value.mensagem == MSG_DATA_PASSADA


def test_aceita_hoje_com_ano():
    assert separar_item_e_data("x 10/11/2026", HOJE) == ("x", HOJE)


@pytest.mark.parametrize("texto", ["x 31/02", "x 32/01", "x 10/13/2027"])
def test_data_inexistente(texto):
    with pytest.raises(EntradaInvalida) as e:
        separar_item_e_data(texto, HOJE)
    assert e.value.mensagem == MSG_DATA_ZOADA


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("sexta", date(2026, 11, 13)), ("dia 15/03", date(2027, 3, 15)), ("Amanhã!", date(2026, 11, 11))],
)
def test_interpretar_data(texto, esperado):
    assert interpretar_data(texto, HOJE) == esperado


@pytest.mark.parametrize("texto", ["", "semana que vem", "fone amanhã"])
def test_interpretar_data_nao_entendeu(texto):
    with pytest.raises(EntradaInvalida) as e:
        interpretar_data(texto, HOJE)
    assert e.value.mensagem == MSG_DATA_NAO_ENTENDI
