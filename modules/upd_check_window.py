import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .upd_parser import parse_upd


class UpdCheckWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.title("Проверка поступления по УПД")
        self.geometry("1100x700")

        self.codes = []
        self.by_key = {}
        self.checked_count = 0
        self.extra_count = 0
        self._all_found_announced = False

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()

    def on_close(self):
        self.app.show_main_window()
        self.destroy()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.doc_label = ttk.Label(main_frame, text="Документ не загружен", foreground="gray")
        self.doc_label.pack(anchor=tk.W)

        self.parties_label = ttk.Label(main_frame, text="", foreground="gray")
        self.parties_label.pack(anchor=tk.W, pady=(0, 6))

        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=5)

        ttk.Label(stats_frame, text="Кодов в УПД:").grid(row=0, column=0, sticky=tk.W)
        self.total_label = ttk.Label(stats_frame, text="0")
        self.total_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))

        ttk.Label(stats_frame, text="Найдено:").grid(row=0, column=2, sticky=tk.W)
        self.found_label = ttk.Label(stats_frame, text="0")
        self.found_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 20))

        ttk.Label(stats_frame, text="Осталось:").grid(row=0, column=4, sticky=tk.W)
        self.remaining_label = ttk.Label(stats_frame, text="0")
        self.remaining_label.grid(row=0, column=5, sticky=tk.W, padx=(5, 20))

        ttk.Label(stats_frame, text="Лишние:").grid(row=0, column=6, sticky=tk.W)
        self.extra_label = ttk.Label(stats_frame, text="0")
        self.extra_label.grid(row=0, column=7, sticky=tk.W, padx=5)

        ttk.Button(main_frame, text="Загрузить УПД (XML)",
                  command=self.load_file).pack(pady=5, anchor=tk.W)

        content_frame = ttk.LabelFrame(main_frame, text="Коды маркировки из УПД (короткий вид 01+21)")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.create_table(content_frame)

        check_frame = ttk.LabelFrame(main_frame, text="Сканируйте полный код маркировки")
        check_frame.pack(fill=tk.X, pady=5)

        self.check_entry = tk.Text(check_frame, height=3, width=70)
        self.check_entry.pack(fill=tk.X, padx=5, pady=5)
        self.check_entry.bind('<Return>', lambda e: self.check_string() or "break")

        ttk.Button(check_frame, text="Проверить код",
                  command=self.check_string).pack(pady=5)

        self.result_label = ttk.Label(check_frame, text="", foreground="blue")
        self.result_label.pack(pady=5)

    def create_table(self, parent):
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('#', 'Товар', 'Артикул', 'GTIN (01)', 'SN (21)', 'Статус')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=16)

        self.tree.heading('#', text='#')
        self.tree.heading('Товар', text='Товар')
        self.tree.heading('Артикул', text='Артикул')
        self.tree.heading('GTIN (01)', text='GTIN (01)')
        self.tree.heading('SN (21)', text='SN (21)')
        self.tree.heading('Статус', text='Статус')

        self.tree.column('#', width=50, stretch=False)
        self.tree.column('Товар', width=360)
        self.tree.column('Артикул', width=110, stretch=False)
        self.tree.column('GTIN (01)', width=140, stretch=False)
        self.tree.column('SN (21)', width=120, stretch=False)
        self.tree.column('Статус', width=110, stretch=False)

        self.tree.tag_configure('found', background='#d9f2d9')

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _initial_dir(self):
        docs = os.path.join(self.app.app_root, 'docs')
        if os.path.isdir(docs):
            return docs
        return self.app.app_root

    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите электронный УПД",
            initialdir=self._initial_dir(),
            filetypes=[("УПД XML", "*.xml"), ("Все файлы", "*.*")],
        )
        if not file_path:
            return

        try:
            document = parse_upd(file_path)
        except Exception as e:
            self.app.speak("Ошибка загрузки файла")
            messagebox.showerror("Ошибка", f"Не удалось прочитать УПД:\n{str(e)}")
            return

        if not document['codes']:
            messagebox.showwarning("Пустой документ", "В УПД не найдены коды маркировки (КИЗ).")
            return

        self.codes = []
        self.by_key = {}
        self.checked_count = 0
        self.extra_count = 0
        self._all_found_announced = False

        for item in self.tree.get_children():
            self.tree.delete(item)

        skipped = 0
        for raw in document['codes']:
            parsed = self.app.simple_gs1_parse(self.app.replace_gs(raw['kiz']))
            gtin = parsed.get('gtin')
            sn = parsed.get('sn')
            if not gtin or not sn:
                skipped += 1
                continue
            index = len(self.codes)
            row = {
                'name': raw['name'],
                'article': raw['article'],
                'gtin': gtin,
                'sn': sn,
                'checked': False,
            }
            self.codes.append(row)
            self.by_key.setdefault(self._key(gtin, sn), []).append(index)
            self.tree.insert('', tk.END, iid=str(index), values=(
                index + 1,
                row['name'],
                row['article'],
                gtin,
                sn,
                'Не проверен',
            ))

        title = f"УПД № {document['number']} от {document['date']}"
        self.doc_label.config(text=title, foreground="black")
        parties = []
        if document['seller']:
            parties.append(f"Продавец: {document['seller']}")
        if document['buyer']:
            parties.append(f"Покупатель: {document['buyer']}")
        self.parties_label.config(text="   |   ".join(parties))
        self.result_label.config(text="", foreground="blue")
        self.update_stats()

        message = f"Загружено кодов: {len(self.codes)}"
        if skipped:
            message += f"\nПропущено нераспознанных КИЗ: {skipped}"
        self.app.speak(f"Загружено {len(self.codes)} кодов")
        messagebox.showinfo("УПД загружен", message)
        self.check_entry.focus_set()

    def update_stats(self):
        total = len(self.codes)
        self.total_label.config(text=str(total))
        self.found_label.config(text=str(self.checked_count))
        self.remaining_label.config(text=str(total - self.checked_count))
        self.extra_label.config(text=str(self.extra_count))

        if total and self.checked_count == total and not self._all_found_announced:
            self._all_found_announced = True
            self.result_label.config(
                text="Все коды из УПД найдены.",
                foreground="green",
            )
            self.app.root.bell()
            self.app.speak("Все коды найдены!")

    def check_string(self):
        if not self.codes:
            self.app.speak("Сначала загрузите УПД!")
            messagebox.showwarning("Ошибка", "Сначала загрузите УПД!")
            return "break"

        text = self.check_entry.get('1.0', tk.END).strip()
        if not text:
            return "break"

        processed = self.app.replace_gs(text)
        parsed = self.app.simple_gs1_parse(processed)
        gtin = parsed.get('gtin')
        sn = parsed.get('sn')
        self.check_entry.delete('1.0', tk.END)

        if not gtin or not sn:
            self.result_label.config(
                text="Не удалось выделить GTIN и серийный номер из скана.",
                foreground="red",
            )
            self.app.speak("Ошибка парсинга")
            return "break"

        indexes = self.by_key.get(self._key(gtin, sn), [])
        pending = next((i for i in indexes if not self.codes[i]['checked']), None)

        if pending is None and indexes:
            self.result_label.config(
                text=f"Код уже проверен: {gtin} / {sn}",
                foreground="orange",
            )
            self.app.root.bell()
            self.app.speak("Эта строка уже была проверена!")
            self._focus_row(indexes[0])
            return "break"

        if pending is None:
            self.extra_count += 1
            self.result_label.config(
                text=f"Кода нет в УПД: {gtin} / {sn}. Лишних: {self.extra_count}",
                foreground="red",
            )
            self.app.speak("Не верно!")
            self.update_stats()
            return "break"

        row = self.codes[pending]
        row['checked'] = True
        self.checked_count += 1
        self.tree.item(str(pending), values=(
            pending + 1,
            row['name'],
            row['article'],
            row['gtin'],
            row['sn'],
            'Найден',
        ), tags=('found',))
        self._focus_row(pending)
        self.result_label.config(
            text=f"Верно! {row['name']}  {gtin} / {sn}   {self.checked_count}/{len(self.codes)}",
            foreground="green",
        )
        self.app.root.bell()
        self.app.speak("Верно!")
        self.update_stats()
        return "break"

    def _focus_row(self, index):
        item_id = str(index)
        self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        self.tree.see(item_id)

    @staticmethod
    def _key(gtin, sn):
        return f"{gtin}|{sn}"
