# notes_app.py
import sqlite3
import os
import sys
from datetime import datetime
import tempfile

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog, filedialog
except Exception as e:
    print("Tkinter is required. On Windows it is included with Python. Error:", e)
    sys.exit(1)

# Matplotlib imports (for stats chart)
import matplotlib
matplotlib.use("Agg")  # for drawing to PNG buffer
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io

DB_FILENAME = os.path.join(os.path.expanduser("~"), ".local_notes_app", "notes.db")

LOCALES = {
    "ru": {
        "app_title": "Заметки",
        "add": "Добавить",
        "edit": "Редактировать",
        "delete": "Удалить",
        "search": "Поиск",
        "sort_asc": "Сортировка ↑",
        "sort_desc": "Сортировка ↓",
        "export": "Экспорт",
        "stats": "Статистика",
        "refresh": "Обновить",
        "confirm_delete": "Удалить выбранную заметку?",
        "empty_note_error": "Текст заметки не может быть пустым.",
        "no_notes": "Заметок нет.",
        "created_at": "Создано",
        "updated_at": "Изменено",
        "deleted_msg": "Заметка перемещена в удалённые.",
        "export_done": "Экспорт завершён",
        "language": "Язык",
        "view_all": "Показать все",
        "search_placeholder": "Введите ключевое слово для поиска",
        "ok": "ОК",
        "cancel": "Отмена"
    },
    "en": {
        "app_title": "Notes",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "search": "Search",
        "sort_asc": "Sort ↑",
        "sort_desc": "Sort ↓",
        "export": "Export",
        "stats": "Statistics",
        "refresh": "Refresh",
        "confirm_delete": "Delete selected note?",
        "empty_note_error": "Note text cannot be empty.",
        "no_notes": "No notes.",
        "created_at": "Created",
        "updated_at": "Updated",
        "deleted_msg": "Note deleted.",
        "export_done": "Export completed",
        "language": "Language",
        "view_all": "View all",
        "search_placeholder": "Enter keyword to search",
        "ok": "OK",
        "cancel": "Cancel"
    }
}

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
        # soft delete (set deleted_at)
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
        cur.execute("SELECT id, text, created_at, updated_at, deleted_at FROM notes WHERE id=?", (note_id,))
        return cur.fetchone()

    def stats_counts_by_date(self, days=30):
        # returns dictionaries for created and deleted counts keyed by date YYYY-MM-DD
        cur = self.conn.cursor()
        # created
        cur.execute("""
            SELECT date(created_at) as d, COUNT(*) FROM notes
            GROUP BY d
            ORDER BY d DESC
            LIMIT ?
        """, (days,))
        created = dict(cur.fetchall())
        # deleted
        cur.execute("""
            SELECT date(deleted_at) as d, COUNT(*) FROM notes
            WHERE deleted_at IS NOT NULL
            GROUP BY d
            ORDER BY d DESC
            LIMIT ?
        """, (days,))
        deleted = dict(cur.fetchall())
        return created, deleted

    def close(self):
        try:
            self.conn.close()
        except:
            pass

