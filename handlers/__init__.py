from handlers.adicionar import criar_handlers_adicionar
from handlers.comandos import remover, start, testar_alerta
from handlers.erros import error_handler
from handlers.jobs import checar_entregas, limpar_encomendas_antigas
from handlers.lista import criar_handlers_lista

__all__ = [
    "checar_entregas",
    "criar_handlers_adicionar",
    "criar_handlers_lista",
    "error_handler",
    "limpar_encomendas_antigas",
    "remover",
    "start",
    "testar_alerta",
]
