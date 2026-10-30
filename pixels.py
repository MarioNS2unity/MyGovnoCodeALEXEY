import os
import time
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageOps, ImageEnhance, ImageFont


def generate_pxs_icon():
    """Генерирует пиксель-арт иконку PxS (Pixels) и сохраняет pixels.ico / pixels.png"""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_color = (10, 18, 42, 255)
    border_color = (59, 130, 246, 255)
    text_color = (96, 165, 250, 255)
    accent_x = (56, 189, 248, 255)

    draw.rectangle([1, 1, 30, 30], fill=bg_color, outline=border_color, width=2)

    P_letter = ["111110", "110011", "110011", "111110", "110000", "110000", "110000"]
    x_letter = ["110011", "011110", "001100", "011110", "110011"]
    S_letter = ["011111", "110000", "110000", "011110", "000011", "000011", "111110"]

    def draw_sprite(sprite, sx, sy, col):
        for r, row in enumerate(sprite):
            for c, val in enumerate(row):
                if val == "1":
                    draw.point((sx + c, sy + r), fill=col)

    draw_sprite(P_letter, 5, 11, text_color)
    draw_sprite(x_letter, 13, 13, accent_x)
    draw_sprite(S_letter, 21, 11, text_color)

    for px, py in [(24, 5), (26, 4), (27, 6), (25, 7)]:
        draw.point((px, py), fill=accent_x)

    icon_256 = img.resize((256, 256), Image.Resampling.NEAREST)
    if not os.path.exists("pixels.ico"):
        icon_256.save("pixels.ico", format="ICO", sizes=[(256, 256), (64, 64), (32, 32)])
    if not os.path.exists("pixels.png"):
        icon_256.save("pixels.png", format="PNG")
    return icon_256


class Layer:
    def __init__(self, name, width, height, bg=(0, 0, 0, 0)):
        self.name = name
        self.image = Image.new("RGBA", (width, height), bg)
        self.visible = True
        self.opacity = 1.0


class PixelsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixels (PxS) — Zero Adobe Edition")
        self.root.geometry("1240x820")
        self.root.configure(bg="#18181b")

        icon_img = generate_pxs_icon()
        self.app_icon = ImageTk.PhotoImage(icon_img)
        self.root.iconphoto(False, self.app_icon)

        self.canvas_w = 800
        self.canvas_h = 600
        self.layers = []
        self.active_idx = 0

        # Таймлайн и время
        self.session_start = time.time()
        self.history = []        # Список словарей: {snap, active_idx, action, elapsed, clock}
        self.history_pos = -1    # Текущая позиция в таймлайне
        self.is_replaying = False

        self.tool = "brush"
        self.color = (59, 130, 246, 255)
        self.size = 12
        self.fill_shapes = tk.BooleanVar(value=False)

        self.start_x = None
        self.start_y = None
        self.last_x = None
        self.last_y = None
        self.preview_img = None

        self._make_checkerboard()
        self._build_ui()
        self._init_project()
        self._bind_shortcuts()
        self._tick_timer()

    def _format_seconds(self, sec):
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def _tick_timer(self):
        elapsed = time.time() - self.session_start
        now_str = time.strftime("%H:%M:%S")
        self.timer_label.configure(text=f"⏱ {self._format_seconds(elapsed)}  |  🕒 {now_str}")
        self.root.after(1000, self._tick_timer)

    def _make_checkerboard(self):
        tile = 16
        cb = Image.new("RGBA", (self.canvas_w, self.canvas_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(cb)
        for y in range(0, self.canvas_h, tile):
            for x in range(0, self.canvas_w, tile):
                if (x // tile + y // tile) % 2 == 1:
                    draw.rectangle([x, y, x + tile, y + tile], fill=(220, 220, 225, 255))
        self.checkerboard = cb

    def _init_project(self):
        self.session_start = time.time()
        self.layers = [
            Layer("Background", self.canvas_w, self.canvas_h, (255, 255, 255, 255)),
            Layer("Layer 1", self.canvas_w, self.canvas_h, (0, 0, 0, 0))
        ]
        self.active_idx = 1
        self.history.clear()
        self.history_pos = -1
        self._record_state("Project Start")
        self._refresh_layer_list()
        self._render_canvas()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background="#27272a", foreground="#e4e4e7", borderwidth=0, padding=6)
        style.map("TButton", background=[("active", "#3b82f6")])

        top = tk.Frame(self.root, bg="#09090b", height=45, padx=10, pady=6)
        top.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top, text="PxS PIXELS", fg="#38bdf8", bg="#09090b", font=("Consolas", 13, "bold")).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(top, text="New", command=self._new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Import", command=self._open_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Save PNG", command=self._save_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="⬅ Undo", command=self._undo).pack(side=tk.LEFT, padx=(10, 2))
        ttk.Button(top, text="Redo ➡", command=self._redo).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="▶ Timelapse", command=self._play_timelapse).pack(side=tk.LEFT, padx=8)

        tk.Label(top, text="Size:", fg="#a1a1aa", bg="#09090b").pack(side=tk.LEFT, padx=(10, 4))
        self.size_slider = tk.Scale(top, from_=1, to=100, orient=tk.HORIZONTAL, bg="#09090b", fg="#e4e4e7",
                                    highlightthickness=0, troughcolor="#27272a", command=self._update_size)
        self.size_slider.set(self.size)
        self.size_slider.pack(side=tk.LEFT)

        tk.Checkbutton(top, text="Fill Shapes", variable=self.fill_shapes, bg="#09090b", fg="#e4e4e7",
                       selectcolor="#27272a", activebackground="#09090b").pack(side=tk.LEFT, padx=10)

        self.color_btn = tk.Button(top, text="  Color  ", bg="#3b82f6", fg="white", relief=tk.FLAT, command=self._pick_color)
        self.color_btn.pack(side=tk.LEFT, padx=8)

        # Таймер справа в шапке
        self.timer_label = tk.Label(top, text="⏱ 00:00  |  🕒 00:00:00", fg="#38bdf8", bg="#18181b",
                                    font=("Consolas", 10, "bold"), padx=10, pady=4)
        self.timer_label.pack(side=tk.RIGHT)

        # Левая панель инструментов
        left = tk.Frame(self.root, bg="#09090b", width=110, padx=6, pady=8)
        left.pack(side=tk.LEFT, fill=tk.Y)

        tools = [
            ("Brush (B)", "brush"),
            ("Eraser (E)", "eraser"),
            ("Bucket (G)", "bucket"),
            ("Picker (I)", "picker"),
            ("Line (L)", "line"),
            ("Rect (U)", "rect"),
            ("Ellipse (C)", "ellipse"),
            ("Text (T)", "text"),
            ("Move (V)", "move"),
        ]
        self.tool_btns = {}
        for label, t_id in tools:
            b = tk.Button(left, text=label, width=11, bg="#27272a", fg="#e4e4e7", relief=tk.FLAT, pady=6,
                          command=lambda t=t_id: self._select_tool(t))
            b.pack(pady=3)
            self.tool_btns[t_id] = b
        self._select_tool("brush")

        # Правая панель (Фильтры + Слои + Таймлайн по секундам)
        right = tk.Frame(self.root, bg="#09090b", width=270, padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(right, text="FILTERS (ACTIVE LAYER)", fg="#a1a1aa", bg="#09090b", font=("Sans", 9, "bold")).pack(anchor="w", pady=(0, 4))
        f_frame = tk.Frame(right, bg="#09090b")
        f_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(f_frame, text="Grayscale", command=lambda: self._apply_filter("gray")).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(f_frame, text="Invert", command=lambda: self._apply_filter("invert")).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ttk.Button(f_frame, text="Blur", command=lambda: self._apply_filter("blur")).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(f_frame, text="Sharpen", command=lambda: self._apply_filter("sharpen")).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        ttk.Button(f_frame, text="Bright +", command=lambda: self._apply_filter("bright_up")).grid(row=2, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(f_frame, text="Contrast +", command=lambda: self._apply_filter("contrast_up")).grid(row=2, column=1, padx=2, pady=2, sticky="ew")
        f_frame.columnconfigure(0, weight=1)
        f_frame.columnconfigure(1, weight=1)

        tk.Label(right, text="LAYERS", fg="#a1a1aa", bg="#09090b", font=("Sans", 9, "bold")).pack(anchor="w")

        op_frame = tk.Frame(right, bg="#09090b")
        op_frame.pack(fill=tk.X, pady=2)
        tk.Label(op_frame, text="Opacity:", fg="#a1a1aa", bg="#09090b").pack(side=tk.LEFT)
        self.op_slider = tk.Scale(op_frame, from_=0, to=100, orient=tk.HORIZONTAL, bg="#09090b", fg="#e4e4e7",
                                  highlightthickness=0, troughcolor="#27272a", command=self._change_opacity)
        self.op_slider.set(100)
        self.op_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        self.layer_listbox = tk.Listbox(right, bg="#18181b", fg="#e4e4e7", selectbackground="#2563eb",
                                        relief=tk.FLAT, height=6, exportselection=False)
        self.layer_listbox.pack(fill=tk.X, pady=4)
        self.layer_listbox.bind("<<ListboxSelect>>", self._on_layer_select)

        l_btns = tk.Frame(right, bg="#09090b")
        l_btns.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(l_btns, text="+ Add", command=self._add_layer).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(l_btns, text="Eye (Show/Hide)", command=self._toggle_vis).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ttk.Button(l_btns, text="Merge Down", command=self._merge_down).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(l_btns, text="Delete", command=self._del_layer).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        l_btns.columnconfigure(0, weight=1)
        l_btns.columnconfigure(1, weight=1)

        # Таймлайн изменений по секундам
        tk.Label(right, text="TIMELINE HISTORY (BY SECONDS)", fg="#38bdf8", bg="#09090b", font=("Sans", 9, "bold")).pack(anchor="w")
        hist_frame = tk.Frame(right, bg="#18181b")
        hist_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = tk.Scrollbar(hist_frame, orient=tk.VERTICAL)
        self.history_listbox = tk.Listbox(hist_frame, bg="#18181b", fg="#e4e4e7", selectbackground="#0284c7",
                                          font=("Consolas", 9), relief=tk.FLAT, exportselection=False,
                                          yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)

        # Центральный холст
        center = tk.Frame(self.root, bg="#18181b")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tk_canvas = tk.Canvas(center, width=self.canvas_w, height=self.canvas_h, bg="#18181b",
                                   highlightthickness=1, highlightbackground="#3f3f46")
        self.tk_canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.tk_canvas.bind("<ButtonPress-1>", self._on_down)
        self.tk_canvas.bind("<B1-Motion>", self._on_drag)
        self.tk_canvas.bind("<ButtonRelease-1>", self._on_up)

    def _bind_shortcuts(self):
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        for key, t in [("b", "brush"), ("e", "eraser"), ("g", "bucket"), ("i", "picker"),
                       ("l", "line"), ("u", "rect"), ("c", "ellipse"), ("t", "text"), ("v", "move")]:
            self.root.bind(key, lambda e, tool=t: self._select_tool(tool))

    def _select_tool(self, t_id):
        self.tool = t_id
        for k, b in self.tool_btns.items():
            b.configure(bg="#2563eb" if k == t_id else "#27272a")

    def _update_size(self, val):
        self.size = int(val)

    def _pick_color(self):
        rgb, hex_c = colorchooser.askcolor(color=self.color_btn["bg"], title="Choose Color")
        if rgb:
            self.color = (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255)
            self.color_btn.configure(bg=hex_c)

    # --- Машина времени (Таймлайн по секундам) ---
    def _record_state(self, action_name):
        if self.history_pos < len(self.history) - 1:
            self.history = self.history[:self.history_pos + 1]

        snap = [(l.name, l.image.copy(), l.visible, l.opacity) for l in self.layers]
        elapsed = self._format_seconds(time.time() - self.session_start)
        clock = time.strftime("%H:%M:%S")

        self.history.append({
            "snap": snap,
            "active_idx": self.active_idx,
            "action": action_name,
            "elapsed": elapsed,
            "clock": clock
        })

        if len(self.history) > 60:
            self.history.pop(0)

        self.history_pos = len(self.history) - 1
        self._refresh_history_ui()

    def _refresh_history_ui(self):
        self.history_listbox.delete(0, tk.END)
        for idx, item in enumerate(self.history):
            entry = f"[{item['elapsed']}] {item['action']} ({item['clock']})"
            self.history_listbox.insert(tk.END, entry)
        if self.history_pos >= 0:
            self.history_listbox.selection_clear(0, tk.END)
            self.history_listbox.selection_set(self.history_pos)
            self.history_listbox.see(self.history_pos)

    def _Jump_to_history(self, index):
        if 0 <= index < len(self.history):
            self.history_pos = index
            state = self.history[index]
            self.layers = []
            for name, img, vis, op in state["snap"]:
                l = Layer(name, self.canvas_w, self.canvas_h)
                l.image = img.copy()
                l.visible = vis
                l.opacity = op
                self.layers.append(l)
            self.active_idx = min(state["active_idx"], len(self.layers) - 1)
            self._refresh_layer_list()
            self._refresh_history_ui()
            self._render_canvas()

    def _on_history_select(self, event):
        if self.is_replaying:
            return
        sel = self.history_listbox.curselection()
        if sel:
            self._Jump_to_history(sel[0])

    def _undo(self):
        if self.history_pos > 0:
            self._Jump_to_history(self.history_pos - 1)

    def _redo(self):
        if self.history_pos < len(self.history) - 1:
            self._Jump_to_history(self.history_pos + 1)

    def _play_timelapse(self):
        if self.is_replaying or len(self.history) <= 1:
            return
        self.is_replaying = True

        def step_frame(idx):
            if idx < len(self.history):
                self._Jump_to_history(idx)
                self.root.after(220, lambda: step_frame(idx + 1))
            else:
                self.is_replaying = False

        step_frame(0)

    def _render_canvas(self, temp_overlay=None):
        comp = self.checkerboard.copy()
        for i, l in enumerate(self.layers):
            if not l.visible:
                continue
            img = temp_overlay if (temp_overlay is not None and i == self.active_idx) else l.image
            if l.opacity < 1.0:
                alpha = img.split()[3].point(lambda p: int(p * l.opacity))
                temp = img.copy()
                temp.putalpha(alpha)
                comp.alpha_composite(temp)
            else:
                comp.alpha_composite(img)

        self.tk_img = ImageTk.PhotoImage(comp)
        self.tk_canvas.delete("all")
        self.tk_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

    def _draw_dab(self, draw, x, y, r, color, erase=False):
        bbox = [x - r, y - r, x + r, y + r]
        draw.ellipse(bbox, fill=(0, 0, 0, 0) if erase else color)

    def _on_down(self, event):
        if self.is_replaying:
            return
        l = self.layers[self.active_idx]
        if not l.visible:
            return
        x, y = event.x, event.y
        self.start_x, self.start_y = x, y
        self.last_x, self.last_y = x, y

        if self.tool in ("brush", "eraser"):
            draw = ImageDraw.Draw(l.image)
            self._draw_dab(draw, x, y, self.size // 2, self.color, erase=(self.tool == "eraser"))
            self._render_canvas()
        elif self.tool == "bucket":
            if 0 <= x < self.canvas_w and 0 <= y < self.canvas_h:
                ImageDraw.floodfill(l.image, (x, y), self.color, thresh=35)
                self._render_canvas()
                self._record_state("Bucket Fill")
        elif self.tool == "picker":
            px = l.image.getpixel((max(0, min(x, self.canvas_w - 1)), max(0, min(y, self.canvas_h - 1))))
            if px[3] > 0:
                self.color = (px[0], px[1], px[2], 255)
                self.color_btn.configure(bg=f"#{px[0]:02x}{px[1]:02x}{px[2]:02x}")
        elif self.tool == "text":
            txt = simpledialog.askstring("Text Tool", "Enter text:")
            if txt:
                draw = ImageDraw.Draw(l.image)
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", max(12, self.size * 2))
                except IOError:
                    font = ImageFont.load_default()
                draw.text((x, y), txt, fill=self.color, font=font)
                self._render_canvas()
                self._record_state(f"Text: {txt[:8]}")
        elif self.tool in ("line", "rect", "ellipse", "move"):
            self.preview_img = l.image.copy()

    def _on_drag(self, event):
        if self.is_replaying:
            return
        l = self.layers[self.active_idx]
        if not l.visible or self.start_x is None:
            return
        x, y = event.x, event.y

        if self.tool in ("brush", "eraser"):
            draw = ImageDraw.Draw(l.image)
            r = max(1, self.size // 2)
            erase = (self.tool == "eraser")
            steps = int(max(abs(x - self.last_x), abs(y - self.last_y)))
            for i in range(0, steps + 1, max(1, r // 2)):
                t = i / steps if steps > 0 else 0
                ix = int(self.last_x + (x - self.last_x) * t)
                iy = int(self.last_y + (y - self.last_y) * t)
                self._draw_dab(draw, ix, iy, r, self.color, erase=erase)
            self.last_x, self.last_y = x, y
            self._render_canvas()

        elif self.tool in ("line", "rect", "ellipse"):
            temp = self.preview_img.copy()
            draw = ImageDraw.Draw(temp)
            fill_c = self.color if self.fill_shapes.get() else None
            box = [min(self.start_x, x), min(self.start_y, y), max(self.start_x, x), max(self.start_y, y)]
            if self.tool == "line":
                draw.line([self.start_x, self.start_y, x, y], fill=self.color, width=self.size)
            elif self.tool == "rect":
                draw.rectangle(box, fill=fill_c, outline=self.color, width=self.size)
            elif self.tool == "ellipse":
                draw.ellipse(box, fill=fill_c, outline=self.color, width=self.size)
            self._render_canvas(temp_overlay=temp)

        elif self.tool == "move":
            dx, dy = x - self.start_x, y - self.start_y
            temp = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))
            temp.paste(self.preview_img, (dx, dy))
            l.image = temp
            self._render_canvas()

    def _on_up(self, event):
        if self.is_replaying or self.start_x is None:
            return
        l = self.layers[self.active_idx]

        if self.tool in ("brush", "eraser"):
            self._record_state("Brush Stroke" if self.tool == "brush" else "Eraser")
        elif self.tool in ("line", "rect", "ellipse") and self.preview_img is not None:
            x, y = event.x, event.y
            draw = ImageDraw.Draw(l.image)
            fill_c = self.color if self.fill_shapes.get() else None
            box = [min(self.start_x, x), min(self.start_y, y), max(self.start_x, x), max(self.start_y, y)]
            if self.tool == "line":
                draw.line([self.start_x, self.start_y, x, y], fill=self.color, width=self.size)
            elif self.tool == "rect":
                draw.rectangle(box, fill=fill_c, outline=self.color, width=self.size)
            elif self.tool == "ellipse":
                draw.ellipse(box, fill=fill_c, outline=self.color, width=self.size)
            self.preview_img = None
            self._render_canvas()
            self._record_state(f"Shape: {self.tool.capitalize()}")
        elif self.tool == "move":
            self.preview_img = None
            self._record_state("Move Layer")

        self.start_x = None

    def _refresh_layer_list(self):
        self.layer_listbox.delete(0, tk.END)
        for i in range(len(self.layers) - 1, -1, -1):
            l = self.layers[i]
            eye = "👁" if l.visible else "🚫"
            self.layer_listbox.insert(tk.END, f"{eye}  {l.name} ({int(l.opacity*100)}%)")
        listbox_idx = len(self.layers) - 1 - self.active_idx
        self.layer_listbox.selection_set(listbox_idx)
        self.op_slider.set(int(self.layers[self.active_idx].opacity * 100))

    def _on_layer_select(self, event):
        sel = self.layer_listbox.curselection()
        if sel:
            self.active_idx = len(self.layers) - 1 - sel[0]
            self.op_slider.set(int(self.layers[self.active_idx].opacity * 100))

    def _add_layer(self):
        new_l = Layer(f"Layer {len(self.layers)}", self.canvas_w, self.canvas_h)
        self.layers.insert(self.active_idx + 1, new_l)
        self.active_idx += 1
        self._refresh_layer_list()
        self._render_canvas()
        self._record_state(f"Add {new_l.name}")

    def _del_layer(self):
        if len(self.layers) <= 1:
            return
        removed = self.layers.pop(self.active_idx)
        self.active_idx = max(0, self.active_idx - 1)
        self._refresh_layer_list()
        self._render_canvas()
        self._record_state(f"Del {removed.name}")

    def _toggle_vis(self):
        l = self.layers[self.active_idx]
        l.visible = not l.visible
        self._refresh_layer_list()
        self._render_canvas()

    def _merge_down(self):
        if self.active_idx == 0:
            return
        top = self.layers.pop(self.active_idx)
        btm = self.layers[self.active_idx - 1]
        btm.image.alpha_composite(top.image)
        self.active_idx -= 1
        self._refresh_layer_list()
        self._render_canvas()
        self._record_state("Merge Down")

    def _change_opacity(self, val):
        self.layers[self.active_idx].opacity = int(val) / 100.0
        self._render_canvas()

    def _apply_filter(self, f_type):
        l = self.layers[self.active_idx]
        r, g, b, a = l.image.split()
        rgb = Image.merge("RGB", (r, g, b))
        if f_type == "gray":
            rgb = ImageOps.grayscale(rgb).convert("RGB")
        elif f_type == "invert":
            rgb = ImageOps.invert(rgb)
        elif f_type == "blur":
            rgb = rgb.filter(ImageFilter.GaussianBlur(3))
        elif f_type == "sharpen":
            rgb = rgb.filter(ImageFilter.SHARPEN)
        elif f_type == "bright_up":
            rgb = ImageEnhance.Brightness(rgb).enhance(1.2)
        elif f_type == "contrast_up":
            rgb = ImageEnhance.Contrast(rgb).enhance(1.3)
        nr, ng, nb = rgb.split()
        l.image = Image.merge("RGBA", (nr, ng, nb, a))
        self._render_canvas()
        self._record_state(f"Filter: {f_type}")

    def _new_file(self):
        if messagebox.askyesno("New Project", "Reset canvas and clear timeline?"):
            self._init_project()

    def _open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if path:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((self.canvas_w, self.canvas_h))
            new_l = Layer(os.path.basename(path), self.canvas_w, self.canvas_h)
            ox = (self.canvas_w - img.width) // 2
            oy = (self.canvas_h - img.height) // 2
            new_l.image.paste(img, (ox, oy))
            self.layers.append(new_l)
            self.active_idx = len(self.layers) - 1
            self._refresh_layer_list()
            self._render_canvas()
            self._record_state("Import Image")

    def _save_image(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if path:
            out = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))
            for l in self.layers:
                if l.visible:
                    out.alpha_composite(l.image)
            out.save(path, "PNG")
            messagebox.showinfo("Saved", f"Saved to {path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PixelsApp(root)
    root.mainloop()
