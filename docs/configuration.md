# Конфигурация

Все параметры агента управляются через переменные окружения или файл `.env` в корне проекта. Класс `Settings` в `app/config.py` использует Pydantic Settings для автоматической загрузки.

## Файл `.env`

Создайте файл `.env` из примера:

```bash
cp .env.example .env
```

Обязательно заполнить только одну переменную — `OPENROUTER_API_KEY`.

## Переменные окружения

### OpenRouter

| Переменная | Тип | По умолчанию | Описание |
|-----------|-----|-------------|---------|
| `OPENROUTER_API_KEY` | string | `""` | **Обязательно.** API-ключ OpenRouter (`sk-or-v1-...`) |
| `OPENROUTER_BASE_URL` | string | `https://openrouter.ai/api/v1` | Базовый URL API. Совместим с OpenAI SDK |
| `OPENROUTER_MODEL` | string | `meta-llama/llama-3.1-8b-instruct:free` | Модель для генерации ответов |
| `OPENROUTER_EMBED_MODEL` | string | `openai/text-embedding-3-small` | Модель для векторных эмбеддингов |

### ChromaDB

| Переменная | Тип | По умолчанию | Описание |
|-----------|-----|-------------|---------|
| `CHROMADB_HOST` | string | `chromadb` | Хост ChromaDB. В Docker Compose = имя сервиса `chromadb`; локально = `localhost` |
| `CHROMADB_PORT` | int | `8000` | Порт ChromaDB. При локальном запуске через Docker — `8001` (маппинг 8001→8000) |
| `CHROMADB_COLLECTION` | string | `hr-knowledge` | Имя коллекции в ChromaDB |

### База знаний

| Переменная | Тип | По умолчанию | Описание |
|-----------|-----|-------------|---------|
| `KB_PATH` | string | `./knowledge_base` | Путь к директории с документами |
| `TOP_K_CHUNKS` | int | `3` | Количество чанков, возвращаемых при семантическом поиске |

## Пример `.env.example`

```dotenv
OPENROUTER_API_KEY=sk-or-v1-ваш_ключ_здесь
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_EMBED_MODEL=openai/text-embedding-3-small

CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
CHROMADB_COLLECTION=hr-knowledge

KB_PATH=./knowledge_base
TOP_K_CHUNKS=3
```

## Конфигурация для локальной разработки

При запуске агента вне Docker Compose необходимо изменить хост ChromaDB:

```dotenv
CHROMADB_HOST=localhost
CHROMADB_PORT=8001   # порт маппинга Docker контейнера
```

## Рекомендации по настройке

### Смена LLM-модели

Параметр `OPENROUTER_MODEL` принимает любой идентификатор модели с [openrouter.ai/models](https://openrouter.ai/models).

Для более точного следования инструкциям (меньше утечек) попробуйте более мощные модели:

```dotenv
# Более строгое следование системному промпту
OPENROUTER_MODEL=anthropic/claude-3-5-haiku

# Максимальная мощность (платная)
OPENROUTER_MODEL=anthropic/claude-opus-4

# Другие бесплатные варианты
OPENROUTER_MODEL=google/gemini-flash-1.5-8b
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free
```

**Важно для целей red teaming:** Более мощные модели лучше следуют ограничениям. Бесплатная `llama-3.1-8b-instruct` выбрана намеренно — она чаще «ломается» при атаках.

### Настройка TOP_K_CHUNKS

| Значение | Эффект |
|---------|-------|
| `1` | Минимальный контекст — меньше шансов что приватный чанк попадёт в ответ |
| `3` | По умолчанию — балансирует качество ответа и риск утечки |
| `5` | Больший контекст — выше шанс утечки (интересно для red teaming) |
| `10` | Максимальный риск — почти всегда приватный чанк в контексте |

Для демонстрации максимальной уязвимости:

```dotenv
TOP_K_CHUNKS=5
```

### Смена embedding-модели

Эмбеддинги влияют на качество семантического поиска. Модель `openai/text-embedding-3-small` хорошо работает с русским языком. Альтернативы через OpenRouter:

```dotenv
OPENROUTER_EMBED_MODEL=openai/text-embedding-3-large   # дороже, точнее
```

**Внимание:** При смене embedding-модели нужно пересобрать коллекцию:

```bash
curl -X POST http://localhost:8000/admin/reload-kb
```

Иначе новые запросы будут использовать другое векторное пространство, несовместимое с хранимыми эмбеддингами.

## Класс Settings (исходный код)

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

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

settings = Settings()
```

Синглтон `settings` импортируется во все модули приложения. Переменные окружения имеют приоритет над значениями из `.env` файла.
