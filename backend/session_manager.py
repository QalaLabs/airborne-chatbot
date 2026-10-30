import time
from datetime import datetime, date
from typing import Dict, Any, Optional

DAILY_CAP_SECONDS = 30 * 60  # 30 minutes = 1800 seconds

class SessionManager:
    def __init__(self):
        # In-memory session tracking by student_id
        # { student_id: { "date": "2026-10-30", "used_seconds": 120, "last_active": timestamp } }
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _get_today_str(self) -> str:
        return date.today().isoformat()

    def get_session(self, student_id: str) -> Dict[str, Any]:
        today = self._get_today_str()
        session = self.sessions.get(student_id)

        if not session or session.get("date") != today:
            session = {
                "student_id": student_id,
                "date": today,
                "used_seconds": 0,
                "last_active": time.time(),
                "created_at": time.time()
            }
            self.sessions[student_id] = session

        remaining = max(0, DAILY_CAP_SECONDS - session["used_seconds"])
        is_capped = remaining <= 0

        return {
            "student_id": student_id,
            "date": today,
            "daily_cap_seconds": DAILY_CAP_SECONDS,
            "used_seconds": session["used_seconds"],
            "remaining_seconds": remaining,
            "is_capped": is_capped,
            "formatted_remaining": self.format_time(remaining),
            "percentage_used": round((session["used_seconds"] / DAILY_CAP_SECONDS) * 100, 1)
        }

    def record_activity(self, student_id: str, elapsed_seconds: int = 15) -> Dict[str, Any]:
        """
        Record interaction activity (via periodic heartbeat or per-turn action).
        Caps at 1800 seconds total for today.
        """
        session_info = self.get_session(student_id)
        session_data = self.sessions[student_id]
        
        now = time.time()
        # Add elapsed interaction time (bounded to reasonable heartbeat delta)
        added_time = min(max(1, elapsed_seconds), 60)
        session_data["used_seconds"] = min(DAILY_CAP_SECONDS, session_data["used_seconds"] + added_time)
        session_data["last_active"] = now

        remaining = max(0, DAILY_CAP_SECONDS - session_data["used_seconds"])
        is_capped = remaining <= 0

        return {
            "student_id": student_id,
            "date": session_data["date"],
            "daily_cap_seconds": DAILY_CAP_SECONDS,
            "used_seconds": session_data["used_seconds"],
            "remaining_seconds": remaining,
            "is_capped": is_capped,
            "formatted_remaining": self.format_time(remaining),
            "percentage_used": round((session_data["used_seconds"] / DAILY_CAP_SECONDS) * 100, 1)
        }

    def check_can_interact(self, student_id: str) -> bool:
        session = self.get_session(student_id)
        return not session["is_capped"]

    def reset_student(self, student_id: str):
        """Helper to reset session cap for testing"""
        if student_id in self.sessions:
            self.sessions[student_id]["used_seconds"] = 0
            self.sessions[student_id]["last_active"] = time.time()

    @staticmethod
    def format_time(seconds: int) -> str:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

session_manager = SessionManager()
