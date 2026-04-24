# CRM Web (контакты + сделки)

Веб-система CRM с импортом существующей базы контактов из CSV в SQLite.

## Что реализовано

- просмотр контактов с группировкой по компаниям;
- добавление новых контактов;
- создание сделок с привязкой к компаниям;
- адаптивный интерфейс для телефона/планшета/десктопа.

## Запуск

```bash
cd /Users/danilermolaev/Documents/77E_DB/crm_web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Откройте: `http://127.0.0.1:8000`

При первом запуске данные автоматически импортируются из:
`/Users/danilermolaev/Documents/77E_DB/CONTACT_20250916_5299b658_68c9c36edbc7d.csv`
