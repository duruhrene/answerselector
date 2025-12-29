import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

class UserDataManager:
    """
    Unified manager for user-generated content:
    1. Templates: Custom answer structures (Stored in usertemplates.db)
    2. Answer Memos: Notes on system answers (Stored in usermemos.db)
    """

    def __init__(self, db_dir: Optional[Any] = None) -> None:
        self.db_dir = Path(db_dir) if db_dir is not None else self._default_db_dir()
        self.templates_db = self.db_dir / "usertemplates.db"
        self.memos_db = self.db_dir / "usermemos.db"
        
        self._observers: List[Any] = []  # List of callables
        self._init_db()

    def add_observer(self, callback) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, event_type: str = "template_changed") -> None:
        for callback in self._observers:
            try:
                callback(event_type)
            except Exception:
                pass  # Ignore failed callbacks

    def _default_db_dir(self) -> Path:
        """Resolve database directory."""
        return Path(__file__).resolve().parent.parent.parent / "database"

    def _init_db(self) -> None:
        """Ensure both databases and relevant tables exist."""
        # 1. Initialize Templates Table
        with sqlite3.connect(self.templates_db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    memo TEXT,
                    modified TEXT NOT NULL
                )
                """
            )
        
        # 2. Initialize Answer Memos Table
        with sqlite3.connect(self.memos_db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS answer_memos (
                    answer_id INTEGER PRIMARY KEY,
                    memo TEXT,
                    modified TEXT NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------ #
    # Section 1: Template Operations (CRUD)
    # ------------------------------------------------------------------ #
    def add_template(self, title: str, text: str, memo: str = "") -> bool:
        """Create a new template. Returns True if successful."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Normalize line breaks to \n
        text = text.replace("\r\n", "\n")
        if memo: memo = memo.replace("\r\n", "\n")
        
        try:
            with sqlite3.connect(self.templates_db) as conn:
                conn.execute(
                    "INSERT INTO templates (title, text, memo, modified) VALUES (?, ?, ?, ?)",
                    (title, text, memo, now)
                )
            self._notify_observers()
            return True
        except Exception:
            return False

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Return list of all templates (ordered by modified desc)."""
        with sqlite3.connect(self.templates_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, title, text, memo, modified FROM templates ORDER BY modified DESC")
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                d = dict(row)
                if d.get("text"): d["text"] = d["text"].replace("\r\n", "\n")
                # Null-safe normalization for memo
                if d.get("memo"): d["memo"] = d["memo"].replace("\r\n", "\n")
                else: d["memo"] = "" # Treat missing memo as empty string for UI
                results.append(d)
            return results

    def update_template(self, template_id: int, title: str, text: str, memo: str) -> None:
        """Update an existing template."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = text.replace("\r\n", "\n")
        memo = memo.replace("\r\n", "\n")

        with sqlite3.connect(self.templates_db) as conn:
            conn.execute(
                "UPDATE templates SET title = ?, text = ?, memo = ?, modified = ? WHERE id = ?",
                (title, text, memo, now, template_id)
            )
        self._notify_observers()

    def delete_template(self, template_id: int) -> None:
        """Delete a template by ID."""
        with sqlite3.connect(self.templates_db) as conn:
            conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self._notify_observers()

    def search_templates(self, keyword: str) -> List[Dict[str, Any]]:
        """Search templates by keyword."""
        if not keyword: return []
        pattern = f"%{keyword}%"
        with sqlite3.connect(self.templates_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM templates WHERE title LIKE ? OR text LIKE ? OR memo LIKE ? ORDER BY modified DESC",
                (pattern, pattern, pattern)
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get("text"): d["text"] = d["text"].replace("\r\n", "\n")
                if d.get("memo"): d["memo"] = d["memo"].replace("\r\n", "\n")
                results.append(d)
            return results

    # ------------------------------------------------------------------ #
    # Section 2: Answer Memo Operations (Linked to answerembed.db)
    # ------------------------------------------------------------------ #
    def save_answer_memo(self, answer_id: int, memo: str) -> None:
        """Add or update a memo for a system answer."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if memo:
            memo = memo.replace("\r\n", "\n")
        
        with sqlite3.connect(self.memos_db) as conn:
            conn.execute(
                """
                INSERT INTO answer_memos (answer_id, memo, modified)
                VALUES (?, ?, ?)
                ON CONFLICT(answer_id) DO UPDATE SET
                    memo = excluded.memo,
                    modified = excluded.modified
                """,
                (answer_id, memo, now)
            )

    def get_answer_memo(self, answer_id: int) -> Optional[str]:
        """Retrieve memo text for a given answer ID."""
        with sqlite3.connect(self.memos_db) as conn:
            cursor = conn.execute("SELECT memo FROM answer_memos WHERE answer_id = ?", (answer_id,))
            row = cursor.fetchone()
            if row:
                val = row[0]
                return val.replace("\r\n", "\n") if val else ""
            return None # No record found

    def delete_answer_memo(self, answer_id: int) -> None:
        """Delete memo for a specific answer."""
        with sqlite3.connect(self.memos_db) as conn:
            conn.execute("DELETE FROM answer_memos WHERE answer_id = ?", (answer_id,))

    def get_template_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific template by its title."""
        with sqlite3.connect(self.templates_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM templates WHERE title = ?", (title,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("text"): d["text"] = d["text"].replace("\r\n", "\n")
                if d.get("memo"): d["memo"] = d["memo"].replace("\r\n", "\n")
                return d
            return None

    def get_all_answer_memos(self) -> Dict[int, str]:
        """Returns all answer memos as {answer_id: memo}."""
        with sqlite3.connect(self.memos_db) as conn:
            cursor = conn.execute("SELECT answer_id, memo FROM answer_memos")
            rows = cursor.fetchall()
            # Normalize and handle None safely
            return {row[0]: (row[1].replace("\r\n", "\n") if row[1] else "") for row in rows}
