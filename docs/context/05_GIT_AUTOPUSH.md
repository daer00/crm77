# Автоматическая заливка в GitHub

## 1) Базовая настройка (один раз)
```bash
git init
git branch -M main
git remote add origin https://github.com/daer00/crm77.git
```

Если remote уже есть:
```bash
git remote set-url origin https://github.com/daer00/crm77.git
```

## 2) Включить скрипт автопуша
```bash
chmod +x scripts/git_autopush.sh
```

Дальше после каждого этапа:
```bash
./scripts/git_autopush.sh "feat: этап N - описание"
```

## 3) Опционально: автоматический push после каждого commit
Создать хук `.git/hooks/post-commit`:
```bash
#!/usr/bin/env bash
git push
```

И выдать права:
```bash
chmod +x .git/hooks/post-commit
```

## Важно
- Автопуш работает только если локально настроена авторизация в GitHub (ssh key или gh auth login).
- `.env` не коммитим и не читаем.
