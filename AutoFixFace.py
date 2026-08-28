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
    python3 AutoFixFace.py

--------------------------------------------------------------------------
Những gì được nâng cấp so với bản gốc
--------------------------------------------------------------------------
- Giao diện làm lại theo tông màu xám - trắng, chia khối rõ ràng, dễ nhìn.
- Nếu đã dùng AutoTokenAPI.py để lưu nhiều Page, có thể CHỌN Page muốn
  đăng ngay trong danh sách xổ xuống, Page ID/Access Token tự điền.
- Nút "Kiểm tra kết nối" xác nhận Token còn dùng được + hiển thị tên Page.
- Đếm số ký tự từng bài viết ngay dưới ô nhập.
- Xuất / nhập nhanh 5 bài viết ra 1 file .txt để chỉnh sửa hàng loạt.
- Khi đang chạy tự động, có đồng hồ đếm ngược tới lần đăng kế tiếp.
- Có thể bật "làm lệch giờ đăng ngẫu nhiên" (±phút) để lịch đăng tự nhiên
  hơn thay vì đúng y hệt mỗi X phút.
- Tự thử lại tối đa 2 lần nếu đăng bài gặp lỗi mạng tạm thời.
- Tránh lặp lại đúng ảnh/video vừa dùng ở lần đăng ngay trước (giống cách
  bản gốc đã tránh lặp bài viết).
- Lưu lại lịch sử đăng bài (thời gian, kết quả, nội dung rút gọn) vào file
  post_history.log, xem lại được ngay trong ứng dụng qua nút "Lịch sử".
- Nhật ký hoạt động có màu (xanh = thành công, đỏ = lỗi, cam = cảnh báo).
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
HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "post_history.log")
GRAPH_API_VERSION = "v19.0"
NUM_POSTS = 5
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

DEFAULT_MEDIA_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "VidFaceAutoFix")


# ==========================================================================
# Giao diện: tông màu xám - trắng dùng chung
# ==========================================================================
class Theme:
    bg = "#f3f4f6"
    surface = "#ffffff"
    border = "#dfe2e6"
    header_bg = "#2f333a"
    header_fg = "#ffffff"
    text = "#23262b"
    subtext = "#6b7280"
    primary = "#3f4551"
    primary_hover = "#54596a"
    success = "#1f9254"
    error = "#d1453d"
    warning = "#b7791f"
    entry_bg = "#ffffff"
    step_bg = "#eceef1"


def setup_style(root):
    root.configure(bg=Theme.bg)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    base_font = ("Segoe UI", 10)
    bold_font = ("Segoe UI", 10, "bold")
    title_font = ("Segoe UI", 13, "bold")

    style.configure("TFrame", background=Theme.bg)
    style.configure("Card.TFrame", background=Theme.surface)
    style.configure("Header.TFrame", background=Theme.header_bg)

    style.configure("TLabel", background=Theme.bg, foreground=Theme.text, font=base_font)
    style.configure("Card.TLabel", background=Theme.surface, foreground=Theme.text, font=base_font)
    style.configure("Sub.TLabel", background=Theme.surface, foreground=Theme.subtext, font=("Segoe UI", 9))
    style.configure("Step.TLabel", background=Theme.surface, foreground=Theme.text, font=bold_font)
    style.configure("Header.TLabel", background=Theme.header_bg, foreground=Theme.header_fg, font=title_font)
    style.configure("HeaderSub.TLabel", background=Theme.header_bg, foreground="#c7cad1", font=("Segoe UI", 9))
    style.configure("Status.TLabel", background=Theme.bg, foreground=Theme.subtext, font=("Segoe UI", 9))
    style.configure("Count.TLabel", background=Theme.surface, foreground=Theme.subtext, font=("Segoe UI", 8))
    style.configure("Running.TLabel", background=Theme.bg, foreground=Theme.success, font=bold_font)
    style.configure("Stopped.TLabel", background=Theme.bg, foreground=Theme.subtext, font=bold_font)

    style.configure(
        "TButton", background=Theme.primary, foreground="#ffffff", font=bold_font,
        padding=(12, 7), borderwidth=0, focusthickness=0,
    )
    style.map(
        "TButton",
        background=[("active", Theme.primary_hover), ("disabled", "#c3c6cc")],
        foreground=[("disabled", "#f0f0f0")],
    )

    style.configure(
        "Secondary.TButton", background=Theme.step_bg, foreground=Theme.text, font=base_font,
        padding=(10, 6), borderwidth=1, relief="flat",
    )
    style.map("Secondary.TButton", background=[("active", "#dfe2e6")])

    style.configure(
        "Danger.TButton", background="#e5484d", foreground="#ffffff", font=bold_font,
        padding=(12, 7), borderwidth=0,
    )
    style.map("Danger.TButton", background=[("active", "#c93f43"), ("disabled", "#e6b3b3")])

    style.configure("TEntry", fieldbackground=Theme.entry_bg, borderwidth=1, relief="solid", padding=6)
    style.configure("TCombobox", fieldbackground=Theme.entry_bg, padding=5)
    style.configure("TCheckbutton", background=Theme.surface, foreground=Theme.text, font=base_font)

    style.configure(
        "Treeview", background=Theme.surface, fieldbackground=Theme.surface,
        foreground=Theme.text, rowheight=24, borderwidth=0, font=base_font,
    )
    style.configure("Treeview.Heading", background=Theme.step_bg, foreground=Theme.text, font=bold_font)
    style.map("Treeview", background=[("selected", "#d7dbe0")], foreground=[("selected", Theme.text)])

    return style


