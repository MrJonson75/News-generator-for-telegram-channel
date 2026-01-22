# Generator Post for Telegram

Автоматическая система сбора новостей, генерации постов для Telegram, тематической классификации и управления контентом через API.

Проект построен на **FastAPI**, **Celery**, **SQLAlchemy**, **Redis**, **SQLite** и **OpenAI**, что позволяет масштабировать проект, управлять источниками и анализировать данные.

---

## 📂 Структура проекта

```ascii
Generator Post for Telegram
├── 📁 .venv/                    # Виртуальное окружение
├── 📁 app/                      # Основное приложение
│   ├── 📁 ai/                  # AI-модули
│   │   ├── __init__.py
│   │   └── openai_client.py   # Клиент для работы с OpenAI API
│   ├── 📁 api/                 # FastAPI роутеры
│   │   ├── __init__.py
│   │   ├── keywords.py        # API для управления ключевыми словами
│   │   ├── schemas.py         # Pydantic схемы для валидации
│   │   └── sources.py         # API для управления источниками
│   ├── 📁 news_parser/        # Модули парсинга новостей
│   │   ├── __init__.py
│   │   ├── load_site.py       # Утилиты загрузки веб-страниц
│   │   ├── news_collector.py  # Оркестратор парсинга
│   │   ├── parser_habr.py     # Парсер Habr
│   │   ├── parser_rbk.py      # Парсер РБК
│   │   └── parser_telegram.py # Парсер Telegram-каналов
│   ├── 📁 tasks/              # Celery задачи
│   │   ├── __init__.py
│   │   ├── news_tasks.py      # Задачи парсинга новостей
│   │   ├── post_tasks.py      # Задачи генерации постов
│   │   └── telegram_tasks.py  # Задачи публикации в Telegram
│   ├── 📁 utils/              # Вспомогательные утилиты
│   │   └── rate_limit.py      # Ограничитель запросов
│   ├── __init__.py
│   ├── celery_app.py          # Конфигурация Celery
│   ├── config.py              # Конфигурация приложения
│   ├── database.py            # Подключение к БД
│   ├── logger.py              # Настройка логирования
│   ├── main.py               # Точка входа FastAPI
│   └── models.py             # SQLAlchemy модели
├── 📁 alembic/                # Миграции базы данных
│   ├── 📁 versions/          # Файлы миграций
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── 📁 logs/                   # Логи приложения
│   └── project.log
├── .env                      # Переменные окружения
├── .gitignore
├── alembic.ini              # Конфигурация Alembic
├── celery_worker.py         # Скрипт запуска Celery worker
├── poetry.lock
├── pyproject.toml
├── README.md
├── requirements.txt
└── run_celery.bat           # Скрипт запуска Celery (Windows)
```


---

## ⚙️ Установка и зависимости

Проект использует **Python 3.13+**.  
Установить зависимости можно через **Poetry** или `pip`:

```bash
# Установка Poetry
pip install poetry

# Установка зависимостей
poetry install

# или через pip
pip install -r requirements.txt
````

---

## 🔧 Настройка `.env`

```dotenv
DEBUG=True

# Telegram
TELEGRAM_API_ID=my_telegram_id
TELEGRAM_API_HASH=my_hash_ip
TELEGRAM_BOT_TOKEN=my_bot_token
TELEGRAM_CHANNEL_ID=@telegram_channel_for_publication

# Фильтр новостей
NEWS_KEYWORDS=python,fastapi,django,flask,asyncio,ai,ml,...

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=api_token_openai
OPENAI_PROXY=user:password@host:port
OPENAI_PROMPT=Сделай краткое, интересное описание новости для Telegram-канала, добавь emoji, call to action
```

---

## 🟢 Redis

Для работы Celery требуется Redis.

Можно использовать **локальную установку**:

```bash
# Ubuntu
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

Или запустить через **Docker**:

```bash
docker run -d --name redis -p 6379:6379 redis:7
```

### Docker Compose

Пример `docker-compose.yml` для Redis:

```yaml
version: "3.9"
services:
  redis:
    image: redis:7
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

Запуск:

```bash
docker-compose up -d
```

---

## 📝 Логирование

Система использует модульный логгер, который пишет логи в файл и выводит в консоль.

Файл логирования: `logs/project.log`
Пример конфигурации в `app/logger.py`:

* **Ротация логов по дню**
* Хранение последних 7 файлов
* Устойчивость к ошибкам на Windows (`WinError 32`)

```python
from app.logger import logger

