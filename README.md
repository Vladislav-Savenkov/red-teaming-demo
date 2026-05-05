# HR Agent — Red Teaming Demo

Учебный стенд для демонстрации атак на LLM-агентов. Намеренно уязвимый HR-чатбот вымышленной компании «Meridian Software», построенный на FastAPI + ChromaDB + OpenRouter.

> **Только для образовательных целей.** Уязвимости заложены намеренно, чтобы показать, почему нельзя полагаться на системный промпт как на единственный механизм защиты.

---

## Что это

Агент отвечает на вопросы кандидатов о компании, вакансиях и процессе найма. База знаний разделена на два слоя:

- **public/** — описание компании, вакансии, процесс найма (агент может раскрывать)
- **private/** — зарплатные вилки, справочник сотрудников, стратегия найма 2025 (агент не должен раскрывать)

Задача красной команды — заставить агента раскрыть приватный слой.

## Три вектора атак

| Вектор | Механизм | Успешность в тестах |
|--------|---------|-------------------|
| **RAG Data Poisoning** | Приватные документы хранятся в одной коллекции с публичными; семантически близкие запросы вытягивают их в top-K | 59% |
| **Role Injection** | Агент без аутентификации; пользователь представляется HR-менеджером или CTO | 51% |
| **Prompt Extraction** | Системный промпт извлекается через jailbreak-форматы (Hyde/Jekyll, Cipher Code, таблицы) | 40% |

## Стек

- **API:** FastAPI + Uvicorn
- **Векторная БД:** ChromaDB (cosine similarity)
- **LLM / Эмбеддинги:** OpenRouter (`llama-3.1-8b-instruct:free` / `text-embedding-3-small`)
- **Red Teaming:** Promptfoo (генератор атак: Gemini 3 Flash)
- **Деплой:** Docker Compose
- **Пакеты:** uv

## Быстрый старт

### 1. Клонировать и настроить окружение

```bash
git clone <repo-url>
cd RT-demo
cp .env.example .env
```

Открыть `.env` и вставить API-ключ OpenRouter:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-...
```

### 2. Запустить

```bash
docker compose up --build
```

Агент будет доступен на `http://localhost:8000`.

### 3. Проверить

```bash
# Health check
curl http://localhost:8000/health

# Задать вопрос
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие вакансии открыты?"}' \
  | python3 -m json.tool
```

## Структура проекта

```
RT-demo/
├── app/
│   ├── main.py          # FastAPI: /chat, /health, /admin/reload-kb
│   ├── agent.py         # RAG-pipeline: retrieve → augment → generate
│   ├── vectorstore.py   # ChromaDB: чанкинг, эмбеддинги, коллекция
│   └── config.py        # Pydantic Settings
├── knowledge_base/
│   ├── public/          # company.md, vacancies.md, process.md
│   └── private/         # employees.md, grades.md, strategy.md
├── promptfoo/
│   ├── promptfooconfig.yaml   # конфиг Promptfoo
│   ├── redteam.yaml           # 210 сгенерированных тест-кейсов
│   └── plugins/
│       ├── rag-poisoning.yaml
│       └── role-injection.yaml
├── docs/                # документация (см. ниже)
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Запуск Red Teaming

```bash
# Установить Promptfoo
npm install -g promptfoo

# Убедиться, что агент запущен, затем:
cd promptfoo
promptfoo eval -c promptfooconfig.yaml

# Просмотр результатов в браузере
promptfoo view
```

**Результаты последнего прогона:** 210 тестов, 50% атак успешны. Подробнее: [docs/red-teaming-report.md](docs/red-teaming-report.md).
