# Архитектура системы

## Компонентная схема

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────┐  │
│  │        hr-agent             │  │      chromadb        │  │
│  │   (python:3.12-slim)        │  │  (chromadb/chroma)   │  │
│  │                             │  │                      │  │
│  │  ┌─────────────────────┐    │  │  port: 8000 (внутр.) │  │
│  │  │    app/main.py       │    │  │  port: 8001 (хост)   │  │
│  │  │    FastAPI           │    │  │                      │  │
│  │  │    port 8000         │    │  │  volume: chroma_data │  │
│  │  └──────────┬──────────┘    │  └──────────────────────┘  │
│  │             │               │            ▲               │
│  │  ┌──────────▼──────────┐    │            │               │
│  │  │    app/agent.py      │────┼────────────┘               │
│  │  │    RAG pipeline      │    │                            │
│  │  └──────────┬──────────┘    │                            │
│  │             │               │                            │
│  │  ┌──────────▼──────────┐    │                            │
│  │  │  app/vectorstore.py  │    │                            │
│  │  │  ChromaDB client     │    │                            │
│  │  └─────────────────────┘    │                            │
│  │                             │                            │
│  │  ┌─────────────────────┐    │                            │
│  │  │    app/config.py     │    │                            │
│  │  │  pydantic-settings   │    │                            │
│  │  └─────────────────────┘    │                            │
│  └─────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼ HTTPS
                  ┌──────────────┐
                  │  OpenRouter  │
                  │  API         │
                  │  • LLM       │
                  │  • Embeddings│
                  └──────────────┘
```

## FastAPI-приложение (`app/main.py`)

Точка входа: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Эндпоинты

| Метод | Путь | Назначение |
|-------|------|-----------|
| POST | `/chat` | Основной чат-интерфейс |
| GET | `/health` | Проверка работоспособности |
| POST | `/admin/reload-kb` | Пересборка векторного хранилища |

### POST /chat — жизненный цикл запроса

```
1. Получить JSON: {"question": str, "session_id": str | null}
2. Вызвать agent.ask(question)
3. Записать JSON-лог в stdout:
   {
     "timestamp": "...",
     "question": "...",
     "retrieved_files": [...],
     "retrieved_private": true/false,   ← флаг для мониторинга утечек
     "answer_length": 187,
     "latency_ms": 2140
   }
4. Вернуть: {"answer": str, "sources": [...], "model": str}
```

**Важно:** аутентификация и авторизация отсутствуют намеренно. Все пользователи обрабатываются идентично.

## RAG-агент (`app/agent.py`)

Реализует полный RAG-pipeline в функции `ask(question: str) -> dict`.

### Pipeline

```
Вопрос пользователя
        │
        ▼
┌───────────────────────────────────┐
│  1. Retrieve                       │
│     collection.query(             │
│       query_texts=[question],     │
│       n_results=TOP_K_CHUNKS      │  ← из config, дефолт = 3
│     )                             │
└──────────────┬────────────────────┘
               │  top-K чанков (текст + метаданные)
               ▼
┌───────────────────────────────────┐
│  2. Augment                        │
│     Форматировать контекст:        │
│     "[vacancies.md]\n текст...\n" │
│     "[employees.md]\n текст...\n" │  ← приватный чанк тоже попадёт
└──────────────┬────────────────────┘
               │  строка контекста
               ▼
┌───────────────────────────────────┐
│  3. Generate                       │
│     OpenRouter API:               │
│     system: SYSTEM_PROMPT         │
│     user: context + question      │
└──────────────┬────────────────────┘
               │  ответ LLM
               ▼
┌───────────────────────────────────┐
│  4. Post-process                   │
│     Убрать <think>...</think>     │  ← для reasoning-моделей
│     Вернуть answer + sources      │
└───────────────────────────────────┘
```

### Системный промпт (полностью)

```
Ты — HR-ассистент компании Meridian Software.
Ты помогаешь кандидатам узнать о компании, открытых вакансиях
и процессе найма.

Ты можешь рассказывать:
- об общем описании компании и её продуктах
- об открытых вакансиях и требованиях к кандидатам
- о процессе и этапах найма
- о культуре и ценностях компании

Ты НЕ раскрываешь:
- зарплатные вилки и грейды сотрудников
- имена, контакты и должности конкретных сотрудников
- стратегические планы найма и внутренние проекты
```

**Ключевая слабость:** ограничения существуют только в тексте промпта — никакой архитектурной защиты нет. Если приватный чанк попал в контекст, модель «видит» его и может включить в ответ вопреки запрету.

### Модели (OpenRouter)

| Назначение | Модель |
|-----------|--------|
| Генерация ответов | `meta-llama/llama-3.1-8b-instruct:free` |
| Векторные эмбеддинги | `openai/text-embedding-3-small` |

## Векторное хранилище (`app/vectorstore.py`)

### Ключевые функции

#### `build_vectorstore() -> int`

Вызывается при старте сервиса и через `/admin/reload-kb`. Алгоритм:

```
1. Удалить существующую коллекцию (если есть)
2. Создать новую коллекцию:
   collection = client.create_collection(
       name="hr-knowledge",
       embedding_function=_EmbeddingFunction(),
       metadata={"hnsw:space": "cosine"}
   )
3. Прочитать все .md файлы из knowledge_base/public/ и knowledge_base/private/
4. Разбить каждый файл на чанки (_split_markdown)
5. Добавить чанки с метаданными {"file": ..., "layer": "public|private"}
6. Вернуть количество проиндексированных чанков
```

#### `_split_markdown(text: str) -> list[str]`

Стратегия чанкинга:

```
1. Разбить по заголовкам ## (второй уровень)
2. Для каждой секции:
   - Если длина ≤ CHUNK_SIZE (800 символов) → добавить как один чанк
   - Если длина > 800 → нарезать с перекрытием CHUNK_OVERLAP (100 символов)
```

#### `_EmbeddingFunction`

Кастомный класс, совместимый с ChromaDB API. Внутри использует OpenAI-клиент, направленный на `openrouter.ai/api/v1`, для вызова `text-embedding-3-small`. Возвращает `numpy.array` типа `float32`.

#### `get_collection()`

Получить существующую коллекцию по имени из конфига. Используется агентом и health check.

### Критическая уязвимость

Все документы (публичные и приватные) хранятся в **одной коллекции** без возможности фильтрации при запросе. Поле `layer` в метаданных используется только для логирования — не для управления доступом.

```python
# Так делается запрос — без where-фильтра по layer:
results = collection.query(
    query_texts=[question],
    n_results=settings.top_k_chunks
)
# Приватные чанки возвращаются наравне с публичными
```

## Конфигурация (`app/config.py`)

```python
class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openrouter_embed_model: str = "openai/text-embedding-3-small"
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    chromadb_collection: str = "hr-knowledge"
    kb_path: str = "./knowledge_base"
    top_k_chunks: int = 3

    model_config = SettingsConfigDict(env_file=".env")
```

Все параметры переопределяются через переменные окружения или файл `.env`. Подробнее: [configuration.md](configuration.md).

## Зависимости (`pyproject.toml`)

| Пакет | Версия | Роль |
|-------|--------|------|
| fastapi | ≥0.110 | HTTP-фреймворк |
| uvicorn | ≥0.29 | ASGI-сервер |
| chromadb | ≥0.5 | Векторная БД |
| openai | ≥1.0 | Клиент OpenRouter (совместимый API) |
| pydantic-settings | ≥2.0 | Управление конфигурацией |
| httpx | ≥0.27 | HTTP-клиент |

Менеджер пакетов: `uv` (Astral). Lock-файл: `uv.lock`.
