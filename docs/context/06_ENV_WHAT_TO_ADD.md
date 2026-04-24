# Что добавить в `.env` (сам файл агент не читает и не правит)

```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

DATABASE_URL=sqlite:///crm_web/crm.db

SESSION_SECRET=change_me_to_long_random_value
SESSION_EXPIRE_MINUTES=43200

SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your_email_login
SMTP_PASSWORD=your_email_password
SMTP_FROM=no-reply@your-domain.com

AUTH_CODE_TTL_SECONDS=600
```

Для production лучше заменить SQLite на PostgreSQL и использовать:
`DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname`