logger.info("Приложение запущено")
logger.error("Ошибка при выполнении задачи")
```

---

## 🚀 Запуск

### FastAPI

```bash
uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`

### Celery

```bash
run_celery.bat
```

---

## 📊 Как это работает

Проект представляет собой асинхронную систему автоматического сбора новостей, генерации постов для Telegram, тематической классификации и управления контентом через API.

Архитектура построена вокруг **Celery**, **FastAPI**, **SQLAlchemy**, **Redis** и **OpenAI**.

---

## 🔄 Взаимодействие компонентов

```ascii
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Источники     │    │     Redis       │    │   FastAPI       │
│   (Websites,    │◄──►│   (Брокер,      │◄──►│   (API,         │
│   Telegram)     │    │   Кэш)          │    │   Документация) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Celery        │    │   SQLite/       │    │   OpenAI API    │
│   (Worker,      │    │   PostgreSQL    │    │   (Генерация,   │
│   Beat)         │    │   (Данные)      │    │   Классификация)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Telegram API  │    │   Логирование   │
│   (Отправка     │    │   (Файлы,       │
│   постов)       │    │   Консоль)      │
└─────────────────┘    └─────────────────┘
```

---

### 1. Парсинг новостей

* Задача `parse_and_save_news` запускается по расписанию (каждые 30 минут)
* Источники берутся из базы `Source`
* Каждая новость валидируется, фильтруется по ключевым словам, проверяется на дубликаты и сохраняется в `NewsItem`

```
Celery Task Worker + Scheduler -> news_collector -> Parser Modules -> Validate & Filter -> Deduplicate -> Database NewsItem
```

---

### 2. Генерация постов для Telegram

* Задача `generate_posts`:

  * получает новости из БД
  * проверяет статус поста
  * генерирует текст через OpenAI
  * создаёт или обновляет запись в `Post`
* Запускается каждые 10 минут через Celery Beat

---

### 3. Публикация постов в Telegram

* Задача `publish_posts_to_telegram`

  * берёт посты со статусом `published`
  * формирует текст с тегами и ссылкой
  * отправляет через Telethon
  * обновляет статус на `sent` и дату публикации

Пример:

```
🎬💰 Основной текст поста…

`#тег1 #тег2 #тег3`

🔗 [Источник](https://example.com)
```

---

### 4. Очистка неудачных постов

* Задача `cleanup_old_failed_posts`

  * удаляет старые посты со статусом `failed`
  * предотвращает накопление мусора

---

### 5. Генерация тегов

* Задача `generate_post_keywords`

  * семантическая разметка постов
  * создаёт новые Keyword и связывает с Post через `post_keywords`
  * масштабируется независимо от генерации постов

---

### 6. API и управление системой

**Посты:**

* `GET /api/posts` — список постов с фильтрацией
* `GET /api/posts/{id}` — пост по ID
* `PATCH /api/posts/{id}/status` — смена статуса
* `POST /generate` — ручной запуск генерации
* `POST /posts/{id}/publish` — публикация
* `DELETE /api/posts/{id}` — удаление

**Источники:**

* `GET /api/sources` — все источники
* `PATCH /api/sources/{id}/enabled` — включение/выключение источника

**Теги:**

* `GET /api/keywords` — все теги
* `POST /api/keywords` — создать тег
* `PATCH /api/keywords/{id}` — обновить тег
* `DELETE /api/keywords/{id}` — удалить тег
* `GET /api/keywords/stats` — статистика по тегам

---

### 7. Health-check

**Проверка состояния системы:**

* `GET /health` — база данных, OpenAI, Redis, Celery
* `GET /health/celery` — активные воркеры и задачи Celery

---

### 8. Итоговая схема работы

```text
Source (enabled)
   ↓
NewsItem (DB)
   ↓
generate_posts (Celery)
   ↓
Post (DB)
   ↓
publish_posts_to_telegram (Celery)
   ↓
generate_post_keywords (Celery)
   ↓
Keyword (DB)
```

---

### 🔄 Схема связей между моделями


```ascii
                    ┌─────────────┐        ┌───────────────┐        ┌─────────────┐
                    │   Source    │        │   NewsItem    │        │    Post     │
                    │─────────────│        │───────────────│        │─────────────│
                    │ id (PK)     │◄──┐    │ id (PK)       │◄───────┤ news_id (FK)│
                    │ type        │   └────┤ source_id (FK)│        │ status      │
                    │ name        │        │ title         │        │ text        │
                    │ url         │        │ url (UNIQ)    │        │ created_at  │
                    │ enabled     │        │ summary       │        └─────────────┘
                    │ created_at  │        │ published_at  │               │
                    └─────────────┘        │ created_at    │               │
                                           └───────────────┘               │
                                                   │                       │
                                                   │                       │
                                           ┌───────┴───────┐               │
                                           │               │               │
                                     ┌─────────────┐   ┌───────────────────┐
                                     │  Keyword    │   │ post_keywords     │
                                     │─────────────│   │───────────────────│
                                     │ id (PK)     │   │ post_id (FK,PK)   │
                                     │ word (UNIQ) │◄──┤ keyword_id (FK,PK)│
                                     │ created_at  │   └───────────────────┘
                                     └─────────────┘
```

---

## 👤 Автор

**MrJonson** – [flashh@list.ru](mailto:flashh@list.ru)

---

## ⚠️ Примечания

* Python 3.13+
* SQLite используется для локального запуска, для продакшена рекомендуется PostgreSQL
* Redis можно использовать локально или через Docker
* `.env` содержит чувствительные данные — храните безопасно
* Логи пишутся в файл и консоль, ротация по дням, последние 7 файлов

---
