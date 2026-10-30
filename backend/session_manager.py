import time
import sqlite3
import hashlib
from datetime import date
from pathlib import Path
from typing import Dict, Any, Optional

DAILY_CAP_SECONDS = 30 * 60  # 30 minutes = 1800 seconds
DB_PATH = Path("data/aviation_rag.db")

class SessionManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path), timeout=30.0)
        con.execute("PRAGMA journal_mode=WAL;")
        return con

    def _init_db(self):
        with self._get_connection() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS student_sessions (
                    student_id TEXT PRIMARY KEY,
                    client_ip_hash TEXT,
                    session_date TEXT,
                    used_seconds INTEGER DEFAULT 0,
                    last_active REAL,
                    created_at REAL
                );
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_date_ip 
                ON student_sessions(session_date, client_ip_hash);
            """)

    def _get_today_str(self) -> str:
        return date.today().isoformat()

    def _hash_ip(self, ip: Optional[str]) -> str:
        if not ip:
            return "unknown"
        # Extract first IP in X-Forwarded-For chain
        raw_ip = ip.split(",")[0].strip()
        return hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()[:16]

    def get_session(self, student_id: str, client_ip: Optional[str] = None) -> Dict[str, Any]:
        today = self._get_today_str()
        ip_hash = self._hash_ip(client_ip)

        with self._get_connection() as con:
            # 1. Check if this student_id has a record today
            row = con.execute("""
                SELECT student_id, client_ip_hash, session_date, used_seconds, last_active 
                FROM student_sessions 
                WHERE student_id = ?;
            """, (student_id,)).fetchone()

            # 2. Check if IP has exhausted quota today under ANY student_id (anti-abuse)
            ip_max_used = 0
            if ip_hash != "unknown":
                ip_row = con.execute("""
                    SELECT MAX(used_seconds) 
                    FROM student_sessions 
                    WHERE client_ip_hash = ? AND session_date = ?;
                """, (ip_hash, today)).fetchone()
                if ip_row and ip_row[0]:
                    ip_max_used = ip_row[0]

            now = time.time()
            if not row or row[2] != today:
                # Initialize new session for today, inheriting IP max usage to prevent incognito bypass
                initial_used = ip_max_used if ip_max_used >= DAILY_CAP_SECONDS else 0
                con.execute("""
                    INSERT OR REPLACE INTO student_sessions 
                    (student_id, client_ip_hash, session_date, used_seconds, last_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (student_id, ip_hash, today, initial_used, now, now))
                used_seconds = initial_used
            else:
                used_seconds = max(row[3], ip_max_used)
                if used_seconds != row[3]:
                    con.execute("""
                        UPDATE student_sessions SET used_seconds = ? WHERE student_id = ?;
                    """, (used_seconds, student_id))

        remaining = max(0, DAILY_CAP_SECONDS - used_seconds)
        is_capped = remaining <= 0

        return {
            "student_id": student_id,
            "date": today,
            "daily_cap_seconds": DAILY_CAP_SECONDS,
            "used_seconds": used_seconds,
            "remaining_seconds": remaining,
            "is_capped": is_capped,
            "formatted_remaining": self.format_time(remaining),
            "percentage_used": round((used_seconds / DAILY_CAP_SECONDS) * 100, 1)
        }

    def record_activity(self, student_id: str, elapsed_seconds: int = 15, client_ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Record interaction activity and persist to SQLite with IP attribution.
        """
        today = self._get_today_str()
        ip_hash = self._hash_ip(client_ip)
        session = self.get_session(student_id, client_ip)
        now = time.time()

        added_time = min(max(1, elapsed_seconds), 60)
        new_used = min(DAILY_CAP_SECONDS, session["used_seconds"] + added_time)

        with self._get_connection() as con:
            con.execute("""
                UPDATE student_sessions 
                SET used_seconds = ?, last_active = ?, client_ip_hash = ?
                WHERE student_id = ?;
            """, (new_used, now, ip_hash, student_id))

        remaining = max(0, DAILY_CAP_SECONDS - new_used)
        is_capped = remaining <= 0

        return {
            "student_id": student_id,
            "date": today,
            "daily_cap_seconds": DAILY_CAP_SECONDS,
            "used_seconds": new_used,
            "remaining_seconds": remaining,
            "is_capped": is_capped,
            "formatted_remaining": self.format_time(remaining),
            "percentage_used": round((new_used / DAILY_CAP_SECONDS) * 100, 1)
        }

    def check_can_interact(self, student_id: str, client_ip: Optional[str] = None) -> bool:
        session = self.get_session(student_id, client_ip)
        return not session["is_capped"]

    def set_student_used_seconds(self, student_id: str, seconds: int):
        """Helper for test simulations"""
        with self._get_connection() as con:
            con.execute("""
                UPDATE student_sessions SET used_seconds = ? WHERE student_id = ?;
            """, (seconds, student_id))

    def reset_student(self, student_id: str):
        """Reset student for testing"""
        with self._get_connection() as con:
            con.execute("DELETE FROM student_sessions WHERE student_id = ?;", (student_id,))

    @staticmethod
    def format_time(seconds: int) -> str:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

session_manager = SessionManager()
