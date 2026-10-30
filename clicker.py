import os
import struct
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import pyautogui

pyautogui.PAUSE = 0
ICON_FILENAME = "clicker.ico"


def create_default_ico(filepath: str):
    """Генерирует корректный 16x16 .ico файл без сторонних библиотек."""
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return

    width, height = 16, 16
    pattern = [
        "1000000000000000",
        "1100000000000000",
        "1110000000000000",
        "1111000000000000",
        "1111100000000000",
        "1111110000000000",
        "1111111000000000",
        "1111111100000000",
        "1111100000000000",
        "1101110000000000",
        "1000111000000000",
        "0000011100000000",
        "0000011100000000",
        "0000001100000000",
        "0000000000000000",
        "0000000000000000",
    ]

    xor_bytes = bytearray()
    and_bytes = bytearray()

    for y in reversed(range(height)):
        and_row = 0
        for x in range(width):
            bit = pattern[y][x]
            if bit == '1':
                # BGRA: контур черный, тело курсора оранжевое
                if x == 0 or y == 0 or pattern[y - 1][x] == '0' or pattern[y][x - 1] == '0':
                    xor_bytes.extend([0, 0, 0, 255])       # Черный контур
                else:
                    xor_bytes.extend([0, 140, 255, 255])   # Оранжевый центр
            else:
                xor_bytes.extend([0, 0, 0, 0])             # Прозрачный пиксель
                and_row |= (1 << (7 - (x % 8)))

            if x % 8 == 7:
                and_bytes.append(and_row)
                and_row = 0

    bmp_header = struct.pack(
        "<IIIHHIIIIII",
        40, width, height * 2, 1, 32, 0,
        len(xor_bytes) + len(and_bytes), 0, 0, 0, 0
    )
    image_data = bmp_header + bytes(xor_bytes) + bytes(and_bytes)
    ico_header = struct.pack("<HHH", 0, 1, 1)
    ico_entry = struct.pack(
        "<BBBBHHII",
        width, height, 0, 0, 1, 32, len(image_data), 6 + 16
    )

    with open(filepath, "wb") as f:
        f.write(ico_header + ico_entry + image_data)


class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Автокликер")
        self.root.geometry("340x260")
        self.root.resizable(False, False)

        create_default_ico(ICON_FILENAME)
        try:
            self.root.iconbitmap(ICON_FILENAME)
        except Exception:
            pass

        self.is_clicking = False
        self.running_thread = True
        self.current_toggle_key = 'f4'

        self.create_widgets()
        self.bind_hotkey(self.current_toggle_key)

        self.click_thread = threading.Thread(target=self.clicker_loop, daemon=True)
        self.click_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Кнопка мыши:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.mouse_button_var = tk.StringVar(value="left")
        button_combo = ttk.Combobox(
            main_frame,
            textvariable=self.mouse_button_var,
            values=["left", "right", "middle"],
            state="readonly",
            width=12
        )
        button_combo.grid(row=0, column=1, sticky=tk.E, pady=5)

        ttk.Label(main_frame, text="Интервал (сек):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.delay_var = tk.StringVar(value="0.01")
        delay_entry = ttk.Entry(main_frame, textvariable=self.delay_var, width=14)
        delay_entry.grid(row=1, column=1, sticky=tk.E, pady=5)

        ttk.Label(main_frame, text="Горячая клавиша:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.hotkey_btn = ttk.Button(
            main_frame,
            text=f"[{self.current_toggle_key.upper()}] (Нажмите)",
            command=self.capture_key,
            width=14
        )
        self.hotkey_btn.grid(row=2, column=1, sticky=tk.E, pady=5)

        self.status_label = tk.Label(
            main_frame,
            text="СТАТУС: ОСТАНОВЛЕН",
            fg="red",
            font=("Arial", 10, "bold")
        )
        self.status_label.grid(row=3, column=0, columnspan=2, pady=15)

        self.toggle_btn = ttk.Button(
            main_frame,
            text="Старт / Стоп",
            command=self.toggle_clicking
        )
        self.toggle_btn.grid(row=4, column=0, columnspan=2, sticky=tk.EW)

    def bind_hotkey(self, key_identifier):
        try:
            keyboard.unhook_all_hotkeys()
            keyboard.add_hotkey(key_identifier, self.toggle_clicking)
            return True
        except Exception:
            return False

    def capture_key(self):
        self.hotkey_btn.config(text="Нажмите клавишу...")
        self.root.update()

        def listen():
            event = keyboard.read_event(suppress=False)
            while event.event_type != keyboard.KEY_DOWN:
                event = keyboard.read_event(suppress=False)

            key_name = event.name if event.name else str(event.scan_code)
            scan_code = event.scan_code

            success = self.bind_hotkey(key_name)
            if not success:
                success = self.bind_hotkey(scan_code)

            if success:
                self.current_toggle_key = key_name
                self.hotkey_btn.config(text=f"[{key_name.upper()}]")
            else:
                self.hotkey_btn.config(text=f"[{self.current_toggle_key.upper()}]")
                messagebox.showerror("Ошибка", f"Не удалось привязать: {key_name}")

        threading.Thread(target=listen, daemon=True).start()

    def toggle_clicking(self):
        self.is_clicking = not self.is_clicking
        if self.is_clicking:
            self.status_label.config(text="СТАТУС: КЛИКАЕТ...", fg="green")
        else:
            self.status_label.config(text="СТАТУС: ОСТАНОВЛЕН", fg="red")

    def clicker_loop(self):
        while self.running_thread:
            if self.is_clicking:
                btn = self.mouse_button_var.get()
                pyautogui.click(button=btn)
                try:
                    delay = float(self.delay_var.get())
                    if delay < 0.001:
                        delay = 0.001
                except ValueError:
                    delay = 0.01
                time.sleep(delay)
            else:
                time.sleep(0.02)

    def on_close(self):
        self.running_thread = False
        self.is_clicking = False
        keyboard.unhook_all_hotkeys()
        self.root.destroy()


if __name__ == "__main__":
    app_window = tk.Tk()
    app = AutoClickerApp(app_window)
    app_window.mainloop()
