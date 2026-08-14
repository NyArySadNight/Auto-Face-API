#!/usr/bin/env python3
"""
FB Auto Poster - Đăng bài tự động lên Facebook Page (Fanpage) mỗi X phút,
chọn ngẫu nhiên 1 trong 5 bài đã chuẩn bị, đồng thời tự động chọn ngẫu nhiên
1 ảnh hoặc 1 video trong thư mục con (mặc định: Downloads/VidFaceAutoFix)
để đính kèm theo bài đăng.

Dùng Facebook Graph API chính thức (KHÔNG đăng nhập giả lập trình duyệt),
nên an toàn, không vi phạm điều khoản Facebook và không sợ bị khóa tài khoản.

Cài đặt (1 lần):
    pip install requests
    # Nếu chưa có tkinter (thường có sẵn với Python):
    #   Ubuntu/Debian: sudo apt install python3-tk

Chạy:
    python3 fb_autopost.py

Cách lấy Page ID + Page Access Token: xem hướng dẫn mình gửi kèm ở chat.
Để lấy Long-lived Page Token (dùng được lâu, ~60 ngày, không hết hạn sau
1-2 tiếng), dùng lệnh sau (thay APP_ID, APP_SECRET, SHORT_TOKEN):

    curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?
grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&
fb_exchange_token=SHORT_TOKEN"

Sau đó dùng /me/accounts với long-lived user token để lấy Page token
(Page token lấy từ long-lived user token thường KHÔNG tự hết hạn).
"""

import json
import os
import random
import threading
import time
import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog

import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb_autopost_config.json")
GRAPH_API_VERSION = "v19.0"
NUM_POSTS = 5

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

DEFAULT_MEDIA_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "VidFaceAutoFix")


def pick_random_media(folder):
    """Quét thư mục, trả về (đường_dẫn, loại) với loại là 'image' hoặc 'video'.
    Trả về (None, None) nếu thư mục không tồn tại hoặc không có file hợp lệ."""
    if not folder or not os.path.isdir(folder):
        return None, None
    candidates = []
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGE_EXTS:
                candidates.append((path, "image"))
            elif ext in VIDEO_EXTS:
                candidates.append((path, "video"))
    except Exception:
        return None, None
    if not candidates:
        return None, None
    return random.choice(candidates)


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "page_id": "",
        "access_token": "",
        "interval_minutes": 60,
        "posts": [""] * NUM_POSTS,
        "media_folder": DEFAULT_MEDIA_FOLDER,
        "use_media": True,
    }


