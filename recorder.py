import os
import sys
import wave
import time
import datetime
import threading
import numpy as np
import pyaudiowpatch as pyaudio
import tkinter as tk
from tkinter import ttk, messagebox

# Определение рабочей директории
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SAVE_DIR = os.path.join(BASE_DIR, "Dict")
os.makedirs(SAVE_DIR, exist_ok=True)

DESKTOP_GAIN = 0.8
CHUNK = 1024
RATE = 44100
CHANNELS = 2

class RecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Диктофон (ПК + Микрофон)")
        self.root.geometry("420x560")
        self.root.resizable(False, False)

        # Безопасная установка иконки окна
        icon_path = os.path.join(BASE_DIR, "rec.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.is_recording = False
        self.is_playing = False
        self.is_seeking = False
        
        self.play_pos = 0
        self.audio_data = None
        self.wf = None
        self.start_time = 0
        self.sample_width = 2
        self.channels = 2
        self.rate = RATE

        self.gain_var = tk.DoubleVar(value=100.0)
        self.progress_var = tk.DoubleVar(value=0.0)

        self.setup_ui()
        self.refresh_records_list()

    def setup_ui(self):
        self.status_label = ttk.Label(self.root, text="Готов к записи", font=("Arial", 11))
        self.status_label.pack(pady=(10, 2))

        self.timer_label = ttk.Label(self.root, text="00:00:00", font=("Arial", 22, "bold"))
        self.timer_label.pack(pady=2)

        gain_frame = ttk.Frame(self.root)
        gain_frame.pack(pady=5, fill="x", padx=20)
        ttk.Label(gain_frame, text="Громкость микрофона (%):").pack(side=tk.LEFT)
        self.gain_slider = ttk.Scale(self.root, from_=0, to=300, orient='horizontal', variable=self.gain_var)
        self.gain_slider.pack(fill="x", padx=20)

        # Ползунок перемотки
        ttk.Label(self.root, text="Перемотка:").pack(anchor="w", padx=20, pady=(8, 0))
        self.progress_slider = ttk.Scale(self.root, from_=0, to=100, orient='horizontal', 
                                         variable=self.progress_var, command=self.seek_audio)
        self.progress_slider.pack(fill="x", padx=20)

        # Кнопки записи
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        self.btn_start = ttk.Button(btn_frame, text="▶ Запись", command=self.start_recording)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_stop = ttk.Button(btn_frame, text="⏹ Стоп", command=self.stop_recording, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # Список записей
        self.records_listbox = tk.Listbox(self.root, height=9)
        self.records_listbox.pack(padx=20, fill="x")

        # Управление плеером
        p_frame = ttk.Frame(self.root)
        p_frame.pack(pady=10)
        ttk.Button(p_frame, text="🔊 Слушать", command=self.start_playback).pack(side=tk.LEFT, padx=5)
        ttk.Button(p_frame, text="⏹ Стоп", command=self.stop_playing).pack(side=tk.LEFT, padx=5)
        ttk.Button(p_frame, text="🔄 Обновить", command=self.refresh_records_list).pack(side=tk.LEFT, padx=5)

    # --- ЗАПИСЬ ---
    def start_recording(self):
        self.is_recording = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_label.config(text="Идёт запись...")
        self.start_time = time.time()
        self.update_timer()

        threading.Thread(target=self._record_thread, daemon=True).start()

    def stop_recording(self):
        self.is_recording = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_label.config(text="Запись сохранена")
        self.refresh_records_list()

    def update_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            hrs, mins = divmod(mins, 60)
            self.timer_label.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")
            self.root.after(500, self.update_timer)

    def _record_thread(self):
        p = pyaudio.PyAudio()
        
        # Поиск loopback устройства (звук Windows)
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            loopback_device = None
            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        loopback_device = loopback
                        break
            else:
                loopback_device = default_speakers
        except Exception:
            loopback_device = None

        # Поиск микрофона
        try:
            mic_device = p.get_default_input_device_info()
        except Exception:
            mic_device = None

        if not loopback_device and not mic_device:
            messagebox.showerror("Ошибка", "Аудиоустройства ввода не обнаружены!")
            self.stop_recording()
            p.terminate()
            return

        desk_stream = None
        mic_stream = None

        if loopback_device:
            desk_stream = p.open(format=pyaudio.paInt16,
                                 channels=loopback_device["maxInputChannels"],
                                 rate=int(loopback_device["defaultSampleRate"]),
                                 input=True,
                                 input_device_index=loopback_device["index"],
                                 frames_per_buffer=CHUNK)

        if mic_device:
            mic_stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=RATE,
                                input=True,
                                input_device_index=mic_device["index"],
                                frames_per_buffer=CHUNK)

        recorded_frames = []

        while self.is_recording:
            if desk_stream:
                d_raw = desk_stream.read(CHUNK, exception_on_overflow=False)
                d_data = np.frombuffer(d_raw, dtype=np.int16)
                if loopback_device["maxInputChannels"] == 1:
                    d_data = np.repeat(d_data, 2)
            else:
                d_data = np.zeros(CHUNK * 2, dtype=np.int16)

            if mic_stream:
                m_raw = mic_stream.read(CHUNK, exception_on_overflow=False)
                m_data = np.frombuffer(m_raw, dtype=np.int16)
                m_data = np.repeat(m_data, 2)
            else:
                m_data = np.zeros(CHUNK * 2, dtype=np.int16)

            mic_gain = self.gain_var.get() / 100.0
            mixed = (d_data.astype(np.float32) * DESKTOP_GAIN) + (m_data.astype(np.float32) * mic_gain)
            mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

            recorded_frames.append(mixed.tobytes())

        for s in (desk_stream, mic_stream):
            if s:
                s.stop_stream()
                s.close()
        p.terminate()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(SAVE_DIR, f"rec_{timestamp}.wav")
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(b''.join(recorded_frames))

    # --- ПЛЕЕР ---
    def start_playback(self):
        sel = self.records_listbox.curselection()
        if not sel:
            return
        
        path = os.path.join(SAVE_DIR, self.records_listbox.get(sel[0]))
        self.stop_playing()

        self.wf = wave.open(path, 'rb')
        self.audio_data = self.wf.readframes(self.wf.getnframes())
        self.sample_width = self.wf.getsampwidth()
        self.channels = self.wf.getnchannels()
        self.rate = self.wf.getframerate()
        self.wf.close()

        self.is_playing = True
        self.play_pos = 0
        threading.Thread(target=self._play_thread, daemon=True).start()

    def _play_thread(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(self.sample_width),
                        channels=self.channels,
                        rate=self.rate,
                        output=True)

        frame_size = self.channels * self.sample_width
        chunk_bytes = CHUNK * frame_size
        total_len = len(self.audio_data)

        while self.is_playing and self.play_pos < total_len:
            end = min(self.play_pos + chunk_bytes, total_len)
            chunk = self.audio_data[self.play_pos:end]
            stream.write(chunk)
            self.play_pos = end

            if total_len > 0:
                prog = (self.play_pos / total_len) * 100
                self.is_seeking = True
                self.progress_var.set(prog)
                self.is_seeking = False

        stream.stop_stream()
        stream.close()
        p.terminate()
        self.is_playing = False

    def seek_audio(self, val):
        if getattr(self, 'is_seeking', False):
            return

        if self.audio_data:
            frame_size = self.channels * self.sample_width
            target_byte = int((float(val) / 100) * len(self.audio_data))
            self.play_pos = target_byte - (target_byte % frame_size)

            if not self.is_playing:
                self.is_playing = True
                threading.Thread(target=self._play_thread, daemon=True).start()

    def stop_playing(self):
        self.is_playing = False
        self.progress_var.set(0)
        self.play_pos = 0

    def refresh_records_list(self):
        self.records_listbox.delete(0, tk.END)
        if os.path.exists(SAVE_DIR):
            for f in sorted(os.listdir(SAVE_DIR), reverse=True):
                if f.endswith(".wav"):
                    self.records_listbox.insert(tk.END, f)

if __name__ == "__main__":
    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()