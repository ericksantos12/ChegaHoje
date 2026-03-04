# ChegaHoje

Um bot do Telegram para **registrar encomendas** e **te notificar quando elas chegarem** (ou estiverem para chegar), evitando esquecer de avisar em casa.

---

## O que ele faz

- Você **registra encomendas** informando o nome/descrição e a **data prevista**
- O bot **te notifica automaticamente** quando houver encomenda **chegando** (com base na data cadastrada)

---

## Requisitos

- Python **3.11+** (o Dockerfile usa `python:3.11-slim`)
- Token de bot do Telegram (variável de ambiente `TELEGRAM_TOKEN`)
- Dependências do `requirements.txt`

---

## Configuração (variáveis de ambiente)

### `TELEGRAM_TOKEN` (obrigatória)
Você precisa criar um bot com o **@BotFather** e pegar o token.

#### Usando `.env` (padrão / recomendado)
Crie um arquivo chamado **`.env`** na raiz do projeto:

```env
TELEGRAM_TOKEN=coloque_seu_token_aqui
```

#### Sobre o `stack.env` (Portainer)
O arquivo **`stack.env` existe apenas para uso no Portainer** (Stacks), como um jeito prático de fornecer variáveis de ambiente ao subir a stack por lá.

Se você **não usa Portainer**, pode ignorar o `stack.env` e usar um `.env` normal (como acima).

---

## Rodando localmente (sem Docker)

1) Crie e ative um venv (opcional, mas recomendado):
```bash
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

2) Instale as dependências:
```bash
pip install -r requirements.txt
```

3) Rode (usando o `.env`):
```bash
python main.py
```

---

## Rodando com Docker Compose

### Opção A) Usando `.env` (padrão do Docker Compose)
1) Crie um arquivo **`.env`** na raiz do projeto:
```env
TELEGRAM_TOKEN=seu_token_aqui
```

2) Suba o container:
```bash
docker compose up -d --build
```

### Opção B) Usando `--env-file` (ex.: Portainer / stacks / arquivo separado)
Se você quiser manter um arquivo de variáveis com outro nome (ex.: `stack.env`), você pode iniciar assim:

```bash
docker compose --env-file stack.env up -d --build
```

> Reforçando: no seu projeto, **`stack.env` é voltado para Portainer**, mas esse comando acima também funciona fora dele.

---

## Como usar no Telegram

Abra o chat com o bot e use:

### Ajuda
- `/start`

### Adicionar encomenda
Formato:
- `/adicionar [item] - [dd/mm/aaaa]`

Exemplo:
- `/adicionar liquidificador - 27/02/2026`

### Listar encomendas
- `/listar`

### Remover encomenda
- `/remover [número]`

Exemplo:
- `/remover 1`

---

## Observações / limitações atuais

- O bot **não consulta rastreio real** (Correios etc.). Ele trabalha com a **data que você informar**.
- O armazenamento é local (SQLite). Se você trocar de máquina/container sem volume, perde os dados.

---

## Autor

- GitHub: [@ericksantos12](https://github.com/ericksantos12)