import tkinter as tk
from tkinter import ttk, simpledialog
from datetime import datetime
import random
import math
import json
import os

CONFIG_FILE = "app_data.json"

class UltimateMegaCalc:
    def __init__(self, root):
        self.root = root
        self.root.title("Calc 2.0")
        self.root.geometry("600x580")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")

        # Перехват закрытия окна для сохранения данных
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Стиль вкладок
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#1e1e1e', borderwidth=0)
        style.configure('TNotebook.Tab', background='#2d2d2d', foreground='#ffffff', padding=[8, 4])
        style.map('TNotebook.Tab', background=[('selected', '#ff79c6')])

        # Главный блок с вкладками
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        self.tab_calc = tk.Frame(self.notebook, bg="#1e1e1e")
        self.tab_love = tk.Frame(self.notebook, bg="#1e1e1e")
        self.tab_nick = tk.Frame(self.notebook, bg="#1e1e1e")
        self.tab_currency = tk.Frame(self.notebook, bg="#1e1e1e")
        self.tab_dates = tk.Frame(self.notebook, bg="#1e1e1e")
        self.tab_wheel = tk.Frame(self.notebook, bg="#1e1e1e")

        self.notebook.add(self.tab_calc, text="Калькулятор")
        self.notebook.add(self.tab_love, text="Любовь")
        self.notebook.add(self.tab_nick, text="Ники")
        self.notebook.add(self.tab_currency, text="Валюты")
        self.notebook.add(self.tab_dates, text="Даты")
        self.notebook.add(self.tab_wheel, text="Колесо")

        self.init_calc_tab()
        self.init_love_tab()
        self.init_nick_tab()
        self.init_currency_tab()
        self.init_dates_tab()
        self.init_wheel_tab()

        # Загрузка сохранённых данных
        self.load_data()

        # CREDITS
        credits_frame = tk.Frame(root, bg="#181818", height=25)
        credits_frame.pack(fill="x", side="bottom")
        credits_label = tk.Label(
            credits_frame,
            text="Created by Mario (Dev) | Assisted by Gemini AI & Claude",
            font=("Arial", 9, "bold"),
            bg="#181818",
            fg="#ff79c6"
        )
        credits_label.pack(pady=3)

    # --- 1. КАЛЬКУЛЯТОР ---
    def init_calc_tab(self):
        self.expression = ""
        main_frame = tk.Frame(self.tab_calc, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True)

        calc_frame = tk.Frame(main_frame, bg="#1e1e1e")
        calc_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        disp_frame = tk.Frame(calc_frame, bg="#1e1e1e")
        disp_frame.pack(fill="x", pady=(0, 8))

        self.display = tk.Entry(disp_frame, font=("Arial", 18), bg="#2d2d2d", fg="#ffffff", bd=0, justify="right")
        self.display.pack(side="left", fill="x", expand=True, ipady=6)

        buttons = [
            ('C', 1, 0, '#ff5555'), ('(', 1, 1, '#44475a'), (')', 1, 2, '#44475a'), ('/', 1, 3, "#fcec5e"),
            ('7', 2, 0, '#6272a4'), ('8', 2, 1, '#6272a4'), ('9', 2, 2, '#6272a4'), ('*', 2, 3, '#ff79c6'),
            ('4', 3, 0, '#6272a4'), ('5', 3, 1, '#6272a4'), ('6', 3, 2, '#6272a4'), ('-', 3, 3, "#f11414"),
            ('1', 4, 0, '#6272a4'), ('2', 4, 1, '#6272a4'), ('3', 4, 2, '#6272a4'), ('+', 4, 3, "#79ffa6"),
            ('0', 5, 0, '#6272a4'), ('.', 5, 1, '#6272a4'), ('=', 5, 2, '#50fa7b')
        ]

        grid_frame = tk.Frame(calc_frame, bg="#1e1e1e")
        grid_frame.pack(fill="both", expand=True)

        for i in range(6): grid_frame.rowconfigure(i, weight=1)
        for i in range(4): grid_frame.columnconfigure(i, weight=1)

        for btn in buttons:
            text, row, col, color = btn[0], btn[1], btn[2], btn[3]
            colspan = 2 if text == '=' else 1
            b = tk.Button(grid_frame, text=text, font=("Arial", 11, "bold"), bg=color, fg="#ffffff" if color not in ['#50fa7b', '#fcec5e', '#79ffa6'] else "#1e1e1e", bd=0,
                          command=lambda t=text: self.on_calc_btn(t))
            b.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=2, pady=2)

        history_frame = tk.Frame(main_frame, bg="#282a36", width=160)
        history_frame.pack(side="right", fill="both", padx=8, pady=8)
        tk.Label(history_frame, text="История", font=("Arial", 10, "bold"), bg="#282a36", fg="#f8f8f2").pack(pady=4)
        self.history_list = tk.Listbox(history_frame, bg="#21222c", fg="#f8f8f2", bd=0, font=("Arial", 8))
        self.history_list.pack(fill="both", expand=True, padx=4, pady=4)

        btn_clear_hist = tk.Button(history_frame, text="Очистить", font=("Arial", 8, "bold"), bg="#ff5555", fg="#ffffff", bd=0, command=self.clear_history)
        btn_clear_hist.pack(fill="x", padx=4, pady=(0, 4))

    def on_calc_btn(self, char):
        if char == 'C': self.expression = ""
        elif char == '=':
            try:
                res = str(eval(self.expression))
                self.history_list.insert(tk.END, f"{self.expression} = {res}")
                self.expression = res
            except Exception: self.expression = "Ошибка"
        else:
            if self.expression == "Ошибка": self.expression = ""
            self.expression += str(char)
        self.display.delete(0, tk.END)
        self.display.insert(0, self.expression)

    def clear_history(self):
        self.history_list.delete(0, tk.END)

    # --- 2. ВКЛАДКА: ЛЮБОВЬ ❤️ ---
    def init_love_tab(self):
        frame = tk.Frame(self.tab_love, bg="#1e1e1e")
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        tk.Label(frame, text="Совместимость имён", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="#ff79c6").pack(pady=5)

        f_names = tk.Frame(frame, bg="#1e1e1e")
        f_names.pack(pady=5)

        self.name1 = tk.Entry(f_names, font=("Arial", 11), bg="#2d2d2d", fg="#fff", bd=0, width=15)
        self.name1.pack(side="left", padx=5)
        tk.Label(f_names, text="+", bg="#1e1e1e", fg="#ff79c6", font=("Arial", 14)).pack(side="left")
        self.name2 = tk.Entry(f_names, font=("Arial", 11), bg="#2d2d2d", fg="#fff", bd=0, width=15)
        self.name2.pack(side="left", padx=5)

        btn_love = tk.Button(frame, text="Рассчитать любовь", font=("Arial", 11, "bold"), bg="#ff79c6", fg="#fff", bd=0, command=self.calc_love)
        btn_love.pack(pady=10, fill="x")

        self.love_res = tk.Label(frame, text="Результат: -", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="#50fa7b")
        self.love_res.pack(pady=5)

        tk.Label(frame, text="Любовное предсказание", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="#ff79c6").pack(pady=(15, 5))
        btn_predict = tk.Button(frame, text="Получить предсказание ✨", font=("Arial", 11, "bold"), bg="#bd93f9", fg="#fff", bd=0, command=self.get_prediction)
        btn_predict.pack(pady=5, fill="x")

        self.predict_res = tk.Label(frame, text="...", font=("Arial", 10, "italic"), bg="#1e1e1e", fg="#f8f8f2", wraplength=400)
        self.predict_res.pack(pady=10)

    def calc_love(self):
        n1, n2 = self.name1.get().strip(), self.name2.get().strip()
        if not n1 or not n2:
            self.love_res.config(text="Введи оба имени!")
            return
        score = (sum(ord(c) for c in (n1 + n2).lower()) % 51) + 50
        self.love_res.config(text=f"Совместимость {n1} и {n2}: {score}%")

    def get_prediction(self):
        predictions = [
            "Сегодня идеальный день для катки в коопе с кем-то важным! С твоим другом!",
            "Кто-то думает о тебе прямо сейчас... и это не просто антивирус! Потому что вирус)",
            "Твой следующий парный скин будет идеальным. Его не будет.",
            "Любовь — это когда вы делите аптеку на двоих. Далее ТГ каналы с рецептами.",
            "Жди приятного сообщения в лс до конца дня! Тебе писать никто не будет.",
            "Идеальная пара — это ты и твой ПК. Он хотя бы не врет, когда лагает.",
            "Скоро тебе признаются в любви... в чате Roblox, чтобы выпросить робуксы.",
            "Твоя любовь где-то рядом. Возможно, в соседней вкладке браузера.",
            "Шанс найти любовь равен шансу выбить легендарку с первого контейнера.",
            "Скатят ли вас в дуо? Только если ты затащишь раунд.",
            "Любовный совет: не забудь покормить кота, он единственная твоя тру верность.",
            "С любовью всё сложно, лучше пойди допиши код или доделай игру."
        ]
        self.predict_res.config(text=random.choice(predictions))

    # --- 3. ВКЛАДКА: ГЕНЕРАТОР НИКОВ 🎲 ---
    def init_nick_tab(self):
        frame = tk.Frame(self.tab_nick, bg="#1e1e1e")
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        tk.Label(frame, text="Генератор ников", font=("Arial", 14, "bold"), bg="#1e1e1e", fg="#50fa7b").pack(pady=10)

        btn_nick = tk.Button(frame, text="Сгенерировать ник", font=("Arial", 12, "bold"), bg="#50fa7b", fg="#1e1e1e", bd=0, command=self.gen_nick)
        btn_nick.pack(pady=10, fill="x")

        self.nick_res = tk.Label(frame, text="-", font=("Arial", 16, "bold"), bg="#1e1e1e", fg="#ff79c6")
        self.nick_res.pack(pady=20)

    def gen_nick(self):
        adj = [
            "Cyber", "Shadow", "Neon", "Dark", "Crazy", "Epic", "Turbo", "Pixel", 
            "Cosmic", "Phantom", "Slayer", "Toxic", "Mega", "Hyper", "Ultra", "Alpha", 
            "Omega", "Retro", "Glitch", "Silent", "Atomic", "Fatal", "Astral", "Vortex"
        ]
        noun = [
            "Mario", "Gamer", "Ghost", "Knight", "Fox", "Viper", "Phoenix", "Panda", 
            "Wolf", "Lord", "Bot", "Hacker", "Samurai", "Hunter", "Dragon", "Wizard", 
            "Reaper", "Spectre", "Titan", "Rider", "Cobra", "Runner", "Pixel", "Dev"
        ]
        nums = [
            str(random.randint(10, 99)), "777", "X", "_", "3000", "007", "1337", 
            "404", "666", "_Dev", "_Pro", "2026", ""
        ]

        nick = f"{random.choice(adj)}{random.choice(noun)}{random.choice(nums)}"
        self.nick_res.config(text=nick)

    # --- 4. ВКЛАДКА: ВАЛЮТЫ ---
    def init_currency_tab(self):
        frame = tk.Frame(self.tab_currency, bg="#1e1e1e")
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.rates = {'RUB': 1.0, 'USD': 90.0, 'EUR': 98.0, 'CNY': 12.5}

        tk.Label(frame, text="Сумма:", font=("Arial", 11), bg="#1e1e1e", fg="#fff").pack(pady=2)
        self.curr_amount = tk.Entry(frame, font=("Arial", 12), bg="#2d2d2d", fg="#fff", bd=0, justify="center")
        self.curr_amount.pack(pady=5, ipady=3)

        f_curr = tk.Frame(frame, bg="#1e1e1e")
        f_curr.pack(pady=5)

        self.from_curr = ttk.Combobox(f_curr, values=list(self.rates.keys()), state="readonly", width=8)
        self.from_curr.current(1)
        self.from_curr.pack(side="left", padx=5)

        tk.Label(f_curr, text="➜", bg="#1e1e1e", fg="#fff", font=("Arial", 12)).pack(side="left")

        self.to_curr = ttk.Combobox(f_curr, values=list(self.rates.keys()), state="readonly", width=8)
        self.to_curr.current(0)
        self.to_curr.pack(side="left", padx=5)

        btn = tk.Button(frame, text="Перевести", font=("Arial", 11, "bold"), bg="#50fa7b", fg="#1e1e1e", bd=0, command=self.convert_currency)
        btn.pack(pady=10, fill="x")

        self.curr_result = tk.Label(frame, text="Результат: -", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="#ff79c6")
        self.curr_result.pack(pady=5)

    def convert_currency(self):
        try:
            val = float(self.curr_amount.get())
            base_val = val * self.rates[self.from_curr.get()]
            res = base_val / self.rates[self.to_curr.get()]
            self.curr_result.config(text=f"Результат: {res:.2f} {self.to_curr.get()}")
        except ValueError:
            self.curr_result.config(text="Введите число!")

    # --- 5. ВКЛАДКА: ДАТЫ ---
    def init_dates_tab(self):
        frame = tk.Frame(self.tab_dates, bg="#1e1e1e")
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        tk.Label(frame, text="Дата 1 (ДД.ММ.ГГГГ):", font=("Arial", 10), bg="#1e1e1e", fg="#fff").pack(pady=2)
        self.date1_entry = tk.Entry(frame, font=("Arial", 11), bg="#2d2d2d", fg="#fff", bd=0, justify="center")
        self.date1_entry.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.date1_entry.pack(pady=3, ipady=2)

        tk.Label(frame, text="Дата 2 (ДД.ММ.ГГГГ):", font=("Arial", 10), bg="#1e1e1e", fg="#fff").pack(pady=2)
        self.date2_entry = tk.Entry(frame, font=("Arial", 11), bg="#2d2d2d", fg="#fff", bd=0, justify="center")
        self.date2_entry.pack(pady=3, ipady=2)

        btn = tk.Button(frame, text="Посчитать разницу", font=("Arial", 11, "bold"), bg="#ff79c6", fg="#fff", bd=0, command=self.calc_date_diff)
        btn.pack(pady=10, fill="x")

        self.date_result = tk.Label(frame, text="Разница: -", font=("Arial", 11, "bold"), bg="#1e1e1e", fg="#50fa7b")
        self.date_result.pack(pady=5)

    def calc_date_diff(self):
        try:
            d1 = datetime.strptime(self.date1_entry.get(), "%d.%m.%Y")
            d2 = datetime.strptime(self.date2_entry.get(), "%d.%m.%Y")
            diff = abs((d2 - d1).days)
            self.date_result.config(text=f"Разница: {diff} дней (~{diff//7} нед.)")
        except ValueError:
            self.date_result.config(text="Формат: ДД.ММ.ГГГГ")

    # --- 6. ВКЛАДКА: КОЛЕСО ФОРТУНЫ 🎡 ---
    WHEEL_PALETTE = ["#ff5555", "#f1fa8c", "#50fa7b", "#8be9fd", "#bd93f9", "#ff79c6", "#6272a4", "#ffb86c"]
    WHEEL_LIGHT_BG = {"#f1fa8c", "#50fa7b", "#8be9fd", "#ffb86c"}

    def init_wheel_tab(self):
        frame = tk.Frame(self.tab_wheel, bg="#1e1e1e")
        frame.pack(expand=True, fill="both", padx=16, pady=10)

        tk.Label(frame, text="Колесо фортуны", font=("Arial", 14, "bold"), bg="#1e1e1e", fg="#ff79c6").pack(pady=(0, 6))

        content = tk.Frame(frame, bg="#1e1e1e")
        content.pack(fill="both", expand=True)

        left = tk.Frame(content, bg="#1e1e1e")
        left.pack(side="left", fill="both", expand=True)

        self.wheel_names = ["1", "2", "3", "4", "5", "6", "7", "8"]
        self.wheel_angle = 0.0
        self.spinning = False

        self.wheel_canvas = tk.Canvas(left, width=220, height=220, bg="#1e1e1e", highlightthickness=0)
        self.wheel_canvas.pack(pady=2)

        self.btn_spin = tk.Button(left, text="Крутить колесо", font=("Arial", 11, "bold"), bg="#50fa7b", fg="#1e1e1e", bd=0, command=self.spin_wheel)
        self.btn_spin.pack(pady=(4, 2), fill="x", padx=10)

        self.spin_result_label = tk.Label(left, text="Результат: -", font=("Arial", 11, "bold"), bg="#1e1e1e", fg="#f8f8f2", wraplength=200)
        self.spin_result_label.pack(pady=2)

        right = tk.Frame(content, bg="#282a36", width=180)
        right.pack(side="right", fill="y", padx=(10, 0))

        tk.Label(right, text="Сектора", font=("Arial", 10, "bold"), bg="#282a36", fg="#f8f8f2").pack(pady=(4, 2))

        self.wheel_listbox = tk.Listbox(right, bg="#21222c", fg="#f8f8f2", bd=0, font=("Arial", 8), selectbackground="#ff79c6", height=6)
        self.wheel_listbox.pack(fill="both", expand=True, padx=6)
        self.wheel_listbox.bind("<Double-Button-1>", lambda e: self.edit_wheel_sector())
        self._refresh_wheel_listbox()

        btn_edit = tk.Button(right, text="Редактировать выбранный", font=("Arial", 8, "bold"), bg="#bd93f9", fg="#fff", bd=0, command=self.edit_wheel_sector)
        btn_edit.pack(fill="x", padx=6, pady=(3, 2))

        btn_remove = tk.Button(right, text="Удалить выбранный", font=("Arial", 8, "bold"), bg="#ff5555", fg="#fff", bd=0, command=self.remove_wheel_sector)
        btn_remove.pack(fill="x", padx=6, pady=(0, 4))

        self.wheel_new_entry = tk.Entry(right, font=("Arial", 9), bg="#2d2d2d", fg="#fff", bd=0)
        self.wheel_new_entry.pack(fill="x", padx=6, pady=(0, 2), ipady=3)
        self.wheel_new_entry.bind("<Return>", lambda e: self.add_wheel_sector())

        btn_add = tk.Button(right, text="Добавить сектор", font=("Arial", 8, "bold"), bg="#50fa7b", fg="#1e1e1e", bd=0, command=self.add_wheel_sector)
        btn_add.pack(fill="x", padx=6, pady=(0, 4))

        self.draw_wheel()

    def _refresh_wheel_listbox(self):
        self.wheel_listbox.delete(0, tk.END)
        for name in self.wheel_names:
            self.wheel_listbox.insert(tk.END, name)

    def add_wheel_sector(self):
        if self.spinning: return
        name = self.wheel_new_entry.get().strip()
        if not name: return
        self.wheel_names.append(name)
        self.wheel_new_entry.delete(0, tk.END)
        self._refresh_wheel_listbox()
        self.draw_wheel()

    def edit_wheel_sector(self):
        if self.spinning: return
        sel = self.wheel_listbox.curselection()
        if not sel: return
        idx = sel[0]
        old_val = self.wheel_names[idx]
        new_val = simpledialog.askstring("Редактирование", "Введите новое название сектора:", initialvalue=old_val)
        if new_val and new_val.strip():
            self.wheel_names[idx] = new_val.strip()
            self._refresh_wheel_listbox()
            self.draw_wheel()

    def remove_wheel_sector(self):
        if self.spinning: return
        sel = self.wheel_listbox.curselection()
        if not sel: return
        if len(self.wheel_names) <= 2:
            self.spin_result_label.config(text="Нужно минимум 2 сектора!", fg="#ff5555")
            return
        idx = sel[0]
        del self.wheel_names[idx]
        self._refresh_wheel_listbox()
        self.draw_wheel()

    def draw_wheel(self):
        c = self.wheel_canvas
        c.delete("all")
        cx, cy, r = 110, 110, 95
        n = len(self.wheel_names)
        if n == 0: return
        seg_extent = 360 / n

        for i, label in enumerate(self.wheel_names):
            color = self.WHEEL_PALETTE[i % len(self.WHEEL_PALETTE)]
            start = self.wheel_angle + i * seg_extent
            c.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=seg_extent, fill=color, outline="#1e1e1e", width=2)
            mid_rad = math.radians(start + seg_extent / 2)
            lx = cx + (r * 0.62) * math.cos(mid_rad)
            ly = cy - (r * 0.62) * math.sin(mid_rad)
            text_color = "#1e1e1e" if color in self.WHEEL_LIGHT_BG else "#ffffff"
            c.create_text(lx, ly, text=label, font=("Arial", 7, "bold"), fill=text_color, width=55)

        c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#282a36", outline="#ff79c6", width=2)
        c.create_polygon(cx - 10, cy - r - 12, cx + 10, cy - r - 12, cx, cy - r + 4, fill="#ff5555", outline="#ffffff")

    def spin_wheel(self):
        if self.spinning or len(self.wheel_names) < 2: return
        self.spinning = True
        self.btn_spin.config(state="disabled")
        self.spin_result_label.config(text="Крутим...", fg="#f8f8f2")
        self.spin_remaining = random.uniform(1080, 1800) + random.uniform(0, 360)
        self._spin_step()

    def _spin_step(self):
        if self.spin_remaining <= 0.5:
            self.spinning = False
            self.wheel_angle %= 360
            self.draw_wheel()
            self.btn_spin.config(state="normal")
            self._announce_wheel_result()
            return
        step = max(2.0, self.spin_remaining * 0.06)
        step = min(step, self.spin_remaining)
        self.wheel_angle = (self.wheel_angle + step) % 360
        self.spin_remaining -= step
        self.draw_wheel()
        self.root.after(20, self._spin_step)

    def _announce_wheel_result(self):
        n = len(self.wheel_names)
        seg_extent = 360 / n
        raw = (90 - self.wheel_angle) % 360
        idx = int(raw // seg_extent) % n
        label = self.wheel_names[idx]
        color = self.WHEEL_PALETTE[idx % len(self.WHEEL_PALETTE)]
        self.spin_result_label.config(text=f"Результат: {label} 🎉", fg=color)

    # --- СОХРАНЕНИЕ И ЗАГРУЗКА ---
    def save_data(self):
        data = {
            "calc_history": list(self.history_list.get(0, tk.END)),
            "love": {
                "name1": self.name1.get(),
                "name2": self.name2.get(),
                "res": self.love_res.cget("text"),
                "predict": self.predict_res.cget("text")
            },
            "nick": self.nick_res.cget("text"),
            "currency": {
                "amount": self.curr_amount.get(),
                "from": self.from_curr.get(),
                "to": self.to_curr.get(),
                "res": self.curr_result.cget("text")
            },
            "dates": {
                "date1": self.date1_entry.get(),
                "date2": self.date2_entry.get(),
                "res": self.date_result.cget("text")
            },
            "wheel_sectors": self.wheel_names
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def load_data(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Калькулятор
            for item in data.get("calc_history", []):
                self.history_list.insert(tk.END, item)

            # Любовь
            love = data.get("love", {})
            self.name1.insert(0, love.get("name1", ""))
            self.name2.insert(0, love.get("name2", ""))
            self.love_res.config(text=love.get("res", "Результат: -"))
            self.predict_res.config(text=love.get("predict", "..."))

            # Ник
            self.nick_res.config(text=data.get("nick", "-"))

            # Валюты
            curr = data.get("currency", {})
            self.curr_amount.insert(0, curr.get("amount", ""))
            if curr.get("from") in self.rates: self.from_curr.set(curr.get("from"))
            if curr.get("to") in self.rates: self.to_curr.set(curr.get("to"))
            self.curr_result.config(text=curr.get("res", "Результат: -"))

            # Даты
            dates = data.get("dates", {})
            if dates.get("date1"):
                self.date1_entry.delete(0, tk.END)
                self.date1_entry.insert(0, dates.get("date1"))
            self.date2_entry.insert(0, dates.get("date2", ""))
            self.date_result.config(text=dates.get("res", "Разница: -"))

            # Колесо
            sectors = data.get("wheel_sectors")
            if sectors and isinstance(sectors, list):
                self.wheel_names = sectors
                self._refresh_wheel_listbox()
                self.draw_wheel()

        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def on_closing(self):
        self.save_data()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateMegaCalc(root)
    root.mainloop()