import tkinter as tk
from tkinter import ttk
from locales import t, LOCALES


class NoteDialog:
    def __init__(self, parent, title="Note", initial_text="", locale="ru"):
        self.parent = parent
        self.locale = locale
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.grab_set()

        self.result_text = None

        self.text = tk.Text(self.top, width=60, height=15, wrap=tk.WORD)
        self.text.pack(padx=10, pady=10)
        self.text.insert("1.0", initial_text)
        self.text.focus_set()

        # бинды Ctrl+V/C/X/A
        self.text.bind("<Control-v>", self._paste)
        self.text.bind("<Control-c>", self._copy)
        self.text.bind("<Control-x>", self._cut)
        self.text.bind("<Control-a>", self._select_all)

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(pady=(0, 10))

        btn_ok = ttk.Button(btn_frame, text="OK", command=self.on_ok)
        btn_ok.pack(side=tk.LEFT, padx=5)

        btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.on_cancel)
        btn_cancel.pack(side=tk.LEFT, padx=5)

        self.top.bind("<Return>", lambda e: self.on_ok())
        self.top.bind("<Escape>", lambda e: self.on_cancel())

    def _paste(self, event):
        try:
            self.text.insert(tk.INSERT, self.top.clipboard_get())
        except:
            pass
        return "break"

    def _copy(self, event):
        try:
            sel = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.top.clipboard_clear()
            self.top.clipboard_append(sel)
        except:
            pass
        return "break"

    def _cut(self, event):
        try:
            sel = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.top.clipboard_clear()
            self.top.clipboard_append(sel)
            self.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except:
            pass
        return "break"

    def _select_all(self, event):
        self.text.tag_add(tk.SEL, "1.0", tk.END)
        return "break"

    def on_ok(self):
        self.result_text = self.text.get("1.0", tk.END).strip()
        self.top.destroy()

    def on_cancel(self):
        self.result_text = None
        self.top.destroy()
