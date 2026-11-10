import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from telegram.constants import ParseMode

from config import Settings
from handlers import (
    checar_entregas,
    error_handler,
    limpar_encomendas_antigas,
    remover,
)
from handlers import (
    testar_alerta as cmd_testar_alerta,  # alias: pytest coletaria 'testar_*' como teste
)
from handlers.adicionar import (
    CB_DESFAZER,
    ESPERANDO_DATA,
    ESPERANDO_ITEM,
    FIM,
    adicionar,
    botao_atalho,
    botao_digitar,
    cancelar,
    desfazer,
    receber_data,
    receber_item,
)
from handlers.lista import (
    CB_REMOVER,
    CB_REMOVER_NAO,
    CB_REMOVER_SIM,
    botao_remover,
    botao_remover_nao,
    botao_remover_sim,
    listar,
)
from services import MSG_ERRO_REMOVER, MSG_ERRO_SALVAR

TZ = ZoneInfo("America/Sao_Paulo")
CHAT = 111
DEV_CHAT = 999


@dataclass
class EncomendaFake:
    id: int
    chat_id: int
    item: str
    data: date
    dono: str = "Sem dono"


class RepositorioFake:
    """Implementação em memória do EncomendaRepository."""

    def __init__(self, falhar: bool = False):
        self.encomendas: list[EncomendaFake] = []
        self.falhar = falhar
        self.removidos: list[tuple[int, int]] = []
        self.remove_before_chamado_com: date | None = None
        self._proximo_id = 1

    def create(self, chat_id, item, data, dono="Sem dono"):
        if self.falhar:
            return None
        encomenda = EncomendaFake(self._proximo_id, chat_id, item, data, dono)
        self._proximo_id += 1
        self.encomendas.append(encomenda)
        return encomenda

    def remove(self, chat_id, encomenda_id):
        self.removidos.append((chat_id, encomenda_id))
        if self.falhar:
            return False
        antes = len(self.encomendas)
        self.encomendas = [e for e in self.encomendas if not (e.id == encomenda_id and e.chat_id == chat_id)]
        return len(self.encomendas) < antes

    def get_by_chat_id(self, chat_id):
        return sorted((e for e in self.encomendas if e.chat_id == chat_id), key=lambda e: (e.data, e.id))

    def get_by_date(self, data):
        return [e for e in self.encomendas if e.data == data]

    def remove_before(self, data):
        self.remove_before_chamado_com = data
        antes = len(self.encomendas)
        self.encomendas = [e for e in self.encomendas if e.data >= data]
        return antes - len(self.encomendas)


def make_settings(developer_chat_id: int | None = DEV_CHAT) -> Settings:
    return Settings(
        telegram_token="token",
        database_url="postgresql://x",
        developer_chat_id=developer_chat_id,
        time_zone=TZ,
        alert_time=time(8, 0, tzinfo=TZ),
        log_level="INFO",
    )


def make_update(chat_id: int = CHAT, first_name: str = "Ana", texto: str | None = None, callback_data=None):
    callback_query = None
    if callback_data is not None:
        callback_query = SimpleNamespace(
            data=callback_data,
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
            edit_message_reply_markup=AsyncMock(),
        )
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_user=SimpleNamespace(
            first_name=first_name, mention_html=lambda: f'<a href="tg://user?id=1">{first_name}</a>'
        ),
        effective_message=SimpleNamespace(message_id=42, text=texto),
        callback_query=callback_query,
    )


def make_context(args=None, error=None, user_data=None):
    return SimpleNamespace(
        bot=SimpleNamespace(
            send_message=AsyncMock(return_value=SimpleNamespace(message_id=100)),
            edit_message_reply_markup=AsyncMock(),
        ),
        args=args or [],
        error=error,
        chat_data={},
        user_data={} if user_data is None else user_data,
    )


def textos_enviados(context) -> list[str]:
    return [chamada.kwargs["text"] for chamada in context.bot.send_message.await_args_list]


# ---------- /adicionar ----------


