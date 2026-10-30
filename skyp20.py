import sys
import socket
import threading
import pickle
import time
import json
import os
import numpy as np
import sounddevice as sd
import soundfile as sf
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QInputDialog, QLabel,
                             QCheckBox, QComboBox, QDialog, QMessageBox)
from PyQt6.QtCore import pyqtSignal, QObject, Qt

# === НАСТРОЙКИ ===
HOST = '0.0.0.0'
PORT = 333
CHUNK = 512
CHANNELS = 1
RATE = 44100
DTYPE = 'int16'
INTRO_FILE = "taksi.mp3"
APP_VERSION = "4.1.0 (Strict Handshake)"

MUSIC_PLAYING = True

class Communicate(QObject):
    text_received = pyqtSignal(str)
    status_received = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    version_mismatch = pyqtSignal(str)

comm = Communicate()

# === ЗВУКОВЫЕ ЭФФЕКТЫ ===
def play_beep(freq, duration, volume=0.1):
    def _play():
        try:
            t = np.linspace(0, duration, int(RATE * duration), False)
            envelope = np.exp(-3 * t / duration)
            audio = np.sin(freq * 2 * np.pi * t) * envelope * volume
            sd.play(audio, RATE, blocking=False)
        except Exception: pass
    threading.Thread(target=_play, daemon=True).start()

def play_intro_then_ambient():
    global MUSIC_PLAYING
    if os.path.exists(INTRO_FILE):
        try:
            data, fs = sf.read(INTRO_FILE, dtype='int16')
            if MUSIC_PLAYING:
                sd.play(data, fs)
                while sd.get_stream().active and MUSIC_PLAYING:
                    time.sleep(0.1)
        except Exception: pass

    def _play_ambient():
        try:
            while MUSIC_PLAYING:
                t = np.linspace(0, 2.5, int(RATE * 2.5), False)
                f1, f2, f3 = 261.63, 329.63, 392.00 
                audio = (np.sin(f1 * 2 * np.pi * t) + np.sin(f2 * 2 * np.pi * t) + np.sin(f3 * 2 * np.pi * t)) * 0.02
                envelope = np.sin(np.linspace(0, np.pi, len(t)))
                sd.play(audio * envelope, RATE, blocking=True)
        except Exception: pass
    threading.Thread(target=_play_ambient, daemon=True).start()

# === ФУНКЦИИ КОНФИГА ===
def get_config_path(nickname):
    safe_nick = "".join([c for c in nickname if c.isalnum() or c in ('-', '_')])
    return f"{safe_nick}_setting.json"

def load_config(nickname):
    path = get_config_path(nickname)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {"nickname": nickname, "input_device": None, "output_device": None, "status": "В сети"}

def save_config(nickname, config):
    path = get_config_path(nickname)
    with open(path, 'w', encoding='utf-8') as f: json.dump(config, f, ensure_ascii=False, indent=4)

