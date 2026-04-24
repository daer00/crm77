# Что добавить в `.env` (сам файл агент не читает и не правит)

```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

DATABASE_URL=postgresql+psycopg://crm_user:crm_password@localhost:5432/crm77

SESSION_SECRET=change_me_to_long_random_value
SESSION_EXPIRE_MINUTES=43200

SMTP_HOST=smtp.yandex.ru
SMTP_PORT=587
SMTP_USER=your_yandex_login
SMTP_PASSWORD=your_yandex_app_password
SMTP_FROM=your_yandex_mail@yandex.ru

AUTH_CODE_TTL_SECONDS=600
```

Для локальной отладки без PostgreSQL можно временно использовать:
`DATABASE_URL=sqlite:///crm_web/crm.db`