def test_adicionar_sucesso():
    repo = RepositorioFake()
    context = make_context(args="Wi-Fi mesh - 10/12/2099".split())
    estado = asyncio.run(adicionar(make_update(), context, repository=repo, settings=make_settings()))

    assert estado == FIM
    assert len(repo.encomendas) == 1
    criada = repo.encomendas[0]
    assert (criada.chat_id, criada.item, criada.data, criada.dono) == (CHAT, "Wi-Fi mesh", date(2099, 12, 10), "Ana")
    context.bot.send_message.assert_awaited_once()
    assert context.bot.send_message.await_args.kwargs["chat_id"] == CHAT
    assert "📦 Wi-Fi mesh" in textos_enviados(context)[0]
    assert "📅 10/12/2099" in textos_enviados(context)[0]


def test_adicionar_falha_no_repositorio():
    repo = RepositorioFake(falhar=True)
    context = make_context(args="fone - 10/12/2099".split())
    asyncio.run(adicionar(make_update(), context, repository=repo, settings=make_settings()))

    assert textos_enviados(context) == [MSG_ERRO_SALVAR]


def test_adicionar_entrada_invalida_nao_salva():
    repo = RepositorioFake()
    context = make_context(args="fone - 01/01/2000".split())
    asyncio.run(adicionar(make_update(), context, repository=repo, settings=make_settings()))

    assert repo.encomendas == []
    assert "já passou" in textos_enviados(context)[0]


# ---------- /listar ----------


def test_listar_so_do_chat():
    repo = RepositorioFake()
    repo.create(CHAT, "fone", date(2099, 1, 2))
    repo.create(222, "de outro chat", date(2099, 1, 1))
    context = make_context()
    asyncio.run(listar(make_update(), context, repository=repo))

    (texto,) = textos_enviados(context)
    assert "1. 📦 fone" in texto
    assert "de outro chat" not in texto


# ---------- /remover ----------


def test_remover_pelo_indice_chama_remove_com_chat_e_id():
    repo = RepositorioFake()
    tardia = repo.create(CHAT, "tardia", date(2099, 5, 1))
    cedo = repo.create(CHAT, "cedo", date(2099, 1, 1))
    context = make_context(args=["2"])
    asyncio.run(remover(make_update(), context, repository=repo))

    # índice 2 segue a ordem do /listar (por data), então é a "tardia"
    assert repo.removidos == [(CHAT, tardia.id)]
    assert [e.id for e in repo.encomendas] == [cedo.id]
    assert "'tardia' foi removido" in textos_enviados(context)[0]


def test_remover_indice_invalido_nao_remove():
    repo = RepositorioFake()
    repo.create(CHAT, "fone", date(2099, 1, 1))
    context = make_context(args=["5"])
    asyncio.run(remover(make_update(), context, repository=repo))

    assert repo.removidos == []
    assert textos_enviados(context) == ["tá viajando? só tem 1 itens na lista. digita um número válido."]


def test_remover_falha_no_repositorio():
    repo = RepositorioFake()
    repo.create(CHAT, "fone", date(2099, 1, 1))
    repo.falhar = True
    context = make_context(args=["1"])
    asyncio.run(remover(make_update(), context, repository=repo))

    assert textos_enviados(context) == [MSG_ERRO_REMOVER]


# ---------- /testar_alerta ----------


def test_testar_alerta_ignorado_fora_do_chat_do_dev():
    repo = RepositorioFake()
    context = make_context()
    asyncio.run(cmd_testar_alerta(make_update(chat_id=CHAT), context, repository=repo, settings=make_settings()))

    context.bot.send_message.assert_not_awaited()


def test_testar_alerta_ignorado_sem_dev_configurado():
    context = make_context()
    asyncio.run(cmd_testar_alerta(make_update(), context, repository=RepositorioFake(), settings=make_settings(None)))

    context.bot.send_message.assert_not_awaited()


