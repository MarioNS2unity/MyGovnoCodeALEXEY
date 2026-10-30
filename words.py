# ==========================================
# === БЛОК 1: ИМПОРТЫ И НАСТРОЙКИ ===
# ==========================================
import os
import sys
import json
import time
import threading
import urllib.request
import urllib.parse
import base64
import io
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw

CONFIG_FILE = "wxd_cloud.json"
TIME_FILE = "app_data_time.json"
CUSTOM_DICT_FILE = "wxd_custom_dict.json"
AFK_TIMEOUT = 10.0  # Секунд бездействия до паузы таймера

# ==========================================
# === БЛОК 1.5: ОБЛАЧНЫЙ СПЕЛЛЧЕКЕР (YANDEX) ===
# ==========================================
class YandexSpellChecker:
    def __init__(self, custom_dict_path):
        self.custom_dict_path = custom_dict_path
        self.custom_words = set()
        self.ignored_words = set()
        self.enabled = True
        self._load_custom_dict()

    def _load_custom_dict(self):
        if os.path.exists(self.custom_dict_path):
            try:
                with open(self.custom_dict_path, "r", encoding="utf-8") as f:
                    words = json.load(f)
                    self.custom_words = set(w.lower() for w in words)
            except Exception:
                self.custom_words = set()

    def save_custom_dict(self):
        try:
            with open(self.custom_dict_path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.custom_words)), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_word(self, word):
        w = word.lower().strip()
        if w:
            self.custom_words.add(w)
            self.save_custom_dict()

    def ignore_word(self, word):
        w = word.lower().strip()
        if w:
            self.ignored_words.add(w)

# ==========================================
# === ФУНКЦИЯ 2: ГЕНЕРАЦИЯ ИКОНКИ ПРИЛОЖЕНИЯ ===
# ==========================================
def generate_wxd_icon():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg_color = (8, 35, 28, 255)
    border_color = (16, 185, 129, 255)
    text_color = (110, 231, 183, 255)
    accent_x = (52, 211, 153, 255)

    draw.rectangle([1, 1, 30, 30], fill=bg_color, outline=border_color, width=2)

    W_letter = ["1100011", "1100011", "1101011", "1101011", "1111111", "0110110", "0100010"]
    x_letter = ["11011", "01110", "00100", "01110", "11011"]
    D_letter = ["111110", "110011", "110011", "110011", "110011", "110011", "111110"]

    def draw_sprite(sprite, sx, sy, col):
        for r, row in enumerate(sprite):
            for c, val in enumerate(row):
                if val == "1":
                    draw.point((sx + c, sy + r), fill=col)

    draw_sprite(W_letter, 4, 11, text_color)
    draw_sprite(x_letter, 13, 13, accent_x)
    draw_sprite(D_letter, 20, 11, text_color)

    for px, py in [(24, 5), (26, 4), (27, 6), (25, 7)]:
        draw.point((px, py), fill=accent_x)

    icon_256 = img.resize((256, 256), Image.Resampling.NEAREST)
    if not os.path.exists("words.ico"):
        try:
            icon_256.save("words.ico", format="ICO", sizes=[(256, 256), (64, 64), (32, 32)])
        except Exception:
            pass
    return icon_256


