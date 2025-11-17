import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from db import NotesDB
from dialogs import NoteDialog
from locales import t
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
from datetime import date, timedelta


class NotesApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.db = NotesDB()
        self.locale = "ru"
        self.sort_order = "DESC"
        self.search_keyword = None

        self.title(t(self.locale, "app_title"))
        self.geometry("900x600")

        self._build_ui()
        self.refresh_notes()

    # ---------- UI ----------
    def _build_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text=t(self.locale, "add"), command=self.on_add).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=t(self.locale, "edit"), command=self.on_edit).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=t(self.locale, "delete"), command=self.on_delete).pack(side=tk.LEFT)

        ttk.Button(toolbar, text=t(self.locale, "sort_asc"), command=lambda: self._set_sort("ASC")).pack(side=tk.LEFT)
        ttk.Button(toolbar, text=t(self.locale, "sort_desc"), command=lambda: self._set_sort("DESC")).pack(side=tk.LEFT)

        self.search_entry = ttk.Entry(toolbar, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar, text=t(self.locale, "search"), command=self.on_search).pack(side=tk.LEFT)

        ttk.Button(toolbar, text=t(self.locale, "stats"), command=self.on_stats).pack(side=tk.RIGHT)

        # main split
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        # left list
        self.listbox = tk.Listbox(main, width=40)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # right text preview
        right = ttk.Frame(main)
        right.pack(fill=tk.BOTH, expand=True)

        self.lbl_created = ttk.Label(right, text="")
        self.lbl_created.pack(anchor="w")

        self.lbl_updated = ttk.Label(right, text="")
        self.lbl_updated.pack(anchor="w")

        self.text_preview = tk.Text(right, wrap=tk.WORD)
        self.text_preview.pack(fill=tk.BOTH, expand=True)
        self.text_preview.config(state=tk.DISABLED)

    # ---------- Actions ----------
    def refresh_notes(self):
        self.listbox.delete(0, tk.END)
        notes = self.db.get_notes(order=self.sort_order, keyword=self.search_keyword)

        if not notes:
            self.listbox.insert(tk.END, t(self.locale, "no_notes"))
            return

        for n in notes:
            nid, text, *_ = n
            preview = text[:50].replace("\n", " ") + "..."
            self.listbox.insert(tk.END, f"{nid}. {preview}")

    def on_select(self, _=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        note_id = int(self.listbox.get(sel).split(".")[0])
        note = self.db.get_note(note_id)

        if note:
            _, text, created, updated, _ = note
            self.text_preview.config(state=tk.NORMAL)
            self.text_preview.delete("1.0", tk.END)
            self.text_preview.insert("1.0", text)
            self.text_preview.config(state=tk.DISABLED)

            self.lbl_created.config(text=f"{t(self.locale,'created_at')} {created}")
            self.lbl_updated.config(text=f"{t(self.locale,'updated_at')} {updated}")

    def on_add(self):
        dlg = NoteDialog(self, title=t(self.locale, "add"), locale=self.locale)
        self.wait_window(dlg.top)
        if dlg.result_text:
            self.db.add_note(dlg.result_text)
            self.refresh_notes()

    def on_edit(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        note_id = int(self.listbox.get(sel).split(".")[0])
        old = self.db.get_note(note_id)

        dlg = NoteDialog(self, title=t(self.locale, "edit"), initial_text=old[1], locale=self.locale)
        self.wait_window(dlg.top)
        if dlg.result_text:
            self.db.update_note(note_id, dlg.result_text)
            self.refresh_notes()

    def on_delete(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        note_id = int(self.listbox.get(sel).split(".")[0])

        if messagebox.askyesno(t(self.locale, "delete"), t(self.locale, "confirm_delete")):
            self.db.delete_note_soft(note_id)
            self.refresh_notes()

    def _set_sort(self, order):
        self.sort_order = order
        self.refresh_notes()

    def on_search(self):
        self.search_keyword = self.search_entry.get().strip()
        self.refresh_notes()

    # ---------- Statistics ----------
    def on_stats(self):
        created, deleted = self.db.stats_counts_by_date(30)

        dates = []
        c_vals = []
        d_vals = []
        today = date.today()

        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            ds = d.isoformat()
            dates.append(d.strftime("%m-%d"))
            c_vals.append(created.get(ds, 0))
            d_vals.append(deleted.get(ds, 0))

        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(dates, c_vals, marker="o", label="Created")
        ax.plot(dates, d_vals, marker="x", label="Deleted")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        plt.close()
        buf.seek(0)

        img = Image.open(buf)
        tk_img = ImageTk.PhotoImage(img)

        win = tk.Toplevel(self)
        win.title(t(self.locale, "stats"))
        lbl = ttk.Label(win, image=tk_img)
        lbl.image = tk_img
        lbl.pack()
