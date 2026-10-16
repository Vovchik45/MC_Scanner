import os
import re
import webbrowser
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

try:
    from tkhtmlview import HTMLScrolledText
    TKHTMLVIEW_AVAILABLE = True
except ImportError:
    TKHTMLVIEW_AVAILABLE = False


class HelpWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.title("Нужна помощь")
        self.geometry("1400x1100")
        self.minsize(1000, 800)

        self.transient(parent)
        self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()

    def on_close(self):
        self.grab_release()
        self.destroy()

    def _help_html_path(self):
        rel = self.app.config.get('UI', 'help_path', fallback='assets/help.html')
        if os.path.isabs(rel):
            return rel
        return os.path.join(self.app.app_root, rel)

    def _load_html(self):
        path = self._help_html_path()
        if not os.path.exists(path):
            return "<p>Файл справки не найден.</p>", path
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), path

    def _body_for_viewer(self, full_html):
        """
        tkhtmlview не умеет полный документ / <style> — отдаём только тело.
        """
        match = re.search(r'<body[^>]*>(.*?)</body>', full_html, flags=re.IGNORECASE | re.DOTALL)
        body = match.group(1) if match else full_html
        # Убираем комментарии и пустоту
        body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL).strip()
        if not body:
            body = '<p>Описание пока не заполнено. Отредактируйте файл help.html.</p>'
        return body

    def _open_in_browser(self):
        path = self._help_html_path()
        if not os.path.exists(path):
            return
        webbrowser.open(path)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X)

        self.app.add_logo(header)

        info = ttk.Frame(header)
        info.grid(row=0, column=1, sticky='w', padx=(15, 0))

        ttk.Label(info, text=f"Версия {self.app.version}",
                  font=("Arial", 9), foreground="gray").pack(anchor=tk.W)
        ttk.Label(info, text=f"Автор: {self.app.author}",
                  font=("Arial", 9), foreground="gray").pack(anchor=tk.W)
        ttk.Label(info, text=f"Контакты: {self.app.contacts}",
                  font=("Arial", 9), foreground="gray").pack(anchor=tk.W)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        title_row = ttk.Frame(main_frame)
        title_row.pack(fill=tk.X)
        ttk.Label(title_row, text="Описание:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(title_row, text="Открыть в браузере",
                   command=self._open_in_browser).pack(side=tk.RIGHT)

        html_content, html_path = self._load_html()
        body_html = self._body_for_viewer(html_content)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        if TKHTMLVIEW_AVAILABLE:
            viewer = HTMLScrolledText(content_frame, html=body_html)
            viewer.pack(fill=tk.BOTH, expand=True)
            # После упаковки иногда нужно повторно задать html
            viewer.set_html(body_html)
        else:
            viewer = ScrolledText(content_frame, wrap=tk.WORD, height=20)
            viewer.insert('1.0', body_html)
            viewer.configure(state='disabled')
            viewer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Файл: {html_path}",
                  font=("Arial", 8), foreground="gray").pack(anchor=tk.W)

        ttk.Button(main_frame, text="Закрыть", command=self.on_close).pack(pady=(10, 0))
