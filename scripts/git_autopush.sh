#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Ошибка: текущая папка не является git-репозиторием."
  exit 1
fi

if [[ -z "$(git status --porcelain)" ]]; then
  echo "Нет изменений для коммита."
  exit 0
fi

MESSAGE="${1:-chore: stage checkpoint}"

git add -A
git commit -m "$MESSAGE"
git push

echo "Готово: изменения закоммичены и отправлены."
