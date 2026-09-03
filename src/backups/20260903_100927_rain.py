#!/usr/bin/env python3
"""
MatrixVision Rain — based on MatrixMix logic
Terminal digital rain + camera brightness drive
ESC open/close settings menu, Space/Enter to confirm
"""

import cv2
import numpy as np
import os
import sys
import time
import shutil
import json
import threading
import queue
import select
import termios
import tty

# ---- 字符集（与 MatrixMix 一致）----
KANA_CH = list("アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポッャュョ")
ASCII_CH = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:.=*+-<>|")
MIX_CH = KANA_CH + ASCII_CH
CHARS = MIX_CH


def _is_kana(ch):
    if not ch:
        return False
    c = ord(ch[0])
    return (0x30A0 <= c <= 0x30FF) or (0xFF66 <= c <= 0xFF9F)


MATRIXMIX_FPS = max(4, int(os.environ.get("MATRIXMIX_FPS", "16")))
MATRIXMIX_SPEED = float(os.environ.get("MATRIXMIX_SPEED", "1"))
MATRIXMIX_AUDIO = int(os.environ.get("MATRIXMIX_AUDIO", "1"))
MATRIXMIX_QUERY = os.environ.get("MATRIXMIX_QUERY", "ytsearch1:lofi hip hop radio")
MATRIXMIX_AUDIO_PRESETS = [
    ("DEFAULT", "ytsearch1:lofi hip hop radio"),
    ("LOFI 1",   "ytsearch1:lofi hip hop radio -live"),
    ("JAZZ",     "ytsearch1:lofi jazz radio -live"),
    ("AMBIENT",  "ytsearch1:ambient electronic music -live"),
    ("SYNTH",    "ytsearch1:synthwave radio -live"),
    ("PIANO",    "ytsearch1:piano study music -live"),
]
MATRIXMIX_AUDIO_QUERY = os.environ.get("MATRIXMIX_AUDIO_QUERY", "")
RUN_INVERT = True
CONTRAST_LEVEL = int(os.environ.get("MATRIXMIX_CONTRAST", "2"))
EDGE_LEVEL = int(os.environ.get("MATRIXMIX_EDGE", "2"))
VERSION = "0.2.0"
save_message = None
save_message_until = 0
audio = None
_audio_init_lock = threading.Lock()
_audio_init_seq = 0
audio_query = MATRIXMIX_AUDIO_QUERY or MATRIXMIX_QUERY
audio_status = ""
CAMERA_ENABLED = True

def _bg_init(expected_seq, query):
    global audio, AUDIO_ENABLED, audio_status
    engine = None
    status = None
    try:
        engine = AudioEngine(query=query)
        with _audio_init_lock:
            if _audio_init_seq != expected_seq:
                if engine is not None:
                    try:
                        engine.stop()
                    except Exception:
                        pass
                return
            if engine.ready:
                audio = engine
                status = "ready"
            elif engine.error:
                AUDIO_ENABLED = False
                status = f"error: {engine.error}"
    except Exception as e:
        with _audio_init_lock:
            if _audio_init_seq == expected_seq:
                AUDIO_ENABLED = False
        status = f"error: {e}"
    if status is not None:
        audio_status = status

def _start_audio_async(query=None):
    global _audio_init_seq
    q = query if query is not None else audio_query
    with _audio_init_lock:
        seq = _audio_init_seq + 1
        _audio_init_seq = seq
    threading.Thread(target=_bg_init, args=(seq, q), daemon=True).start()

OUT = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT, exist_ok=True)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "matrixvision.json")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(contrast, edge, fps=16, speed=1.0, audio=True, audio_query="", camera_enabled=True):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "contrast": contrast,
                "edge": edge,
                "fps": fps,
                "speed": speed,
                "audio": audio,
                "audio_query": audio_query,
                "camera_enabled": camera_enabled,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def backup_version():
    try:
        ts = time.strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(BACKUP_DIR, f"{ts}_rain.py")
        shutil.copy2(__file__, dst)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.py')])
        while len(backups) > 20:
            os.remove(os.path.join(BACKUP_DIR, backups.pop(0)))
    except Exception:
        pass


class AudioEngine:
    def __init__(self, query=None):
        self.proc_ffmpeg = None
        self.proc_ffplay = None
        self.audio_enabled = bool(MATRIXMIX_AUDIO)
        self.energy = 0.0
        self._sum_sq = 0
        self._n = 0
        self._W = 400
        self._ready = False
        self._error = None
        if not self.audio_enabled:
            self._error = "audio disabled"
            return
        query = query or MATRIXMIX_QUERY
        yt_dlp = os.path.expanduser('~/.local/bin/yt-dlp')
        if not os.path.exists(yt_dlp):
            self._error = "yt-dlp not found"
            return
        url = None
        try:
            out = subprocess.check_output([yt_dlp, '--js-runtimes', 'node', '-f', 'bestaudio', '-g', query], stderr=subprocess.DEVNULL, text=True, timeout=30)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if lines:
                url = lines[-1]
        except Exception as e:
            self._error = str(e)
        if not url or not url.startswith('http'):
            self._error = "no audio url"
            return
        try:
            self.proc_ffmpeg = subprocess.Popen(
                ['ffmpeg', '-i', url, '-f', 's16le', '-ac', '1', '-ar', '8000', '-loglevel', 'error', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
            )
        except Exception as e:
            self._error = str(e)
            return

        ffplay_done = threading.Event()
        ffplay_proc = [None]
        ffplay_err = [None]
        def _launch_ffplay():
            try:
                ffplay_proc[0] = subprocess.Popen(
                    ['ffplay', '-nodisp', '-loglevel', 'error', '-f', 's16le', '-ar', '8000', '-ch_layout', 'mono', '-i', '-'],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception as e:
                ffplay_err[0] = e
            ffplay_done.set()

        launch_t = threading.Thread(target=_launch_ffplay, daemon=True)
        launch_t.start()
        if not ffplay_done.wait(timeout=8):
            self._error = "ffplay start timeout"
            try:
                self.proc_ffmpeg.kill()
            except Exception:
                pass
            return
        if ffplay_err[0] is not None:
            self._error = str(ffplay_err[0])
            try:
                self.proc_ffmpeg.kill()
            except Exception:
                pass
            return
        self.proc_ffplay = ffplay_proc[0]
        self._ready = True
        pump_t = threading.Thread(target=self._pump, daemon=True)
        pump_t.start()

    def _pump(self):
        if not self.proc_ffmpeg or not self.proc_ffmpeg.stdout:
            return
        try:
            while True:
                buf = self.proc_ffmpeg.stdout.read(4096)
                if not buf:
                    break
                if self.proc_ffplay and self.proc_ffplay.stdin and not self.proc_ffplay.stdin.closed:
                    try:
                        self.proc_ffplay.stdin.write(buf)
                    except Exception:
                        pass
                for i in range(0, len(buf) - 1, 2):
                    s = int.from_bytes(buf[i:i+2], byteorder='little', signed=True)
                    self._sum_sq += s * s
                    self._n += 1
                    if self._n >= self._W:
                        rms = (self._sum_sq / self._n) ** 0.5 / 32768.0
                        lvl = min(1.0, rms * 9)
                        target = lvl if lvl > self.energy else self.energy + (lvl - self.energy) * 0.5
                        if lvl <= self.energy:
                            target = self.energy + (lvl - self.energy) * 0.12
                        self.energy = target
                        self._sum_sq = 0
                        self._n = 0
        except Exception:
            pass

    @property
    def ready(self):
        return self._ready

    @property
    def error(self):
        return self._error

    def stop(self):
        self._ready = False
        self.energy = 0.0
        ffplay = self.proc_ffplay
        ffmpeg = self.proc_ffmpeg
        self.proc_ffplay = None
        self.proc_ffmpeg = None
        try:
            if ffplay is not None and ffplay.stdin and not ffplay.stdin.closed:
                try:
                    ffplay.stdin.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if ffmpeg is not None:
                ffmpeg.kill()
                try:
                    ffmpeg.wait(timeout=2)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if ffplay is not None:
                ffplay.kill()
                try:
                    ffplay.wait(timeout=2)
                except Exception:
                    pass
        except Exception:
            pass


import subprocess


def capture_gray_resized(cap, rows, cols, cam_w=1280, cam_h=720, invert=False, contrast_level=0, edge_level=0):
    ok, frame = cap.read()
    if not ok:
        return None

    cam_h = max(1, cam_h)
    cam_w = max(1, cam_w)
    out_h = max(1, rows)
    out_w = max(1, cols)

    cam_aspect = cam_w / cam_h
    # The output is rendered into terminal cells, and each row is visually taller
    # than one cell is wide. Compensate the target aspect so the camera frame
    # isn't displayed stretched taller than its real proportions.
    cell_aspect = 1.2
    visual_term_aspect = out_w / (out_h * cell_aspect)

    if cam_aspect > visual_term_aspect:
        crop_w = max(1, int(round(cam_h * visual_term_aspect)))
        crop_h = cam_h
        x0 = max(0, (cam_w - crop_w) // 2)
        frame = frame[:, x0:x0 + crop_w]
    else:
        crop_h = max(1, int(round(cam_w / visual_term_aspect)))
        crop_w = cam_w
        y0 = max(0, (cam_h - crop_h) // 2)
        frame = frame[y0:y0 + crop_h, :]

    scale = max(out_w / max(1, frame.shape[1]), out_h / max(1, frame.shape[0]))
    scaled_w = max(1, int(round(frame.shape[1] * scale)))
    scaled_h = max(1, int(round(frame.shape[0] * scale)))

    resized = cv2.resize(frame, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    y0 = max(0, (scaled_h - out_h) // 2)
    x0 = max(0, (scaled_w - out_w) // 2)
    result = gray[y0:y0 + out_h, x0:x0 + out_w]
    if result.shape[0] != out_h or result.shape[1] != out_w:
        result = cv2.resize(result, (out_w, out_h), interpolation=cv2.INTER_AREA)

    if invert:
        result = cv2.bitwise_not(result)

    if contrast_level > 0:
        clahe = cv2.createCLAHE(clipLimit=float(contrast_level), tileGridSize=(8, 8))
        result = clahe.apply(result)

    if edge_level > 0:
        gx = cv2.Sobel(result, cv2.CV_16S, 1, 0, ksize=3)
        gy = cv2.Sobel(result, cv2.CV_16S, 0, 1, ksize=3)
        gx = gx.astype(np.float32)
        gy = gy.astype(np.float32)
        mag = cv2.magnitude(gx, gy)
        edge_map = cv2.convertScaleAbs(mag)
        result = cv2.addWeighted(result, 0.5, edge_map, 0.5, 0)

    return result


class RainGrid:
    def __init__(self, rows, logicalCols):
        self.rows = rows
        self.logicalCols = logicalCols
        self.bright = [np.random.rand(logicalCols).astype(np.float32) * 0.35 for _ in range(rows)]
        self.chars = [[np.random.choice(CHARS) for _ in range(logicalCols)] for _ in range(rows)]
        self.prev = [['' for _ in range(logicalCols)] for _ in range(rows)]
        self.heads = [(-np.random.rand() * rows) for _ in range(logicalCols)]
        self.colSpeed = [(0.6 + np.random.rand() * 0.8) for _ in range(logicalCols)]
        self.cam_bright = [np.zeros(logicalCols, dtype=np.float32) for _ in range(rows)]
        self.prev_cam_bright = [np.zeros(logicalCols, dtype=np.float32) for _ in range(rows)]

    def reset(self, rows):
        self.rows = rows
        self.bright = [np.random.rand(self.logicalCols).astype(np.float32) * 0.35 for _ in range(rows)]
        self.chars = [[np.random.choice(CHARS) for _ in range(self.logicalCols)] for _ in range(rows)]
        self.prev = [['' for _ in range(self.logicalCols)] for _ in range(rows)]
        self.heads = [(-np.random.rand() * rows) for _ in range(self.logicalCols)]
        self.colSpeed = [(0.6 + np.random.rand() * 0.8) for _ in range(self.logicalCols)]
        self.cam_bright = [np.zeros(self.logicalCols, dtype=np.float32) for _ in range(rows)]
        self.prev_cam_bright = [np.zeros(self.logicalCols, dtype=np.float32) for _ in range(rows)]
    def update(self, gray, speed_mult=1.0, audio_energy=0.0):
        rows = self.rows
        lc = self.logicalCols
        if gray is not None and gray.shape[0] == rows and gray.shape[1] == lc:
            cam = gray.astype(np.float32) / 255.0
            for y in range(rows):
                np.maximum(self.cam_bright[y], cam[y], out=self.cam_bright[y])
                self.cam_bright[y] *= 0.85
            energy = max(float(cam.mean()), audio_energy)
        else:
            for y in range(rows):
                self.cam_bright[y] *= 0.85
            energy = audio_energy
        speed = (0.14 + energy * 0.45) * speed_mult
        spawnP = 0.22 + 0.4 * energy
        # Fade rain trails and move heads.
        for y in range(rows):
            br = self.bright[y]
            for x in range(lc):
                br[x] *= 0.96
        for x in range(lc):
            prevHy = int(self.heads[x])
            self.heads[x] += speed * self.colSpeed[x]
            hy = int(self.heads[x])
            for yy in range(prevHy + 1, hy + 1):
                if 0 <= yy < rows:
                    self.chars[yy][x] = np.random.choice(CHARS)
                    self.bright[yy][x] = 1.0
            if self.heads[x] > rows + 2:
                if np.random.rand() < spawnP * 0.18:
                    self.heads[x] = -np.random.rand() * rows * 0.6

        # Camera layer: change characters only when brightness changes.
        for y in range(rows):
            cb = self.cam_bright[y]
            prev = self.prev_cam_bright[y]
            br = self.bright[y]
            ch = self.chars[y]
            for x in range(lc):
                if cb[x] > br[x] and cb[x] > 0.08:
                    delta = abs(cb[x] - prev[x])
                    if delta > 0.05 and np.random.rand() < 0.4:
                        ch[x] = np.random.choice(CHARS)
            np.copyto(prev, cb)

    def _cell_str(self, y, x):
        b = float(max(self.bright[y][x], self.cam_bright[y][x]))
        c = self.chars[y][x]
        if b < 0.06:
            return '\x1b[0m  '
        if b > 0.92:
            col = '\x1b[38;2;190;255;190m'
        else:
            g = max(0, min(255, int(b * 255)))
            col = f'\x1b[38;2;0;{g};0m'
        if c in (' ', '') or c is None:
            body = '  '
        elif _is_kana(c):
            body = c
        else:
            body = c + ' '
        return col + body

    def draw(self):
        out = ''
        rows = self.rows
        lc = self.logicalCols
        for y in range(rows):
            x = 0
            while x < lc:
                cur = self._cell_str(y, x)
                if cur != self.prev[y][x]:
                    run = ''
                    sx = x
                    while x < lc and self._cell_str(y, x) != self.prev[y][x]:
                        cs = self._cell_str(y, x)
                        run += cs
                        self.prev[y][x] = cs
                        x += 1
                    out += f'\x1b[{y + 1};{sx * 2 + 1}H{run}'
                else:
                    x += 1
        if out:
            sys.stdout.write(out)
            sys.stdout.flush()


def draw_settings_overlay(term_rows, term_cols, selected, contrast, edge, audio_enabled=True, camera_enabled=True, audio_query="", save_msg=None, audio_status=""):
    header = f"MatrixVision  v{VERSION}"
    preset_names = [p[0] for p in MATRIXMIX_AUDIO_PRESETS]
    try:
        query_idx = next((i for i, (_, url) in enumerate(MATRIXMIX_AUDIO_PRESETS) if url == audio_query), 0)
    except Exception:
        query_idx = 0
    display_val = preset_names[query_idx]

    items = [
        ("CONTRAST", ["0","1","2","3"], max(0, min(3, int(contrast)))),
        ("EDGE", ["0","1","2","3"], max(0, min(3, int(edge)))),
        ("AUDIO", ["OFF","ON"], 1 if audio_enabled else 0),
        ("CAMERA", ["OFF","ON"], 1 if camera_enabled else 0),
        ("AUDIO_QUERY", preset_names, query_idx),
        ("SAVE", None, None),
        ("QUIT", None, None),
    ]

    panel_w = min(term_cols - 2, max(len(header) + 8, len(f"AUDIO_QUERY: [ {display_val} ]") + 8, len("← → adjust  ↑ ↓ select   Space/Enter confirm   ESC close") + 4))
    panel_h = 13
    sx = max(1, (term_cols - panel_w) // 2)
    sy = max(1, (term_rows - panel_h) // 2)
    out = "\x1b[?25h\x1b[H"
    for y in range(term_rows):
        row = ""
        for x in range(term_cols):
            if sy <= y < sy + panel_h and sx <= x < sx + panel_w:
                if y == sy:
                    row += "╔" if x == sx else ("═" if x < sx + panel_w - 1 else ("╗" if x == sx + panel_w - 1 else " "))
                elif y == sy + panel_h - 1:
                    row += "╚" if x == sx else ("═" if x < sx + panel_w - 1 else ("╝" if x == sx + panel_w - 1 else " "))
                else:
                    row += "║" if x in (sx, sx + panel_w - 1) else " "
            else:
                row += " "
        out += row + "\x1b[0m\n"
    title_x = sx + 2 + max(0, (panel_w - 2 - len(header)) // 2)
    out += f"\x1b[{sy + 1};{title_x}H\x1b[1;37m{header}\x1b[0m"
    for row_idx, (label, values, cur) in enumerate(items):
        y = sy + 2 + row_idx
        x = sx + 2
        marker = "▸ " if row_idx == selected else "  "
        if values is not None:
            cur_val = values[cur]
            if row_idx == 4 and audio_status:
                line = f"{marker}{label}: [ {cur_val}  {audio_status} ]"
            else:
                line = f"{marker}{label}: [ {cur_val} ]"
        else:
            line = f"{marker}{label}"
        out += f"\x1b[{y};{x}H{line}\x1b[0m"

    if save_msg:
        out += f"\x1b[{sy + panel_h - 2};{sx + 2}H\x1b[32m{save_msg}\x1b[0m"
    else:
        hint = "← → adjust  ↑ ↓ select   Space/Enter confirm   ESC close"
        out += f"\x1b[{sy + panel_h - 2};{sx + 2}H{hint}\x1b[0m"
    sys.stdout.write(out)
    sys.stdout.flush()


def init_term():
    sys.stdout.write("\x1b[?25l\x1b[2J\x1b[3J\x1b[H")
    sys.stdout.flush()


def restore_term():
    try:
        sys.stdout.write("\x1b[?25h\x1b[0m\x1b[2J\x1b[H")
        sys.stdout.flush()
    except Exception:
        pass


def find_camera():
    candidates = []
    for i in range(4):
        p = f"/dev/video{i}"
        if os.path.exists(p):
            candidates.append((i, p))
    return candidates


def run(cam_idx=0, cam_w=1280, cam_h=720):
    global CONTRAST_LEVEL, EDGE_LEVEL, AUDIO_ENABLED, save_message, save_message_until, audio, audio_query, _audio_init_seq, CAMERA_ENABLED, audio_status
    backup_version()
    try:
        my_pid = os.getpid()
        for entry in os.listdir('/proc'):
            if not entry.isdigit():
                continue
            pid = int(entry)
            if pid == my_pid:
                continue
            try:
                cmdline = open(f'/proc/{pid}/cmdline', 'rb').read().replace(b'\x00', b' ').decode('utf-8', 'replace')
            except Exception:
                continue
            if 'matrixvision/src/rain.py' in cmdline or 'MatrixVision' in cmdline:
                try:
                    os.kill(pid, 9)
                except Exception:
                    pass
                time.sleep(0.2)
    except Exception:
        pass

    cams = find_camera()
    if not cams:
        print("未找到摄像头设备 /dev/video0..3", file=sys.stderr)
        return
    cam = cams[min(cam_idx, len(cams) - 1)]
    cap = cv2.VideoCapture(cam[0], cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)
    cap.set(cv2.CAP_PROP_AUDIO_STREAM, 0)
    if not cap.isOpened():
        print(f"无法打开摄像头 {cam[1]}", file=sys.stderr)
        return

    for _ in range(20):
        cap.read()
    cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or cam_w
    cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or cam_h

    term_cols, term_rows = shutil.get_terminal_size((80, 24))
    term_rows = max(10, term_rows)
    term_cols = max(20, term_cols)

    logicalCols = term_cols // 2
    rows = term_rows

    cfg = load_config()
    CONTRAST_LEVEL = int(cfg.get("contrast", CONTRAST_LEVEL))
    EDGE_LEVEL = int(cfg.get("edge", EDGE_LEVEL))
    AUDIO_ENABLED = bool(cfg.get("audio", True)) and bool(MATRIXMIX_AUDIO)
    audio_query = cfg.get("audio_query", "") or MATRIXMIX_QUERY
    CAMERA_ENABLED = bool(cfg.get("camera_enabled", True))

    init_term()
    audio = None

    if AUDIO_ENABLED and MATRIXMIX_AUDIO:
        _start_audio_async(audio_query)

    sys.stderr.write(f"MatrixVision v{VERSION}  {cam[1]}  {cam_w}x{cam_h} -> {logicalCols}x{rows}\n")
    time.sleep(0.5)

    paused = False
    settings_open = False
    settings_selected = 0
    save_message = None
    save_message_until = 0
    last = time.time()
    frames = 0
    fps = 0
    frame_idx = 0
    target_frame_time = 1.0 / MATRIXMIX_FPS
    camera_interval = max(1, int(MATRIXMIX_FPS / 12))

    grid = RainGrid(rows, logicalCols)

    key_q = queue.Queue()

    input_fd = None
    input_old_attr = None
    tty_file = None
    try:
        if sys.stdin.isatty():
            input_fd = sys.stdin.fileno()
            input_old_attr = termios.tcgetattr(input_fd)
            tty.setcbreak(input_fd)
        else:
            tty_file = open('/dev/tty', 'r', buffering=1, closefd=True)
            input_fd = tty_file.fileno()
            input_old_attr = termios.tcgetattr(input_fd)
            tty.setcbreak(input_fd)
    except Exception:
        input_fd = None
        input_old_attr = None
        if tty_file is not None:
            try:
                tty_file.close()
            except Exception:
                pass
            tty_file = None

    def _reader(fd):
        try:
            while True:
                try:
                    r, _, _ = select.select([fd], [], [], 0.1)
                    if r:
                        ch = os.read(fd, 1)
                        if ch:
                            key_q.put(ch.decode('utf-8', 'replace'))
                except Exception:
                    break
        except Exception:
            pass

    if input_fd is not None:
        t = threading.Thread(target=_reader, args=(input_fd,), daemon=True)
        t.start()

    try:
        while True:
            if not paused and not settings_open:
                gray = None
                if CAMERA_ENABLED and frame_idx % camera_interval == 0:
                    gray = capture_gray_resized(cap, rows, logicalCols, cam_w=cam_w, cam_h=cam_h, invert=RUN_INVERT, contrast_level=CONTRAST_LEVEL, edge_level=EDGE_LEVEL)
                audio_energy = audio.energy if audio is not None and AUDIO_ENABLED else 0.0
                grid.update(gray, MATRIXMIX_SPEED, audio_energy=audio_energy)
                grid.draw()

                frames += 1
                now = time.time()
                if now - last >= 0.5:
                    fps = int(frames / (now - last))
                    frames = 0
                    last = now
                    sys.stderr.write(f"\rFPS: {fps:2d}                    ")
                    sys.stderr.flush()

                frame_idx += 1
                time.sleep(target_frame_time)

            try:
                ch = key_q.get_nowait()
            except Exception:
                time.sleep(0.005)
                continue

            first = ch
            if first == '\x1b':
                rem = ''
                try:
                    rem = key_q.get(timeout=0.12)
                    rem += key_q.get(timeout=0.12)
                except Exception:
                    rem = ''
                if len(rem) >= 2 and rem[0] == '[' and rem[1] in ('A', 'B', 'C', 'D'):
                    if settings_open:
                        if rem[1] == 'A':
                            settings_selected = (settings_selected - 1) % 7
                        elif rem[1] == 'B':
                            settings_selected = (settings_selected + 1) % 7
                        elif rem[1] == 'C':
                            if settings_selected in (0, 1, 2, 5, 6):
                                _apply_setting(settings_selected)
                            elif settings_selected == 3:
                                CAMERA_ENABLED = not CAMERA_ENABLED
                            elif settings_selected == 4:
                                presets = MATRIXMIX_AUDIO_PRESETS
                                for i, (name, url) in enumerate(presets):
                                    if url == audio_query:
                                        audio_query = presets[(i - 1) % len(presets)][1]
                                        break
                                if AUDIO_ENABLED:
                                    _apply_setting(4)
                        elif rem[1] == 'D':
                            if settings_selected in (0, 1, 2, 5, 6):
                                _apply_setting(settings_selected)
                            elif settings_selected == 3:
                                CAMERA_ENABLED = not CAMERA_ENABLED
                            elif settings_selected == 4:
                                presets = MATRIXMIX_AUDIO_PRESETS
                                for i, (name, url) in enumerate(presets):
                                    if url == audio_query:
                                        audio_query = presets[(i + 1) % len(presets)][1]
                                        break
                                if AUDIO_ENABLED:
                                    _apply_setting(4)
                        draw_settings_overlay(term_rows, term_cols, settings_selected, CONTRAST_LEVEL, EDGE_LEVEL, AUDIO_ENABLED, CAMERA_ENABLED, audio_query, save_message if save_message else None, audio_status)
                elif not rem:
                    if settings_open:
                        settings_open = False
                        init_term()
                        sys.stdout.write("\x1b[?25h")
                        sys.stdout.flush()
                        save_message = None
                    else:
                        settings_open = True
                        settings_selected = 0
                        draw_settings_overlay(term_rows, term_cols, settings_selected, CONTRAST_LEVEL, EDGE_LEVEL, AUDIO_ENABLED, CAMERA_ENABLED, audio_query, save_message if save_message else None, audio_status)
                        try:
                            while True:
                                key_q.get_nowait()
                        except Exception:
                            pass
                continue

            if settings_open:
                if first == '\x1b':
                    settings_open = False
                    init_term()
                    sys.stdout.write("\x1b[?25h")
                    sys.stdout.flush()
                    save_message = None
                    audio_status = ""
                    continue
                elif first in ('\x1b[A', '\x1b[B', '\x1b[C', '\x1b[D'):
                    if first == '\x1b[A':
                        settings_selected = (settings_selected - 1) % 7
                    elif first == '\x1b[B':
                        settings_selected = (settings_selected + 1) % 7
                    elif first == '\x1b[C':
                        if settings_selected == 3:
                            CAMERA_ENABLED = not CAMERA_ENABLED
                        elif settings_selected == 4:
                            presets = MATRIXMIX_AUDIO_PRESETS
                            for i, (name, url) in enumerate(presets):
                                if url == audio_query:
                                    audio_query = presets[(i - 1) % len(presets)][1]
                                    break
                        else:
                            settings_selected = (settings_selected + 1) % 7
                    elif first == '\x1b[D':
                        if settings_selected == 3:
                            CAMERA_ENABLED = not CAMERA_ENABLED
                        elif settings_selected == 4:
                            presets = MATRIXMIX_AUDIO_PRESETS
                            for i, (name, url) in enumerate(presets):
                                if url == audio_query:
                                    audio_query = presets[(i + 1) % len(presets)][1]
                                    break
                        else:
                            settings_selected = (settings_selected + 1) % 7
                elif first in ('\r', ' '):
                    _apply_setting(settings_selected)
                if audio_status == "connecting..." and audio is not None and getattr(audio, 'ready', False):
                    audio_status = "ready"
                draw_settings_overlay(term_rows, term_cols, settings_selected, CONTRAST_LEVEL, EDGE_LEVEL, AUDIO_ENABLED, CAMERA_ENABLED, audio_query, save_message if save_message else None, audio_status)
                continue

            if first in ('q', 'Q', '\x03'):
                break
            elif first == ' ':
                paused = not paused
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if audio is not None:
                audio.stop()
        except Exception:
            pass
        if input_old_attr is not None and input_fd is not None:
            try:
                termios.tcsetattr(input_fd, termios.TCSADRAIN, input_old_attr)
            except Exception:
                pass
        if tty_file is not None:
            try:
                tty_file.close()
            except Exception:
                pass
        try:
            restore_term()
        except Exception:
            pass
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass
        sys.stderr.write("\n")


def _apply_setting(idx):
    global CONTRAST_LEVEL, EDGE_LEVEL, AUDIO_ENABLED, save_message, save_message_until, audio, audio_query, _audio_init_seq, CAMERA_ENABLED, audio_status
    if idx == 0:
        CONTRAST_LEVEL = (CONTRAST_LEVEL + 1) % 4
    elif idx == 1:
        EDGE_LEVEL = (EDGE_LEVEL + 1) % 4
    elif idx == 2:
        if AUDIO_ENABLED:
            try:
                if audio is not None:
                    audio.stop()
            except Exception:
                pass
            with _audio_init_lock:
                _audio_init_seq += 1
            AUDIO_ENABLED = False
            audio = None
            audio_status = ""
        else:
            AUDIO_ENABLED = True
            audio_status = "connecting..."
            _start_audio_async(audio_query)
    elif idx == 3:
        CAMERA_ENABLED = not CAMERA_ENABLED
        if not CAMERA_ENABLED:
            try:
                if grid is not None:
                    grid.cam_bright = [np.zeros_like(v) for v in grid.cam_bright]
                    grid.prev_cam_bright = [np.zeros_like(v) for v in grid.prev_cam_bright]
            except Exception:
                pass
    elif idx == 4:
        presets = MATRIXMIX_AUDIO_PRESETS
        for i, (name, url) in enumerate(presets):
            if url == audio_query:
                audio_query = presets[(i + 1) % len(presets)][1]
                break
        if AUDIO_ENABLED:
            try:
                if audio is not None:
                    audio.stop()
            except Exception:
                pass
            audio_status = "connecting..."
            _start_audio_async(audio_query)
    elif idx == 5:
        save_config(CONTRAST_LEVEL, EDGE_LEVEL, fps=MATRIXMIX_FPS, speed=MATRIXMIX_SPEED, audio=AUDIO_ENABLED, audio_query=audio_query, camera_enabled=CAMERA_ENABLED)
        save_message = "✔ Saved"
        save_message_until = time.time() + 1.5
    elif idx == 6:
        raise KeyboardInterrupt


if __name__ == "__main__":
    run(0)
