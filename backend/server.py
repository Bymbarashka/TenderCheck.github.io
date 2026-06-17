from __future__ import annotations

import cgi
import hashlib
import http.server
import json
import os
import secrets
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "tendercheck.sqlite3"
PRIVATE_FILES = ROOT / "backend" / "private_uploads"
HOST = "127.0.0.1"
PORT = 8026

PRIVATE_FILES.mkdir(parents=True, exist_ok=True)

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            create table if not exists users (
                id integer primary key autoincrement,
                email text unique,
                password_hash text,
                full_name text,
                phone text,
                role text default 'client',
                is_active integer default 1,
                created_at text,
                updated_at text
            );
            create table if not exists companies (
                id integer primary key autoincrement,
                owner_user_id integer,
                name text,
                inn text,
                ogrn text,
                legal_address text,
                actual_address text,
                phone text,
                email text,
                region text,
                vat text,
                resources text,
                bitrix_company_id text,
                bitrix_contact_id text,
                created_at text,
                updated_at text
            );
            create table if not exists applications (
                id integer primary key autoincrement,
                company_id integer,
                title text,
                type text,
                client_role text,
                region text,
                budget text,
                deadline text,
                description text,
                goal text,
                status text,
                assigned_operator_id integer,
                tariff_id integer,
                bitrix_deal_id text,
                bitrix_task_id text,
                created_at text,
                updated_at text
            );
            create table if not exists application_files (
                id integer primary key autoincrement,
                application_id integer,
                file_name text,
                file_path text,
                file_size integer,
                file_type text,
                uploaded_by integer,
                uploaded_at text,
                is_deleted integer default 0
            );
            create table if not exists application_comments (
                id integer primary key autoincrement,
                application_id integer,
                user_id integer,
                text text,
                is_internal integer default 0,
                created_at text
            );
            create table if not exists application_matrix (
                id integer primary key autoincrement,
                application_id integer,
                block text,
                status text,
                comment text,
                recommendation text,
                visible_to_client integer default 1,
                updated_at text
            );
            create table if not exists application_roadmap (
                id integer primary key autoincrement,
                application_id integer,
                title text,
                description text,
                priority text,
                due_note text,
                status text,
                visible_to_client integer default 1,
                created_at text
            );
            create table if not exists suppliers_registry (
                id integer primary key autoincrement,
                company_name text,
                inn text,
                ogrn text,
                category text,
                region text,
                contact_person text,
                phone text,
                email text,
                website text,
                vat text,
                deferment text,
                min_budget text,
                response_time text,
                experience text,
                notes text,
                verified_status text,
                rating_internal real,
                created_at text,
                updated_at text
            );
            create table if not exists supplier_requests (
                id integer primary key autoincrement,
                company_name text,
                inn text,
                ogrn text,
                contact_person text,
                phone text,
                email text,
                region text,
                category text,
                vat text,
                deferment text,
                min_budget text,
                response_time text,
                experience text,
                website text,
                file_path text,
                status text,
                created_at text
            );
            create table if not exists application_recommendations (
                id integer primary key autoincrement,
                application_id integer,
                supplier_id integer,
                role text,
                comment text,
                visible_to_client integer default 0,
                created_at text
            );
            create table if not exists reports (
                id integer primary key autoincrement,
                application_id integer,
                pdf_path text,
                docx_path text,
                summary text,
                created_by integer,
                created_at text
            );
            create table if not exists tariffs (
                id integer primary key autoincrement,
                name text,
                slug text,
                description text,
                price text,
                price_period text,
                applications_limit integer,
                validity_days integer,
                features_json text,
                is_active integer default 1,
                created_at text
            );
            create table if not exists company_tariff_balance (
                id integer primary key autoincrement,
                company_id integer,
                tariff_id integer,
                valid_from text,
                valid_to text,
                included_applications integer,
                used_applications integer,
                extra_discount text,
                status text,
                created_at text
            );
            create table if not exists payments (
                id integer primary key autoincrement,
                company_id integer,
                application_id integer,
                tariff_id integer,
                amount text,
                status text,
                payment_method text,
                invoice_number text,
                invoice_path text,
                act_path text,
                paid_at text,
                created_at text
            );
            create table if not exists audit_log (
                id integer primary key autoincrement,
                user_id integer,
                action text,
                entity_type text,
                entity_id integer,
                ip_address text,
                user_agent text,
                created_at text
            );
            create table if not exists integration_logs (
                id integer primary key autoincrement,
                provider text,
                entity_type text,
                entity_id integer,
                direction text,
                payload text,
                status text,
                created_at text
            );
            """
        )


def now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
      _, salt, digest = stored.split("$", 2)
    except ValueError:
      return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return secrets.compare_digest(check, digest)


def save_uploads(form: cgi.FieldStorage, folder: str) -> list[str]:
    saved: list[str] = []
    target = PRIVATE_FILES / folder
    target.mkdir(parents=True, exist_ok=True)
    for key in form.keys():
        item = form[key]
        items = item if isinstance(item, list) else [item]
        for field in items:
            if not getattr(field, "filename", None):
                continue
            safe_name = Path(field.filename).name
            path = target / f"{secrets.token_hex(8)}_{safe_name}"
            with path.open("wb") as out:
                shutil.copyfileobj(field.file, out)
            saved.append(str(path.relative_to(ROOT)))
    return saved


def fields(form: cgi.FieldStorage) -> dict[str, str]:
    data: dict[str, str] = {}
    for key in form.keys():
        item = form[key]
        if isinstance(item, list):
            data[key] = ", ".join(str(x.value) for x in item if not getattr(x, "filename", None))
        elif not getattr(item, "filename", None):
            data[key] = str(item.value)
    return data


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urlparse(path).path
        if parsed == "/":
            parsed = "/index.html"
        safe = Path(parsed.lstrip("/")).as_posix()
        return str((ROOT / safe).resolve())

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            self.handle_api_get(urlparse(self.path).path)
            return
        path = Path(self.translate_path(self.path))
        if not str(path).startswith(str(ROOT)) or "private_uploads" in path.parts:
            self.send_error(403)
            return
        if path.exists() and path.is_file():
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(path.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(path.stat().st_size))
            self.end_headers()
            with path.open("rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return
        self.send_error(404)

    def do_PATCH(self) -> None:
        if not self.path.startswith("/api/"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"raw": raw}
        created = now()
        with db() as conn:
            conn.execute(
                "insert into audit_log (action,entity_type,ip_address,user_agent,created_at) values (?,?,?,?,?)",
                (f"patch:{urlparse(self.path).path}", "api", self.client_address[0], self.headers.get("User-Agent"), created),
            )
        self.json(200, {"ok": True, "path": urlparse(self.path).path, "received": data})

    def do_POST(self) -> None:
        if not self.path.startswith("/api/"):
            self.send_error(404)
            return
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        data = fields(form)
        endpoint = urlparse(self.path).path
        try:
            payload = self.handle_api(endpoint, data, form)
            self.json(200, payload)
        except Exception as exc:
            self.json(500, {"ok": False, "error": str(exc)})

    def handle_api_get(self, endpoint: str) -> None:
        with db() as conn:
            if endpoint == "/api/applications":
                rows = [dict(row) for row in conn.execute("select * from applications order by id desc").fetchall()]
                self.json(200, {"ok": True, "items": rows})
                return
            if endpoint.startswith("/api/applications/") and endpoint.endswith("/matrix"):
                self.json(200, {"ok": True, "items": []})
                return
            if endpoint.startswith("/api/applications/") and endpoint.endswith("/roadmap"):
                self.json(200, {"ok": True, "items": []})
                return
            if endpoint.startswith("/api/applications/"):
                app_id = endpoint.split("/")[3]
                row = conn.execute("select * from applications where id = ?", (app_id,)).fetchone()
                self.json(200, {"ok": bool(row), "item": dict(row) if row else None})
                return
            if endpoint == "/api/admin/supplier-requests":
                rows = [dict(row) for row in conn.execute("select * from supplier_requests order by id desc").fetchall()]
                self.json(200, {"ok": True, "items": rows})
                return
            if endpoint == "/api/admin/suppliers":
                rows = [dict(row) for row in conn.execute("select * from suppliers_registry order by id desc").fetchall()]
                self.json(200, {"ok": True, "items": rows})
                return
            if endpoint == "/api/reports":
                rows = [dict(row) for row in conn.execute("select * from reports order by id desc").fetchall()]
                self.json(200, {"ok": True, "items": rows})
                return
            if endpoint == "/api/payments":
                rows = [dict(row) for row in conn.execute("select * from payments order by id desc").fetchall()]
                self.json(200, {"ok": True, "items": rows})
                return
            if endpoint == "/api/admin/integration-logs":
                rows = [dict(row) for row in conn.execute("select * from integration_logs order by id desc").fetchall()]
                self.json(200, {"ok": True, "items": rows})
                return
        self.json(404, {"ok": False, "error": "unknown_endpoint"})

    def handle_api(self, endpoint: str, data: dict[str, str], form: cgi.FieldStorage) -> dict:
        created = now()
        with db() as conn:
            if endpoint == "/api/applications":
                company_id = self.ensure_company(conn, data)
                cur = conn.execute(
                    "insert into applications (company_id,title,type,client_role,region,budget,deadline,description,goal,status,created_at,updated_at) values (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (company_id, data.get("title") or data.get("company") or "Новая заявка", data.get("task_type"), data.get("client_role"), data.get("region"), data.get("budget"), data.get("deadline"), data.get("description"), data.get("goal"), "ожидает оплаты", created, created),
                )
                app_id = cur.lastrowid
                for saved in save_uploads(form, f"applications/{app_id}"):
                    conn.execute("insert into application_files (application_id,file_name,file_path,file_size,file_type,uploaded_at) values (?,?,?,?,?,?)", (app_id, Path(saved).name, saved, 0, Path(saved).suffix, created))
                self.audit(conn, "create_application", "applications", app_id)
                return {"ok": True, "id": app_id, "status": "ожидает оплаты"}

            if endpoint == "/api/supplier-requests":
                saved = save_uploads(form, "supplier_requests")
                cur = conn.execute(
                    "insert into supplier_requests (company_name,inn,ogrn,contact_person,phone,email,region,category,vat,deferment,min_budget,response_time,experience,website,file_path,status,created_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (data.get("company_name"), data.get("inn"), data.get("ogrn"), data.get("contact_person"), data.get("phone"), data.get("email"), data.get("regions"), data.get("categories"), data.get("vat"), data.get("deferment"), data.get("min_budget"), data.get("response_time"), data.get("experience"), data.get("website"), json.dumps(saved, ensure_ascii=False), "новая", created),
                )
                self.audit(conn, "create_supplier_request", "supplier_requests", cur.lastrowid)
                return {"ok": True, "id": cur.lastrowid, "status": "новая"}

            if endpoint == "/api/auth/register":
                cur = conn.execute("insert into users (email,password_hash,full_name,phone,role,created_at,updated_at) values (?,?,?,?,?,?,?)", (data.get("email"), password_hash(data.get("password", "")), data.get("full_name"), data.get("phone"), "client", created, created))
                user_id = cur.lastrowid
                self.ensure_company(conn, data, user_id)
                self.audit(conn, "register", "users", user_id)
                return {"ok": True, "id": user_id, "email_confirmation_required": True}

            if endpoint == "/api/auth/login":
                row = conn.execute("select * from users where email = ?", (data.get("email"),)).fetchone()
                if not row or not verify_password(data.get("password", ""), row["password_hash"]):
                    return {"ok": False, "error": "invalid_credentials"}
                self.audit(conn, "login", "users", row["id"])
                return {"ok": True, "role": row["role"]}

            if endpoint == "/api/auth/recover":
                conn.execute("insert into integration_logs (provider,entity_type,direction,payload,status,created_at) values (?,?,?,?,?,?)", ("email", "password_recovery", "out", json.dumps(data, ensure_ascii=False), "queued", created))
                return {"ok": True}

            if endpoint == "/api/comments":
                cur = conn.execute("insert into application_comments (application_id,text,is_internal,created_at) values (?,?,?,?)", (data.get("application_id"), data.get("text"), 0, created))
                self.audit(conn, "comment", "application_comments", cur.lastrowid)
                return {"ok": True}

            if endpoint == "/api/company":
                company_id = self.ensure_company(conn, data)
                return {"ok": True, "id": company_id}

            if endpoint == "/api/support":
                self.audit(conn, "support_request", "support", None)
                return {"ok": True}

            if endpoint == "/api/operator/roadmap":
                cur = conn.execute("insert into application_roadmap (application_id,title,description,priority,due_note,status,visible_to_client,created_at) values (?,?,?,?,?,?,?,?)", (data.get("application_id"), data.get("title"), data.get("description"), data.get("priority"), data.get("due_note"), "new", 1 if data.get("visible_to_client") else 0, created))
                self.audit(conn, "roadmap_create", "application_roadmap", cur.lastrowid)
                return {"ok": True}

            if endpoint == "/api/operator/recommendations":
                cur = conn.execute("insert into application_recommendations (application_id,role,comment,visible_to_client,created_at) values (?,?,?,?,?)", (data.get("application_id"), data.get("role"), data.get("comment"), 1 if data.get("visible_to_client") else 0, created))
                self.audit(conn, "recommendation_create", "application_recommendations", cur.lastrowid)
                return {"ok": True}

            if endpoint == "/api/operator/reports":
                saved = save_uploads(form, "reports")
                cur = conn.execute("insert into reports (application_id,pdf_path,docx_path,summary,created_at) values (?,?,?,?,?)", (data.get("application_id"), saved[0] if saved else None, None, data.get("summary"), created))
                self.audit(conn, "report_upload", "reports", cur.lastrowid)
                return {"ok": True}

            if endpoint == "/api/operator/payments":
                cur = conn.execute("insert into payments (company_id,application_id,amount,status,invoice_number,created_at) values (?,?,?,?,?,?)", (data.get("company_id"), data.get("application_id"), data.get("amount"), data.get("status") or "ожидает оплаты", data.get("invoice_number"), created))
                self.audit(conn, "payment_create", "payments", cur.lastrowid)
                return {"ok": True}

            if endpoint in {
                "/api/auth/logout",
                "/api/applications/:id/files",
                "/api/applications/:id/comments",
                "/api/admin/suppliers",
                "/api/admin/reports",
                "/api/admin/payments",
                "/api/admin/integrations/bitrix/sync",
            }:
                conn.execute("insert into integration_logs (provider,entity_type,direction,payload,status,created_at) values (?,?,?,?,?,?)", ("internal", endpoint, "in", json.dumps(data, ensure_ascii=False), "accepted", created))
                return {"ok": True, "status": "accepted"}

        return {"ok": False, "error": "unknown_endpoint"}

    def ensure_company(self, conn: sqlite3.Connection, data: dict[str, str], owner_user_id: int | None = None) -> int:
        inn = data.get("inn")
        existing = conn.execute("select id from companies where inn = ?", (inn,)).fetchone() if inn else None
        if existing:
            return int(existing["id"])
        cur = conn.execute(
            "insert into companies (owner_user_id,name,inn,ogrn,phone,email,region,vat,resources,created_at,updated_at) values (?,?,?,?,?,?,?,?,?,?,?)",
            (owner_user_id, data.get("company") or data.get("name") or data.get("company_name"), inn, data.get("ogrn"), data.get("phone"), data.get("email"), data.get("region"), data.get("vat"), data.get("resources"), now(), now()),
        )
        return int(cur.lastrowid)

    def audit(self, conn: sqlite3.Connection, action: str, entity_type: str, entity_id: int | None) -> None:
        conn.execute("insert into audit_log (action,entity_type,entity_id,ip_address,user_agent,created_at) values (?,?,?,?,?,?)", (action, entity_type, entity_id, self.client_address[0], self.headers.get("User-Agent"), now()))

    def json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    init_db()
    print(f"TenderCheck server: http://{HOST}:{PORT}/")
    http.server.ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