def test_testar_alerta_no_chat_do_dev_roda_checagem():
    context = make_context()
    update = make_update(chat_id=DEV_CHAT)
    asyncio.run(cmd_testar_alerta(update, context, repository=RepositorioFake(), settings=make_settings()))

    assert textos_enviados(context) == ["⚙️ forçando a checagem de entregas de amanhã agr..."]


# ---------- jobs ----------


def test_checar_entregas_avisa_cada_chat_mesmo_se_um_falhar():
    amanha = datetime.now(TZ).date() + timedelta(days=1)
    repo = RepositorioFake()
    repo.create(1, "bloqueado", amanha)
    repo.create(2, "fone", amanha)
    repo.create(3, "depois", amanha + timedelta(days=1))
    context = make_context()
    context.bot.send_message.side_effect = [Exception("bot bloqueado"), None]
    asyncio.run(checar_entregas(context, repository=repo, settings=make_settings()))

    chats = [c.kwargs["chat_id"] for c in context.bot.send_message.await_args_list]
    assert chats == [1, 2]
    assert "'fone' tá previsto pra chegar AMANHÃ" in textos_enviados(context)[1]


def test_limpar_encomendas_antigas_remove_antes_de_hoje():
    repo = RepositorioFake()
    asyncio.run(limpar_encomendas_antigas(make_context(), repository=repo, settings=make_settings()))

    assert repo.remove_before_chamado_com == datetime.now(TZ).date()


# ---------- error_handler ----------


def _erro_com_traceback(mensagem: str) -> Exception:
    try:
        raise ValueError(mensagem)
    except ValueError as e:
        return e


def test_error_handler_sem_dev_so_loga():
    context = make_context(error=_erro_com_traceback("boom"))
    asyncio.run(error_handler(None, context, settings=make_settings(None)))

    context.bot.send_message.assert_not_awaited()


def test_error_handler_escapa_html():
    context = make_context(error=_erro_com_traceback("<b>quebrou</b> & tal"))
    asyncio.run(error_handler("<update>", context, settings=make_settings()))

    context.bot.send_message.assert_awaited_once()
    kwargs = context.bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == DEV_CHAT
    assert kwargs["parse_mode"] == ParseMode.HTML
    assert "&lt;b&gt;quebrou&lt;/b&gt; &amp; tal" in kwargs["text"]
    assert "&lt;update&gt;" in kwargs["text"]
    assert "<b>" not in kwargs["text"]


def test_error_handler_trunca_mantendo_fim_do_traceback():
    context = make_context(error=_erro_com_traceback("x" * 10_000 + " FIM_DO_ERRO"))
    context.chat_data = {"lixo": "y" * 10_000}
    asyncio.run(error_handler("u" * 10_000, context, settings=make_settings()))

    texto = context.bot.send_message.await_args.kwargs["text"]
    assert len(texto) <= 4096
    assert "FIM_DO_ERRO" in texto


# ---------- /adicionar: fluxo guiado ----------


def _botoes(chamada) -> list[str]:
    teclado = chamada.kwargs.get("reply_markup")
    return [b.callback_data for linha in getattr(teclado, "inline_keyboard", []) for b in linha]


def _rodar(callback, update, context, repo, **extra):
    return asyncio.run(callback(update, context, repository=repo, settings=make_settings(), **extra))