class WordsApp:
    # ==========================================
    # === ФУНКЦИЯ 3: СТАРТ ПРИЛОЖЕНИЯ (INIT) ===
    # ==========================================
    def __init__(self, root):
        self.root = root
        self.root.title("WxD — 2.4")
        self.root.geometry("1350x820")
        self.root.configure(bg="#18181b")

        icon_img = generate_wxd_icon()
        self.app_icon = ImageTk.PhotoImage(icon_img)
        self.root.iconphoto(False, self.app_icon)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.speller = YandexSpellChecker(CUSTOM_DICT_FILE)

        self.webhook_url = self._load_cloud_url()
        self.tab_texts = {}      # {node_id: text_widget}
        self.tab_frames = {}     # {node_id: frame_widget}
        self.active_node = None
        self.tab_count = 0

        self.total_app_time = self._load_total_time()
        self.last_tick_time = time.time()
        self.last_save_time = time.time()

        self.current_font_family = tk.StringVar(value="Consolas")
        self.current_font_size = tk.IntVar(value=14)

        self._build_ui()
        self._bind_shortcuts()
        self._tick_timer()

        # Запуск с файлом (через двойной клик) или пустой
        if len(sys.argv) > 1:
            filepath = sys.argv[1]
            if os.path.exists(filepath):
                self._load_file(filepath)
            else:
                self._add_tab("📄 Документ 1")
        else:
            self._add_tab("📄 Документ 1")

    # ==========================================
    # === ФУНКЦИЯ: ПЕРЕИМЕНОВАНИЕ И ПЕРЕМЕЩЕНИЕ ===
    # ==========================================
    def _rename_tab(self):
        if not self.active_node:
            return
        current_text = self.tree.item(self.active_node, "text").strip()
        new_name = simpledialog.askstring("Переименовать", "Введите новое название раздела:", initialvalue=current_text)
        if new_name:
            self.tree.item(self.active_node, text=f" {new_name.strip()}")
            self._mark_activity()
            self._record_state(f"Переименовано в: {new_name}")

    def _move_tab(self, direction):
        if not self.active_node:
            return
        parent = self.tree.parent(self.active_node)
        siblings = self.tree.get_children(parent)
        idx = list(siblings).index(self.active_node)

        new_idx = idx + direction
        if 0 <= new_idx < len(siblings):
            self.tree.move(self.active_node, parent, new_idx)
            self._mark_activity()
            self._record_state("Перемещение вкладки")

    # ==========================================
    # === БЛОК 4: ЗАГРУЗКА И СОХРАНЕНИЕ ДАННЫХ ===
    # ==========================================
    def _load_cloud_url(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f).get("webhook_url", "")
            except Exception:
                return ""
        return ""

    def _save_cloud_url(self, url):
        self.webhook_url = url.strip()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"webhook_url": self.webhook_url}, f)
        except Exception:
            pass

    def _load_total_time(self):
        if os.path.exists(TIME_FILE):
            try:
                with open(TIME_FILE, "r", encoding="utf-8") as f:
                    return float(json.load(f).get("total_seconds", 0.0))
            except Exception:
                return 0.0
        return 0.0

    def _save_total_time(self):
        try:
            with open(TIME_FILE, "w", encoding="utf-8") as f:
                json.dump({"total_seconds": self.total_app_time}, f)
        except Exception:
            pass

    def _on_close(self):
        self._save_total_time()
        self.speller.save_custom_dict()
        self.root.destroy()

    def _format_seconds(self, sec):
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    # ==========================================
    # === ФУНКЦИЯ 5: УМНЫЙ ТАЙМЕР АКТИВНОСТИ ===
    # ==========================================
    def _mark_activity(self, text_widget=None):
        if not text_widget:
            text_widget = self._get_active_text()
        if text_widget:
            text_widget.last_activity = time.time()

    def _tick_timer(self):
        now = time.time()
        delta = now - self.last_tick_time
        self.last_tick_time = now

        active = self._get_active_text()
        is_working = False

        if active:
            if (now - active.last_activity) <= AFK_TIMEOUT:
                active.active_seconds += delta
                self.total_app_time += delta
                is_working = True

        if now - self.last_save_time >= 30:
            self._save_total_time()
            self.last_save_time = now

        tot_h, tot_rem = divmod(int(self.total_app_time), 3600)
        tot_m, tot_s = divmod(tot_rem, 60)
        total_str = f"{tot_h:02d}:{tot_m:02d}:{tot_s:02d}"
        now_str = time.strftime("%H:%M:%S")

        if active:
            sess_str = self._format_seconds(active.active_seconds)
            status_icon = "🔥 В работе:" if is_working else "💤 Пауза:"
            timer_fg = "#34d399" if is_working else "#71717a"
            self.timer_label.configure(
                text=f"{status_icon} {sess_str}  |  🌍 Всего: {total_str}  |  🕒 {now_str}",
                fg=timer_fg
            )
        else:
            self.timer_label.configure(text=f"⏱ Вкладка: --:--  |  🌍 Всего: {total_str}  |  🕒 {now_str}")

        self.root.after(1000, self._tick_timer)

    # ==========================================
    # === ФУНКЦИЯ 6: ОТРИСОВКА ИНТЕРФЕЙСА (UI) ===
    # ==========================================
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background="#27272a", foreground="#e4e4e7", borderwidth=0, padding=6)
        style.map("TButton", background=[("active", "#10b981")])

        style.configure("Treeview", background="#121215", foreground="#e4e4e7", fieldbackground="#121215",
                        borderwidth=0, rowheight=32, font=("Segoe UI Emoji", 10))
        style.map("Treeview", background=[("selected", "#065f46")], foreground=[("selected", "#34d399")])

        top = tk.Frame(self.root, bg="#09090b", height=48, padx=10, pady=6)
        top.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top, text="WxD", fg="#34d399", bg="#09090b", font=("Consolas", 13, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(top, text="➕ Раздел", command=lambda: self._add_tab()).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="↳ Под-вкладка", command=self._add_subtab).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="❌ Удалить", command=self._close_tab).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Open", command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Save .TXT", command=self._save_txt).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="✏ Rename", command=self._rename_tab).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="⬆ Up", command=lambda: self._move_tab(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="⬇ Down", command=lambda: self._move_tab(1)).pack(side=tk.LEFT, padx=2)

        push_btn = tk.Button(top, text="☁ Push", bg="#10b981", fg="#09090b",
                             relief=tk.FLAT, font=("Sans", 9, "bold"), padx=10, pady=4, command=self._push_to_cloud)
        push_btn.pack(side=tk.LEFT, padx=(10, 2))

        pull_btn = tk.Button(top, text="⬇ Pull GDoc", bg="#059669", fg="white",
                             relief=tk.FLAT, font=("Sans", 9, "bold"), padx=10, pady=4, command=self._pull_from_cloud)
        pull_btn.pack(side=tk.LEFT, padx=2)

        cfg_btn = tk.Button(top, text="⚙ Link", bg="#27272a", fg="#34d399",
                            relief=tk.FLAT, font=("Sans", 9), padx=6, pady=4, command=self._configure_cloud)
        cfg_btn.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Button(top, text="⬅ Undo", command=self._undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Redo ➡", command=self._redo).pack(side=tk.LEFT, padx=2)

        self.timer_label = tk.Label(top, text="", fg="#34d399", bg="#09090b",
                                    font=("Consolas", 10, "bold"), padx=10, pady=4)
        self.timer_label.pack(side=tk.RIGHT)

        fmt = tk.Frame(self.root, bg="#121215", height=40, padx=10, pady=5)
        fmt.pack(side=tk.TOP, fill=tk.X)

        tk.Label(fmt, text="Font:", fg="#a1a1aa", bg="#121215").pack(side=tk.LEFT, padx=(0, 4))
        fonts = ["Consolas", "Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"]
        ttk.OptionMenu(fmt, self.current_font_family, "Consolas", *fonts, command=self._update_base_font).pack(side=tk.LEFT, padx=4)

        tk.Label(fmt, text="Size:", fg="#a1a1aa", bg="#121215").pack(side=tk.LEFT, padx=(8, 4))
        spin = tk.Spinbox(fmt, from_=8, to=72, textvariable=self.current_font_size, width=4,
                          bg="#27272a", fg="white", relief=tk.FLAT, command=self._update_base_font)
        spin.pack(side=tk.LEFT, padx=4)
        spin.bind("<Return>", lambda e: self._update_base_font())

        ttk.Button(fmt, text="B", command=lambda: self._toggle_tag("bold")).pack(side=tk.LEFT, padx=3)
        ttk.Button(fmt, text="I", command=lambda: self._toggle_tag("italic")).pack(side=tk.LEFT, padx=3)
        ttk.Button(fmt, text="U", command=lambda: self._toggle_tag("underline")).pack(side=tk.LEFT, padx=3)
        ttk.Button(fmt, text="🎨 Color", command=self._color_text).pack(side=tk.LEFT, padx=(10, 3))
        ttk.Button(fmt, text="🖍 Highlight", command=self._highlight_text).pack(side=tk.LEFT, padx=3)
        ttk.Button(fmt, text="• List", command=self._insert_bullet).pack(side=tk.LEFT, padx=6)

        # Кнопки управления орфографией
        self.spell_btn = tk.Button(fmt, text="🔤 Орфография: ВКЛ", bg="#065f46", fg="#34d399",
                                   relief=tk.FLAT, font=("Sans", 9, "bold"), padx=8, pady=3, command=self._toggle_spellcheck)
        self.spell_btn.pack(side=tk.LEFT, padx=(10, 3))

        ttk.Button(fmt, text="📖 Мой словарь", command=self._add_word_dialog).pack(side=tk.LEFT, padx=3)

        self.cloud_status = tk.Label(fmt, text="☁ Cloud: Ready" if self.webhook_url else "☁ Cloud: Not linked",
                                     fg="#34d399" if self.webhook_url else "#71717a", bg="#121215", font=("Consolas", 9))
        self.cloud_status.pack(side=tk.RIGHT, padx=10)

        # --- ЛЕВАЯ ПАНЕЛЬ: ВЕРТИКАЛЬНЫЕ ВКЛАДКИ (ДЕРЕВО) ---
        left_sidebar = tk.Frame(self.root, bg="#121215", width=260, padx=6, pady=10)
        left_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        left_sidebar.pack_propagate(False)

        tk.Label(left_sidebar, text="ВКЛАДКИ В ДОКУМЕНТЕ", fg="#a1a1aa", bg="#121215", font=("Sans", 8, "bold")).pack(anchor="w", padx=4, pady=(0, 6))

        tree_scroll = tk.Scrollbar(left_sidebar, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(left_sidebar, show="tree", selectmode="browse", yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # --- ПРАВАЯ ПАНЕЛЬ: СТАТИСТИКА И ИСТОРИЯ ---
        right = tk.Frame(self.root, bg="#09090b", width=270, padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(right, text="TAB STATS", fg="#a1a1aa", bg="#09090b", font=("Sans", 9, "bold")).pack(anchor="w")
        self.stats_label = tk.Label(right, text="Words: 0  |  Chars: 0  |  Lines: 1", fg="#e4e4e7", bg="#18181b",
                                    font=("Consolas", 10), padx=8, pady=8, anchor="w", justify=tk.LEFT)
        self.stats_label.pack(fill=tk.X, pady=(4, 12))

        tk.Label(right, text="QUICK TEMPLATES", fg="#a1a1aa", bg="#09090b", font=("Sans", 9, "bold")).pack(anchor="w", pady=(0, 4))
        t_frame = tk.Frame(right, bg="#09090b")
        t_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(t_frame, text="📋 План", command=self._insert_plan_template).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(t_frame, text="🎮 GDD", command=self._insert_gdd_template).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        t_frame.columnconfigure(0, weight=1)
        t_frame.columnconfigure(1, weight=1)

        tk.Label(right, text="TAB HISTORY", fg="#34d399", bg="#09090b", font=("Sans", 9, "bold")).pack(anchor="w")
        hist_frame = tk.Frame(right, bg="#18181b")
        hist_frame.pack(fill=tk.BOTH, expand=True, pady=4)
        scrollbar = tk.Scrollbar(hist_frame, orient=tk.VERTICAL)
        self.history_listbox = tk.Listbox(hist_frame, bg="#18181b", fg="#e4e4e7", selectbackground="#059669",
                                          font=("Consolas", 9), relief=tk.FLAT, exportselection=False,
                                          yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)

        # --- ЦЕНТРАЛЬНАЯ ЧАСТЬ: ЗОНА РЕДАКТИРОВАНИЯ ---
        self.editor_container = tk.Frame(self.root, bg="#18181b", padx=15, pady=10)
        self.editor_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ==========================================
    # === БЛОК 7: УПРАВЛЕНИЕ ВЕРТИКАЛЬНЫМИ ВКЛАДКАМИ ===
    # ==========================================
    def _add_tab(self, title=None, parent_node="", tab_id=None):
        self.tab_count += 1
        if not title:
            title = f"📄 Документ {self.tab_count}"

        frame = tk.Frame(self.editor_container, bg="#0f0f12")
        text_scroll = tk.Scrollbar(frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            frame, bg="#0f0f12", fg="#f4f4f5", insertbackground="#34d399",
            selectbackground="#065f46", font=(self.current_font_family.get(), self.current_font_size.get()),
            wrap=tk.WORD, padx=35, pady=30, relief=tk.FLAT, undo=False, yscrollcommand=text_scroll.set
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=text_widget.yview)

        text_widget.history = []
        text_widget.history_pos = -1
        text_widget.active_seconds = 0.0
        text_widget.last_activity = time.time()
        text_widget.is_replaying = False
        text_widget._typing_job = None
        text_widget._spell_job = None
        text_widget.gdoc_tab_id = tab_id
        text_widget.image_refs = []
        text_widget.image_b64_map = {}
        text_widget.spell_suggestions = {}

        text_widget.bind("<KeyRelease>", lambda e: self._on_key_release(e, text_widget))
        text_widget.bind("<ButtonRelease-1>", lambda e: self._mark_activity(text_widget))
        text_widget.bind("<Button-3>", lambda e: self._show_context_menu(e, text_widget))

        node_id = self.tree.insert(parent_node, tk.END, text=f" {title}", open=True)
        self.tab_texts[node_id] = text_widget
        self.tab_frames[node_id] = frame

        self.tree.selection_set(node_id)
        self._switch_to_node(node_id)
        self._setup_tags(text_widget)
        self._record_state("Создана вкладка", text_widget)
        self._update_stats()
        return node_id

    def _add_subtab(self):
        sel = self.tree.selection()
        parent = sel[0] if sel else ""
        self._add_tab("📝 Под-вкладка", parent_node=parent)

    def _switch_to_node(self, node_id):
        if self.active_node and self.active_node in self.tab_frames:
            self.tab_frames[self.active_node].pack_forget()
        self.active_node = node_id
        if node_id in self.tab_frames:
            self.tab_frames[node_id].pack(fill=tk.BOTH, expand=True)
        self._update_stats()
        self._refresh_history_ui()
        active = self._get_active_text()
        if active:
            self._run_spellcheck(active)

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            self._switch_to_node(sel[0])

    def _close_tab(self):
        if not self.active_node:
            return
        if len(self.tab_texts) <= 1:
            messagebox.showinfo("WxD", "Нельзя удалить последнюю вкладку!")
            return

        if messagebox.askyesno("Удалить вкладку", "Точно закрыть эту вкладку (и все её под-вкладки)?"):
            def delete_recursive(node):
                for child in self.tree.get_children(node):
                    delete_recursive(child)
                if node in self.tab_frames:
                    self.tab_frames[node].destroy()
                    del self.tab_frames[node]
                if node in self.tab_texts:
                    del self.tab_texts[node]

            target = self.active_node
            delete_recursive(target)
            self.tree.delete(target)
            remaining = list(self.tab_texts.keys())
            if remaining:
                self.tree.selection_set(remaining[0])
                self._switch_to_node(remaining[0])

    def _get_active_text(self):
        if self.active_node:
            return self.tab_texts.get(self.active_node)
        return None

    def _setup_tags(self, text_widget=None):
        if not text_widget:
            text_widget = self._get_active_text()
        if not text_widget:
            return
        f_fam = self.current_font_family.get()
        try:
            f_sz = int(self.current_font_size.get())
        except ValueError:
            f_sz = 14
        text_widget.configure(font=(f_fam, f_sz))
        text_widget.tag_configure("bold", font=(f_fam, f_sz, "bold"))
        text_widget.tag_configure("italic", font=(f_fam, f_sz, "italic"))
        text_widget.tag_configure("underline", underline=True)
        # Фикс для Windows: красное выделение с фоном
        text_widget.tag_configure("misspelled", underline=True, foreground="#ef4444", background="#450a0a")

    def _update_base_font(self, *args):
        for tw in self.tab_texts.values():
            self._setup_tags(tw)
        active = self._get_active_text()
        if active:
            self._mark_activity(active)
            self._record_state(f"Шрифт: {self.current_font_family.get()}", active)

    def _bind_shortcuts(self):
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        self.root.bind("<Control-b>", lambda e: self._toggle_tag("bold"))
        self.root.bind("<Control-i>", lambda e: self._toggle_tag("italic"))
        self.root.bind("<Control-u>", lambda e: self._toggle_tag("underline"))
        self.root.bind("<Control-S>", lambda e: self._push_to_cloud())
        self.root.bind("<Control-s>", lambda e: self._push_to_cloud())
        self.root.bind("<Control-w>", lambda e: self._close_tab())

    # ==========================================
    # === БЛОК 7.5: ЛОГИКА ПРОВЕРКИ YANDEX ===
    # ==========================================
    def _toggle_spellcheck(self):
        self.speller.enabled = not self.speller.enabled
        if self.speller.enabled:
            self.spell_btn.configure(text="🔤 Орфография: ВКЛ", bg="#065f46", fg="#34d399")
            active = self._get_active_text()
            if active:
                self._run_spellcheck(active)
        else:
            self.spell_btn.configure(text="🔤 Орфография: ВЫКЛ", bg="#27272a", fg="#a1a1aa")
            for tw in self.tab_texts.values():
                tw.tag_remove("misspelled", "1.0", tk.END)

    def _add_word_dialog(self):
        word = simpledialog.askstring(
            "Пользовательский словарь",
            f"Слов в твоём словаре: {len(self.speller.custom_words)}\n\nВведи новое слово (на любом языке), чтобы добавить его в словарь:"
        )
        if word:
            self.speller.add_word(word)
            active = self._get_active_text()
            if active:
                self._run_spellcheck(active)

    def _run_spellcheck(self, text_widget=None):
        if not text_widget:
            text_widget = self._get_active_text()
        if not text_widget:
            return

        if not self.speller.enabled:
            text_widget.tag_remove("misspelled", "1.0", tk.END)
            return

        content = text_widget.get("1.0", "end-1c")
        if not content.strip():
            text_widget.tag_remove("misspelled", "1.0", tk.END)
            return

        def worker():
            try:
                url = "https://speller.yandex.net/services/spellservice.json/checkText"
                data = urllib.parse.urlencode({
                    'text': content,
                    'lang': 'ru,en',
                    'options': 14  # IGNORE_DIGITS + IGNORE_URLS + IGNORE_CAPITALIZATION
                }).encode('utf-8')

                req = urllib.request.Request(url, data=data, method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    errors = json.loads(resp.read().decode('utf-8'))

                self.root.after(0, lambda: self._apply_yandex_errors(text_widget, errors, content))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_yandex_errors(self, text_widget, errors, original_content):
        current_content = text_widget.get("1.0", "end-1c")
        if abs(len(current_content) - len(original_content)) > 20:
            return

        text_widget.tag_remove("misspelled", "1.0", tk.END)
        text_widget.spell_suggestions = {}

        for err in errors:
            word = err['word']
            sugs = err['s']

            w_low = word.lower()
            if w_low in self.speller.custom_words or w_low in self.speller.ignored_words:
                continue

            start_idx = f"{err['row'] + 1}.{err['col']}"
            end_idx = f"{start_idx} + {err['len']} chars"

            try:
                actual_word = text_widget.get(start_idx, end_idx)
                if actual_word == word:
                    text_widget.tag_add("misspelled", start_idx, end_idx)
                    text_widget.spell_suggestions[word] = sugs
            except tk.TclError:
                pass

    def _show_context_menu(self, event, text_widget):
        index = text_widget.index(f"@{event.x},{event.y}")
        word_start = text_widget.index(f"{index} wordstart")
        word_end = text_widget.index(f"{index} wordend")
        word = text_widget.get(word_start, word_end).strip()

        menu = tk.Menu(self.root, tearoff=0, bg="#18181b", fg="#e4e4e7",
                       activebackground="#059669", activeforeground="white", font=("Sans", 10))

        if word and "misspelled" in text_widget.tag_names(index):
            suggestions = getattr(text_widget, "spell_suggestions", {}).get(word, [])

            if suggestions:
                menu.add_command(label=f"🔍 Варианты для «{word}»:", state=tk.DISABLED)
                for sug in suggestions[:5]:
                    menu.add_command(
                        label=f"   👉 {sug}",
                        command=lambda s=sug, ws=word_start, we=word_end: self._replace_word(text_widget, ws, we, s)
                    )
            else:
                menu.add_command(label="Нет вариантов замены", state=tk.DISABLED)

            menu.add_separator()
            menu.add_command(
                label=f"➕ Добавить «{word}» в мой словарь",
                command=lambda w=word: self._add_to_dict_and_recheck(w, text_widget)
            )
            menu.add_command(
                label=f"👁 Игнорировать «{word}»",
                command=lambda w=word: self._ignore_and_recheck(w, text_widget)
            )
            menu.add_separator()

        menu.add_command(label="📋 Копировать", command=lambda: text_widget.event_generate("<<Copy>>"))
        menu.add_command(label="📥 Вставить", command=lambda: text_widget.event_generate("<<Paste>>"))
        menu.add_command(label="✂ Вырезать", command=lambda: text_widget.event_generate("<<Cut>>"))

        menu.tk_popup(event.x_root, event.y_root)

    def _replace_word(self, text_widget, start, end, replacement):
        text_widget.delete(start, end)
        text_widget.insert(start, replacement)
        self._mark_activity(text_widget)
        self._run_spellcheck(text_widget)
        self._record_state(f"Исправлено: {replacement}", text_widget)

    def _add_to_dict_and_recheck(self, word, text_widget):
        self.speller.add_word(word)
        self._mark_activity(text_widget)
        self._run_spellcheck(text_widget)

    def _ignore_and_recheck(self, word, text_widget):
        self.speller.ignore_word(word)
        self._mark_activity(text_widget)
        self._run_spellcheck(text_widget)

    # ==========================================
    # === БЛОК 8: СИНХРОНИЗАЦИЯ С ОБЛАКОМ ===
    # ==========================================
    def _configure_cloud(self):
        url = simpledialog.askstring(
            "Google Doc Webhook",
            "Вставь URL веб-приложения Google Apps Script:",
            initialvalue=self.webhook_url
        )
        if url is not None:
            self._save_cloud_url(url)
            self.cloud_status.configure(
                text="☁ Cloud: Linked!" if self.webhook_url else "☁ Cloud: Not linked",
                fg="#34d399" if self.webhook_url else "#71717a"
            )

    def _push_to_cloud(self):
        active = self._get_active_text()
        if not active or not self.active_node:
            return
        if not self.webhook_url:
            self._configure_cloud()
            if not self.webhook_url:
                return

        self._mark_activity(active)
        content = active.get("1.0", "end-1c")
        tab_id = getattr(active, "gdoc_tab_id", None)
        title = self.tree.item(self.active_node, "text").strip()

        payload_dict = {
            "text": content,
            "title": title,
            "tabId": tab_id
        }
        payload = json.dumps(payload_dict).encode("utf-8")

        self.cloud_status.configure(text="☁ Отправка...", fg="#facc15")

        def worker():
            try:
                req = urllib.request.Request(
                    self.webhook_url,
                    data=payload,
                    headers={"Content-Type": "text/plain; charset=utf-8", "User-Agent": "Mozilla/5.0"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    resp_raw = resp.read().decode("utf-8")
                    mode_info = ""
                    try:
                        resp_json = json.loads(resp_raw)
                        if resp_json.get("mode") == "appended":
                            mode_info = " (добавлено в документ)"
                    except Exception:
                        pass

                now_t = time.strftime("%H:%M:%S")
                self.root.after(0, lambda: self.cloud_status.configure(
                    text=f"☁ Сохранено в {now_t}{mode_info}", fg="#34d399"
                ))
                self.root.after(0, lambda: self._record_state("☁ Cloud Push", active))
            except Exception as e:
                self.root.after(0, lambda: self.cloud_status.configure(text="☁ Ошибка отправки!", fg="#f87171"))
                self.root.after(0, lambda: messagebox.showerror("Cloud Sync Error", f"Не удалось отправить в облако:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _pull_from_cloud(self):
        if not self.webhook_url:
            self._configure_cloud()
            if not self.webhook_url:
                return

        self.cloud_status.configure(text="☁ Скачивание...", fg="#facc15")

        def worker():
            try:
                req = urllib.request.Request(
                    self.webhook_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    method="GET"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    response_data = resp.read().decode("utf-8")

                try:
                    data = json.loads(response_data)
                except json.JSONDecodeError:
                    data = [{"title": "Cloud", "tabId": None, "parentId": None, "elements": [{"type": "text", "content": response_data}]}]

                self.root.after(0, lambda: self._apply_pulled_data(data))
            except Exception as e:
                self.root.after(0, lambda: self.cloud_status.configure(text="☁ Ошибка скачивания!", fg="#f87171"))
                self.root.after(0, lambda: messagebox.showerror("Cloud Sync Error", f"Не удалось забрать данные:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_pulled_data(self, data):
        for frame in self.tab_frames.values():
            frame.destroy()
        self.tab_frames.clear()
        self.tab_texts.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tab_count = 0
        self.active_node = None

        gdoc_to_node = {}
        first_node = None

        for doc_tab in data:
            title = doc_tab.get("title", "Вкладка")
            tab_id = doc_tab.get("tabId", None)
            parent_gdoc_id = doc_tab.get("parentId", None)
            elements = doc_tab.get("elements", [])

            parent_node = gdoc_to_node.get(parent_gdoc_id, "")
            node_id = self._add_tab(title, parent_node=parent_node, tab_id=tab_id)

            if tab_id:
                gdoc_to_node[tab_id] = node_id
            if not first_node:
                first_node = node_id

            active = self.tab_texts[node_id]
            active.delete("1.0", tk.END)
            active.image_refs.clear()
            active.image_b64_map.clear()

            for item in elements:
                if item.get("type") == "text":
                    active.insert(tk.END, item.get("content", ""))
                elif item.get("type") == "image":
                    try:
                        b64_str = item["data"]
                        img_data = base64.b64decode(b64_str)
                        image = Image.open(io.BytesIO(img_data))
                        image.thumbnail((500, 500), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(image)
                        active.image_refs.append(photo)
                        active.insert(tk.END, "\n")
                        img_name = active.image_create(tk.END, image=photo)
                        active.image_b64_map[img_name] = b64_str
                        active.insert(tk.END, "\n")
                    except Exception:
                        pass

            active.history.clear()
            self._record_state("⬇ Скачано из GDoc", active)
            self._run_spellcheck(active)

        if first_node:
            self.tree.selection_set(first_node)
            self._switch_to_node(first_node)

        now_t = time.strftime("%H:%M:%S")
        self.cloud_status.configure(text=f"☁ Скачано в {now_t}", fg="#34d399")

    # ==========================================
    # === БЛОК 9: СТИЛИ, ШАБЛОНЫ, ВВОД ТЕКСТА ===
    # ==========================================
    def _toggle_tag(self, tag_name):
        active = self._get_active_text()
        if not active:
            return "break"
        try:
            start, end = active.index("sel.first"), active.index("sel.last")
        except tk.TclError:
            return "break"
        if tag_name in active.tag_names("sel.first"):
            active.tag_remove(tag_name, start, end)
        else:
            active.tag_add(tag_name, start, end)
        self._mark_activity(active)
        self._record_state(f"Стиль: {tag_name}", active)
        return "break"

    def _color_text(self):
        active = self._get_active_text()
        if not active:
            return
        try:
            start, end = active.index("sel.first"), active.index("sel.last")
        except tk.TclError:
            return
        _, hex_c = colorchooser.askcolor(title="Цвет текста")
        if hex_c:
            tag = f"fg_{hex_c}"
            active.tag_configure(tag, foreground=hex_c)
            active.tag_add(tag, start, end)
            self._mark_activity(active)
            self._record_state("Изменен цвет", active)

    def _highlight_text(self):
        active = self._get_active_text()
        if not active:
            return
        try:
            start, end = active.index("sel.first"), active.index("sel.last")
        except tk.TclError:
            return
        _, hex_c = colorchooser.askcolor(title="Цвет фона")
        if hex_c:
            tag = f"bg_{hex_c}"
            active.tag_configure(tag, background=hex_c)
            active.tag_add(tag, start, end)
            self._mark_activity(active)
            self._record_state("Изменен фон", active)

    def _insert_bullet(self):
        active = self._get_active_text()
        if active:
            active.insert("insert linestart", "• ")
            self._mark_activity(active)
            self._record_state("Маркер списка", active)

    def _insert_plan_template(self):
        active = self._get_active_text()
        if not active:
            return
        tpl = "====================================\nПЛАН / КОНСПЕКТ\n====================================\n\n1. Главная цель:\n   • \n\n2. Этапы:\n   • \n"
        active.insert(tk.INSERT, tpl)
        self._mark_activity(active)
        self._update_stats()
        self._run_spellcheck(active)
        self._record_state("Шаблон: План", active)

    def _insert_gdd_template(self):
        active = self._get_active_text()
        if not active:
            return
        tpl = "====================================\nGAME DESIGN DOCUMENT\n====================================\n\n• Название: \n• Жанр: \n\n1. Механики:\n   • \n"
        active.insert(tk.INSERT, tpl)
        self._mark_activity(active)
        self._update_stats()
        self._run_spellcheck(active)
        self._record_state("Шаблон: GDD", active)

    def _update_stats(self):
        active = self._get_active_text()
        if not active:
            self.stats_label.configure(text="Вкладок нет")
            return
        content = active.get("1.0", "end-1c")
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        lines = int(active.index("end-1c").split(".")[0])
        self.stats_label.configure(text=f"Words: {words}  |  Chars: {chars}  |  Lines: {lines}")

    def _on_key_release(self, event, text_widget):
        if text_widget.is_replaying or event.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L"):
            return
        self._mark_activity(text_widget)
        self._update_stats()

        if text_widget._typing_job:
            self.root.after_cancel(text_widget._typing_job)
        if event.keysym in ("Return", "space", "BackSpace"):
            self._record_state(f"Ввод ({event.keysym})", text_widget)
        else:
            text_widget._typing_job = self.root.after(600, lambda: self._record_state("Печать текста", text_widget))

        if text_widget._spell_job:
            self.root.after_cancel(text_widget._spell_job)
        text_widget._spell_job = self.root.after(500, lambda: self._run_spellcheck(text_widget))

    # ==========================================
    # === БЛОК 10: ИСТОРИЯ И ОТКАТЫ (МАШИНА ВРЕМЕНИ) ===
    # ==========================================
    def _serialize_text(self, text_widget):
        content = text_widget.get("1.0", "end-1c")
        tags_data = []
        for tag in text_widget.tag_names():
            if tag in ("sel", "misspelled"):
                continue
            ranges = text_widget.tag_ranges(tag)
            fg = text_widget.tag_cget(tag, "foreground")
            bg = text_widget.tag_cget(tag, "background")
            for i in range(0, len(ranges), 2):
                tags_data.append((tag, str(ranges[i]), str(ranges[i + 1]), fg, bg))

        images_data = []
        for img_name in text_widget.image_names():
            try:
                idx = str(text_widget.index(img_name))
                b64 = text_widget.image_b64_map.get(img_name)
                if b64:
                    images_data.append((idx, b64))
            except Exception:
                pass

        return content, tags_data, images_data

    def _restore_serialized(self, text_widget, content, tags_data, images_data):
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", content)

        text_widget.image_refs.clear()
        text_widget.image_b64_map.clear()

        for idx, b64_str in images_data:
            try:
                img_data = base64.b64decode(b64_str)
                image = Image.open(io.BytesIO(img_data))
                image.thumbnail((500, 500), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                text_widget.image_refs.append(photo)
                img_name = text_widget.image_create(idx, image=photo)
                text_widget.image_b64_map[img_name] = b64_str
            except Exception:
                pass

        for tag, start, end, fg, bg in tags_data:
            if tag.startswith("fg_") and fg:
                text_widget.tag_configure(tag, foreground=fg)
            elif tag.startswith("bg_") and bg:
                text_widget.tag_configure(tag, background=bg)
            text_widget.tag_add(tag, start, end)

        self._update_stats()
        self._run_spellcheck(text_widget)

    def _record_state(self, action_name, text_widget=None):
        if not text_widget:
            text_widget = self._get_active_text()
        if not text_widget:
            return
        content, tags_data, images_data = self._serialize_text(text_widget)
        if text_widget.history and text_widget.history_pos >= 0:
            last = text_widget.history[text_widget.history_pos]
            if (last["content"] == content and
                last["tags"] == tags_data and
                last.get("images", []) == images_data and
                "Cloud" not in action_name):
                return

        if text_widget.history_pos < len(text_widget.history) - 1:
            text_widget.history = text_widget.history[:text_widget.history_pos + 1]

        elapsed = self._format_seconds(text_widget.active_seconds)
        clock = time.strftime("%H:%M:%S")
        text_widget.history.append({
            "content": content,
            "tags": tags_data,
            "images": images_data,
            "action": action_name,
            "elapsed": elapsed,
            "clock": clock
        })
        if len(text_widget.history) > 100:
            text_widget.history.pop(0)
        text_widget.history_pos = len(text_widget.history) - 1
        if text_widget == self._get_active_text():
            self._refresh_history_ui()

    def _refresh_history_ui(self):
        self.history_listbox.delete(0, tk.END)
        active = self._get_active_text()
        if not active:
            return
        for item in active.history:
            self.history_listbox.insert(tk.END, f"[{item['elapsed']}] {item['action']}")
        if active.history_pos >= 0:
            self.history_listbox.selection_clear(0, tk.END)
            self.history_listbox.selection_set(active.history_pos)
            self.history_listbox.see(active.history_pos)

    def _jump_to_history(self, idx):
        active = self._get_active_text()
        if not active or not (0 <= idx < len(active.history)):
            return
        active.history_pos = idx
        st = active.history[idx]
        self._restore_serialized(active, st["content"], st["tags"], st.get("images", []))
        self._refresh_history_ui()

    def _on_history_select(self, event):
        active = self._get_active_text()
        if not active or active.is_replaying:
            return
        sel = self.history_listbox.curselection()
        if sel:
            self._mark_activity(active)
            self._jump_to_history(sel[0])

    def _undo(self):
        active = self._get_active_text()
        if active and active.history_pos > 0:
            self._mark_activity(active)
            self._jump_to_history(active.history_pos - 1)
        return "break"

    def _redo(self):
        active = self._get_active_text()
        if active and active.history_pos < len(active.history) - 1:
            self._mark_activity(active)
            self._jump_to_history(active.history_pos + 1)
        return "break"

    # ==========================================
    # === БЛОК 11: РАБОТА С ФАЙЛАМИ (.TXT / .MD) ===
    # ==========================================
    def _load_file(self, path):
        fname = os.path.basename(path)
        self._add_tab(fname)
        active = self._get_active_text()
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            active.delete("1.0", tk.END)
            active.insert("1.0", txt)
            self._mark_activity(active)
            self._update_stats()
            self._run_spellcheck(active)
            self._record_state(f"Открыт файл: {fname}", active)
        except Exception:
            pass

    def _open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.md *.html"), ("All Files", "*.*")])
        if path:
            self._load_file(path)

    def _save_txt(self):
        active = self._get_active_text()
        if not active or not self.active_node:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(active.get("1.0", "end-1c"))
            self.tree.item(self.active_node, text=f" {os.path.basename(path)}")
            self._mark_activity(active)


# ==========================================
# === ТОЧКА ВХОДА В ПРОГРАММУ ===
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = WordsApp(root)
    root.mainloop()
