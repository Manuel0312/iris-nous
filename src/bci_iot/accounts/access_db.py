"""SQLite database for access logs and admin people directory."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
            conn.commit()

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
            st = str(row["status"] or "active")
            first_acc = str(row["first_access"] or "")
            last_acc = str(row["last_access"] or "")
            count = int(row["access_count"] or 0)

            if status != "all" and st != status:
                continue
            hay = f"{first} {last} {username}".lower()
            if needle and needle not in hay:
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
                    COUNT(l.id) AS access_count,
                    MIN(l.created_at) AS first_access,
                    MAX(l.created_at) AS last_access
                FROM user_anagrafica a
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
