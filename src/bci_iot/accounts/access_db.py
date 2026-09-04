"""SQLite database for access logs and admin people directory."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal


INBOX_KEEP_DAYS = 10


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _parse_dt(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(slots=True)
class AccessEvent:
    id: int
    username: str
    event: str
    ip: str
    user_agent: str
    created_at: str


@dataclass(slots=True)
class PersonRow:
    username: str
    first_name: str
    last_name: str
    access_count: int
    first_access: str
    last_access: str
    status: str  # active | deleted
    email: str = ""
    phone_e164: str = ""
    phone_label: str = ""


SortKey = Literal["name_asc", "name_desc", "accesses_asc", "accesses_desc", "last_asc", "last_desc"]


class AccessDatabase:
    """Persist login/register/logout events in a local SQLite file."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    event TEXT NOT NULL,
                    ip TEXT NOT NULL DEFAULT '',
                    user_agent TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_access_logs_created
                ON access_logs (created_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_access_logs_user
                ON access_logs (username, created_at)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_anagrafica (
                    username TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    first_name TEXT NOT NULL DEFAULT '',
                    last_name TEXT NOT NULL DEFAULT '',
                    gender TEXT NOT NULL DEFAULT '',
                    phone_label TEXT NOT NULL DEFAULT '',
                    headset_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    photo_path TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    phone_e164 TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            # Migrations for older DBs
            cols = {
                str(r["name"])
                for r in conn.execute("PRAGMA table_info(user_anagrafica)").fetchall()
            }
            if "status" not in cols:
                conn.execute(
                    "ALTER TABLE user_anagrafica ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                )
            if "photo_path" not in cols:
                conn.execute(
                    "ALTER TABLE user_anagrafica ADD COLUMN photo_path TEXT NOT NULL DEFAULT ''"
                )
            if "email" not in cols:
                conn.execute(
                    "ALTER TABLE user_anagrafica ADD COLUMN email TEXT NOT NULL DEFAULT ''"
                )
            if "phone_e164" not in cols:
                conn.execute(
                    "ALTER TABLE user_anagrafica ADD COLUMN phone_e164 TEXT NOT NULL DEFAULT ''"
                )
            self._init_users_table(conn)
            self._init_support_tables(conn)
            conn.commit()

    def _init_users_table(self, conn: sqlite3.Connection) -> None:
        """Full account table (replaces JSON ProfileStore files)."""

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                headset_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL,
                action_map_json TEXT NOT NULL DEFAULT '{}',
                notes TEXT NOT NULL DEFAULT '',
                is_admin INTEGER NOT NULL DEFAULT 0,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                gender TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone_label TEXT NOT NULL DEFAULT '',
                phone_country TEXT NOT NULL DEFAULT '',
                phone_dial TEXT NOT NULL DEFAULT '',
                phone_national TEXT NOT NULL DEFAULT '',
                phone_e164 TEXT NOT NULL DEFAULT '',
                email_verified INTEGER NOT NULL DEFAULT 0,
                phone_verified INTEGER NOT NULL DEFAULT 0,
                otp_hash TEXT NOT NULL DEFAULT '',
                otp_channel TEXT NOT NULL DEFAULT '',
                otp_purpose TEXT NOT NULL DEFAULT '',
                otp_expires_at TEXT NOT NULL DEFAULT '',
                otp_issued_at TEXT NOT NULL DEFAULT '',
                otp_attempts INTEGER NOT NULL DEFAULT 0,
                email_confirm_hash TEXT NOT NULL DEFAULT '',
                email_confirm_expires_at TEXT NOT NULL DEFAULT '',
                anagrafica_complete INTEGER NOT NULL DEFAULT 0,
                calibration_complete INTEGER NOT NULL DEFAULT 0,
                pairing_code TEXT NOT NULL DEFAULT '',
                phone_paired INTEGER NOT NULL DEFAULT 0,
                phone_last_seen_at TEXT NOT NULL DEFAULT '',
                photo_filename TEXT NOT NULL DEFAULT '',
                last_seen_at TEXT NOT NULL DEFAULT '',
                deleted_at TEXT NOT NULL DEFAULT '',
                spotify_access_token TEXT NOT NULL DEFAULT '',
                spotify_refresh_token TEXT NOT NULL DEFAULT '',
                spotify_token_expires_at TEXT NOT NULL DEFAULT '',
                spotify_user_id TEXT NOT NULL DEFAULT '',
                spotify_display_name TEXT NOT NULL DEFAULT '',
                usage_stats_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_phone ON users (phone_e164)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_deleted ON users (deleted_at)"
        )
        # Forward-compatible column migrations for older installs of this table.
        user_cols = {
            str(r["name"]) for r in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        extra_cols = {
            "otp_issued_at": "TEXT NOT NULL DEFAULT ''",
            "otp_attempts": "INTEGER NOT NULL DEFAULT 0",
            "email_confirm_hash": "TEXT NOT NULL DEFAULT ''",
            "email_confirm_expires_at": "TEXT NOT NULL DEFAULT ''",
        }
        for name, decl in extra_cols.items():
            if name not in user_cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {decl}")

    def _init_support_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL DEFAULT '',
                guest_name TEXT NOT NULL DEFAULT '',
                guest_email TEXT NOT NULL DEFAULT '',
                guest_phone TEXT NOT NULL DEFAULT '',
                channel TEXT NOT NULL DEFAULT 'chat',
                subject TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'unread',
                viewed_at TEXT NOT NULL DEFAULT '',
                replied_at TEXT NOT NULL DEFAULT '',
                inbox_hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_support_threads_status
            ON support_threads (status, inbox_hidden, updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_support_threads_user
            ON support_threads (username, updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_support_messages_thread
            ON support_messages (thread_id, id)
            """
        )

    def upsert_user(self, data: dict[str, Any]) -> None:
        """Insert or replace a full user profile row."""

        username = str(data.get("username") or "").strip()
        if not username:
            raise ValueError("username required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username, password_hash, headset_id, user_id, action_map_json, notes,
                    is_admin, first_name, last_name, gender, email, phone_label,
                    phone_country, phone_dial, phone_national, phone_e164,
                    email_verified, phone_verified, otp_hash, otp_channel, otp_purpose,
                    otp_expires_at, otp_issued_at, otp_attempts, email_confirm_hash,
                    email_confirm_expires_at, anagrafica_complete, calibration_complete,
                    pairing_code, phone_paired, phone_last_seen_at, photo_filename,
                    last_seen_at, deleted_at, spotify_access_token, spotify_refresh_token,
                    spotify_token_expires_at, spotify_user_id, spotify_display_name,
                    usage_stats_json, updated_at
                ) VALUES (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
                ON CONFLICT(username) DO UPDATE SET
                    password_hash=excluded.password_hash,
                    headset_id=excluded.headset_id,
                    user_id=excluded.user_id,
                    action_map_json=excluded.action_map_json,
                    notes=excluded.notes,
                    is_admin=excluded.is_admin,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    gender=excluded.gender,
                    email=excluded.email,
                    phone_label=excluded.phone_label,
                    phone_country=excluded.phone_country,
                    phone_dial=excluded.phone_dial,
                    phone_national=excluded.phone_national,
                    phone_e164=excluded.phone_e164,
                    email_verified=excluded.email_verified,
                    phone_verified=excluded.phone_verified,
                    otp_hash=excluded.otp_hash,
                    otp_channel=excluded.otp_channel,
                    otp_purpose=excluded.otp_purpose,
                    otp_expires_at=excluded.otp_expires_at,
                    otp_issued_at=excluded.otp_issued_at,
                    otp_attempts=excluded.otp_attempts,
                    email_confirm_hash=excluded.email_confirm_hash,
                    email_confirm_expires_at=excluded.email_confirm_expires_at,
                    anagrafica_complete=excluded.anagrafica_complete,
                    calibration_complete=excluded.calibration_complete,
                    pairing_code=excluded.pairing_code,
                    phone_paired=excluded.phone_paired,
                    phone_last_seen_at=excluded.phone_last_seen_at,
                    photo_filename=excluded.photo_filename,
                    last_seen_at=excluded.last_seen_at,
                    deleted_at=excluded.deleted_at,
                    spotify_access_token=excluded.spotify_access_token,
                    spotify_refresh_token=excluded.spotify_refresh_token,
                    spotify_token_expires_at=excluded.spotify_token_expires_at,
                    spotify_user_id=excluded.spotify_user_id,
                    spotify_display_name=excluded.spotify_display_name,
                    usage_stats_json=excluded.usage_stats_json,
                    updated_at=excluded.updated_at
                """,
                (
                    username,
                    str(data.get("password_hash") or ""),
                    str(data.get("headset_id") or ""),
                    str(data.get("user_id") or ""),
                    str(data.get("action_map_json") or "{}"),
                    str(data.get("notes") or ""),
                    1 if data.get("is_admin") else 0,
                    str(data.get("first_name") or ""),
                    str(data.get("last_name") or ""),
                    str(data.get("gender") or ""),
                    str(data.get("email") or ""),
                    str(data.get("phone_label") or ""),
                    str(data.get("phone_country") or ""),
                    str(data.get("phone_dial") or ""),
                    str(data.get("phone_national") or ""),
                    str(data.get("phone_e164") or ""),
                    1 if data.get("email_verified") else 0,
                    1 if data.get("phone_verified") else 0,
                    str(data.get("otp_hash") or ""),
                    str(data.get("otp_channel") or ""),
                    str(data.get("otp_purpose") or ""),
                    str(data.get("otp_expires_at") or ""),
                    str(data.get("otp_issued_at") or ""),
                    int(data.get("otp_attempts") or 0),
                    str(data.get("email_confirm_hash") or ""),
                    str(data.get("email_confirm_expires_at") or ""),
                    1 if data.get("anagrafica_complete") else 0,
                    1 if data.get("calibration_complete") else 0,
                    str(data.get("pairing_code") or ""),
                    1 if data.get("phone_paired") else 0,
                    str(data.get("phone_last_seen_at") or ""),
                    str(data.get("photo_filename") or ""),
                    str(data.get("last_seen_at") or ""),
                    str(data.get("deleted_at") or ""),
                    str(data.get("spotify_access_token") or ""),
                    str(data.get("spotify_refresh_token") or ""),
                    str(data.get("spotify_token_expires_at") or ""),
                    str(data.get("spotify_user_id") or ""),
                    str(data.get("spotify_display_name") or ""),
                    str(data.get("usage_stats_json") or "{}"),
                    _utc_now(),
                ),
            )
            conn.commit()

    def get_user(self, username: str, *, include_deleted: bool = False) -> dict[str, Any] | None:
        key = username.strip()
        with self._connect() as conn:
            if include_deleted:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
                    (key,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ? COLLATE NOCASE AND deleted_at = ''",
                    (key,),
                ).fetchone()
        return dict(row) if row else None

    def list_user_rows(self, *, include_deleted: bool = False) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if include_deleted:
                rows = conn.execute(
                    "SELECT * FROM users ORDER BY username COLLATE NOCASE"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM users WHERE deleted_at = '' ORDER BY username COLLATE NOCASE"
                ).fetchall()
        return [dict(row) for row in rows]

    def username_taken(self, username: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 AS ok FROM users WHERE username = ? COLLATE NOCASE LIMIT 1",
                (username.strip(),),
            ).fetchone()
        return row is not None

    def soft_delete_user(self, username: str) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET deleted_at = CASE WHEN deleted_at = '' THEN ? ELSE deleted_at END,
                    updated_at = ?
                WHERE username = ?
                """,
                (now, now, username.strip()),
            )
            conn.commit()
        self.mark_deleted(username)

    def count_users(self, *, deleted: bool = False, exclude_admin: bool = False) -> int:
        clauses: list[str] = []
        if deleted:
            clauses.append("deleted_at != ''")
        else:
            clauses.append("deleted_at = ''")
        if exclude_admin:
            clauses.append("is_admin = 0")
        where = " AND ".join(clauses)
        with self._connect() as conn:
            n = conn.execute(f"SELECT COUNT(*) AS n FROM users WHERE {where}").fetchone()["n"]
        return int(n)

    def upsert_anagrafica(
        self,
        *,
        username: str,
        user_id: str,
        first_name: str,
        last_name: str,
        gender: str,
        phone_label: str = "",
        headset_id: str = "",
        status: str = "active",
        photo_path: str = "",
        email: str = "",
        phone_e164: str = "",
    ) -> None:
        """Store personal data without passwords (SQLite mirror)."""

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_anagrafica (
                    username, user_id, first_name, last_name, gender,
                    phone_label, headset_id, status, photo_path, email,
                    phone_e164, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    user_id=excluded.user_id,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    gender=excluded.gender,
                    phone_label=excluded.phone_label,
                    headset_id=excluded.headset_id,
                    status=excluded.status,
                    photo_path=excluded.photo_path,
                    email=excluded.email,
                    phone_e164=excluded.phone_e164,
                    updated_at=excluded.updated_at
                """,
                (
                    username.strip(),
                    user_id,
                    first_name.strip()[:64],
                    last_name.strip()[:64],
                    gender.strip()[:32],
                    phone_label.strip()[:64],
                    headset_id.strip()[:128],
                    status if status in {"active", "deleted"} else "active",
                    photo_path.strip()[:256],
                    email.strip()[:254],
                    phone_e164.strip()[:32],
                    _utc_now(),
                ),
            )
            conn.commit()

    def mark_deleted(self, username: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_anagrafica
                SET status='deleted', updated_at=?
                WHERE username=?
                """,
                (_utc_now(), username.strip()),
            )
            conn.execute(
                """
                INSERT INTO access_logs (username, event, ip, user_agent, created_at)
                VALUES (?, 'account_deleted', '', '', ?)
                """,
                (username.strip(), _utc_now()),
            )
            conn.commit()

    def log(
        self,
        *,
        username: str,
        event: str,
        ip: str = "",
        user_agent: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO access_logs (username, event, ip, user_agent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (username or "").strip() or "(sconosciuto)",
                    event,
                    (ip or "")[:128],
                    (user_agent or "")[:256],
                    _utc_now(),
                ),
            )
            conn.commit()

    def list_recent(self, limit: int = 200) -> list[AccessEvent]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, username, event, ip, user_agent, created_at
                FROM access_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_event(row) for row in rows]

    def list_user_events(self, username: str, limit: int = 500) -> list[AccessEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, username, event, ip, user_agent, created_at
                FROM access_logs
                WHERE username = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (username.strip(), max(1, min(limit, 2000))),
            ).fetchall()
        return [self._row_event(row) for row in rows]

    def get_anagrafica(self, username: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_anagrafica WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def list_people(
        self,
        *,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        status: str = "active",
        sort: SortKey = "name_asc",
    ) -> list[PersonRow]:
        """One row per person (anagrafica), with access counts. Unique usernames."""

        rows = self._list_people_compat()
        needle = q.strip().lower()
        people: list[PersonRow] = []
        for row in rows:
            username = str(row["username"] or "")
            if not username:
                continue
            first = str(row["first_name"] or "")
            last = str(row["last_name"] or "")
            email = str(row["email"] or "")
            phone_e164 = str(row["phone_e164"] or "")
            phone_label = str(row["phone_label"] or "")
            phone_national = str(row["phone_national"] or "")
            st = str(row["status"] or "active")
            first_acc = str(row["first_access"] or "")
            last_acc = str(row["last_access"] or "")
            count = int(row["access_count"] or 0)

            if status != "all" and st != status:
                continue
            hay = f"{first} {last} {username} {email} {phone_label} {phone_e164} {phone_national}".lower()
            hay_digits = _digits(f"{phone_e164}{phone_national}{phone_label}")
            needle_digits = _digits(needle)
            if needle and needle not in hay and (not needle_digits or needle_digits not in hay_digits):
                continue
            if date_from and last_acc and last_acc[:10] < date_from[:10]:
                continue
            if date_to and last_acc and last_acc[:10] > date_to[:10]:
                continue
            if (date_from or date_to) and not last_acc:
                continue

            people.append(
                PersonRow(
                    username=username,
                    first_name=first,
                    last_name=last,
                    access_count=count,
                    first_access=first_acc,
                    last_access=last_acc,
                    status=st,
                    email=email,
                    phone_e164=phone_e164,
                    phone_label=phone_label,
                )
            )

        return self._sort_people(people, sort)

    def _list_people_compat(self) -> list[sqlite3.Row]:
        """LEFT JOIN path (SQLite without FULL OUTER JOIN)."""

        with self._connect() as conn:
            # Ensure people with only logs appear
            conn.execute(
                """
                INSERT OR IGNORE INTO user_anagrafica (
                    username, user_id, first_name, last_name, gender,
                    phone_label, headset_id, status, photo_path, updated_at
                )
                SELECT DISTINCT username, '', '', '', '', '', '', 'active', '', ?
                FROM access_logs
                WHERE username NOT IN (SELECT username FROM user_anagrafica)
                  AND username != '(sconosciuto)'
                """,
                (_utc_now(),),
            )
            return conn.execute(
                """
                SELECT
                    a.username AS username,
                    a.first_name AS first_name,
                    a.last_name AS last_name,
                    a.status AS status,
                    COALESCE(a.email, '') AS email,
                    COALESCE(a.phone_e164, '') AS phone_e164,
                    COALESCE(a.phone_label, '') AS phone_label,
                    COALESCE(u.phone_national, '') AS phone_national,
                    COUNT(l.id) AS access_count,
                    MIN(l.created_at) AS first_access,
                    MAX(l.created_at) AS last_access
                FROM user_anagrafica a
                LEFT JOIN users u
                  ON u.username = a.username
                LEFT JOIN access_logs l
                  ON a.username = l.username
                 AND l.event IN ('login_ok', 'register', 'logout', 'login_fail')
                GROUP BY a.username
                """
            ).fetchall()

    @staticmethod
    def _sort_people(people: list[PersonRow], sort: SortKey) -> list[PersonRow]:
        if sort == "name_desc":
            return sorted(
                people,
                key=lambda p: (p.last_name.lower(), p.first_name.lower()),
                reverse=True,
            )
        if sort == "accesses_asc":
            return sorted(people, key=lambda p: (p.access_count, p.last_name.lower()))
        if sort == "accesses_desc":
            return sorted(
                people,
                key=lambda p: (p.access_count, p.last_name.lower()),
                reverse=True,
            )
        if sort == "last_asc":
            return sorted(people, key=lambda p: p.last_access or "")
        if sort == "last_desc":
            return sorted(people, key=lambda p: p.last_access or "", reverse=True)
        return sorted(people, key=lambda p: (p.last_name.lower(), p.first_name.lower()))

    def hide_expired_inbox(self, *, days: int = INBOX_KEEP_DAYS) -> int:
        """Hide replied threads from the inbox after the retention window."""

        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        hidden = 0
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, replied_at FROM support_threads
                WHERE status = 'replied' AND inbox_hidden = 0
                """
            ).fetchall()
            for row in rows:
                replied = _parse_dt(str(row["replied_at"] or ""))
                if replied is None:
                    continue
                if replied.tzinfo is None:
                    replied = replied.replace(tzinfo=timezone.utc)
                if replied <= cutoff:
                    conn.execute(
                        "UPDATE support_threads SET inbox_hidden = 1 WHERE id = ?",
                        (int(row["id"]),),
                    )
                    hidden += 1
            conn.commit()
        return hidden

    def support_unread_count(self) -> int:
        self.hide_expired_inbox()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM support_threads
                WHERE status = 'unread' AND inbox_hidden = 0
                """
            ).fetchone()
        return int(row["n"] if row else 0)

    def list_support_threads(self, *, archive: bool = False) -> list[dict[str, Any]]:
        self.hide_expired_inbox()
        with self._connect() as conn:
            if archive:
                rows = conn.execute(
                    """
                    SELECT * FROM support_threads
                    WHERE inbox_hidden = 1
                    ORDER BY updated_at DESC, id DESC
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM support_threads
                    WHERE inbox_hidden = 0
                    ORDER BY
                        CASE status
                            WHEN 'unread' THEN 0
                            WHEN 'viewed' THEN 1
                            ELSE 2
                        END,
                        updated_at DESC, id DESC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def list_user_support_threads(
        self, *, username: str = "", email: str = ""
    ) -> list[dict[str, Any]]:
        username = (username or "").strip()
        email = (email or "").strip().lower()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM support_threads
                WHERE (username != '' AND username = ?)
                   OR (? != '' AND lower(guest_email) = ?)
                ORDER BY updated_at DESC, id DESC
                """,
                (username, email, email),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_support_thread(self, thread_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM support_threads WHERE id = ?",
                (int(thread_id),),
            ).fetchone()
        return dict(row) if row else None

    def list_support_messages(self, thread_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM support_messages
                WHERE thread_id = ?
                ORDER BY id ASC
                """,
                (int(thread_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def _latest_open_thread(
        self, conn: sqlite3.Connection, *, username: str, email: str
    ) -> sqlite3.Row | None:
        if username:
            row = conn.execute(
                """
                SELECT * FROM support_threads
                WHERE username = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (username,),
            ).fetchone()
            if row:
                return row
        if email:
            return conn.execute(
                """
                SELECT * FROM support_threads
                WHERE lower(guest_email) = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (email.lower(),),
            ).fetchone()
        return None

    def add_user_support_message(
        self,
        *,
        username: str = "",
        guest_name: str = "",
        guest_email: str = "",
        guest_phone: str = "",
        channel: str = "chat",
        subject: str = "",
        body: str = "",
    ) -> int:
        username = (username or "").strip()
        guest_name = (guest_name or "").strip()[:80]
        guest_email = (guest_email or "").strip().lower()[:254]
        guest_phone = (guest_phone or "").strip()[:32]
        channel = "email" if channel == "email" else "chat"
        subject = (subject or "").strip()[:160] or (
            "Messaggio via email" if channel == "email" else "Chatta con noi"
        )
        body = (body or "").strip()[:4000]
        if not body:
            raise ValueError("message required")
        now = _utc_now()
        with self._connect() as conn:
            existing = self._latest_open_thread(conn, username=username, email=guest_email)
            if existing is not None:
                thread_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE support_threads
                    SET status = 'unread',
                        inbox_hidden = 0,
                        channel = ?,
                        subject = CASE WHEN subject = '' THEN ? ELSE subject END,
                        guest_name = CASE WHEN guest_name = '' THEN ? ELSE guest_name END,
                        guest_email = CASE WHEN guest_email = '' THEN ? ELSE guest_email END,
                        guest_phone = CASE WHEN guest_phone = '' THEN ? ELSE guest_phone END,
                        username = CASE WHEN username = '' THEN ? ELSE username END,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        channel,
                        subject,
                        guest_name,
                        guest_email,
                        guest_phone,
                        username,
                        now,
                        thread_id,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO support_threads (
                        username, guest_name, guest_email, guest_phone, channel,
                        subject, status, viewed_at, replied_at, inbox_hidden,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'unread', '', '', 0, ?, ?)
                    """,
                    (
                        username,
                        guest_name,
                        guest_email,
                        guest_phone,
                        channel,
                        subject,
                        now,
                        now,
                    ),
                )
                thread_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO support_messages (thread_id, sender, body, created_at)
                VALUES (?, 'user', ?, ?)
                """,
                (thread_id, body, now),
            )
            conn.commit()
        return thread_id

    def mark_support_viewed(self, thread_id: int) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE support_threads
                SET status = CASE WHEN status = 'unread' THEN 'viewed' ELSE status END,
                    viewed_at = CASE WHEN viewed_at = '' THEN ? ELSE viewed_at END,
                    updated_at = ?
                WHERE id = ? AND status != 'replied'
                """,
                (now, now, int(thread_id)),
            )
            conn.commit()

    def add_admin_support_reply(self, thread_id: int, body: str) -> dict[str, Any] | None:
        body = (body or "").strip()[:4000]
        if not body:
            raise ValueError("message required")
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM support_threads WHERE id = ?",
                (int(thread_id),),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """
                INSERT INTO support_messages (thread_id, sender, body, created_at)
                VALUES (?, 'admin', ?, ?)
                """,
                (int(thread_id), body, now),
            )
            conn.execute(
                """
                UPDATE support_threads
                SET status = 'replied',
                    replied_at = ?,
                    inbox_hidden = 0,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, int(thread_id)),
            )
            conn.commit()
            fresh = conn.execute(
                "SELECT * FROM support_threads WHERE id = ?",
                (int(thread_id),),
            ).fetchone()
        return dict(fresh) if fresh else dict(row)

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS n FROM access_logs").fetchone()["n"]
            by_event = {
                str(row["event"]): int(row["n"])
                for row in conn.execute(
                    """
                    SELECT event, COUNT(*) AS n
                    FROM access_logs
                    GROUP BY event
                    ORDER BY n DESC
                    """
                ).fetchall()
            }
            registered = conn.execute(
                "SELECT COUNT(*) AS n FROM user_anagrafica WHERE status='active'"
            ).fetchone()["n"]
            deleted = conn.execute(
                "SELECT COUNT(*) AS n FROM user_anagrafica WHERE status='deleted'"
            ).fetchone()["n"]
        return {
            "total": int(total),
            "by_event": by_event,
            "registered": int(registered),
            "deleted": int(deleted),
        }

    @staticmethod
    def _row_event(row: sqlite3.Row) -> AccessEvent:
        return AccessEvent(
            id=int(row["id"]),
            username=str(row["username"]),
            event=str(row["event"]),
            ip=str(row["ip"]),
            user_agent=str(row["user_agent"]),
            created_at=str(row["created_at"]),
        )