# === ПОТОК СЕТИ (MULTI-USER) ===
class NetworkThread(threading.Thread):
    def __init__(self, role, target_ip, nickname, status, max_clients=1):
        super().__init__(daemon=True)
        self.role = role
        self.target_ip = target_ip
        self.nickname = nickname
        self.status = status
        self.max_clients = max_clients
        self.sock = None
        self.clients = []
        self.conn = None
        self.running = True
        self.audio_queue = []
        self.connected = False

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            if self.role == 'server':
                self.sock.bind((HOST, PORT))
                self.sock.listen(5)
                
                # Ждем клиентов
                while len(self.clients) < self.max_clients and self.running:
                    conn, addr = self.sock.accept()
                    # --- СТРОГАЯ ПРОВЕРКА ВЕРСИЙ ДЛЯ КАЖДОГО КЛИЕНТА ---
                    try:
                        # Читаем версию клиента
                        size_data = conn.recv(4)
                        if not size_data: 
                            conn.close()
                            continue
                        size = int.from_bytes(size_data, 'big')
                        data = b""
                        while len(data) < size:
                            chunk = conn.recv(size - len(data))
                            if not chunk: break
                            data += chunk
                        
                        packet = pickle.loads(data)
                        client_ver = packet[1]
                        
                        # Отправляем свою версию
                        version_packet = pickle.dumps(('version', APP_VERSION))
                        conn.sendall(len(version_packet).to_bytes(4, 'big'))
                        conn.sendall(version_packet)
                        
                        if client_ver != APP_VERSION:
                            # Ждем от клиента сигнал MISMATCH
                            size_data = conn.recv(4)
                            if size_data:
                                size = int.from_bytes(size_data, 'big')
                                data = b""
                                while len(data) < size:
                                    chunk = conn.recv(size - len(data))
                                    if not chunk: break
                                    data += chunk
                                mismatch_packet = pickle.loads(data)
                                if mismatch_packet[0] == 'mismatch':
                                    comm.version_mismatch.emit(f"Извините.\nВаш собеседник отключился из-за несовместимости версий.\nУ вас: {APP_VERSION}\nУ друга: {client_ver}")
                                    self.running = False
                                    self.sock.close()
                                    return
                        else:
                            # Версии совпали, начинаем прием
                            self.clients.append(conn)
                            threading.Thread(target=self.client_handler, args=(conn,), daemon=True).start()
                    except Exception as e:
                        conn.close()
                        continue
                
                if self.running:
                    self.connected = True
                    comm.connected.emit()
            else:
                self.sock.connect((self.target_ip, PORT))
                self.conn = self.sock
                
                # Отправляем свою версию
                version_packet = pickle.dumps(('version', APP_VERSION))
                self.conn.sendall(len(version_packet).to_bytes(4, 'big'))
                self.conn.sendall(version_packet)
                
                # Читаем версию сервера
                size_data = self.conn.recv(4)
                if not size_data: raise Exception("Соединение закрыто")
                size = int.from_bytes(size_data, 'big')
                data = b""
                while len(data) < size:
                    chunk = self.conn.recv(size - len(data))
                    if not chunk: break
                    data += chunk
                    
                packet = pickle.loads(data)
                if packet[1] != APP_VERSION:
                    # Отправляем серверу MISMATCH
                    mismatch_msg = pickle.dumps(('mismatch', APP_VERSION))
                    self.conn.sendall(len(mismatch_msg).to_bytes(4, 'big'))
                    self.conn.sendall(mismatch_msg)
                    self.conn.close()
                    comm.version_mismatch.emit(f"Извините.\nВаш собеседник отключился из-за несовместимости версий.\nУ вас: {APP_VERSION}\nУ друга: {packet[1]}")
                    self.running = False
                    return
                
                self.connected = True
                comm.connected.emit()
                threading.Thread(target=self.receive_loop, daemon=True).start()

        except Exception as e:
            if self.running:
                comm.error_occurred.emit(f"Ошибка сети: {e}")
            self.running = False

    def client_handler(self, conn):
        while self.running:
            try:
                size_data = conn.recv(4)
                if not size_data: break
                size = int.from_bytes(size_data, 'big')
                if size > 10_000_000: continue
                data = b""
                while len(data) < size:
                    chunk = conn.recv(size - len(data))
                    if not chunk: break
                    data += chunk
                if len(data) < size: continue
                
                packet = pickle.loads(data)
                msg_type = packet[0]
                
                for c in self.clients:
                    if c != conn:
                        try:
                            c.sendall(len(data).to_bytes(4, 'big'))
                            c.sendall(data)
                        except: pass
                self.process_packet(packet)
                
            except Exception:
                break
        if conn in self.clients:
            self.clients.remove(conn)
        conn.close()

    def receive_loop(self):
        while self.running:
            try:
                size_data = self.conn.recv(4)
                if not size_data: break
                size = int.from_bytes(size_data, 'big')
                if size > 10_000_000: continue
                data = b""
                while len(data) < size:
                    chunk = self.conn.recv(size - len(data))
                    if not chunk: break
                    data += chunk
                if len(data) < size: continue
                
                packet = pickle.loads(data)
                self.process_packet(packet)
            except Exception: break
        
        self.connected = False
        if self.running:
            comm.disconnected.emit()

    def process_packet(self, packet):
        msg_type = packet[0]
        if msg_type == 'text':
            _, nick, payload = packet
            comm.text_received.emit(f"{nick}: {payload}")
        elif msg_type == 'voice':
            _, payload = packet
            self.audio_queue.append(payload)
        elif msg_type == 'status':
            _, nick, status = packet
            comm.status_received.emit(f"Статус {nick}: {status}")

    def send_packet(self, packet):
        if not self.connected: return
        try:
            data = pickle.dumps(packet)
            if self.role == 'server':
                for c in self.clients:
                    c.sendall(len(data).to_bytes(4, 'big'))
                    c.sendall(data)
            else:
                self.conn.sendall(len(data).to_bytes(4, 'big'))
                self.conn.sendall(data)
        except: pass

    def send_text(self, text): self.send_packet(('text', self.nickname, text))
    def send_voice(self, data): self.send_packet(('voice', data))
    def send_status(self, status): self.send_packet(('status', self.nickname, status))

