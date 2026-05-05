# Быстрый старт

## Предварительные требования

### Вариант A — Docker (рекомендуется)

- Docker Engine ≥ 20.10
- Docker Compose v2 (`docker compose` без дефиса)
- Аккаунт на [openrouter.ai](https://openrouter.ai) и API-ключ

### Вариант B — Локальная разработка

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — менеджер пакетов (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Запущенный экземпляр ChromaDB (или через Docker отдельно)
- Аккаунт на [openrouter.ai](https://openrouter.ai) и API-ключ

## Настройка переменных окружения

Скопируйте пример файла `.env.example` в `.env` и заполните свой ключ:

```bash
cp .env.example .env
```

Откройте `.env` и укажите API-ключ:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-ваш_ключ_здесь
```

Остальные параметры можно оставить по умолчанию. Подробное описание всех переменных: [configuration.md](configuration.md).

## Запуск через Docker Compose

```bash
# 1. Убедитесь, что .env заполнен
# 2. Запустите все сервисы
docker compose up --build

# Для фонового запуска:
docker compose up --build -d
```

После запуска:
- HR-агент доступен на `http://localhost:8000`
- ChromaDB доступен на `http://localhost:8001`

При первом запуске агент автоматически проиндексирует все документы из `knowledge_base/`.

### Остановка

```bash
docker compose down          # остановить контейнеры
docker compose down -v       # + удалить данные ChromaDB
```

## Запуск локально (для разработки)

### 1. Установить зависимости

```bash
uv sync
```

### 2. Запустить ChromaDB

Проще всего — через Docker отдельным командой:

```bash
docker run -d \
  --name chromadb \
  -p 8001:8000 \
  -v chroma_data:/chroma/chroma \
  chromadb/chroma
```

### 3. Настроить .env для локального запуска

Измените хост ChromaDB (по умолчанию он называется `chromadb` — имя сервиса в Docker Compose):

```dotenv
CHROMADB_HOST=localhost
CHROMADB_PORT=8001
```

### 4. Запустить агента

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Флаг `--reload` включает автоперезагрузку при изменении кода.

## Проверка работоспособности

### Health check

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status": "ok", "chromadb": "connected"}
```

### Первый вопрос агенту

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Расскажи о компании Meridian Software"}' \
  | python3 -m json.tool
```

Ожидаемый ответ (сокращённо):

```json
{
  "answer": "Meridian Software — это B2B SaaS-компания...",
  "sources": [
    {
      "file": "company.md",
      "layer": "public",
      "chunk": "## О компании\nMeridian Software...",
      "score": 0.94
    }
  ],
  "model": "meta-llama/llama-3.1-8b-instruct:free"
}
```

### Вопрос о вакансиях

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие вакансии сейчас открыты?"}' \
  | python3 -m json.tool
```

### Пересборка базы знаний

После изменения файлов в `knowledge_base/` — пересоберите индекс без перезапуска сервиса:

```bash
curl -s -X POST http://localhost:8000/admin/reload-kb | python3 -m json.tool
```

Ожидаемый ответ:

```json
{"status": "reloaded", "chunks_indexed": 24}
```

## Типичные проблемы

### ChromaDB недоступна

```json
{"status": "ok", "chromadb": "disconnected"}
```

Проверьте, запущен ли контейнер `chromadb`:

```bash
docker compose ps
# или
docker ps | grep chroma
```

### Ошибка аутентификации OpenRouter

```
openai.AuthenticationError: 401 Unauthorized
```

Проверьте значение `OPENROUTER_API_KEY` в файле `.env`. Убедитесь, что ключ скопирован полностью (начинается с `sk-or-v1-`).

### Агент отвечает на английском

Бесплатные модели OpenRouter могут переключаться на английский при нагрузке на серверы. Попробуйте явно добавить в вопрос «Отвечай на русском» или смените модель на более мощную (см. [configuration.md](configuration.md)).