def test_adicionar_sem_nada_pergunta_item_e_depois_data_e_salva_pelo_atalho():
    repo = RepositorioFake()
    user_data = {}

    context = make_context(user_data=user_data)
    assert _rodar(adicionar, make_update(), context, repo) == ESPERANDO_ITEM
    pergunta = context.bot.send_message.await_args
    assert pergunta.kwargs["text"] == "qual o pacote? 📦"
    assert pergunta.kwargs["reply_markup"].force_reply
    assert pergunta.kwargs["reply_markup"].selective
    assert pergunta.kwargs["reply_parameters"].message_id == 42  # responde a mensagem da pessoa

    context = make_context(user_data=user_data)
    assert _rodar(receber_item, make_update(texto="fone bluetooth"), context, repo) == ESPERANDO_DATA
    assert "fone bluetooth" in textos_enviados(context)[0]
    assert "add:dias:1" in _botoes(context.bot.send_message.await_args)

    context = make_context(user_data=user_data)
    update = make_update(callback_data="add:dias:1")
    assert _rodar(botao_atalho, update, context, repo) == FIM
    update.callback_query.answer.assert_awaited_once()
    criada = repo.encomendas[0]
    assert (criada.item, criada.chat_id) == ("fone bluetooth", CHAT)
    assert criada.data == datetime.now(TZ).date() + timedelta(days=1)
    # tirou os botões da pergunta da data e mandou confirmação com desfazer
    context.bot.edit_message_reply_markup.assert_awaited_once()
    assert context.bot.edit_message_reply_markup.await_args.kwargs["message_id"] == 100
    assert _botoes(context.bot.send_message.await_args) == [f"{CB_DESFAZER}{criada.id}"]
    assert user_data == {}


def test_adicionar_so_item_pergunta_data_e_aceita_data_digitada():
    repo = RepositorioFake()
    user_data = {}
    context = make_context(args=["teclado"], user_data=user_data)
    assert _rodar(adicionar, make_update(), context, repo) == ESPERANDO_DATA

    context = make_context(user_data=user_data)
    assert _rodar(receber_data, make_update(texto="não sei"), context, repo) == ESPERANDO_DATA
    assert "não entendi a data" in textos_enviados(context)[0]
    assert repo.encomendas == []

    context = make_context(user_data=user_data)
    assert _rodar(receber_data, make_update(texto="15/03/2099"), context, repo) == FIM
    assert (repo.encomendas[0].item, repo.encomendas[0].data) == ("teclado", date(2099, 3, 15))


def test_adicionar_so_data_pergunta_item_e_salva():
    repo = RepositorioFake()
    user_data = {}
    context = make_context(args=["10/12/2099"], user_data=user_data)
    assert _rodar(adicionar, make_update(), context, repo) == ESPERANDO_ITEM

    context = make_context(user_data=user_data)
    assert _rodar(receber_item, make_update(texto="caixa"), context, repo) == FIM
    assert (repo.encomendas[0].item, repo.encomendas[0].data) == ("caixa", date(2099, 12, 10))


def test_resposta_do_item_pode_trazer_a_data_junto():
    repo = RepositorioFake()
    user_data = {}
    _rodar(adicionar, make_update(), make_context(user_data=user_data), repo)
    estado = _rodar(receber_item, make_update(texto="mesa 10/12/2099"), make_context(user_data=user_data), repo)
    assert estado == FIM
    assert (repo.encomendas[0].item, repo.encomendas[0].data) == ("mesa", date(2099, 12, 10))


def test_botao_digitar_menciona_a_pessoa_com_force_reply():
    user_data = {}
    _rodar(adicionar, make_update(), make_context(args=["fone"], user_data=user_data), RepositorioFake())
    context = make_context(user_data=user_data)
    update = make_update(callback_data="add:digitar")
    assert asyncio.run(botao_digitar(update, context)) == ESPERANDO_DATA
    chamada = context.bot.send_message.await_args
    assert chamada.kwargs["text"].startswith('<a href="tg://user?id=1">Ana</a>')
    assert chamada.kwargs["parse_mode"] == ParseMode.HTML
    assert chamada.kwargs["reply_markup"].selective


def test_cancelar_limpa_rascunho_e_tira_botoes():
    user_data = {}
    _rodar(adicionar, make_update(), make_context(args=["fone"], user_data=user_data), RepositorioFake())
    assert user_data
    context = make_context(user_data=user_data)
    assert asyncio.run(cancelar(make_update(), context)) == FIM
    assert user_data == {}
    context.bot.edit_message_reply_markup.assert_awaited_once()
    assert textos_enviados(context) == ["beleza, cancelei ❌"]