# === ВЫБОР УСТРОЙСТВА ===
def select_device(kind):
    devices = sd.query_devices()
    options = []
    for i, dev in enumerate(devices):
        if kind == 'input' and dev['max_input_channels'] > 0: options.append(f"{i}: {dev['name']}")
        elif kind == 'output' and dev['max_output_channels'] > 0: options.append(f"{i}: {dev['name']}")
    
    if not options: return None
    
    item, ok = QInputDialog.getItem(None, f"Выбор ({kind})", f"Выбери {kind}:", options, 0, False)
    return int(item.split(":")[0]) if ok else None

# === ДИАЛОГ ОЖИДАНИЯ ===
class WaitingDialog(QDialog):
    def __init__(self, role):
        super().__init__()
        self.setWindowTitle("Skyp 2.0")
        self.setFixedSize(350, 200)
        self.setStyleSheet("background-color: #18181b; color: #e4e4e7;")
        layout = QVBoxLayout()
        text = "Ожидание подключения клиентов..." if role == 'server' else "Подключение к серверу..."
        self.label = QLabel(f"{text}\n(Играет музыка)")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        if role == 'server':
            threading.Thread(target=play_intro_then_ambient, daemon=True).start()

# === ДИАЛОГ ВХОДА ===
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Skyp 2.0 - Вход")
        self.setFixedSize(350, 300)
        self.setStyleSheet("background-color: #18181b; color: #e4e4e7;")
        self.role = None
        self.nickname = None
        self.target_ip = "127.0.0.1"
        self.max_clients = 1

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Версия: {APP_VERSION}"))
        layout.addWidget(QLabel("Твой ник:"))
        
        self.nick_input = QLineEdit()
        self.nick_input.setStyleSheet("background-color: #27272a; color: white; padding: 5px;")
        layout.addWidget(self.nick_input)

        layout.addWidget(QLabel("Сколько человек ждать (для сервера):"))
        self.clients_input = QLineEdit("1")
        self.clients_input.setStyleSheet("background-color: #27272a; color: white; padding: 5px;")
        layout.addWidget(self.clients_input)

        btn_server = QPushButton("Создать сервер")
        btn_server.clicked.connect(lambda: self.do_login('server'))
        btn_server.setStyleSheet("background-color: #3b82f6; color: white; padding: 10px;")
        layout.addWidget(btn_server)

        btn_client = QPushButton("Подключиться (127.0.0.1)")
        btn_client.clicked.connect(lambda: self.do_login('client'))
        btn_client.setStyleSheet("background-color: #10b981; color: white; padding: 10px;")
        layout.addWidget(btn_client)
        
        self.setLayout(layout)

    def do_login(self, role):
        nick = self.nick_input.text().strip()
        if not nick:
            QMessageBox.warning(self, "Ошибка", "Введи свой ник!")
            return
        self.nickname = nick
        self.role = role
        try:
            self.max_clients = int(self.clients_input.text())
        except:
            self.max_clients = 1
        self.accept()