def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class FBAutoPosterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FB Auto Poster - Đăng bài tự động")
        self.root.geometry("640x680")

        self.config_data = load_config()
        self.running = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.last_posted_index = None

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        frm_top = ttk.Frame(self.root)
        frm_top.pack(fill="x", **pad)

        ttk.Label(frm_top, text="Page ID:").grid(row=0, column=0, sticky="w")
        self.page_id_var = tk.StringVar(value=self.config_data.get("page_id", ""))
        ttk.Entry(frm_top, textvariable=self.page_id_var, width=40).grid(row=0, column=1, sticky="w")

        ttk.Label(frm_top, text="Access Token:").grid(row=1, column=0, sticky="w")
        self.token_var = tk.StringVar(value=self.config_data.get("access_token", ""))
        ttk.Entry(frm_top, textvariable=self.token_var, width=60, show="*").grid(row=1, column=1, sticky="w")

        ttk.Label(frm_top, text="Đăng mỗi (phút):").grid(row=2, column=0, sticky="w")
        self.interval_var = tk.StringVar(value=str(self.config_data.get("interval_minutes", 60)))
        ttk.Entry(frm_top, textvariable=self.interval_var, width=10).grid(row=2, column=1, sticky="w")

        ttk.Label(frm_top, text="Thư mục ảnh/video:").grid(row=3, column=0, sticky="w")
        self.media_folder_var = tk.StringVar(
            value=self.config_data.get("media_folder", DEFAULT_MEDIA_FOLDER)
        )
        frm_media_path = ttk.Frame(frm_top)
        frm_media_path.grid(row=3, column=1, sticky="w")
        ttk.Entry(frm_media_path, textvariable=self.media_folder_var, width=48).pack(side="left")
        ttk.Button(frm_media_path, text="Chọn...", command=self._browse_media_folder).pack(
            side="left", padx=(5, 0)
        )

        self.use_media_var = tk.BooleanVar(value=self.config_data.get("use_media", True))
        ttk.Checkbutton(
            frm_top,
            text="Kèm 1 ảnh/video ngẫu nhiên từ thư mục trên khi đăng",
            variable=self.use_media_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # 5 post text boxes
        self.post_boxes = []
        for i in range(NUM_POSTS):
            ttk.Label(self.root, text=f"Bài viết {i+1}:").pack(anchor="w", padx=10)
            box = scrolledtext.ScrolledText(self.root, height=4, wrap="word")
            box.pack(fill="x", padx=10, pady=(0, 6))
            existing = self.config_data.get("posts", [""] * NUM_POSTS)
            if i < len(existing):
                box.insert("1.0", existing[i])
            self.post_boxes.append(box)

        # Controls
        frm_ctrl = ttk.Frame(self.root)
        frm_ctrl.pack(fill="x", padx=10, pady=5)

        self.status_var = tk.StringVar(value="Đang dừng")
        ttk.Label(frm_ctrl, textvariable=self.status_var, foreground="blue").pack(side="left")

        self.start_btn = ttk.Button(frm_ctrl, text="▶ Bắt đầu", command=self.start)
        self.start_btn.pack(side="right", padx=5)
        self.stop_btn = ttk.Button(frm_ctrl, text="■ Dừng", command=self.stop, state="disabled")
        self.stop_btn.pack(side="right", padx=5)
        ttk.Button(frm_ctrl, text="Đăng thử ngay 1 bài", command=self.post_now_test).pack(side="right", padx=5)
        ttk.Button(frm_ctrl, text="Lưu cấu hình", command=self.save).pack(side="right", padx=5)

        # Log
        ttk.Label(self.root, text="Nhật ký hoạt động:").pack(anchor="w", padx=10)
        self.log_box = scrolledtext.ScrolledText(self.root, height=12, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _browse_media_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self.media_folder_var.get() or os.path.expanduser("~")
        )
        if chosen:
            self.media_folder_var.set(chosen)

    def log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def get_posts(self):
        return [box.get("1.0", "end").strip() for box in self.post_boxes]

    def save(self, silent=False):
        data = {
            "page_id": self.page_id_var.get().strip(),
            "access_token": self.token_var.get().strip(),
            "interval_minutes": self.interval_var.get().strip() or "60",
            "posts": self.get_posts(),
            "media_folder": self.media_folder_var.get().strip(),
            "use_media": bool(self.use_media_var.get()),
        }
        save_config(data)
        self.config_data = data
        if not silent:
            self.log("Đã lưu cấu hình vào fb_autopost_config.json")

    def _validate(self):
        page_id = self.page_id_var.get().strip()
        token = self.token_var.get().strip()
        posts = [p for p in self.get_posts() if p]
        try:
            interval = float(self.interval_var.get().strip())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Lỗi", "Số phút phải là số dương.")
            return None
        if not page_id or not token:
            messagebox.showerror("Lỗi", "Bạn cần nhập Page ID và Access Token.")
            return None
        if not posts:
            messagebox.showerror("Lỗi", "Cần ít nhất 1 bài viết có nội dung.")
            return None
        return page_id, token, interval, posts

    def post_to_facebook(self, page_id, token, message, media_path=None, media_type=None):
        """
        - Không có media -> đăng bài text thường qua /feed
        - media_type == 'image' -> đăng qua /photos (kèm caption)
        - media_type == 'video' -> đăng qua graph-video.facebook.com/.../videos (kèm description)
        """
        if media_type == "video" and media_path:
            url = f"https://graph-video.facebook.com/{GRAPH_API_VERSION}/{page_id}/videos"
            with open(media_path, "rb") as f:
                files = {"source": f}
                data = {"description": message, "access_token": token}
                resp = requests.post(url, data=data, files=files, timeout=600)
        elif media_type == "image" and media_path:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
            with open(media_path, "rb") as f:
                files = {"source": f}
                data = {"caption": message, "access_token": token}
                resp = requests.post(url, data=data, files=files, timeout=120)
        else:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
            resp = requests.post(url, data={"message": message, "access_token": token}, timeout=30)

        ok = resp.status_code == 200
        return ok, resp.json() if resp.content else {}

    def _select_media(self):
        """Trả về (path, type) nếu tính năng kèm media đang bật và tìm được file, ngược lại (None, None)."""
        if not self.use_media_var.get():
            return None, None
        folder = self.media_folder_var.get().strip()
        path, mtype = pick_random_media(folder)
        if path is None:
            self.log(f"⚠️ Không tìm thấy ảnh/video hợp lệ trong thư mục: {folder}")
        return path, mtype

    def post_now_test(self):
        valid = self._validate()
        if not valid:
            return
        page_id, token, _, posts = valid
        choice = random.choice(posts)
        media_path, media_type = self._select_media()
        self.log("Đang đăng thử 1 bài..." + (f" (kèm {media_type}: {os.path.basename(media_path)})" if media_path else ""))
        threading.Thread(
            target=self._do_post, args=(page_id, token, choice, media_path, media_type), daemon=True
        ).start()

    def _do_post(self, page_id, token, message, media_path=None, media_type=None):
        try:
            ok, data = self.post_to_facebook(page_id, token, message, media_path, media_type)
            if ok:
                post_id = data.get("id") or data.get("post_id", "?")
                self.log(f"✅ Đăng thành công. Post ID: {post_id}")
            else:
                err = data.get("error", {}).get("message", str(data))
                self.log(f"❌ Đăng thất bại: {err}")
        except Exception as e:
            self.log(f"❌ Lỗi kết nối: {e}")

    def start(self):
        valid = self._validate()
        if not valid:
            return
        self.save(silent=True)
        page_id, token, interval, posts = valid

        self.running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set(f"Đang chạy - đăng mỗi {interval:g} phút")
        self.log(f"Bắt đầu tự động đăng, mỗi {interval:g} phút, ngẫu nhiên trong {len(posts)} bài.")

        self.worker_thread = threading.Thread(
            target=self._worker_loop, args=(page_id, token, interval), daemon=True
        )
        self.worker_thread.start()

    def _worker_loop(self, page_id, token, interval_minutes):
        interval_seconds = interval_minutes * 60
        while not self.stop_event.is_set():
            posts = [p for p in self.get_posts() if p]
            if not posts:
                self.log("⚠️ Không có bài viết nào để đăng, dừng lại.")
                break

            # tránh đăng trùng bài ngay lần liền trước, nếu có nhiều hơn 1 bài
            choices = posts
            if len(posts) > 1 and self.last_posted_index is not None and self.last_posted_index < len(posts):
                choices = [p for idx, p in enumerate(posts) if idx != self.last_posted_index] or posts
            chosen = random.choice(choices)
            self.last_posted_index = posts.index(chosen)

            media_path, media_type = self._select_media()
            if media_path:
                self.log(f"🎞️ Đính kèm ngẫu nhiên: {os.path.basename(media_path)} ({media_type})")
            self._do_post(page_id, token, chosen, media_path, media_type)

            # chờ, nhưng kiểm tra stop_event mỗi giây để dừng nhanh khi bấm Dừng
            waited = 0
            while waited < interval_seconds and not self.stop_event.is_set():
                time.sleep(1)
                waited += 1

        self.root.after(0, self._on_stopped)

    def _on_stopped(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("Đang dừng")

    def stop(self):
        self.stop_event.set()
        self.log("Đã yêu cầu dừng...")


def main():
    root = tk.Tk()
    app = FBAutoPosterApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
