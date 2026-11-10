"""Interpretação de datas escritas do jeito que a galera fala.

Aceita (sem diferenciar maiúsculas e acentos):
- dd/mm, dd/mm/aa, dd/mm/aaaa (também com '.'); sem ano vale a próxima ocorrência,
  exceto se a data passou há pouco (até JANELA_DATA_PASSADA_DIAS): aí é recusada como passada
- hoje, amanhã, depois de amanhã
- dia da semana (segunda ... domingo, com ou sem '-feira', 'na'/'no'/'próxima' na frente);
  sempre a próxima ocorrência depois de hoje (na sexta, 'sexta' é a da semana que vem)
- em N dias / em N semanas / daqui a N dias (N em número, 'um' ou 'uma')
"""

import re
import unicodedata
from datetime import date, timedelta

from services.erros import EntradaInvalida

JANELA_DATA_PASSADA_DIAS = 60

MSG_DATA_ZOADA = "opa, data zoada! essa data não existe, confere aí (ex: 15/03)"
MSG_DATA_PASSADA = "eita, essa data já passou! só aceito data de hoje pra frente."
MSG_DATA_NAO_ENTENDI = "não entendi a data 🤔 manda tipo: 15/03, amanhã, sexta ou em 5 dias"

_DIAS_SEMANA = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}

_EXPRESSAO_DATA = r"""
(?P<data>
    (?P<dia>\d{1,2})(?P<sep>[/.])(?P<mes>\d{1,2})(?:(?P=sep)(?P<ano>\d{4}|\d{2}))?
  | (?P<hoje>hoje)
  | (?P<depois_de_amanha>depois\s+de\s+amanha)
  | (?P<amanha>amanha)
  | (?:em|daqui\s+a)\s+(?P<qtd>\d{1,3}|uma?)\s+(?P<unidade>dias?|semanas?)
  | (?:(?:na|no|nessa|nesse|essa|esse|proxima|proximo|na\s+proxima|no\s+proximo)\s+)?
    (?P<semana>segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:[\s-]feira)?
)
"""

# a data fica no FIM do texto; antes dela vem o item e, opcionalmente, um separador
# ('-', ',', ':') e/ou 'dia' / 'pra' / 'chega'
_ITEM_E_DATA = re.compile(
    rf"""^(?P<item>.*?)
    (?:^|[\s,;:\-–—]+)
    (?:(?:chega|chegando|pra|para|dia)\s+)*
    {_EXPRESSAO_DATA}
    [\s.!]*$""",
    re.VERBOSE,
)
_SO_DATA = re.compile(rf"^\s*(?:dia\s+)?{_EXPRESSAO_DATA}[\s.!]*$", re.VERBOSE)


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento, mantendo o MESMO tamanho (pra fatiar o texto original)."""
    saida = []
    for caractere in texto:
        base = unicodedata.normalize("NFD", caractere)[0]
        minuscula = base.lower()
        saida.append(minuscula if len(minuscula) == 1 else base)
    return "".join(saida)


def _resolver(m: re.Match[str], hoje: date) -> date:
    if m.group("dia"):
        dia, mes = int(m.group("dia")), int(m.group("mes"))
        ano_txt = m.group("ano")
        try:
            if ano_txt:
                ano = int(ano_txt) + (2000 if len(ano_txt) == 2 else 0)
                data = date(ano, mes, dia)
            else:
                data = date(hoje.year, mes, dia)
                # data recente no passado provavelmente é engano; mais antiga é do ano que vem
                if data < hoje and (hoje - data).days > JANELA_DATA_PASSADA_DIAS:
                    data = date(hoje.year + 1, mes, dia)
        except ValueError:
            raise EntradaInvalida(MSG_DATA_ZOADA) from None
        if data < hoje:
            raise EntradaInvalida(MSG_DATA_PASSADA)
        return data

    if m.group("hoje"):
        return hoje
    if m.group("depois_de_amanha"):
        return hoje + timedelta(days=2)
    if m.group("amanha"):
        return hoje + timedelta(days=1)

    if m.group("qtd"):
        qtd_txt = m.group("qtd")
        qtd = 1 if qtd_txt in ("um", "uma") else int(qtd_txt)
        dias = qtd * 7 if m.group("unidade").startswith("semana") else qtd
        return hoje + timedelta(days=dias)

    alvo = _DIAS_SEMANA[m.group("semana")]
    return hoje + timedelta(days=(alvo - hoje.weekday() - 1) % 7 + 1)


def separar_item_e_data(texto: str, hoje: date) -> tuple[str, date | None]:
    """Separa '<item> <data>' em (item, data).

    Se não tiver data no fim do texto, devolve (texto, None). O item pode vir vazio
    quando a pessoa só mandou a data. Data reconhecida mas inválida/passada
    levanta EntradaInvalida.
    """
    texto = (texto or "").strip()
    m = _ITEM_E_DATA.match(_normalizar(texto))
    if not m:
        return texto, None
    item = texto[m.start("item") : m.end("item")].strip(" \t,;:-–—")
    return item, _resolver(m, hoje)


def interpretar_data(texto: str, hoje: date) -> date:
    """Interpreta um texto que deveria ser SÓ uma data (resposta do fluxo guiado)."""
    m = _SO_DATA.match(_normalizar(texto or ""))
    if not m:
        raise EntradaInvalida(MSG_DATA_NAO_ENTENDI)
    return _resolver(m, hoje)
