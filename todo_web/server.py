from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import secrets
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "todos.db"

STATUS_VALUES = {"pending", "doing", "done"}
PRIORITY_VALUES = {"low", "medium", "high"}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(r["name"] == column_name for r in rows)


def _normalize_due_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError("due_date must use YYYY-MM-DD") from exc


def _normalize_priority(value: str) -> str:
    text = str(value or "medium").strip().lower()
    if text not in PRIORITY_VALUES:
        raise ValueError("invalid priority")
    return text


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return digest.hex()


def _create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
        (token, user_id),
    )
    return token


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                due_date TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        if not _column_exists(conn, "todos", "user_id"):
            conn.execute("ALTER TABLE todos ADD COLUMN user_id INTEGER")
        if not _column_exists(conn, "todos", "due_date"):
            conn.execute("ALTER TABLE todos ADD COLUMN due_date TEXT NOT NULL DEFAULT ''")
        if not _column_exists(conn, "todos", "priority"):
            conn.execute("ALTER TABLE todos ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'")

        legacy_user = conn.execute("SELECT id FROM users WHERE username = ?", ("legacy",)).fetchone()
        if legacy_user is None:
            salt = secrets.token_bytes(16)
            conn.execute(
                "INSERT INTO users (username, password_salt, password_hash) VALUES (?, ?, ?)",
                ("legacy", salt.hex(), _hash_password("legacy-password", salt)),
            )
            legacy_user = conn.execute("SELECT id FROM users WHERE username = ?", ("legacy",)).fetchone()
        conn.execute("UPDATE todos SET user_id = ? WHERE user_id IS NULL", (legacy_user["id"],))

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_todos_user_status
            ON todos(user_id, status, priority, due_date)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_user
            ON sessions(user_id)
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS todos_updated_at
            AFTER UPDATE ON todos
            FOR EACH ROW
            BEGIN
                UPDATE todos SET updated_at = datetime('now') WHERE id = OLD.id;
            END;
            """
        )


def as_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "due_date": row["due_date"],
        "priority": row["priority"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class TodoHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: int, content: bytes, content_type: str, attachment_name: str = "") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        if attachment_name:
            self.send_header("Content-Disposition", f"attachment; filename={attachment_name}")
        self.end_headers()
        self.wfile.write(content)

    def _send_text(self, status: int, content: str, content_type: str = "text/plain; charset=utf-8") -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _auth_user(self) -> dict | None:
        auth = self.headers.get("Authorization", "").strip()
        token = ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        if not token:
            token = self.headers.get("X-Auth-Token", "").strip()
        if not token:
            return None

        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, s.token
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
            if row is None:
                return None
            conn.execute("UPDATE sessions SET last_seen_at = datetime('now') WHERE token = ?", (token,))
        return {"id": row["id"], "username": row["username"], "token": row["token"]}

    def _require_user(self) -> dict | None:
        user = self._auth_user()
        if user is None:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
            return None
        return user

    def _parse_todo_filters(self, parsed_qs: dict[str, list[str]]) -> tuple[str, list]:
        where = []
        params: list = []

        q = (parsed_qs.get("q", [""])[0] or "").strip()
        status = (parsed_qs.get("status", [""])[0] or "").strip().lower()
        priority = (parsed_qs.get("priority", [""])[0] or "").strip().lower()
        due_before = (parsed_qs.get("due_before", [""])[0] or "").strip()
        due_after = (parsed_qs.get("due_after", [""])[0] or "").strip()

        if q:
            where.append("(title LIKE ? OR description LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])

        if status and status in STATUS_VALUES:
            where.append("status = ?")
            params.append(status)

        if priority and priority in PRIORITY_VALUES:
            where.append("priority = ?")
            params.append(priority)

        if due_before:
            where.append("due_date != '' AND due_date <= ?")
            params.append(_normalize_due_date(due_before))

        if due_after:
            where.append("due_date != '' AND due_date >= ?")
            params.append(_normalize_due_date(due_after))

        where_sql = ""
        if where:
            where_sql = " AND " + " AND ".join(where)

        return where_sql, params

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self._send_text(HTTPStatus.NOT_FOUND, "Not Found")
            return

        suffix_map = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }
        content_type = suffix_map.get(file_path.suffix.lower(), "application/octet-stream")
        data = file_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/auth/me":
            user = self._require_user()
            if user is None:
                return
            self._send_json(HTTPStatus.OK, {"id": user["id"], "username": user["username"]})
            return

        if path == "/api/todos":
            user = self._require_user()
            if user is None:
                return
            try:
                where_sql, filter_params = self._parse_todo_filters(qs)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            with get_conn() as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, title, description, status, due_date, priority, created_at, updated_at
                    FROM todos
                    WHERE user_id = ? {where_sql}
                    ORDER BY
                      CASE status
                        WHEN 'doing' THEN 1
                        WHEN 'pending' THEN 2
                        WHEN 'done' THEN 3
                        ELSE 4
                      END,
                      CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                      END,
                      CASE WHEN due_date = '' THEN 1 ELSE 0 END,
                      due_date ASC,
                      id DESC
                    """,
                    [user["id"], *filter_params],
                ).fetchall()
            self._send_json(HTTPStatus.OK, [as_dict(r) for r in rows])
            return

        if path == "/api/export":
            user = self._require_user()
            if user is None:
                return

            fmt = (qs.get("format", ["json"])[0] or "json").strip().lower()
            if fmt not in {"json", "csv"}:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "format must be json or csv"})
                return

            try:
                where_sql, filter_params = self._parse_todo_filters(qs)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            with get_conn() as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, title, description, status, due_date, priority, created_at, updated_at
                    FROM todos
                    WHERE user_id = ? {where_sql}
                    ORDER BY id DESC
                    """,
                    [user["id"], *filter_params],
                ).fetchall()

            data = [as_dict(r) for r in rows]
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            if fmt == "json":
                payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                self._send_bytes(
                    HTTPStatus.OK,
                    payload,
                    "application/json; charset=utf-8",
                    attachment_name=f"todos_{user['username']}_{stamp}.json",
                )
                return

            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=["id", "title", "description", "status", "due_date", "priority", "created_at", "updated_at"],
            )
            writer.writeheader()
            for row in data:
                writer.writerow(row)
            self._send_bytes(
                HTTPStatus.OK,
                buf.getvalue().encode("utf-8-sig"),
                "text/csv; charset=utf-8",
                attachment_name=f"todos_{user['username']}_{stamp}.csv",
            )
            return

        if path == "/" or path == "/index.html":
            self._serve_file(ROOT / "index.html")
            return

        target = ROOT / path.lstrip("/")
        if target.resolve().is_relative_to(ROOT.resolve()):
            self._serve_file(target)
            return

        self._send_text(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/auth/register":
            data = self._read_json()
            username = str(data.get("username", "")).strip().lower()
            password = str(data.get("password", ""))
            if not username or len(username) < 3:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "username must be at least 3 chars"})
                return
            if not password or len(password) < 6:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "password must be at least 6 chars"})
                return

            salt = secrets.token_bytes(16)
            pwd_hash = _hash_password(password, salt)

            try:
                with get_conn() as conn:
                    cur = conn.execute(
                        "INSERT INTO users (username, password_salt, password_hash) VALUES (?, ?, ?)",
                        (username, salt.hex(), pwd_hash),
                    )
                    token = _create_session(conn, cur.lastrowid)
            except sqlite3.IntegrityError:
                self._send_json(HTTPStatus.CONFLICT, {"error": "username already exists"})
                return

            self._send_json(HTTPStatus.CREATED, {"token": token, "username": username})
            return

        if parsed.path == "/api/auth/login":
            data = self._read_json()
            username = str(data.get("username", "")).strip().lower()
            password = str(data.get("password", ""))
            if not username or not password:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "username and password are required"})
                return

            with get_conn() as conn:
                row = conn.execute(
                    "SELECT id, username, password_salt, password_hash FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                if row is None:
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid credentials"})
                    return

                salted = bytes.fromhex(row["password_salt"])
                hashed = _hash_password(password, salted)
                if hashed != row["password_hash"]:
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid credentials"})
                    return

                token = _create_session(conn, row["id"])

            self._send_json(HTTPStatus.OK, {"token": token, "username": row["username"]})
            return

        if parsed.path == "/api/auth/logout":
            user = self._require_user()
            if user is None:
                return
            with get_conn() as conn:
                conn.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
            self._send_json(HTTPStatus.OK, {"ok": True})
            return

        if parsed.path != "/api/todos":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
            return

        user = self._require_user()
        if user is None:
            return

        data = self._read_json()
        title = str(data.get("title", "")).strip()
        description = str(data.get("description", "")).strip()
        status = str(data.get("status", "pending")).strip().lower()
        due_date_raw = str(data.get("due_date", "")).strip()
        priority_raw = str(data.get("priority", "medium")).strip()

        if not title:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "title is required"})
            return

        if status not in STATUS_VALUES:
            status = "pending"

        try:
            due_date = _normalize_due_date(due_date_raw)
            priority = _normalize_priority(priority_raw)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO todos (user_id, title, description, status, due_date, priority) VALUES (?, ?, ?, ?, ?, ?)",
                (user["id"], title, description, status, due_date, priority),
            )
            row = conn.execute(
                "SELECT id, title, description, status, due_date, priority, created_at, updated_at FROM todos WHERE id = ? AND user_id = ?",
                (cur.lastrowid, user["id"]),
            ).fetchone()

        self._send_json(HTTPStatus.CREATED, as_dict(row))

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) != 3 or path_parts[0] != "api" or path_parts[1] != "todos":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
            return

        try:
            todo_id = int(path_parts[2])
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid id"})
            return

        user = self._require_user()
        if user is None:
            return

        data = self._read_json()
        fields = []
        params = []

        if "title" in data:
            title = str(data.get("title", "")).strip()
            if not title:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "title cannot be empty"})
                return
            fields.append("title = ?")
            params.append(title)

        if "description" in data:
            fields.append("description = ?")
            params.append(str(data.get("description", "")).strip())

        if "status" in data:
            status = str(data.get("status", "")).strip().lower()
            if status not in STATUS_VALUES:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid status"})
                return
            fields.append("status = ?")
            params.append(status)

        if "due_date" in data:
            try:
                due_date = _normalize_due_date(data.get("due_date", ""))
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            fields.append("due_date = ?")
            params.append(due_date)

        if "priority" in data:
            try:
                priority = _normalize_priority(data.get("priority", "medium"))
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            fields.append("priority = ?")
            params.append(priority)

        if not fields:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "No updatable fields provided"})
            return

        params.append(todo_id)
        params.append(user["id"])

        with get_conn() as conn:
            conn.execute(f"UPDATE todos SET {', '.join(fields)} WHERE id = ? AND user_id = ?", params)
            row = conn.execute(
                "SELECT id, title, description, status, due_date, priority, created_at, updated_at FROM todos WHERE id = ? AND user_id = ?",
                (todo_id, user["id"]),
            ).fetchone()

        if row is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Todo not found"})
            return

        self._send_json(HTTPStatus.OK, as_dict(row))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) != 3 or path_parts[0] != "api" or path_parts[1] != "todos":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
            return

        try:
            todo_id = int(path_parts[2])
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid id"})
            return

        user = self._require_user()
        if user is None:
            return

        with get_conn() as conn:
            cur = conn.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user["id"]))

        if cur.rowcount == 0:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Todo not found"})
            return

        self._send_json(HTTPStatus.OK, {"ok": True, "deleted_id": todo_id})

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Auth-Token")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def run(host: str = "127.0.0.1", port: int = 8015) -> None:
    init_db()
    server = ThreadingHTTPServer((host, port), TodoHandler)
    print(f"Todo app running at http://{host}:{port}")
    print(f"DB file: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
