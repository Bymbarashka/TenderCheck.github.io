# TenderCheck backend skeleton

Минимальный backend без внешних зависимостей: Python stdlib + SQLite.

Запуск из папки `outputs/tendercheck-site`:

```powershell
python backend/server.py
```

После запуска сайт доступен на `http://127.0.0.1:8026/`, API принимает формы:

- `POST /api/applications`
- `POST /api/supplier-requests`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/recover`
- `POST /api/comments`
- `POST /api/company`
- `POST /api/support`
- `POST /api/operator/roadmap`
- `POST /api/operator/recommendations`
- `POST /api/operator/reports`
- `POST /api/operator/payments`
- `GET /api/applications`
- `GET /api/applications/:id`
- `PATCH /api/applications/:id`
- `GET /api/admin/supplier-requests`
- `GET /api/admin/suppliers`
- `GET /api/reports`
- `GET /api/payments`
- `POST /api/admin/integrations/bitrix/sync`
- `GET /api/admin/integration-logs`

Это не production-безопасность. Для запуска продукта нужны HTTPS, Argon2id/bcrypt, CSRF, rate limit, secure/HttpOnly/SameSite cookies, полноценные роли и приватное файловое хранилище.
