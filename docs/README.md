# Документация: HR-агент Red Teaming Demo

Документация к учебному стенду для демонстрации атак на LLM-агентов.  
Стенд воспроизводит намеренно уязвимый HR-чатбот компании «Meridian Software».

## Содержание

### Начало работы

| Документ | Описание |
|---------|---------|
| [overview.md](overview.md) | Цель проекта, три вектора атак, карта компонентов |
| [getting-started.md](getting-started.md) | Запуск через Docker Compose и локально, curl-примеры |
| [configuration.md](configuration.md) | Переменные окружения, рекомендации по моделям и TOP_K_CHUNKS |

### Устройство системы

| Документ | Описание |
|---------|---------|
| [architecture.md](architecture.md) | Компонентная схема, RAG-pipeline, FastAPI-эндпоинты |
| [knowledge-base.md](knowledge-base.md) | Структура документов (public/private), механизм чанкинга |
| [api-reference.md](api-reference.md) | REST API: схемы запросов, ответов, JSON-логи |

### Безопасность и тестирование

| Документ | Описание |
|---------|---------|
| [vulnerabilities.md](vulnerabilities.md) | Разбор трёх уязвимостей с примерами атак и исправлений |
| [red-teaming.md](red-teaming.md) | Как запускать Promptfoo, плагины, интерпретация результатов |
| [red-teaming-report.md](red-teaming-report.md) | Отчёт по результатам прогона: 210 тестов, статистика, паттерны |

## Быстрая навигация

**Хочу запустить стенд →** [getting-started.md](getting-started.md)  
**Хочу понять архитектуру →** [architecture.md](architecture.md)  
**Хочу провести атаку →** [red-teaming.md](red-teaming.md)  
**Хочу посмотреть результаты →** [red-teaming-report.md](red-teaming-report.md)  
**Хочу понять уязвимости →** [vulnerabilities.md](vulnerabilities.md)
