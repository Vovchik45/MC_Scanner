import os
import configparser
import tkinter as tk
from tkinter import ttk
import pyttsx3
import threading
from PIL import Image, ImageTk

from .windows import (
    NewFileWindow,
    NewCsvFileWindow,
    FileCheckWindow,
    UpdCheckWindow,
    BoxCollectionWindow,
    PrintBarcodeWindow,
    HelpWindow,
)

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StringCollectorApp:
    def __init__(self, root):
        self.root = root
        self.version = "1.16"
        self.author = "Борисов Владимир"
        self.contacts = "@MC_1C"
        self.root.title(f"MC_Сканер - Версия {self.version}")
        self.collected_strings = set()
        self.current_strings = []
        self.app_root = APP_ROOT

        self.config = configparser.ConfigParser()
        self.load_config()
        self.enable_chz = self.config.getboolean('FEATURES', 'enable_chz', fallback=False)

        self.trueapi_client = None
        if self.enable_chz:
            from .api_clients import TrueApiClient
            self.trueapi_client = TrueApiClient()

        self.tts_engine = pyttsx3.init()
        self.setup_tts()

        self.create_main_interface()

    def load_config(self):
        config_path = os.path.join(self.app_root, 'config.ini')
        if os.path.exists(config_path):
            self.config.read(config_path, encoding='utf-8')
        if not self.config.has_section('FEATURES'):
            self.config['FEATURES'] = {'enable_chz': 'false'}
        if not self.config.has_section('UI'):
            self.config['UI'] = {
                'logo_path': 'assets/logo.png',
                'logo_width': '180',
                'help_path': 'assets/help.html',
            }

    def get_data_dir(self, folder_name):
        """Возвращает путь data/<folder_name>, создаёт папки при необходимости."""
        data_root = os.path.join(self.app_root, 'data')
        target = os.path.join(data_root, folder_name)
        os.makedirs(target, exist_ok=True)
        return target

    def get_export_dir(self):
        """Папка по умолчанию для выпуска продукции."""
        return self.get_data_dir('Выпуск')

    def get_assembly_dir(self):
        """Папка по умолчанию для сборки/CSV."""
        return self.get_data_dir('Сборка')

    def get_boxes_dir(self):
        """Папка по умолчанию для файлов коробок."""
        return self.get_data_dir('Коробки')

    def get_barcodes_dir(self):
        """Папка по умолчанию для PDF со штрихкодами."""
        return self.get_data_dir('Штрихкода')

    def show_main_window(self):
        """Показывает главное окно"""
        self.root.deiconify()

    def hide_main_window(self):
        """Скрывает главное окно"""
        self.root.withdraw()

    def create_new_file(self):
        self.hide_main_window()
        NewFileWindow(self.root, self)

    def create_new_csv_file(self):
        self.hide_main_window()
        NewCsvFileWindow(self.root, self)

    def load_and_check_file(self):
        self.hide_main_window()
        FileCheckWindow(self.root, self)

    def check_upd(self):
        self.hide_main_window()
        UpdCheckWindow(self.root, self)

    def collect_boxes(self):
        self.hide_main_window()
        BoxCollectionWindow(self.root, self)

    def print_barcode(self):
        self.hide_main_window()
        PrintBarcodeWindow(self.root, self)

    def show_help(self):
        HelpWindow(self.root, self)

    def setup_tts(self):
        """Настройка синтезатора речи"""
        try:
            voices = self.tts_engine.getProperty('voices')
            russian_voice = None
            for voice in voices:
                if 'russian' in voice.name.lower() or 'russian' in voice.id.lower():
                    russian_voice = voice
                    break

            if russian_voice:
                self.tts_engine.setProperty('voice', russian_voice.id)
            else:
                if voices:
                    self.tts_engine.setProperty('voice', voices[0].id)

            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.8)

        except Exception as e:
            print(f"Ошибка настройки синтезатора речи: {e}")

    def speak(self, text):
        """Произносит текст в отдельном потоке"""
        def speak_thread():
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"Ошибка синтеза речи: {e}")

        thread = threading.Thread(target=speak_thread)
        thread.daemon = True
        thread.start()

    def speak_count(self, count):
        """Озвучивает количество строк"""
        phrases = {
            10: "Десять",
            20: "Двадцать",
            30: "Тридцать",
            40: "Сорок",
            50: "Пятьдесят",
            60: "Шестьдесят",
            70: "Семьдесят",
            80: "Восемьдесят",
            90: "Девяносто",
            100: "Соточка готова",
            150: "Сто пятьдесят",
            200: "Двести"
        }

        if count in phrases:
            self.speak(phrases[count])
        elif count % 10 == 0 and count <= 1000:
            numbers = {
                100: "сто",
                200: "двести",
                300: "триста",
                400: "четыреста",
                500: "пятьсот",
                600: "шестьсот",
                700: "семьсот",
                800: "восемьсот",
                900: "девятьсот",
                1000: "тысяча"
            }
            if count in numbers:
                self.speak(numbers[count])

    def add_logo(self, parent):
        try:
            logo_rel = self.config.get('UI', 'logo_path', fallback='assets/logo.png')
            logo_path = logo_rel if os.path.isabs(logo_rel) else os.path.join(self.app_root, logo_rel)
            width = self.config.getint('UI', 'logo_width', fallback=180)

            image = Image.open(logo_path)
            orig_w, orig_h = image.size
            if orig_w <= 0:
                raise ValueError("Некорректный размер логотипа")
            height = max(1, round(orig_h * (width / orig_w)))
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            logo_label = ttk.Label(parent, image=photo)
            logo_label.image = photo
            logo_label.grid(row=0, column=0, pady=(0, 10))
        except Exception as e:
            print(f"Не удалось загрузить логотип: {e}")

    def replace_gs(self, text):
        return text.replace('<GS>', chr(29))

    def is_sscc(self, text):
        """Проверяет, является ли строка SSCC (18 цифр или AI 00 + 18 цифр)."""
        if not text:
            return False
        cleaned = text.strip()
        if cleaned.startswith('00') and len(cleaned) == 20 and cleaned[2:].isdigit():
            return True
        return len(cleaned) == 18 and cleaned.isdigit()

    def normalize_sscc(self, text):
        """Возвращает 18-значный SSCC без AI-префикса 00."""
        cleaned = text.strip()
        if cleaned.startswith('00') and len(cleaned) == 20 and cleaned[2:].isdigit():
            return cleaned[2:]
        return cleaned

    def is_full_sgtin(self, parsed_data):
        """
        Полный КМ Честного знака:
        GTIN (01) + SN (21) + криптохвост (92 / 93 / 94).
        Ключ проверки (91) опционален (для короткого формата 93 часто без 91).
        """
        return bool(
            parsed_data
            and parsed_data.get('gtin')
            and parsed_data.get('sn')
            and parsed_data.get('crypto_tail')
        )

    def classify_code(self, text):
        """
        Классифицирует отсканированную строку.
        Возвращает ('SGTIN', parsed_data) | ('SSCC', normalized_sscc) | (None, None).
        """
        parsed = self.parse_gs1_string(text)
        if self.is_full_sgtin(parsed):
            return 'SGTIN', parsed
        if self.is_sscc(text):
            return 'SSCC', self.normalize_sscc(text)
        return None, None

    def _empty_gs1_result(self):
        return {
            'gtin': None,
            'sn': None,
            'check_code': None,
            'crypto_tail': None,
            'crypto_ai': None,
        }

    def parse_gs1_string(self, gs1_string):
        """
        Парсит строку GS1 и извлекает AI коды.
        Криптохвост: AI 92, 93 или 94.
        """
        try:
            from gs1 import parse
            parsed = parse(gs1_string)

            result = self._empty_gs1_result()

            for ai in parsed:
                if ai.ai == '01':
                    result['gtin'] = ai.value
                elif ai.ai == '21':
                    result['sn'] = ai.value
                elif ai.ai == '91':
                    result['check_code'] = ai.value
                elif ai.ai in ('92', '93', '94'):
                    result['crypto_tail'] = ai.value
                    result['crypto_ai'] = ai.ai

            return result
        except ImportError:
            return self.simple_gs1_parse(gs1_string)
        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            return self._empty_gs1_result()

    def simple_gs1_parse(self, gs1_string):
        """
        Парсер GS1: 01, 21, 91, 92/93/94 (криптохвост).
        """
        result = self._empty_gs1_result()

        working_string = gs1_string
        gs_char = chr(29)

        while working_string:
            if len(working_string) < 2:
                break

            ai = working_string[:2]
            remaining = working_string[2:]

            if ai == '01':
                if len(remaining) >= 14:
                    result['gtin'] = remaining[:14]
                    working_string = remaining[14:]
                else:
                    break

            elif ai == '21':
                gs_pos = remaining.find(gs_char)
                if gs_pos != -1:
                    result['sn'] = remaining[:gs_pos]
                    working_string = remaining[gs_pos + 1:]
                else:
                    result['sn'] = remaining
                    working_string = ""

            elif ai == '91':
                gs_pos = remaining.find(gs_char)
                if gs_pos != -1:
                    result['check_code'] = remaining[:gs_pos]
                    working_string = remaining[gs_pos + 1:]
                else:
                    result['check_code'] = remaining
                    working_string = ""

            elif ai in ('92', '93', '94'):
                gs_pos = remaining.find(gs_char)
                if gs_pos != -1:
                    result['crypto_tail'] = remaining[:gs_pos]
                    working_string = remaining[gs_pos + 1:]
                else:
                    result['crypto_tail'] = remaining
                    working_string = ""
                result['crypto_ai'] = ai

            else:
                gs_pos = remaining.find(gs_char)
                if gs_pos != -1:
                    working_string = remaining[gs_pos + 1:]
                else:
                    working_string = ""

        return result

    def create_main_interface(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.add_logo(main_frame)

        version_label = ttk.Label(main_frame, text=f"Версия {self.version}",
                                 font=("Arial", 8), foreground="gray")
        version_label.grid(row=1, column=0, sticky='w', pady=(0, 0))

        author_label = ttk.Label(main_frame, text=f"Автор: {self.author}",
                                 font=("Arial", 8), foreground="gray")
        author_label.grid(row=2, column=0, sticky='w')

        contacts_label = ttk.Label(main_frame, text=f"Контакты: {self.contacts}",
                                   font=("Arial", 8), foreground="gray")
        contacts_label.grid(row=3, column=0, sticky='w')

        help_link = tk.Label(
            main_frame,
            text="Перейти на удобное ПО",
            font=("Arial", 8, "underline"),
            foreground="#0563C1",
            cursor="hand2",
        )
        help_link.grid(row=4, column=0, sticky='w', pady=(2, 10))
        help_link.bind("<Button-1>", lambda e: self.show_help())

        ttk.Button(main_frame, text="1) Собрать новый файл выпуска продукции",
                  command=self.create_new_file).grid(row=5, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="2) Собрать новый файл csv",
                  command=self.create_new_csv_file).grid(row=6, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="3) Загрузить и проверить файл",
                  command=self.load_and_check_file).grid(row=7, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="4) Проверить поступление по УПД",
                  command=self.check_upd).grid(row=8, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="5) Собрать коробки",
                  command=self.collect_boxes).grid(row=9, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="6) Печать штрихкода гофроящика",
                  command=self.print_barcode).grid(row=10, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="7) Нужна помощь",
                  command=self.show_help).grid(row=11, column=0, pady=5, sticky='ew')
        ttk.Button(main_frame, text="8) Выход",
                  command=self.root.destroy).grid(row=12, column=0, pady=5, sticky='ew')
