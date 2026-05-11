#!/usr/bin/env python3
"""
OCR Auto Typer — Full MVP
Screen region → OCR → auto keyboard output

Dependencies:
    pip install pyautogui pytesseract opencv-python numpy pillow pyperclip keyboard

Tesseract binary must also be installed:
    Windows : https://github.com/UB-Mannheim/tesseract/wiki
    macOS   : brew install tesseract
    Linux   : sudo apt install tesseract-ocr
"""

# ─────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
import pyautogui
import pyperclip
import pytesseract
import keyboard
from PIL import Image, ImageTk

# ─────────────────────────────────────────────
# Config  (edit these as needed)
# ─────────────────────────────────────────────
HOTKEY          = "F8"          # hotkey that triggers capture + type
TYPE_DELAY      = 1.5           # seconds to wait before typing starts (switch window)
TYPE_INTERVAL   = 0.02          # seconds between each keypress (ASCII mode)
USE_CLIPBOARD   = True          # True  → paste via clipboard (supports Unicode)
                                # False → pyautogui.write() ASCII-only
LIVE_MODE       = False         # True  → continuously OCR every LIVE_INTERVAL seconds
LIVE_INTERVAL   = 2.0           # seconds between live OCR sweeps
TESSERACT_CMD   = ""            # leave "" to use system PATH
                                # Windows example: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
LANG            = "eng"         # tesseract language(s), e.g. "eng+hin"

# ─────────────────────────────────────────────
# Tesseract path (optional override)
# ─────────────────────────────────────────────
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ─────────────────────────────────────────────
# Global state
# ─────────────────────────────────────────────
selected_region = None   # (x, y, w, h)
live_running    = False
live_thread     = None

# ─────────────────────────────────────────────
# Step 1 — Screen region selector (tkinter)
# ─────────────────────────────────────────────
class RegionSelector:
    """Full-screen transparent overlay; user drags a rectangle."""

    def __init__(self):
        self.root   = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.25)
        self.root.attributes("-topmost", True)
        self.root.config(cursor="crosshair", bg="black")

        self.canvas = tk.Canvas(self.root, cursor="crosshair", bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x = self.start_y = 0
        self.rect    = None
        self.region  = None

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>",            lambda e: self.root.destroy())

        tk.Label(
            self.root,
            text="Drag to select region • Esc to cancel",
            fg="white", bg="black",
            font=("Helvetica", 14)
        ).place(relx=0.5, rely=0.02, anchor="n")

    def _on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="lime", width=2
        )

    def _on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        w, h   = x2 - x1, y2 - y1
        if w > 10 and h > 10:
            self.region = (x1, y1, w, h)
        self.root.destroy()

    def select(self):
        self.root.mainloop()
        return self.region


def pick_region():
    """Open the region selector and return (x, y, w, h) or None."""
    selector = RegionSelector()
    return selector.select()


# ─────────────────────────────────────────────
# Step 2 — Screenshot capture
# ─────────────────────────────────────────────
def capture_region(region):
    """
    Capture the given screen region.
    region: (x, y, w, h)
    Returns: PIL Image
    """
    x, y, w, h = region
    screenshot = pyautogui.screenshot(region=(x, y, w, h))
    return screenshot


# ─────────────────────────────────────────────
# Step 3 — OpenCV image preprocessing
# ─────────────────────────────────────────────
def preprocess_image(pil_img):
    """
    Improve OCR accuracy with:
      • Upscaling (2×)
      • Grayscale conversion
      • Otsu binarisation
      • Non-local-means denoising
    Returns a preprocessed PIL Image.
    """
    img = np.array(pil_img)

    # Upscale small captures — Tesseract works best at 300 dpi+
    h, w = img.shape[:2]
    if w < 600 or h < 100:
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Otsu threshold (works on both light-on-dark and dark-on-light text)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, h=10, templateWindowSize=7, searchWindowSize=21)

    return Image.fromarray(denoised)


# ─────────────────────────────────────────────
# Step 4 — OCR text extraction
# ─────────────────────────────────────────────
def extract_text(pil_img, lang=LANG):
    """
    Run Tesseract OCR on the preprocessed image.
    Returns raw text string.
    """
    config = r"--oem 3 --psm 6"   # LSTM engine, assume uniform block of text
    text   = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    return text


# ─────────────────────────────────────────────
# Step 5 — Text cleaning / processing
# ─────────────────────────────────────────────
def clean_text(text, mode="single_line"):
    """
    Clean OCR output.

    mode="single_line" — collapse everything to one line (good for UI labels / code snippets)
    mode="preserve"    — keep paragraph breaks, just trim trailing whitespace
    """
    if mode == "single_line":
        # Replace newlines with space, collapse multiple spaces
        text = " ".join(text.split())
    else:
        # Preserve intentional blank lines (paragraphs), trim trailing whitespace per line
        lines = [line.rstrip() for line in text.splitlines()]
        # Collapse 3+ consecutive blank lines to 2
        result, blanks = [], 0
        for line in lines:
            if line == "":
                blanks += 1
                if blanks <= 2:
                    result.append(line)
            else:
                blanks = 0
                result.append(line)
        text = "\n".join(result).strip()

    # Remove common OCR artifacts
    text = text.replace("\x0c", "")     # form-feed character
    text = text.replace("\x00", "")     # null bytes

    return text


# ─────────────────────────────────────────────
# Step 6 — Auto typing engine
# ─────────────────────────────────────────────
def type_text(text, delay=TYPE_DELAY, use_clipboard=USE_CLIPBOARD):
    """
    Type text into the currently active window after a brief delay.

    use_clipboard=True  → copies to clipboard, pastes with Ctrl+V
                          (supports Unicode, special chars, much faster)
    use_clipboard=False → uses pyautogui.write() keystroke simulation
                          (ASCII only, ~0.02 s per character)
    """
    if not text.strip():
        print("[OCR] No text detected — nothing to type.")
        return

    print(f"[OCR] Detected text:\n{text}\n")
    print(f"[OCR] Typing in {delay:.1f}s — switch to target window now…")
    time.sleep(delay)

    if use_clipboard:
        original_clipboard = pyperclip.paste()   # save so we can restore
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyperclip.copy(original_clipboard)        # restore clipboard
    else:
        # ASCII-safe fallback — strips non-ASCII characters
        ascii_text = text.encode("ascii", errors="replace").decode("ascii")
        pyautogui.write(ascii_text, interval=TYPE_INTERVAL)

    print("[OCR] Done typing.")


# ─────────────────────────────────────────────
# Full pipeline (single run)
# ─────────────────────────────────────────────
def run_pipeline(region, clean_mode="single_line"):
    """
    Execute the full OCR → type pipeline for a given region.
    """
    print(f"\n[OCR] Capturing region {region}…")
    screenshot = capture_region(region)

    print("[OCR] Preprocessing image…")
    processed  = preprocess_image(screenshot)

    print("[OCR] Extracting text…")
    raw_text   = extract_text(processed)

    print("[OCR] Cleaning text…")
    clean      = clean_text(raw_text, mode=clean_mode)

    type_text(clean)


# ─────────────────────────────────────────────
# Live mode (continuous OCR loop)
# ─────────────────────────────────────────────
def _live_loop(region, interval):
    global live_running
    print(f"[OCR] Live mode active — OCR every {interval}s. Press {HOTKEY} to stop.")
    while live_running:
        screenshot = capture_region(region)
        processed  = preprocess_image(screenshot)
        raw_text   = extract_text(processed)
        clean      = clean_text(raw_text)
        if clean:
            print(f"[OCR Live] {clean}")
            type_text(clean, delay=0)
        time.sleep(interval)
    print("[OCR] Live mode stopped.")


def start_live_mode(region):
    global live_running, live_thread
    live_running = True
    live_thread  = threading.Thread(target=_live_loop, args=(region, LIVE_INTERVAL), daemon=True)
    live_thread.start()


def stop_live_mode():
    global live_running
    live_running = False


# ─────────────────────────────────────────────
# Hotkey handler
# ─────────────────────────────────────────────
def on_hotkey():
    global selected_region, live_running

    if LIVE_MODE:
        if live_running:
            stop_live_mode()
        else:
            if selected_region is None:
                print("[OCR] No region selected — open region selector first.")
                return
            start_live_mode(selected_region)
        return

    # Single-shot mode
    if selected_region is None:
        print("[OCR] No region set — opening selector…")
        region = pick_region()
        if region is None:
            print("[OCR] Selection cancelled.")
            return
        selected_region = region

    threading.Thread(target=run_pipeline, args=(selected_region,), daemon=True).start()


# ─────────────────────────────────────────────
# Simple status tray window
# ─────────────────────────────────────────────
def launch_tray():
    """
    Small always-on-top status window with:
      • Select region button
      • Status label
      • Exit button
    """
    root = tk.Tk()
    root.title("OCR Auto Typer")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.geometry("340x160+40+40")

    status_var = tk.StringVar(value=f"Ready — press {HOTKEY} to capture & type")

    tk.Label(root, text="OCR Auto Typer", font=("Helvetica", 13, "bold")).pack(pady=(14, 4))
    status_lbl = tk.Label(root, textvariable=status_var, wraplength=300,
                          font=("Helvetica", 10), fg="#555")
    status_lbl.pack(pady=4)

    def select_region_ui():
        global selected_region
        root.withdraw()
        time.sleep(0.2)
        region = pick_region()
        root.deiconify()
        if region:
            selected_region = region
            status_var.set(f"Region set: {region}\nPress {HOTKEY} to OCR & type")
        else:
            status_var.set("Selection cancelled.")

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Select Region",
              command=select_region_ui, width=14).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Run Now",
              command=lambda: (
                  threading.Thread(target=run_pipeline,
                                   args=(selected_region,), daemon=True).start()
                  if selected_region else
                  messagebox.showwarning("No region", "Select a region first.")
              ), width=10).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Exit",
              command=root.destroy, width=8).pack(side=tk.LEFT, padx=6)

    # Register global hotkey
    keyboard.add_hotkey(HOTKEY, on_hotkey, suppress=False)
    print(f"[OCR] Hotkey registered: {HOTKEY}")
    print(f"[OCR] Clipboard mode  : {USE_CLIPBOARD}")
    print(f"[OCR] Live mode       : {LIVE_MODE}")

    root.mainloop()

    # Cleanup on close
    keyboard.unhook_all()


# ─────────────────────────────────────────────
# CLI entry point (headless, no tray)
# ─────────────────────────────────────────────
def cli_mode():
    """Run without the tray window: select region once, then loop on hotkey."""
    print("[OCR] CLI mode — opening region selector…")
    region = pick_region()
    if not region:
        print("[OCR] No region selected. Exiting.")
        sys.exit(0)

    global selected_region
    selected_region = region
    print(f"[OCR] Region set to {region}")
    print(f"[OCR] Press {HOTKEY} to capture & type. Press Ctrl+C to quit.")

    keyboard.add_hotkey(HOTKEY, on_hotkey, suppress=False)
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[OCR] Exiting.")
        keyboard.unhook_all()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Pass --cli flag for headless / terminal use
    if "--cli" in sys.argv:
        cli_mode()
    else:
        launch_tray()