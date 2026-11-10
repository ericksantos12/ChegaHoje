"""Ponta a ponta: Application real do PTB com os handlers do main, bot falso sem rede.

Testa o que os testes unitários não pegam: estados do ConversationHandler, padrões de
callback, ordem dos handlers e conversa separada por usuário no mesmo grupo.
"""

import asyncio
import itertools
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from telegram import Bot, CallbackQuery, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application

import handlers.adicionar
from config import Settings
from handlers import criar_handlers_adicionar, criar_handlers_lista
from repositories.interfaces import EncomendaRepository

TZ = ZoneInfo("America/Sao_Paulo")
GRUPO = Chat(id=-1001234567890, type=Chat.SUPERGROUP)
ANA = User(id=1, first_name="Ana", is_bot=False)
BETO = User(id=2, first_name="Beto", is_bot=False)
BOT_USER = User(id=99, first_name="ChegaHoje", is_bot=True, username="chegahoje_bot")


class BotFalso(Bot):
    """Grava o que o bot mandaria em vez de chamar a API."""

    def __init__(self):
        super().__init__(token="123:falso")
        object.__setattr__(self, "enviadas", [])
        object.__setattr__(self, "respostas_callback", [])
        object.__setattr__(self, "edicoes", [])
        object.__setattr__(self, "_ids", itertools.count(1000))

    async def initialize(self):
        object.__setattr__(self, "_bot_user", BOT_USER)
        object.__setattr__(self, "_initialized", True)

    async def shutdown(self):
        pass

    async def get_me(self, *args, **kwargs):
        return BOT_USER

    async def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        self.enviadas.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup, **kwargs})
        msg = Message(next(self._ids), datetime.now(TZ), Chat(id=chat_id, type=Chat.SUPERGROUP), text=text)
        msg.set_bot(self)
        return msg

    async def answer_callback_query(self, callback_query_id, text=None, **kwargs):
        self.respostas_callback.append(text)
        return True

    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **kwargs):
        self.edicoes.append({"text": text, "reply_markup": reply_markup})
        return True

    async def edit_message_reply_markup(self, chat_id=None, message_id=None, reply_markup=None, **kwargs):
        self.edicoes.append({"message_id": message_id, "reply_markup": reply_markup})
        return True


class RepositorioMemoria:
    def __init__(self):
        self.encomendas = []
        self._ids = itertools.count(1)

    def create(self, chat_id, item, data, dono="Sem dono"):
        from types import SimpleNamespace

        e = SimpleNamespace(id=next(self._ids), chat_id=chat_id, item=item, data=data, dono=dono)
        self.encomendas.append(e)
        return e

    def remove(self, chat_id, encomenda_id):
        antes = len(self.encomendas)
        self.encomendas = [e for e in self.encomendas if not (e.chat_id == chat_id and e.id == encomenda_id)]
        return len(self.encomendas) < antes

    def get_by_chat_id(self, chat_id):
        return sorted((e for e in self.encomendas if e.chat_id == chat_id), key=lambda e: (e.data, e.id))

    def get_by_date(self, data):
        return [e for e in self.encomendas if e.data == data]

    def remove_before(self, data):
        return 0


_repo_tipado: EncomendaRepository = RepositorioMemoria()  # confere que o fake segue o Protocol


class Cenario:
    def __init__(self):
        self.bot = BotFalso()
        self.repo = RepositorioMemoria()
        settings = Settings("123:falso", "postgresql://x", None, TZ, time(8, tzinfo=TZ), "INFO")
        self.app = Application.builder().bot(self.bot).updater(None).build()
        self.app.add_handlers(criar_handlers_adicionar(repository=self.repo, settings=settings))
        self.app.add_handlers(criar_handlers_lista(repository=self.repo))
        self._ids = itertools.count(1)

    def _update(self, **kwargs):
        update = Update(next(self._ids), **kwargs)
        update.set_bot(self.bot)
        return update

    async def mensagem(self, usuario, texto):
        entidades = []
        if texto.startswith("/"):
            entidades = [MessageEntity(MessageEntity.BOT_COMMAND, 0, len(texto.split()[0]))]
        msg = Message(next(self._ids), datetime.now(TZ), GRUPO, from_user=usuario, text=texto, entities=entidades)
        msg.set_bot(self.bot)
        await self.app.process_update(self._update(message=msg))

    async def botao(self, usuario, dados, mensagem_id=500):
        msg = Message(mensagem_id, datetime.now(TZ), GRUPO, from_user=BOT_USER, text="...")
        msg.set_bot(self.bot)
        query = CallbackQuery(str(next(self._ids)), usuario, "inst", message=msg, data=dados)
        query.set_bot(self.bot)
        await self.app.process_update(self._update(callback_query=query))

    def botoes(self, indice=-1):
        teclado = self.bot.enviadas[indice]["reply_markup"]
        return [b.callback_data for linha in teclado.inline_keyboard for b in linha]


