# Coding Agents CLI

Агент создаёт изменения по GitHub issues и выполняет обзор созданных им pull request'ов через OpenRouter.

## Безопасная модель работы

- Issue обрабатывается только с меткой `agent:implement`.
- Агент не рассматривает pull request как issue.
- Для review подходят только PR с метками `agent-generated` и `agent:review-pending`.
- Автоматическое слияние выключено по умолчанию (`AUTO_MERGE=false`). Даже при его включении нужны успешные checks, не-draft PR и GitHub-разрешение на merge.
- Агент не изменяет `.github`, `.git`, `.env`, пути с traversal или шаблоны файлов.

Передайте GitHub token с минимальными правами для целевого репозитория. Не используйте токен администратора организации. Токен не добавляется в URL и не логируется.

## Быстрый запуск

```bash
cp .env.example .env
# Заполните GITHUB_TOKEN, GITHUB_REPOSITORY и OPENROUTER_API_KEY
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python main.py run --mode single --issue-number 123
```

Для daemon-режима добавьте к нужной задаче метку `agent:implement`, затем запустите `python main.py run`. Интервал задаётся `DAEMON_INTERVAL_SECONDS`.

## Проверки

Перед созданием PR агент клонирует только свою ветку и запускает Ruff, Black, MyPy и pytest. Если хотя бы одна включённая проверка не проходит, PR не создаётся. Все инструменты и их конфигурация находятся в `requirements.txt` и `pyproject.toml`.

Локальная проверка проекта:

```bash
ruff check main.py src tests
black --check main.py src tests
pytest tests -q
```

## Восстановление

При ошибке issue получает метку `blocked` и комментарий с причиной. После исправления причины снимите `blocked`, оставьте `agent:implement` и повторите запуск. PR, уже получивший review, отмечается `agent:reviewed`; для повторного review после новой ревизии вручную добавьте `agent:review-pending` и снимите `agent:reviewed`.
