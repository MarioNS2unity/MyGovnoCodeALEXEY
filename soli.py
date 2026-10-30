import tkinter as tk
from tkinter import messagebox
import random

# === НАСТРОЙКИ ===
CARD_W, CARD_H = 80, 110
RADIUS = 8
COLORS = {'♠': 'black', '♣': 'black', '♥': 'red', '♦': 'red'}
SUITS = ['♠', '♣', '♥', '♦']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.face_up = False
        self.value = RANKS.index(rank) + 1

    def __repr__(self):
        return f"{self.rank}{self.suit}"

class Solitaire:
    def __init__(self, root):
        self.root = root
        self.root.title("Косынка на Python")
        self.root.configure(bg="#006400")  # Зеленое сукно
        self.canvas = tk.Canvas(root, width=800, height=600, bg="#006400", highlightthickness=0)
        self.canvas.pack()

        self.deck = []
        self.stock = []      # Колода (закрытая)
        self.waste = []      # Сброс (открытая)
        self.foundations = [[], [], [], []]  # Дома (4 масти)
        self.tableau = [[] for _ in range(7)]  # 7 столбцов

        self.selected_card = None
        self.selected_col = None
        
        self.new_game()
        self.canvas.bind("<Button-1>", self.on_click)

    def new_game(self):
        self.deck = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.deck)
        
        # Раздача
        for i in range(7):
            for j in range(i, 7):
                card = self.deck.pop()
                if j == i:
                    card.face_up = True
                self.tableau[j].append(card)
        
        self.stock = self.deck
        self.waste = []
        self.foundations = [[], [], [], []]
        self.selected_card = None
        self.selected_col = None
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        
        # Рисуем колоду (сток)
        self.draw_card_rect(50, 50, None, False)
        if self.stock:
            self.canvas.create_text(90, 110, text="🂠", font=("Arial", 30), fill="white")
        
        # Рисуем сброс (вейст)
        if self.waste:
            card = self.waste[-1]
            self.draw_card_rect(150, 50, card, True)
        
        # Рисуем дома (foundations)
        for i in range(4):
            x = 400 + i * (CARD_W + 10)
            y = 50
            self.draw_card_rect(x, y, None, False)
            if self.foundations[i]:
                self.draw_card_rect(x, y, self.foundations[i][-1], True)
        
        # Рисуем столбцы (tableau)
        for col in range(7):
            x = 50 + col * (CARD_W + 20)
            y = 200
            for row, card in enumerate(self.tableau[col]):
                # Смещение для веера
                offset = 25 if card.face_up else 10
                card_y = y + row * offset
                self.draw_card_rect(x, card_y, card, card.face_up, col, row)

    def draw_card_rect(self, x, y, card, face_up, col=None, row=None):
        # Тень
        self.canvas.create_rectangle(x+3, y+3, x+CARD_W+3, y+CARD_H+3, fill="#003300", outline="")
        
        if not face_up:
            # Рубашка
            self.canvas.create_rectangle(x, y, x+CARD_W, y+CARD_H, fill="#1E90FF", outline="black", width=2)
            self.canvas.create_text(x+CARD_W//2, y+CARD_H//2, text="?", font=("Arial", 24), fill="white")
        else:
            # Лицо
            self.canvas.create_rectangle(x, y, x+CARD_W, y+CARD_H, fill="white", outline="black", width=1)
            color = COLORS[card.suit]
            self.canvas.create_text(x+10, y+10, text=card.rank, font=("Arial", 16, "bold"), fill=color, anchor="nw")
            self.canvas.create_text(x+10, y+30, text=card.suit, font=("Arial", 16), fill=color, anchor="nw")
            # Большая масть по центру
            self.canvas.create_text(x+CARD_W//2, y+CARD_H//2, text=card.suit, font=("Arial", 30), fill=color)
            
            # Если карта выделена
            if self.selected_card == card:
                self.canvas.create_rectangle(x-2, y-2, x+CARD_W+2, y+CARD_H+2, outline="yellow", width=3)
            
            # Привязываем координаты для клика
            tag = f"card_{col}_{row}" if col is not None else f"card_{id(card)}"
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, c=card, cl=col: self.on_card_click(c, cl))
            self.canvas.addtag_withtag(tag, self.canvas.find_closest(x+CARD_W//2, y+CARD_H//2))

    def on_click(self, event):
        # Клик по колоде
        if 50 <= event.x <= 50 + CARD_W and 50 <= event.y <= 50 + CARD_H:
            self.draw_from_stock()
            return

    def on_card_click(self, card, col):
        if not card.face_up:
            return

        # Если ничего не выбрано - выбираем
        if self.selected_card is None:
            self.selected_card = card
            self.selected_col = col
            self.draw()
            return
        
        # Если выбрана та же карта - снимаем выделение
        if self.selected_card == card:
            self.selected_card = None
            self.selected_col = None
            self.draw()
            return

        # Пытаемся переместить
        if self.try_move(self.selected_card, self.selected_col, card, col):
            self.selected_card = None
            self.selected_col = None
        else:
            # Если не получилось, выделяем новую
            self.selected_card = card
            self.selected_col = col
        
        self.draw()

    def draw_from_stock(self):
        if self.stock:
            card = self.stock.pop()
            card.face_up = True
            self.waste.append(card)
        elif self.waste:
            # Переворачиваем сброс обратно в колоду
            for card in reversed(self.waste):
                card.face_up = False
                self.stock.append(card)
            self.waste = []
        self.draw()

    def try_move(self, card, from_col, target_card, target_col):
        # Здесь логика проверки правил
        # (Упрощенно: проверяем, можно ли положить карту на карту)
        if card.suit in ('♥', '♦'):
            is_red = True
        else:
            is_red = False
            
        if target_card.suit in ('♥', '♦'):
            target_is_red = True
        else:
            target_is_red = False

        # В столбцы (Tableau): карта должна быть на 1 меньше и другого цвета
        if is_red != target_is_red and target_card.value == card.value + 1:
            # Перемещаем
            self.move_card(card, from_col, target_col)
            return True
        
        return False

    def move_card(self, card, from_col, to_col):
        if from_col is not None and to_col is not None:
            # Перемещение внутри столбцов (нужно переносить стопку)
            idx = self.tableau[from_col].index(card)
            moving_cards = self.tableau[from_col][idx:]
            self.tableau[from_col] = self.tableau[from_col][:idx]
            self.tableau[to_col].extend(moving_cards)
            
            # Если открыли новую карту в старом столбце
            if self.tableau[from_col] and not self.tableau[from_col][-1].face_up:
                self.tableau[from_col][-1].face_up = True

if __name__ == "__main__":
    root = tk.Tk()
    game = Solitaire(root)
    root.mainloop()