def make_card(parent, **pack_kwargs):
    outer = tk.Frame(parent, bg=Theme.border)
    outer.pack(**pack_kwargs)
    inner = tk.Frame(outer, bg=Theme.surface)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    return inner


def log_to_text(widget, msg, tag="info"):
    widget.configure(state="normal")
    widget.insert("end", msg + "\n", tag)
    widget.see("end")
    widget.configure(state="disabled")


def configure_log_tags(widget):
    widget.tag_configure("success", foreground=Theme.success)
    widget.tag_configure("error", foreground=Theme.error)
    widget.tag_configure("warning", foreground=Theme.warning)
    widget.tag_configure("info", foreground=Theme.subtext)


# ==========================================================================
# Xử lý dữ liệu
# ==========================================================================
def pick_random_media(folder, exclude_path=None):
    """Quét thư mục, trả về (đường_dẫn, loại) với loại là 'image' hoặc 'video'.
    Trả về (None, None) nếu thư mục không tồn tại hoặc không có file hợp lệ.
    Nếu có nhiều hơn 1 lựa chọn, tránh chọn lại đúng exclude_path (file dùng
    ở lần đăng ngay trước) khi có thể."""
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
    if exclude_path and len(candidates) > 1:
        filtered = [c for c in candidates if c[0] != exclude_path]
        if filtered:
            candidates = filtered
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
        "jitter_minutes": 0,
        "posts": [""] * NUM_POSTS,
        "media_folder": DEFAULT_MEDIA_FOLDER,
        "use_media": True,
    }


def save_config(data):
    # Gộp (merge) với cấu hình hiện có thay vì ghi đè toàn bộ, để không làm
    # mất danh sách "pages" / fb_app_id / fb_app_secret mà AutoTokenAPI.py
    # đã lưu trước đó trong cùng file fb_autopost_config.json.
    current = load_config()
    current.update(data)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)


def append_history(entry):
    try:
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_history(limit=200):
    if not os.path.exists(HISTORY_PATH):
        return []
    rows = []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return rows[-limit:]


class FBAutoPosterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FB Auto Poster - Đăng bài tự động")
        self.root.geometry("720x900")
        self.root.minsize(660, 720)

        setup_style(root)

        self.config_data = load_config()
        self.running = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.last_posted_index = None
        self.last_media_path = None
        self.next_post_at = None
        self.countdown_job = None
        self.page_name_cache = None

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        header = ttk.Frame(self.root, style="Header.TFrame")
        header.pack(fill="x")
        inner = ttk.Frame(header, style="Header.TFrame")
        inner.pack(fill="x", padx=18, pady=14)
        ttk.Label(inner, text="FB Auto Poster", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            inner, text="Tự động đăng bài + ảnh/video ngẫu nhiên lên Fanpage",
            style="HeaderSub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        canvas_wrap = tk.Frame(self.root, bg=Theme.bg)
        canvas_wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(canvas_wrap, bg=Theme.bg, highlightthickness=0)
        vscroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = ttk.Frame(canvas)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_configure(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(body_id, width=canvas.winfo_width())

        body.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        pad = dict(padx=16, pady=(14, 0))

        # ---- Card: kết nối Page ----
        card_conn = make_card(body, fill="x", **pad)
        ttk.Label(card_conn, text="Kết nối Fanpage", style="Step.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(10, 6)
        )

        saved_pages = self.config_data.get("pages") or []
        self.saved_pages = saved_pages
        ttk.Label(card_conn, text="Page đã lưu:", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(14, 4))
        self.page_choice_var = tk.StringVar()
        page_names = [f'{p.get("name")}  (ID: {p.get("id")})' for p in saved_pages]
        self.page_combo = ttk.Combobox(
            card_conn, textvariable=self.page_choice_var, values=page_names, state="readonly", width=40,
        )
        self.page_combo.grid(row=1, column=1, sticky="w", pady=4)
        self.page_combo.bind("<<ComboboxSelected>>", self._on_page_selected)
        if not saved_pages:
            self.page_combo.configure(values=["(chưa có Page nào - dùng AutoTokenAPI.py để lấy)"])

        ttk.Label(card_conn, text="Page ID:", style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=(14, 4))
        self.page_id_var = tk.StringVar(value=self.config_data.get("page_id", ""))
        ttk.Entry(card_conn, textvariable=self.page_id_var, width=40).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(card_conn, text="Access Token:", style="Card.TLabel").grid(row=3, column=0, sticky="w", padx=(14, 4))
        self.token_var = tk.StringVar(value=self.config_data.get("access_token", ""))
        ttk.Entry(card_conn, textvariable=self.token_var, width=40, show="*").grid(row=3, column=1, sticky="w", pady=4)

        conn_btn_row = ttk.Frame(card_conn, style="Card.TFrame")
        conn_btn_row.grid(row=4, column=0, columnspan=3, sticky="w", padx=14, pady=(4, 12))
        ttk.Button(conn_btn_row, text="Kiểm tra kết nối", style="Secondary.TButton", command=self.test_connection).pack(
            side="left"
        )
        self.connection_status_var = tk.StringVar(value="Chưa kiểm tra kết nối.")
        ttk.Label(card_conn, textvariable=self.connection_status_var, style="Sub.TLabel").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 10)
        )

        # ---- Card: lịch đăng ----
        card_sched = make_card(body, fill="x", **pad)
        ttk.Label(card_sched, text="Lịch đăng bài", style="Step.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(10, 6)
        )
        ttk.Label(card_sched, text="Đăng mỗi (phút):", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=(14, 4))
        self.interval_var = tk.StringVar(value=str(self.config_data.get("interval_minutes", 60)))
        ttk.Entry(card_sched, textvariable=self.interval_var, width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(card_sched, text="± lệch ngẫu nhiên (phút):", style="Card.TLabel").grid(
            row=1, column=2, sticky="w", padx=(20, 4)
        )
        self.jitter_var = tk.StringVar(value=str(self.config_data.get("jitter_minutes", 0)))
        ttk.Entry(card_sched, textvariable=self.jitter_var, width=8).grid(row=1, column=3, sticky="w", padx=(0, 14))

        ttk.Label(card_sched, text="Thư mục ảnh/video:", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", padx=(14, 4), pady=(8, 0)
        )
        self.media_folder_var = tk.StringVar(value=self.config_data.get("media_folder", DEFAULT_MEDIA_FOLDER))
        frm_media_path = ttk.Frame(card_sched, style="Card.TFrame")
        frm_media_path.grid(row=2, column=1, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Entry(frm_media_path, textvariable=self.media_folder_var, width=44).pack(side="left")
        ttk.Button(frm_media_path, text="Chọn...", style="Secondary.TButton", command=self._browse_media_folder).pack(
            side="left", padx=(6, 0)
        )

        self.use_media_var = tk.BooleanVar(value=self.config_data.get("use_media", True))
        ttk.Checkbutton(
            card_sched, text="Kèm 1 ảnh/video ngẫu nhiên từ thư mục trên khi đăng",
            variable=self.use_media_var,
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=14, pady=(8, 12))

        # ---- Card: nội dung bài viết ----
        card_posts = make_card(body, fill="x", **pad)
        top_row = ttk.Frame(card_posts, style="Card.TFrame")
        top_row.pack(fill="x", padx=14, pady=(10, 4))
        ttk.Label(top_row, text="Nội dung bài viết (chọn ngẫu nhiên mỗi lần đăng)", style="Step.TLabel").pack(
            side="left"
        )
        ttk.Button(top_row, text="Xuất ra .txt", style="Secondary.TButton", command=self._export_posts).pack(
            side="right", padx=(6, 0)
        )
        ttk.Button(top_row, text="Nhập từ .txt", style="Secondary.TButton", command=self._import_posts).pack(
            side="right"
        )

        self.post_boxes = []
        self.count_labels = []
        for i in range(NUM_POSTS):
            ttk.Label(card_posts, text=f"Bài viết {i + 1}:", style="Card.TLabel").pack(
                anchor="w", padx=14, pady=(6, 0)
            )
            box = scrolledtext.ScrolledText(
                card_posts, height=3, wrap="word", bg=Theme.entry_bg, fg=Theme.text,
                relief="solid", borderwidth=1, font=("Segoe UI", 10),
            )
            box.pack(fill="x", padx=14, pady=(2, 0))
            existing = self.config_data.get("posts", [""] * NUM_POSTS)
            if i < len(existing):
                box.insert("1.0", existing[i])
            count_lbl = ttk.Label(card_posts, text="0 ký tự", style="Count.TLabel")
            count_lbl.pack(anchor="e", padx=14, pady=(0, 8))
            box.bind("<KeyRelease>", lambda _e, idx=i: self._update_count(idx))
            self.post_boxes.append(box)
            self.count_labels.append(count_lbl)
            self._update_count(i)

        # ---- Card: điều khiển ----
        card_ctrl = make_card(body, fill="x", **pad)
        frm_ctrl = ttk.Frame(card_ctrl, style="Card.TFrame")
        frm_ctrl.pack(fill="x", padx=14, pady=12)

        status_col = ttk.Frame(frm_ctrl, style="Card.TFrame")
        status_col.pack(side="left", fill="x", expand=True)
        self.status_var = tk.StringVar(value="Đang dừng")
        self.status_label = ttk.Label(status_col, textvariable=self.status_var, style="Stopped.TLabel")
        self.status_label.pack(anchor="w")
        self.countdown_var = tk.StringVar(value="")
        ttk.Label(status_col, textvariable=self.countdown_var, style="Sub.TLabel").pack(anchor="w")

        btn_col = ttk.Frame(frm_ctrl, style="Card.TFrame")
        btn_col.pack(side="right")
        ttk.Button(btn_col, text="Lưu cấu hình", style="Secondary.TButton", command=self.save).pack(
            side="left", padx=4
        )
        ttk.Button(btn_col, text="Đăng thử ngay 1 bài", style="Secondary.TButton", command=self.post_now_test).pack(
            side="left", padx=4
        )
        self.stop_btn = ttk.Button(btn_col, text="■ Dừng", style="Danger.TButton", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        self.start_btn = ttk.Button(btn_col, text="▶ Bắt đầu", command=self.start)
        self.start_btn.pack(side="left", padx=4)

        # ---- Card: nhật ký ----
        card_log = make_card(body, fill="both", expand=True, padx=16, pady=(14, 16))
        log_top = ttk.Frame(card_log, style="Card.TFrame")
        log_top.pack(fill="x", padx=14, pady=(10, 4))
        ttk.Label(log_top, text="Nhật ký hoạt động", style="Step.TLabel").pack(side="left")
        ttk.Button(log_top, text="Lịch sử đăng bài", style="Secondary.TButton", command=self._open_history).pack(
            side="right"
        )

        self.log_box = scrolledtext.ScrolledText(
            card_log, height=12, state="disabled", bg=Theme.surface, fg=Theme.text,
            relief="flat", font=("Consolas", 9), padx=8, pady=6,
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        configure_log_tags(self.log_box)

        if saved_pages:
            self.log(f"Đã nạp {len(saved_pages)} Page đã lưu, chọn Page ở khung trên cùng nếu cần đổi.", "info")

    # ------------------------------------------------------------------
    def _browse_media_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.media_folder_var.get() or os.path.expanduser("~"))
        if chosen:
            self.media_folder_var.set(chosen)

    def _on_page_selected(self, _event=None):
        idx = self.page_combo.current()
        if idx < 0 or idx >= len(self.saved_pages):
            return
        page = self.saved_pages[idx]
        self.page_id_var.set(page.get("id", ""))
        self.token_var.set(page.get("access_token", ""))
        self.connection_status_var.set(f'Đã chọn Page "{page.get("name")}" - bấm "Kiểm tra kết nối" để xác nhận.')

    def _update_count(self, idx):
        text = self.post_boxes[idx].get("1.0", "end").strip()
        self.count_labels[idx].config(text=f"{len(text)} ký tự")

    def log(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        log_to_text(self.log_box, f"[{ts}] {msg}", tag)

    def get_posts(self):
        return [box.get("1.0", "end").strip() for box in self.post_boxes]

    # ---------- Xuất / nhập bài viết ----------

    def _export_posts(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text file", "*.txt")], initialfile="bai_viet.txt"
        )
        if not path:
            return
        posts = self.get_posts()
        with open(path, "w", encoding="utf-8") as f:
            f.write(("\n---\n").join(posts))
        self.log(f"Đã xuất {len(posts)} bài viết ra {os.path.basename(path)}.", "success")

    def _import_posts(self):
        path = filedialog.askopenfilename(filetypes=[("Text file", "*.txt"), ("Tất cả file", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không đọc được file: {e}")
            return
        parts = [p.strip() for p in content.split("---")]
        for i, box in enumerate(self.post_boxes):
            box.delete("1.0", "end")
            if i < len(parts):
                box.insert("1.0", parts[i])
            self._update_count(i)
        self.log(f"Đã nhập bài viết từ {os.path.basename(path)}.", "success")

    # ---------- Lưu / kiểm tra cấu hình ----------

    def save(self, silent=False):
        data = {
            "page_id": self.page_id_var.get().strip(),
            "access_token": self.token_var.get().strip(),
            "interval_minutes": self.interval_var.get().strip() or "60",
            "jitter_minutes": self.jitter_var.get().strip() or "0",
            "posts": self.get_posts(),
            "media_folder": self.media_folder_var.get().strip(),
            "use_media": bool(self.use_media_var.get()),
        }
        save_config(data)
        self.config_data = data
        if not silent:
            self.log("Đã lưu cấu hình vào fb_autopost_config.json", "success")

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
        try:
            jitter = float(self.jitter_var.get().strip() or "0")
            if jitter < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Lỗi", "Độ lệch ngẫu nhiên phải là số không âm.")
            return None
        if jitter >= interval:
            messagebox.showerror("Lỗi", "Độ lệch ngẫu nhiên phải nhỏ hơn khoảng thời gian đăng.")
            return None
        if not page_id or not token:
            messagebox.showerror("Lỗi", "Bạn cần nhập Page ID và Access Token.")
            return None
        if not posts:
            messagebox.showerror("Lỗi", "Cần ít nhất 1 bài viết có nội dung.")
            return None
        return page_id, token, interval, jitter, posts

    def test_connection(self):
        page_id = self.page_id_var.get().strip()
        token = self.token_var.get().strip()
        if not page_id or not token:
            messagebox.showerror("Lỗi", "Nhập Page ID và Access Token trước.")
            return
        self.connection_status_var.set("Đang kiểm tra...")
        threading.Thread(target=self._do_test_connection, args=(page_id, token), daemon=True).start()

    def _do_test_connection(self, page_id, token):
        try:
            resp = requests.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}",
                params={"fields": "name,fan_count", "access_token": token},
                timeout=20,
            )
            data = resp.json()
            if resp.status_code == 200 and "name" in data:
                self.page_name_cache = data["name"]
                msg = f'Kết nối OK - đang trỏ tới Page "{data["name"]}".'
                self.root.after(0, lambda: self.connection_status_var.set(msg))
                self.root.after(0, lambda: self.log(msg, "success"))
            else:
                err = data.get("error", {}).get("message", str(data))
                self.root.after(0, lambda: self.connection_status_var.set(f"Kết nối lỗi: {err}"))
                self.root.after(0, lambda: self.log(f"Kiểm tra kết nối thất bại: {err}", "error"))
        except Exception as e:
            self.root.after(0, lambda: self.connection_status_var.set(f"Lỗi kết nối: {e}"))
            self.root.after(0, lambda: self.log(f"Lỗi kết nối khi kiểm tra: {e}", "error"))

    # ---------- Đăng bài ----------

    def post_to_facebook(self, page_id, token, message, media_path=None, media_type=None):
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
        if not self.use_media_var.get():
            return None, None
        folder = self.media_folder_var.get().strip()
        path, mtype = pick_random_media(folder, exclude_path=self.last_media_path)
        if path is None:
            self.log(f"Không tìm thấy ảnh/video hợp lệ trong thư mục: {folder}", "warning")
        return path, mtype

    def post_now_test(self):
        valid = self._validate()
        if not valid:
            return
        page_id, token, _, _, posts = valid
        choice = random.choice(posts)
        media_path, media_type = self._select_media()
        self.log(
            "Đang đăng thử 1 bài..." + (f" (kèm {media_type}: {os.path.basename(media_path)})" if media_path else ""),
            "info",
        )
        threading.Thread(
            target=self._do_post, args=(page_id, token, choice, media_path, media_type), daemon=True
        ).start()

    def _do_post(self, page_id, token, message, media_path=None, media_type=None):
        attempt = 0
        last_err = None
        while attempt <= MAX_RETRIES:
            try:
                ok, data = self.post_to_facebook(page_id, token, message, media_path, media_type)
                if ok:
                    post_id = data.get("id") or data.get("post_id", "?")
                    self.log(f"Đăng thành công. Post ID: {post_id}", "success")
                    append_history(
                        {
                            "time": datetime.datetime.now().isoformat(timespec="seconds"),
                            "status": "success",
                            "post_id": post_id,
                            "message": message[:120],
                            "media": os.path.basename(media_path) if media_path else None,
                        }
                    )
                    if media_path:
                        self.last_media_path = media_path
                    return
                else:
                    last_err = data.get("error", {}).get("message", str(data))
            except Exception as e:
                last_err = str(e)

            attempt += 1
            if attempt <= MAX_RETRIES:
                self.log(f"Đăng thất bại ({last_err}). Thử lại lần {attempt}/{MAX_RETRIES}...", "warning")
                time.sleep(RETRY_DELAY_SECONDS)

        self.log(f"Đăng thất bại sau {MAX_RETRIES} lần thử: {last_err}", "error")
        append_history(
            {
                "time": datetime.datetime.now().isoformat(timespec="seconds"),
                "status": "error",
                "error": last_err,
                "message": message[:120],
                "media": os.path.basename(media_path) if media_path else None,
            }
        )

    def start(self):
        valid = self._validate()
        if not valid:
            return
        self.save(silent=True)
        page_id, token, interval, jitter, posts = valid

        self.running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set(f"Đang chạy - đăng mỗi {interval:g} phút")
        self.status_label.configure(style="Running.TLabel")
        jitter_msg = f" (lệch ngẫu nhiên ±{jitter:g} phút)" if jitter else ""
        self.log(f"Bắt đầu tự động đăng, mỗi {interval:g} phút{jitter_msg}, ngẫu nhiên trong {len(posts)} bài.", "info")

        self.worker_thread = threading.Thread(
            target=self._worker_loop, args=(page_id, token, interval, jitter), daemon=True
        )
        self.worker_thread.start()

    def _worker_loop(self, page_id, token, interval_minutes, jitter_minutes):
        while not self.stop_event.is_set():
            posts = [p for p in self.get_posts() if p]
            if not posts:
                self.log("Không có bài viết nào để đăng, dừng lại.", "warning")
                break

            choices = posts
            if len(posts) > 1 and self.last_posted_index is not None and self.last_posted_index < len(posts):
                choices = [p for idx, p in enumerate(posts) if idx != self.last_posted_index] or posts
            chosen = random.choice(choices)
            self.last_posted_index = posts.index(chosen)

            media_path, media_type = self._select_media()
            if media_path:
                self.log(f"Đính kèm ngẫu nhiên: {os.path.basename(media_path)} ({media_type})", "info")
            self._do_post(page_id, token, chosen, media_path, media_type)

            actual_interval = interval_minutes
            if jitter_minutes:
                actual_interval = max(0.1, interval_minutes + random.uniform(-jitter_minutes, jitter_minutes))
            interval_seconds = actual_interval * 60
            self.next_post_at = time.time() + interval_seconds
            self.root.after(0, self._tick_countdown)

            waited = 0
            while waited < interval_seconds and not self.stop_event.is_set():
                time.sleep(1)
                waited += 1

        self.next_post_at = None
        self.root.after(0, self._on_stopped)

    def _tick_countdown(self):
        if not self.running or self.next_post_at is None:
            self.countdown_var.set("")
            return
        remaining = int(self.next_post_at - time.time())
        if remaining <= 0 or self.stop_event.is_set():
            self.countdown_var.set("")
            return
        mins, secs = divmod(remaining, 60)
        self.countdown_var.set(f"Bài tiếp theo sau: {mins:02d}:{secs:02d}")
        self.countdown_job = self.root.after(1000, self._tick_countdown)

    def _on_stopped(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("Đang dừng")
        self.status_label.configure(style="Stopped.TLabel")
        self.countdown_var.set("")
        if self.countdown_job:
            try:
                self.root.after_cancel(self.countdown_job)
            except Exception:
                pass
            self.countdown_job = None

    def stop(self):
        self.stop_event.set()
        self.log("Đã yêu cầu dừng...", "info")

    # ---------- Lịch sử ----------

    def _open_history(self):
        rows = read_history()
        win = tk.Toplevel(self.root)
        win.title("Lịch sử đăng bài")
        win.geometry("640x420")
        win.configure(bg=Theme.bg)

        ttk.Label(win, text=f"{len(rows)} lần đăng gần nhất", style="TLabel").pack(anchor="w", padx=12, pady=(10, 4))

        columns = ("time", "status", "detail")
        tree = ttk.Treeview(win, columns=columns, show="headings", height=16)
        tree.heading("time", text="Thời gian")
        tree.heading("status", text="Kết quả")
        tree.heading("detail", text="Chi tiết")
        tree.column("time", width=140, anchor="w")
        tree.column("status", width=90, anchor="w")
        tree.column("detail", width=380, anchor="w")
        tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        for row in reversed(rows):
            status = "Thành công" if row.get("status") == "success" else "Lỗi"
            if row.get("status") == "success":
                detail = f'Post ID {row.get("post_id", "?")} - {row.get("message", "")}'
            else:
                detail = f'{row.get("error", "")} - {row.get("message", "")}'
            tree.insert("", "end", values=(row.get("time", ""), status, detail))

        if not rows:
            ttk.Label(win, text="Chưa có lịch sử đăng bài nào.", style="TLabel").pack(padx=12, pady=8)


def main():
    root = tk.Tk()
    app = FBAutoPosterApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
