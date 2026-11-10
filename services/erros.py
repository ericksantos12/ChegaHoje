class EntradaInvalida(ValueError):
    """Entrada do usuário inválida. `mensagem` é o texto pra responder no chat."""

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem
