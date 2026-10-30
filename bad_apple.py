import imageio.v3 as iio
import numpy as np
import os
import sys
import time
import threading
import glob
from PIL import Image

# ---------- настройки ----------
WIDTH = 100          
HEIGHT = 48          # Уменьшили на 2 строки, чтобы освободить место под субтитры
THRESHOLD = 128      
VIDEO_EXTS = ("mp4", "webm", "mkv", "avi")
AUDIO_EXTS = ("mp3", "wav", "m4a", "ogg")
SUB_FILE = "bad_apple_ru.srt"

CHARS = {
    (0, 0): " ",
    (1, 0): "▄",
    (0, 1): "▀",
    (1, 1): "█",
}

def find_file(exts):
    for ext in exts:
        files = glob.glob(f"*bad*apple*.{ext}") + glob.glob(f"*Bad*Apple*.{ext}")
        if files:
            return files[0]
    return None

def parse_srt(filepath):
    subs = []
    if not os.path.exists(filepath):
        print(f"Внимание: файл субтитров {filepath} не найден. Видео будет без текста.")
        return subs

    def time_to_sec(t_str):
        h, m, s_ms = t_str.split(':')
        s, ms = s_ms.split(',')
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip().split('\n\n')
        for block in content:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                times = lines[1].split(' --> ')
                start = time_to_sec(times[0])
                end = time_to_sec(times[1])
                text = " ".join(lines[2:])
                subs.append((start, end, text))
    return subs

def get_subtitle_at_time(subs, current_time):
    for start, end, text in subs:
        if start <= current_time <= end:
            return text
    return ""

def frame_to_ascii(frame_rgb):
    img = Image.fromarray(frame_rgb)
    img = img.resize((WIDTH, HEIGHT * 2), Image.Resampling.LANCZOS)
    gray = np.array(img.convert("L"))
    binary = (gray < THRESHOLD).astype(np.uint8)
    
    lines = []
    for y in range(0, HEIGHT * 2, 2):
        top = binary[y]
        bottom = binary[y + 1]
        lines.append("".join(CHARS[(t, b)] for t, b in zip(top, bottom)))
    return "\n".join(lines)

def preload_frames(video_path):
    print("Чтение метаданных...")
    try:
        meta = iio.immeta(video_path, plugin="FFMPEG")
        fps = meta.get("fps", 30.0)
    except Exception:
        fps = 30.0
    if isinstance(fps, str): fps = 30.0
    fps = float(fps)
    
    frames = []
    print("Предрендер кадров... (пожалуйста, подожди)")
    for frame_rgb in iio.imiter(video_path, plugin="FFMPEG"):
        frames.append(frame_to_ascii(frame_rgb))
    print(f"Готово: {len(frames)} кадров, {fps:.2f} fps")
    return frames, fps

def play_audio(path, stop_event):
    import pygame
    pygame.mixer.init()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() and not stop_event.is_set():
        time.sleep(0.05)
    pygame.mixer.music.stop()

def main():
    video = find_file(VIDEO_EXTS)
    audio = find_file(AUDIO_EXTS)
    if not video or not audio:
        print("Не найдены видео или аудио файлы.")
        return

    subs = parse_srt(SUB_FILE)
    frames, fps = preload_frames(video)
    if not frames: return

    os.system("")  
    sys.stdout.write("\033[2J\033[?25l")  
    sys.stdout.flush()

    stop_event = threading.Event()
    threading.Thread(target=play_audio, args=(audio, stop_event), daemon=True).start()

    for i in (3, 2, 1):
        sys.stdout.write(f"\033[H\033[2JНачинаем через {i}...\n")
        sys.stdout.flush()
        time.sleep(1)
    
    sys.stdout.write("\033[2J")
    sys.stdout.flush()

    frame_time = 1.0 / fps
    start = time.time()
    last_sub = ""

    try:
        for idx, frame in enumerate(frames):
            current_time = idx * frame_time
            
            # Получаем текущую строку субтитров
            current_sub = get_subtitle_at_time(subs, current_time)
            
            # Очищаем старую строку субтитров, если текст изменился или пропал
            if current_sub != last_sub:
                # Перемещаем курсор вниз (HEIGHT строк) и очищаем строку
                sys.stdout.write(f"\033[{HEIGHT + 1};0H\033[K")
                if current_sub:
                    sys.stdout.write(current_sub)
                sys.stdout.flush()
                last_sub = current_sub

            # Рисуем видео
            sys.stdout.write("\033[H" + frame)
            sys.stdout.flush()
            
            target = start + idx * frame_time
            now = time.time()
            if target > now:
                time.sleep(target - now)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        sys.stdout.write("\033[?25h\033[2J\033[H") 
        sys.stdout.flush()

if __name__ == "__main__":
    main()