class NotesApp(tk.Tk):
    def __init__(self, db: NotesDB):
        super().__init__()
        self.db = db
        self.locale = "ru"
        self.trans = LOCALES[self.locale]
        self.title(self.trans["app_title"])
        self.geometry("900x600")
        self.minsize(800, 500)

        self.sort_order = "DESC"  # newest first
        self.search_keyword = None

        self._build_ui()
        self.refresh_notes()

    def _t(self, key):
        return LOCALES[self.locale].get(key, key)

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        self.btn_add = ttk.Button(toolbar, text=self._t("add"), command=self.on_add)
        self.btn_add.pack(side=tk.LEFT, padx=2)
        self.btn_edit = ttk.Button(toolbar, text=self._t("edit"), command=self.on_edit)
        self.btn_edit.pack(side=tk.LEFT, padx=2)
        self.btn_delete = ttk.Button(toolbar, text=self._t("delete"), command=self.on_delete)
        self.btn_delete.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.btn_sort_asc = ttk.Button(toolbar, text=self._t("sort_asc"), command=self.set_sort_asc)
        self.btn_sort_asc.pack(side=tk.LEFT, padx=2)
        self.btn_sort_desc = ttk.Button(toolbar, text=self._t("sort_desc"), command=self.set_sort_desc)
        self.btn_sort_desc.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.entry_search = ttk.Entry(toolbar, width=30)
        self.entry_search.insert(0, self._t("search_placeholder"))
        self.entry_search.bind("<FocusIn>", lambda e: self._clear_search_placeholder())
        self.entry_search.pack(side=tk.LEFT, padx=2)
        self.btn_search = ttk.Button(toolbar, text=self._t("search"), command=self.on_search)
        self.btn_search.pack(side=tk.LEFT, padx=2)
        self.btn_refresh = ttk.Button(toolbar, text=self._t("refresh"), command=self.refresh_notes)
        self.btn_refresh.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.btn_export = ttk.Button(toolbar, text=self._t("export"), command=self.on_export)
        self.btn_export.pack(side=tk.LEFT, padx=2)
        self.btn_stats = ttk.Button(toolbar, text=self._t("stats"), command=self.on_stats)
        self.btn_stats.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # Language combobox
        lang_label = ttk.Label(toolbar, text=self._t("language") + ":")
        lang_label.pack(side=tk.LEFT, padx=(10,2))
        self.lang_combo = ttk.Combobox(toolbar, values=["ru", "en"], width=4, state="readonly")
        self.lang_combo.set(self.locale)
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_change_language)
        self.lang_combo.pack(side=tk.LEFT)

        # Main area: left list of notes, right full text + meta
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.notes_listbox = tk.Listbox(left, width=40)
        self.notes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notes_listbox.bind("<<ListboxSelect>>", self.on_note_select)

        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.notes_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_listbox.config(yscrollcommand=scrollbar.set)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,0))

        meta_frame = ttk.Frame(right)
        meta_frame.pack(fill=tk.X)

        self.lbl_created = ttk.Label(meta_frame, text=self._t("created_at") + ": ")
        self.lbl_created.pack(anchor="w")
        self.lbl_updated = ttk.Label(meta_frame, text=self._t("updated_at") + ": ")
        self.lbl_updated.pack(anchor="w")

        self.text_area = tk.Text(right, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        self.text_area.config(state=tk.DISABLED)

    def _clear_search_placeholder(self):
        cur = self.entry_search.get()
        if cur == self._t("search_placeholder"):
            self.entry_search.delete(0, tk.END)

    def on_change_language(self, event=None):
        self.locale = self.lang_combo.get()
        self._apply_locale()

    def _apply_locale(self):
        self.title(self._t("app_title"))
        self.btn_add.config(text=self._t("add"))
        self.btn_edit.config(text=self._t("edit"))
        self.btn_delete.config(text=self._t("delete"))
        self.btn_sort_asc.config(text=self._t("sort_asc"))
        self.btn_sort_desc.config(text=self._t("sort_desc"))
        self.btn_search.config(text=self._t("search"))
        self.btn_export.config(text=self._t("export"))
        self.btn_stats.config(text=self._t("stats"))
        self.btn_refresh.config(text=self._t("refresh"))
        # placeholder
        if not self.entry_search.get().strip():
            self.entry_search.delete(0, tk.END)
            self.entry_search.insert(0, self._t("search_placeholder"))
        self.lbl_created.config(text=self._t("created_at") + ": ")
        self.lbl_updated.config(text=self._t("updated_at") + ": ")

    def refresh_notes(self):
        self.notes_listbox.delete(0, tk.END)
        notes = self.db.get_notes(include_deleted=False, order=self.sort_order, keyword=self.search_keyword)
        if not notes:
            self.notes_listbox.insert(tk.END, self._t("no_notes"))
            self.clear_preview()
            return
        for n in notes:
            nid, text, created_at, updated_at, deleted_at = n
            preview = text.replace("\n", " ")[:80]
            display = f"{nid}. {preview}..."
            self.notes_listbox.insert(tk.END, display)
        # clear search after refresh
        self.search_keyword = None

    def clear_preview(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        self.text_area.config(state=tk.DISABLED)
        self.lbl_created.config(text=self._t("created_at") + ": ")
        self.lbl_updated.config(text=self._t("updated_at") + ": ")

    def on_note_select(self, event=None):
        sel = self.notes_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        txt = self.notes_listbox.get(idx)
        try:
            note_id = int(txt.split(".")[0])
        except Exception:
            return
        note = self.db.get_note(note_id)
        if not note:
            return
        nid, text, created_at, updated_at, deleted_at = note
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert(tk.END, text)
        self.text_area.config(state=tk.DISABLED)
        self.lbl_created.config(text=f"{self._t('created_at')}: {created_at}")
        self.lbl_updated.config(text=f"{self._t('updated_at')}: {updated_at}")

    def on_add(self):
        dialog = NoteDialog(self, title=self._t("add"), locale=self.locale)
        self.wait_window(dialog.top)
        if dialog.result_text is not None:
            txt = dialog.result_text.strip()
            if not txt:
                messagebox.showerror(self._t("add"), self._t("empty_note_error"))
                return
            self.db.add_note(txt)
            self.refresh_notes()

    def on_edit(self):
        sel = self.notes_listbox.curselection()
        if not sel:
            messagebox.showinfo(self._t("edit"), self._t("no_notes"))
            return
        idx = sel[0]
        txt = self.notes_listbox.get(idx)
        try:
            note_id = int(txt.split(".")[0])
        except Exception:
            messagebox.showinfo(self._t("edit"), self._t("no_notes"))
            return
        note = self.db.get_note(note_id)
        if not note:
            messagebox.showinfo(self._t("edit"), self._t("no_notes"))
            return
        nid, text, created_at, updated_at, deleted_at = note
        dialog = NoteDialog(self, title=self._t("edit"), initial_text=text, locale=self.locale)
        self.wait_window(dialog.top)
        if dialog.result_text is not None:
            new_text = dialog.result_text.strip()
            if not new_text:
                messagebox.showerror(self._t("edit"), self._t("empty_note_error"))
                return
            self.db.update_note(note_id, new_text)
            self.refresh_notes()

    def on_delete(self):
        sel = self.notes_listbox.curselection()
        if not sel:
            messagebox.showinfo(self._t("delete"), self._t("no_notes"))
            return
        idx = sel[0]
        txt = self.notes_listbox.get(idx)
        try:
            note_id = int(txt.split(".")[0])
        except Exception:
            messagebox.showinfo(self._t("delete"), self._t("no_notes"))
            return
        if messagebox.askyesno(self._t("delete"), self._t("confirm_delete")):
            self.db.delete_note_soft(note_id)
            messagebox.showinfo(self._t("delete"), self._t("deleted_msg"))
            self.refresh_notes()

    def set_sort_asc(self):
        self.sort_order = "ASC"
        self.refresh_notes()

    def set_sort_desc(self):
        self.sort_order = "DESC"
        self.refresh_notes()

    def on_search(self):
        kw = self.entry_search.get().strip()
        if kw == "" or kw == self._t("search_placeholder"):
            self.search_keyword = None
        else:
            self.search_keyword = kw
        self.refresh_notes()

    def on_export(self):
        sel = self.notes_listbox.curselection()
        if not sel:
            messagebox.showinfo(self._t("export"), self._t("no_notes"))
            return
        # allow multiple selection? listbox currently single-select; export selected note
        idx = sel[0]
        txt = self.notes_listbox.get(idx)
        try:
            note_id = int(txt.split(".")[0])
        except Exception:
            messagebox.showinfo(self._t("export"), self._t("no_notes"))
            return
        note = self.db.get_note(note_id)
        if not note:
            return
        nid, text, created_at, updated_at, deleted_at = note
        # choose folder
        folder = filedialog.askdirectory(title=self._t("export"))
        if not folder:
            return
        fname = os.path.join(folder, f"note_{nid}.txt")
        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo(self._t("export"), f"{self._t('export_done')}: {fname}")
        except Exception as e:
            messagebox.showerror(self._t("export"), str(e))

    def on_stats(self):
        # create small window with chart for last 30 days
        created, deleted = self.db.stats_counts_by_date(days=30)
        # prepare x-axis dates (last 30 days)
        dates = []
        counts_created = []
        counts_deleted = []
        from datetime import date, timedelta
        today = date.today()
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            ds = d.isoformat()
            dates.append(d.strftime("%m-%d"))
            counts_created.append(created.get(ds, 0))
            counts_deleted.append(deleted.get(ds, 0))

        # draw plot to PNG buffer
        plt.figure(figsize=(8,4))
        plt.plot(dates, counts_created, marker='o', label=self._t("created_at"))
        plt.plot(dates, counts_deleted, marker='s', label=self._t("delete") if "delete" in LOCALES[self.locale] else "Deleted")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        plt.close()
        buf.seek(0)
        img = Image.open(buf)
        # show in new window
        win = tk.Toplevel(self)
        win.title(self._t("stats"))
        win.geometry("900x420")
        tk_img = ImageTk.PhotoImage(img)
        lbl = ttk.Label(win, image=tk_img)
        lbl.image = tk_img
        lbl.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

class NoteDialog:
    def __init__(self, parent, title="Note", initial_text="", locale="ru"):
        self.parent = parent
        self.locale = locale
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.grab_set()

        self.result_text = None

        # текстовое поле
        self.text = tk.Text(self.top, width=60, height=15, wrap=tk.WORD)
        self.text.pack(padx=10, pady=10)
        self.text.insert("1.0", initial_text)

        # Фикс: курсор сразу активен
        self.text.focus_set()

        # Фикс: нормальная работа Ctrl+V/C/X/A
        self.text.bind("<Control-v>", self._paste)
        self.text.bind("<Control-V>", self._paste)
        self.text.bind("<Control-c>", self._copy)
        self.text.bind("<Control-C>", self._copy)
        self.text.bind("<Control-x>", self._cut)
        self.text.bind("<Control-X>", self._cut)
        self.text.bind("<Control-a>", self._select_all)
        self.text.bind("<Control-A>", self._select_all)

        # Кнопки OK / Cancel
        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=(0, 10))

        ok_text = LOCALES[self.locale].get("ok", "OK")
        cancel_text = LOCALES[self.locale].get("cancel", "Cancel")

        btn_ok = ttk.Button(btn_frame, text=ok_text, command=self.on_ok)
        btn_ok.pack(side=tk.LEFT, padx=5)

        btn_cancel = ttk.Button(btn_frame, text=cancel_text, command=self.on_cancel)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        # Enter = OK, Escape = Cancel
        self.top.bind("<Return>", lambda e: self.on_ok())
        self.top.bind("<Escape>", lambda e: self.on_cancel())

    # ----------- Hotkeys -------------

    def _paste(self, event):
        try:
            text = self.top.clipboard_get()
            self.text.insert(tk.INSERT, text)
        except:
            pass
        return "break"

    def _copy(self, event):
        try:
            selected = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.top.clipboard_clear()
            self.top.clipboard_append(selected)
        except:
            pass
        return "break"

    def _cut(self, event):
        try:
            selected = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.top.clipboard_clear()
            self.top.clipboard_append(selected)
            self.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except:
            pass
        return "break"

    def _select_all(self, event):
        self.text.tag_add(tk.SEL, "1.0", tk.END)
        self.text.mark_set(tk.INSERT, "1.0")
        self.text.see(tk.INSERT)
        return "break"



    def on_ok(self):
        self.result_text = self.text.get("1.0", tk.END).rstrip("\n")
        self.top.destroy()

    def on_cancel(self):
        self.result_text = None
        self.top.destroy()



def main():
    db = NotesDB()
    app = NotesApp(db)
    try:
        app.mainloop()
    finally:
        db.close()

if __name__ == "__main__":
    main()