# === ИНТЕРФЕЙС ЧАТА ===
class ChatWindow(QWidget):
    def __init__(self, network, input_device, output_device):
        super().__init__()
        self.network = network
        self.input_device = input_device
        self.output_device = output_device
        self.setWindowTitle(f"Skyp - {network.nickname} (v{APP_VERSION})")
        self.resize(600, 500)
        self.setStyleSheet("background-color: #18181b; color: #e4e4e7;")

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.status_label = QLabel(f"Микрофон активен | Статус: {network.status}")
        self.status_label.setStyleSheet("color: #10b981; font-weight: bold;")
        top_layout.addWidget(self.status_label)

        self.status_box = QComboBox()
        self.status_box.addItems(["В сети", "Играю", "Стримлю", "Не беспокоить"])
        self.status_box.setCurrentText(network.status)
        self.status_box.currentTextChanged.connect(self.change_status)
        self.status_box.setStyleSheet("background-color: #27272a; color: white;")
        top_layout.addWidget(self.status_box)

        layout.addLayout(top_layout)

        controls_layout = QHBoxLayout()
        self.mic_check = QCheckBox("Микрофон ВКЛ")
        self.mic_check.setChecked(True)
        self.mic_check.stateChanged.connect(self.toggle_mic)
        
        self.speaker_check = QCheckBox("Наушники ВКЛ")
        self.speaker_check.setChecked(True)
        self.speaker_check.stateChanged.connect(self.toggle_speaker)
        
        controls_layout.addWidget(self.mic_check)
        controls_layout.addWidget(self.speaker_check)
        layout.addLayout(controls_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #27272a; color: #e4e4e7;")
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setStyleSheet("background-color: #27272a; color: white; padding: 5px;")
        self.text_input.returnPressed.connect(self.send_text)
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setStyleSheet("background-color: #10b981; color: white; padding: 5px;")
        self.send_btn.clicked.connect(self.send_text)
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self.setLayout(layout)
        comm.text_received.connect(self.add_message)
        comm.status_received.connect(self.add_message)

        self.mic_enabled = True
        self.speaker_enabled = True
        self.is_running = True

        threading.Thread(target=self.record_loop, daemon=True).start()
        threading.Thread(target=self.play_loop, daemon=True).start()

    def change_status(self, text):
        self.network.status = text
        self.network.send_status(text)
        self.status_label.setText(f"Микрофон активен | Статус: {text}")

    def toggle_mic(self, state):
        self.mic_enabled = (state == 2)
        self.status_label.setStyleSheet("color: #10b981;" if self.mic_enabled else "color: red;")

    def toggle_speaker(self, state):
        self.speaker_enabled = (state == 2)

    def send_text(self):
        text = self.text_input.text().strip()
        if text:
            self.network.send_text(text)
            self.add_message(f"Вы: {text}")
            self.text_input.clear()

    def add_message(self, text):
        self.chat_display.append(text)
        if not text.startswith("Вы:"):
            play_beep(1200, 0.1, 0.05)

    def record_loop(self):
        try:
            with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=DTYPE, blocksize=CHUNK, device=self.input_device) as stream:
                while self.is_running:
                    data, overflowed = stream.read(CHUNK)
                    if self.mic_enabled and self.network.connected:
                        self.network.send_voice(data.tobytes())
        except Exception: pass

    def play_loop(self):
        try:
            stream = sd.OutputStream(samplerate=RATE, channels=CHANNELS, dtype=DTYPE, blocksize=CHUNK, device=self.output_device)
            stream.start()
            while self.is_running:
                if self.network.audio_queue:
                    data = self.network.audio_queue.pop(0)
                    if self.speaker_enabled and self.network.connected:
                        audio_array = np.frombuffer(data, dtype=np.int16)
                        try:
                            stream.write(audio_array)
                        except: pass
                else:
                    time.sleep(0.01)
        except Exception: pass

# === ЗАПУСК ===
if __name__ == "__main__":
    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    config = load_config(login.nickname)
    input_device = config.get("input_device") or select_device('input')
    output_device = config.get("output_device") or select_device('output')

    if input_device is None or output_device is None:
        sys.exit(1)

    config["input_device"] = input_device
    config["output_device"] = output_device
    save_config(login.nickname, config)

    waiting_dialog = WaitingDialog(login.role)
    waiting_dialog.show()
    app.processEvents()

    network_thread = NetworkThread(login.role, login.target_ip, login.nickname, config.get("status", "В сети"), login.max_clients)
    
    def on_connected():
        global MUSIC_PLAYING
        MUSIC_PLAYING = False
        
        if waiting_dialog:
            waiting_dialog.accept()
            waiting_dialog.close()
            
        play_beep(880, 0.2)
        window = ChatWindow(network_thread, input_device, output_device)
        window.show()
        app.window = window 

    def on_disconnect():
        if hasattr(app, 'window'):
            play_beep(440, 0.3)
            app.window.add_message("--- Собеседник отключился ---")

    def on_version_mismatch(msg):
        global MUSIC_PLAYING
        MUSIC_PLAYING = False
        
        if waiting_dialog:
            waiting_dialog.accept()
            waiting_dialog.close()
            
        err = QMessageBox()
        err.setIcon(QMessageBox.Icon.Critical)
        err.setWindowTitle("Несовместимые версии")
        err.setText(msg)
        err.exec()
        sys.exit(0)

    def on_error(msg):
        global MUSIC_PLAYING
        MUSIC_PLAYING = False
        
        if waiting_dialog:
            waiting_dialog.accept()
            waiting_dialog.close()
        err = QMessageBox(); err.setIcon(QMessageBox.Icon.Critical); err.setText(msg); err.exec(); sys.exit(1)

    comm.connected.connect(on_connected)
    comm.disconnected.connect(on_disconnect)
    comm.error_occurred.connect(on_error)
    comm.version_mismatch.connect(on_version_mismatch)

    network_thread.start()
    sys.exit(app.exec())