def test_rascunho_separado_por_chat():
    user_data = {}
    _rodar(adicionar, make_update(chat_id=1), make_context(args=["fone"], user_data=user_data), RepositorioFake())
    _rodar(adicionar, make_update(chat_id=2), make_context(args=["mesa"], user_data=user_data), RepositorioFake())
    assert user_data["adicionar:1"]["item"] == "fone"
    assert user_data["adicionar:2"]["item"] == "mesa"


# ---------- desfazer ----------


def test_desfazer_remove_e_edita_mensagem():
    repo = RepositorioFake()
    encomenda = repo.create(CHAT, "fone", date(2099, 1, 1))
    update = make_update(callback_data=f"{CB_DESFAZER}{encomenda.id}")
    asyncio.run(desfazer(update, make_context(), repository=repo))
    assert repo.encomendas == []
    assert "desfeito" in update.callback_query.edit_message_text.await_args.args[0]


def test_desfazer_nao_remove_de_outro_chat():
    repo = RepositorioFake()
    encomenda = repo.create(222, "fone", date(2099, 1, 1))
    update = make_update(callback_data=f"{CB_DESFAZER}{encomenda.id}")
    asyncio.run(desfazer(update, make_context(), repository=repo))
    assert len(repo.encomendas) == 1
    assert repo.removidos == []
    update.callback_query.answer.assert_awaited_once_with("esse já não tá mais na lista")


# ---------- /listar: botões ----------


def test_listar_tem_um_botao_por_encomenda():
    repo = RepositorioFake()
    a = repo.create(CHAT, "fone", date(2099, 1, 2))
    b = repo.create(CHAT, "um item com um nome muito comprido demais", date(2099, 1, 1))
    context = make_context()
    asyncio.run(listar(make_update(), context, repository=repo))
    assert _botoes(context.bot.send_message.await_args) == [f"{CB_REMOVER}{b.id}", f"{CB_REMOVER}{a.id}"]
    rotulo = context.bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard[0][0].text
    assert rotulo.startswith("🗑️ 1. ") and rotulo.endswith("…")


def test_listar_vazia_sem_botoes():
    context = make_context()
    asyncio.run(listar(make_update(), context, repository=RepositorioFake()))
    assert context.bot.send_message.await_args.kwargs["reply_markup"] is None


def test_botao_remover_pede_confirmacao_sem_apagar():
    repo = RepositorioFake()
    e = repo.create(CHAT, "fone", date(2099, 1, 2))
    update = make_update(callback_data=f"{CB_REMOVER}{e.id}")
    asyncio.run(botao_remover(update, make_context(), repository=repo))
    assert len(repo.encomendas) == 1
    chamada = update.callback_query.edit_message_text.await_args
    assert "tirar 📦 'fone' (02/01/2099)" in chamada.args[0]
    assert _botoes(chamada) == [f"{CB_REMOVER_SIM}{e.id}", CB_REMOVER_NAO]


def test_botao_remover_sim_apaga_e_atualiza_lista():
    repo = RepositorioFake()
    e = repo.create(CHAT, "fone", date(2099, 1, 2))
    fica = repo.create(CHAT, "mesa", date(2099, 1, 3))
    update = make_update(callback_data=f"{CB_REMOVER_SIM}{e.id}")
    asyncio.run(botao_remover_sim(update, make_context(), repository=repo))
    assert repo.removidos == [(CHAT, e.id)]
    chamada = update.callback_query.edit_message_text.await_args
    assert "1. 📦 mesa" in chamada.args[0]
    assert _botoes(chamada) == [f"{CB_REMOVER}{fica.id}"]


def test_botao_remover_nao_volta_pra_lista():
    repo = RepositorioFake()
    repo.create(CHAT, "fone", date(2099, 1, 2))
    update = make_update(callback_data=CB_REMOVER_NAO)
    asyncio.run(botao_remover_nao(update, make_context(), repository=repo))
    assert len(repo.encomendas) == 1
    assert "1. 📦 fone" in update.callback_query.edit_message_text.await_args.args[0]