def rodar(corrotina_fn):
    async def principal():
        cenario = Cenario()
        await cenario.app.initialize()
        await cenario.app.start()  # liga o JobQueue (timeout da conversa)
        try:
            await corrotina_fn(cenario)
        finally:
            await cenario.app.stop()
            await cenario.app.shutdown()

    asyncio.run(principal())


def test_comando_completo_salva_direto_com_botao_desfazer():
    async def fluxo(c):
        await c.mensagem(ANA, "/adicionar Wi-Fi mesh 10/12/2099")
        assert [(e.item, e.data, e.dono) for e in c.repo.encomendas] == [("Wi-Fi mesh", date(2099, 12, 10), "Ana")]
        assert c.botoes() == ["desfazer:1"]

        await c.botao(ANA, "desfazer:1")
        assert c.repo.encomendas == []
        assert "desfeito" in c.bot.edicoes[-1]["text"]

    rodar(fluxo)


def test_conversa_guiada_com_atalho_de_data():
    async def fluxo(c):
        await c.mensagem(ANA, "/adicionar")
        assert c.bot.enviadas[-1]["text"] == "qual o pacote? 📦"

        await c.mensagem(ANA, "fone bluetooth")
        assert "e chega quando?" in c.bot.enviadas[-1]["text"]
        assert "add:dias:1" in c.botoes()

        await c.botao(ANA, "add:dias:1")
        amanha = datetime.now(TZ).date() + timedelta(days=1)
        assert [(e.item, e.data) for e in c.repo.encomendas] == [("fone bluetooth", amanha)]

        # conversa acabou: texto solto não vira encomenda
        await c.mensagem(ANA, "outra coisa")
        assert len(c.repo.encomendas) == 1

    rodar(fluxo)


def test_outra_pessoa_nao_mexe_na_conversa_de_quem_ta_adicionando():
    async def fluxo(c):
        await c.mensagem(ANA, "/adicionar fone")
        await c.botao(BETO, "add:dias:0")
        assert c.repo.encomendas == []
        assert c.bot.respostas_callback[-1] == "esse botão não é pra você (ou já expirou) 👀"

        await c.mensagem(BETO, "15/03/2099")  # Beto não tá em conversa nenhuma
        assert c.repo.encomendas == []

        await c.mensagem(ANA, "15/03/2099")
        assert [(e.item, e.data, e.dono) for e in c.repo.encomendas] == [("fone", date(2099, 3, 15), "Ana")]

    rodar(fluxo)


def test_cancelar_e_reentrada():
    async def fluxo(c):
        await c.mensagem(ANA, "/adicionar fone")
        await c.mensagem(ANA, "/adicionar mesa")  # recomeça
        await c.mensagem(ANA, "amanhã")
        assert [e.item for e in c.repo.encomendas] == ["mesa"]

        await c.mensagem(ANA, "/adicionar")
        await c.mensagem(ANA, "/cancelar")
        assert c.bot.enviadas[-1]["text"] == "beleza, cancelei ❌"
        await c.mensagem(ANA, "cadeira amanhã")
        assert [e.item for e in c.repo.encomendas] == ["mesa"]

    rodar(fluxo)


def test_listar_e_remover_pelos_botoes():
    async def fluxo(c):
        await c.mensagem(ANA, "/adicionar fone 10/12/2099")
        await c.mensagem(ANA, "/adicionar mesa 11/12/2099")
        await c.mensagem(BETO, "/listar")
        assert c.botoes() == ["rm:1", "rm:2"]

        await c.botao(BETO, "rm:1")
        assert "tirar 📦 'fone'" in c.bot.edicoes[-1]["text"]
        await c.botao(BETO, "rmnao")
        assert len(c.repo.encomendas) == 2

        await c.botao(BETO, "rm:1")
        await c.botao(BETO, "rmsim:1")
        assert [e.item for e in c.repo.encomendas] == ["mesa"]
        assert "1. 📦 mesa" in c.bot.edicoes[-1]["text"]

    rodar(fluxo)


def test_conversa_expira_e_avisa(monkeypatch):
    monkeypatch.setattr(handlers.adicionar, "TEMPO_LIMITE_CONVERSA", 0.3)

    async def fluxo(c):
        await c.mensagem(ANA, "/adicionar fone")
        mensagem_teclado = len(c.bot.enviadas) + 999  # id que o BotFalso deu pra pergunta da data
        await asyncio.sleep(1.5)
        assert c.bot.enviadas[-1]["text"].startswith("⏰ demorou demais")
        assert {"message_id": mensagem_teclado, "reply_markup": None} in c.bot.edicoes

        await c.mensagem(ANA, "amanhã")  # conversa já era
        assert c.repo.encomendas == []

    rodar(fluxo)
