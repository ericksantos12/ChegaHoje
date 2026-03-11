<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="https://i.imgur.com/6yutiN1.png" alt="Bot logo"></a>
</p>

<h3 align="center">ChegaHoje Bot</h3>

<div align="center">

  [![Status](https://img.shields.io/badge/status-active-success.svg)]()
  [![Platform](https://img.shields.io/badge/platform-telegram-blue.svg)](https://telegram.org/)
  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)

</div>

---

<p align="center"> 🤖 A Telegram bot to track package deliveries and notify you before they arrive.
    <br> 
</p>

## 📝 Table of Contents
+ [About](#about)
+ [Features](#features)
+ [Tech Stack](#tech_stack)
+ [Getting Started](#getting_started)
+ [Usage](#usage)
+ [Project Structure](#project_structure)
+ [Deployment](#deployment)
+ [Authors](#authors)

## 🧐 About <a name = "about"></a>
**ChegaHoje** is a Telegram bot designed to help users keep track of their incoming packages. It allows users to register expected delivery dates and receive notifications.

The main goal is to prevent surprises by reminding the user at 08:00 AM if a package is scheduled to arrive the next day.

## ✨ Features <a name = "features"></a>
- **Add Package**: Register a new package with a description and expected arrival date.
- **List Packages**: View a list of all currently tracked packages.
- **Remove Package**: Delete a package from the tracking list.
- **Daily Reminders**: Automatically checks for packages arriving the next day and sends a notification at 08:00 AM.

## 🛠️ Tech Stack <a name = "tech_stack"></a>
- **Language**: [Python 3.12+](https://www.python.org/)
- **Framework**: [python-telegram-bot](https://python-telegram-bot.org/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Containerization**: [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)

## 🏁 Getting Started <a name = "getting_started"></a>
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (Recommended)
- [Python 3.11+](https://www.python.org/downloads/) (For local non-docker setup)
- A Telegram Bot Token (Get one from [@BotFather](https://t.me/BotFather))

### Environment Variables
Create a `.env` file in the root directory with the following variables:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://postgres:password@db:5432/chegahoje
POSTGRES_DB=chegahoje
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
TIME_ZONE=America/Sao_Paulo
```

### Running with Docker (Recommended)
1. Clone the repository.
2. Create the `.env` file as described above.
3. Build and verify the containers:
   ```bash
   docker-compose up -d --build
   ```
   This command starts the bot, the PostgreSQL database, and an Adminer instance (for DB management) accessible at [http://localhost:5460](http://localhost:5460).

### Running Locally (Without Docker)
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure you have a PostgreSQL database running and update `DATABASE_URL` in `.env` to point to it (e.g., `postgresql://user:pass@localhost:5432/dbname`).
4. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
5. Run the bot:
   ```bash
   python main.py
   ```

### Running Unit Tests
The project uses Python's built-in `unittest` framework for the usecase test suite. To run the tests:

```bash
python -m unittest discover -s tests
```

The unit tests use mocks for Telegram and repository interactions, so they do not require a running PostgreSQL instance.

## 🎈 Usage <a name = "usage"></a>

Once the bot is running, you can interact with it on Telegram using the following commands:

- `/start`: Initializes the bot and shows the help message.
- `/adicionar [item] - [dd/mm/aaaa]`: Adds a new package to track.
  - Example: `/adicionar Liquidificador - 27/02/2026`
- `/listar`: Lists all saved packages with their IDs.
- `/remover [number]`: Removes a package using its list number (obtained from `/listar`).
  - Example: `/remover 2`

## 📂 Project Structure <a name = "project_structure"></a>

```
ChegaHoje/
├── db/                 # Database models and connection logic
├── migrations/         # Alembic migration scripts
├── repositories/       # Data access layer (Repository Pattern)
├── utils/              # Utility functions (logger, etc.)
├── main.py             # Application entry point and bot logic
├── docker-compose.yml  # Docker services configuration
├── Dockerfile          # Docker image definition
└── requirements.txt    # Python dependencies
```

## 🚀 Deployment <a name = "deployment"></a>
To deploy on a server, ensure Docker and Docker Compose are installed, clone the repo, set up your `.env` file with production credentials, and run:

```bash
docker-compose up -d --build
```

You can use `watchtower` or similar tools to automate updates if needed.

## ✍️ Authors <a name = "authors"></a>
- [@ericksantos12](https://github.com/ericksantos12) - Initial work

## 🎉 Acknowledgements <a name = "acknowledgement"></a>
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) community
