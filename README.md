# TenderCheck site

Сервисный B2B-портал TenderCheck для технической проверки КП, ТЗ, смет, закупок и сделок до входа.

## Что внутри

- Статический сайт: публичные страницы, кабинет клиента, админка оператора.
- `assets/demo-report.pdf` - демонстрационный отчёт.
- `backend/server.py` - минимальный Python/SQLite backend-скелет без внешних зависимостей.

## Локальный запуск

```powershell
python backend/server.py
```

Открыть: http://127.0.0.1:8026/

## Структура

- `index.html` - главная
- `clients.html` - клиентам
- `suppliers.html` - поставщикам и партнёрам
- `report.html` - пример отчёта
- `knowledge.html` - база знаний
- `legal.html` - документы и регламенты
- `about.html` - о сервисе
- `contacts.html` - контакты
- `login.html` - вход / регистрация
- `dashboard.html` - кабинет клиента
- `admin.html` - админка оператора

## Важно перед production

Нужны HTTPS, нормальная авторизация, Argon2id/bcrypt, CSRF, rate limit, secure cookies, ролевой доступ, приватное файловое хранилище, бэкапы и юридическая проверка документов.
