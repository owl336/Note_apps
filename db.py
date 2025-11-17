import sqlite3
import os
from datetime import datetime


DB_FILENAME = os.path.join(os.path.expanduser("~"), ".local_notes_app", "notes.db")


class NotesDB:
    def __init__(self, db_path=DB_FILENAME):
        self.db_path = db_path
        self._ensure_dir()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _ensure_dir(self):
        d = os.path.dirname(self.db_path)
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT
            )
        """)
        self.conn.commit()

    def add_note(self, text):
        now = datetime.now().isoformat()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO notes (text, created_at, updated_at) VALUES (?, ?, ?)", (text, now, now))
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, note_id, new_text):
        now = datetime.now().isoformat()
        cur = self.conn.cursor()
        cur.execute("UPDATE notes SET text=?, updated_at=? WHERE id=?", (new_text, now, note_id))
        self.conn.commit()

    def delete_note_soft(self, note_id):
        now = datetime.now().isoformat()
        cur = self.conn.cursor()
        cur.execute("UPDATE notes SET deleted_at=? WHERE id=?", (now, note_id))
        self.conn.commit()

    def get_notes(self, include_deleted=False, order="DESC", keyword=None):
        cur = self.conn.cursor()
        q = "SELECT id, text, created_at, updated_at, deleted_at FROM notes"
        conds = []
        params = []
        if not include_deleted:
            conds.append("deleted_at IS NULL")
        if keyword:
            conds.append("LOWER(text) LIKE ?")
            params.append(f"%{keyword.lower()}%")
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += f" ORDER BY datetime(created_at) {order}"
        cur.execute(q, params)
        return cur.fetchall()

    def get_note(self, note_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM notes WHERE id=?", (note_id,))
        return cur.fetchone()

    def stats_counts_by_date(self, days=30):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT date(created_at) as d, COUNT(*) 
            FROM notes GROUP BY d ORDER BY d DESC LIMIT ?
        """, (days,))
        created = dict(cur.fetchall())

        cur.execute("""
            SELECT date(deleted_at) as d, COUNT(*) 
            FROM notes WHERE deleted_at IS NOT NULL 
            GROUP BY d ORDER BY d DESC LIMIT ?
        """, (days,))
        deleted = dict(cur.fetchall())

        return created, deleted

    def close(self):
        try:
            self.conn.close()
        except:
            pass
