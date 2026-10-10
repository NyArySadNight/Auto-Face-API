#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FB Auto Poster & Share Group Pro - ArtTools UI Edition
=====================================================
Tích hợp:
  1) Đăng bài Fanpage tự động qua Facebook Graph API.
  2) Tự động làm mới Access Token & Trả lời tự động Messenger / Bình luận.
  3) Auto Share Group: Điều khiển trình duyệt (Playwright Chrome/Cốc Cốc Profile)
     để giả lập người dùng thật share bài vào các nhóm Facebook.

Cài đặt phụ thuộc:
    pip install PyQt6 requests playwright
    playwright install chromium
"""

import copy
import html
import http.server
import json
import os
import queue
import random
import subprocess
import threading
import time
import datetime
import urllib.parse
import webbrowser
import sys

import requests

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QLineEdit, QFrame, QCheckBox,
    QPlainTextEdit, QTextEdit, QStackedWidget, QScrollArea, QFileDialog,
    QMessageBox, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QLocale
from PyQt6.QtGui import QFont, QDoubleValidator

# Kiểm tra thư viện Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# ==========================================================================
# Hằng số & Cấu hình mặc định
# ==========================================================================
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb_autopost_config.json")
HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "post_history.log")
GRAPH_API_VERSION = "v19.0"
NUM_POSTS = 8
MAX_TARGETS = 8
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

OAUTH_REDIRECT_PORT = 8765
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_REDIRECT_PORT}/"
OAUTH_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts,pages_messaging,pages_manage_engagement"

DEFAULT_REPLY_WEBHOOK_PORT = 8766
DEFAULT_REPLY_VERIFY_TOKEN = "myverifytoken123"
DEFAULT_MSG_RULES = [
    {"keywords": "gia, bao nhieu tien, gia bao nhieu, gia ca", "reply": "Dạ sản phẩm bên em có nhiều mức giá khác nhau ạ 🥰 Anh/chị cho em xin tên sản phẩm quan tâm để em báo giá chính xác nhé!"},
    {"keywords": "ship, giao hang, van chuyen, phi ship", "reply": "Dạ shop có giao hàng toàn quốc ạ 🚚 Anh/chị ở khu vực nào để em kiểm tra phí ship giúp mình ạ?"},
    {"keywords": "xin chao, hello, hi, alo, chao shop", "reply": "Dạ em chào anh/chị 👋 Shop mình có thể hỗ trợ gì cho mình ạ?"},
    {"keywords": "cam on, thank, thanks", "reply": "Dạ em cảm ơn anh/chị đã ủng hộ shop ạ 🥰"},
]
DEFAULT_COMMENT_RULES = [
    {"keywords": "gia, bao nhieu tien, gia bao nhieu", "reply": "Dạ shop đã inbox tư vấn chi tiết giúp mình ạ 💌"},
    {"keywords": "xin chao, hello, hi", "reply": "Dạ em chào anh/chị 👋 Shop mình đã inbox hỗ trợ giúp mình ạ!"},
]
DEFAULT_MESSAGE_REPLY = "Dạ em đã nhận được tin nhắn của anh/chị ạ 🥰 Shop sẽ phản hồi sớm nhất có thể!"
DEFAULT_COMMENT_REPLY = ""

CONTACT_HOTLINE = "0966.785.179"

DEFAULT_REGION_RULES = {
    "ha_long": {
        "label": "🌊 HẠ LONG",
        "rules": [
            {"enabled": True, "keywords": "cao xanh, phuong cao xanh, doc cao xanh",
             "reply": "Dạ bên em có xe chạy Cao Xanh (Hạ Long) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "bai chay, cau bai chay, ben pha bai chay",
             "reply": "Dạ Bãi Cháy là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hạ Long ⇄ Hà Nội / Hải Phòng, lịch chạy: 5h00 - 7h00 - 9h00 - 11h00 - 13h00 - 15h00 - 17h00 - 19h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "hon gai, hongai, cho hon gai",
             "reply": "Dạ có xe qua Hòn Gai ạ 🚙 Anh/chị đi ghép giá 200.000đ/khách, muốn đi riêng thì bao xe 1.000.000đ (4 chỗ) / 1.300.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Hạ Long ⇄ Hà Nội / Hải Phòng và hỗ trợ nhà đất khu vực Hạ Long ạ. Hotline {hotline}",
    },
    "ha_noi": {
        "label": "🏙️ HÀ NỘI",
        "rules": [
            {"enabled": True, "keywords": "my dinh, ben xe my dinh, khu my dinh",
             "reply": "Dạ bên em có xe chạy Mỹ Đình (Hà Nội) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Hotline {hotline}"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh ạ. Hotline {hotline}",
    },
    "hai_phong": {"label": "⚓ HẢI PHÒNG", "rules": [], "default_reply": "Dạ xe Hải Phòng ⇄ Hạ Long / Hà Nội đón trả tận nhà ạ. Hotline {hotline}"},
    "quang_ninh": {"label": "🚩 QUẢNG NINH", "rules": [], "default_reply": "Dạ nhận xe ghép, tiện chuyến toàn tỉnh Quảng Ninh ạ. Hotline {hotline}"},
    "thai_nguyen": {"label": "⛰️ THÁI NGUYÊN", "rules": [], "default_reply": "Dạ tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long bên em chạy hàng ngày ạ. Hotline {hotline}"}
}

REGION_ORDER = ["ha_long", "ha_noi", "hai_phong", "quang_ninh", "thai_nguyen"]

DEFAULT_GLOBAL_REPLY = (
    "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe "
    "tuyến Hạ Long / Hà Nội / Hải Phòng / Quảng Ninh / Thái Nguyên và hỗ trợ "
    "nhà đất các khu vực trên ạ. Hotline {hotline}"
)

def _apply_hotline(value, hotline=None):
    hotline = hotline or CONTACT_HOTLINE
    if isinstance(value, str):
        return value.replace("{hotline}", hotline)
    if isinstance(value, dict):
        for reg in value.values():
            if not isinstance(reg, dict):
                continue
            for rule in reg.get("rules", []) or []:
                rule["reply"] = _apply_hotline(rule.get("reply", ""), hotline)
            reg["default_reply"] = _apply_hotline(reg.get("default_reply", ""), hotline)
    return value

DEFAULT_REGION_RULES = _apply_hotline(DEFAULT_REGION_RULES)
DEFAULT_GLOBAL_REPLY = _apply_hotline(DEFAULT_GLOBAL_REPLY)

def region_label(key):
    reg = DEFAULT_REGION_RULES.get(key) or {}
    return reg.get("label", key)

def count_region_keywords(region_rules):
    total_rules, total_keywords = 0, 0
    for reg in (region_rules or {}).values():
        rules = reg.get("rules", []) if isinstance(reg, dict) else []
        total_rules += len(rules)
        for rule in rules:
            total_keywords += len([k for k in rule.get("keywords", "").split(",") if k.strip()])
    return total_rules, total_keywords

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
DEFAULT_MEDIA_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "VidFaceAutoFix")

COCCOC_EXECUTABLE_PATH = r"C:\Program Files\CocCoc\Browser\Application\browser.exe"
DEFAULT_COCCOC_PROFILE_PATH = r"C:\Users\daon3\AppData\Local\CocCoc\Browser\User Data"

# ==========================================================================
# Xử lý dữ liệu & Config
# ==========================================================================
def pick_random_media(folder, exclude_path=None):
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

def _empty_target():
    return {"enabled": False, "page_id": "", "access_token": "", "name": ""}

def load_config():
    data = None
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
    if data is None:
        data = {}

    targets = data.get("targets")
    if not isinstance(targets, list):
        targets = [_empty_target() for _ in range(MAX_TARGETS)]
    else:
        targets = (targets + [_empty_target() for _ in range(MAX_TARGETS)])[:MAX_TARGETS]
        for t in targets:
            for key, default in _empty_target().items():
                t.setdefault(key, default)

    data["targets"] = targets
    data.setdefault("posts", [""] * NUM_POSTS)
    data.setdefault("interval_minutes", 60)
    data.setdefault("jitter_minutes", 0)
    data.setdefault("media_folder", DEFAULT_MEDIA_FOLDER)
    data.setdefault("use_media", True)
    data.setdefault("fb_app_id", "")
    data.setdefault("fb_app_secret", "")
    data.setdefault("fb_user_token", "")
    data.setdefault("pages", [])

    data.setdefault("reply_webhook_port", DEFAULT_REPLY_WEBHOOK_PORT)
    data.setdefault("reply_verify_token", DEFAULT_REPLY_VERIFY_TOKEN)
    data.setdefault("reply_msg_rules", DEFAULT_MSG_RULES)
    data.setdefault("reply_comment_rules", DEFAULT_COMMENT_RULES)
    data.setdefault("reply_default_message", DEFAULT_MESSAGE_REPLY)
    data.setdefault("reply_default_comment", DEFAULT_COMMENT_REPLY)

    region_rules = data.get("reply_region_rules")
    if not isinstance(region_rules, dict) or not region_rules:
        region_rules = copy.deepcopy(DEFAULT_REGION_RULES)
    else:
        for key in REGION_ORDER:
            reg = region_rules.get(key)
            if not isinstance(reg, dict) or not isinstance(reg.get("rules"), list):
                region_rules[key] = copy.deepcopy(DEFAULT_REGION_RULES[key])
                continue
            reg.setdefault("label", DEFAULT_REGION_RULES[key]["label"])
            reg.setdefault("default_reply", DEFAULT_REGION_RULES[key]["default_reply"])
            for rule in reg["rules"]:
                rule.setdefault("enabled", True)
                rule.setdefault("keywords", "")
                rule.setdefault("reply", "")
    data["reply_region_rules"] = region_rules

    enabled = data.get("reply_region_enabled")
    if not isinstance(enabled, dict):
        enabled = {}
    for key in REGION_ORDER:
        enabled.setdefault(key, True)
    data["reply_region_enabled"] = enabled

    data.setdefault("reply_enable_message", True)
    data.setdefault("reply_enable_comment", True)
    data.setdefault("reply_region_priority", True)
    data.setdefault("reply_global_default", DEFAULT_GLOBAL_REPLY)

    data.setdefault("auto_share_enabled", False)
    data.setdefault("browser_profile_path", DEFAULT_COCCOC_PROFILE_PATH)
    data.setdefault("group_list", "")
    data.setdefault("share_delay_min", 15)
    data.setdefault("share_delay_max", 30)

    return data

def save_config(data):
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
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        return []
    return rows[-limit:]

def normalize_text(text=""):
    import unicodedata
    text = (text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return text.strip()

def find_reply(text, rules, fallback):
    norm_text = normalize_text(text)
    for rule in rules:
        keywords = [k.strip() for k in rule.get("keywords", "").split(",") if k.strip()]
        for kw in keywords:
            if normalize_text(kw) in norm_text:
                return rule.get("reply", "")
    return fallback

def find_region_match(text, region_rules, region_enabled=None):
    norm_text = normalize_text(text)
    if not norm_text:
        return None, "", ""

    best_score = None
    best = (None, "", "")
    for key, reg in (region_rules or {}).items():
        if not isinstance(reg, dict):
            continue
        if region_enabled is not None and not region_enabled.get(key, True):
            continue
        for rule in reg.get("rules", []) or []:
            if not rule.get("enabled", True):
                continue
            matched = []
            for kw in rule.get("keywords", "").split(","):
                nk = normalize_text(kw)
                if nk and nk in norm_text:
                    matched.append(nk)
            if not matched:
                continue
            longest = max(matched, key=len)
            score = (len(matched), len(longest))
            if best_score is None or score > best_score:
                best_score = score
                best = (key, rule.get("reply", ""), longest)
    return best

def format_fb_error(data):
    err = data.get("error", {}) if isinstance(data, dict) else {}
    if not err:
        return str(data)
    msg = err.get("message", str(data))
    code = err.get("code")
    subcode = err.get("error_subcode")
    if code is None:
        return msg
    tag = f"code {code}" + (f"/{subcode}" if subcode is not None else "")
    return f"{msg} [{tag}]"

LOG_COLORS = {
    "success": "#4ade80",
    "error": "#f87171",
    "warning": "#fbbf24",
    "info": "#8b93a8",
}

def make_card(parent_layout, title=None, subtitle=None):
    frame = QFrame()
    frame.setObjectName("card")
    inner = QVBoxLayout(frame)
    inner.setContentsMargins(16, 14, 16, 14)
    inner.setSpacing(8)
    if title:
        t = QLabel(title)
        t.setObjectName("cardTitle")
        inner.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("cardSub")
        s.setWordWrap(True)
        inner.addWidget(s)
    parent_layout.addWidget(frame)
    return frame, inner

# ==========================================================================
# Handlers OAuth & Webhook
# ==========================================================================
class _OAuthCaptureHandler(http.server.BaseHTTPRequestHandler):
    captured_code = None
    captured_error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if "code" in qs:
            _OAuthCaptureHandler.captured_code = qs["code"][0]
            body = "<html><body style='font-family:sans-serif;background:#111113;color:#788cf0;padding:40px;'><h2>Đã nhận quyền thành công.</h2><p>Bạn có thể đóng tab này.</p></body></html>"
        elif "error" in qs:
            _OAuthCaptureHandler.captured_error = qs.get("error_description", qs.get("error"))[0]
            body = f"<html><body style='font-family:sans-serif;background:#111113;color:#788cf0;padding:40px;'><h2>Lỗi cấp quyền.</h2><p>{_OAuthCaptureHandler.captured_error}</p></body></html>"
        else:
            body = "<html><body><h2>Đang chờ...</h2></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        pass

class _ReplyWebhookHandler(http.server.BaseHTTPRequestHandler):
    app_ref = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        mode = qs.get("hub.mode", [""])[0]
        token = qs.get("hub.verify_token", [""])[0]
        challenge = qs.get("hub.challenge", [""])[0]

        expected = self.app_ref.get_reply_verify_token() if self.app_ref else ""
        if mode == "subscribe" and token == expected:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            if self.app_ref:
                self.app_ref.sig.log_sig.emit("Webhook đã xác thực thành công.", "success")
        else:
            self.send_response(403)
            self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"EVENT_RECEIVED")

        if self.app_ref and body.get("object") == "page":
            for entry in body.get("entry", []):
                page_id = entry.get("id", "")
                for event in entry.get("messaging", []) or []:
                    self.app_ref.handle_incoming_message(page_id, event)
                for change in entry.get("changes", []) or []:
                    if change.get("field") == "feed":
                        self.app_ref.handle_incoming_comment(page_id, change.get("value", {}))

    def log_message(self, format, *args):
        pass

# ==========================================================================
# Worker Auto Share Group (Playwright Cốc Cốc) - Hàng đợi xử lý TUẦN TỰ
# ==========================================================================
class ShareQueueWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(str)

    IDLE_CLOSE_TIMEOUT = 5.0
    POLL_INTERVAL = 1.0

    def __init__(self, post_urls, group_list, profile_path, delay_min, delay_max, posts=None):
        super().__init__()
        self.queue = queue.Queue()
        for url in (post_urls or []):
            if url:
                self.queue.put(url)
        self.groups = [g.strip() for g in group_list.split("\n") if g.strip()]
        self.profile_path = profile_path
        self.delay_min = float(delay_min or 120.0)
        self.delay_max = float(delay_max or 240.0)
        self.posts = [p.strip() for p in (posts or []) if p and p.strip()]
        self.coccoc_exe = COCCOC_EXECUTABLE_PATH
        self._stop_event = threading.Event()

    def enqueue(self, post_urls):
        for url in (post_urls or []):
            if url:
                self.queue.put(url)

    def request_stop(self):
        self._stop_event.set()

    def _sleep_interruptible(self, seconds):
        self._stop_event.wait(seconds)

    def _countdown_sleep(self, seconds, label="nghỉ anti-bot"):
        end_time = time.time() + max(0.0, seconds)
        while not self._stop_event.is_set():
            remaining = end_time - time.time()
            if remaining <= 0:
                break
            mins, secs = divmod(int(remaining) + 1, 60)
            remain_txt = f"{mins} phút {secs:02d} giây" if mins else f"{secs} giây"
            self.progress_signal.emit(f"⏳ Đang đếm ngược {label}: còn {remain_txt}...")
            self._stop_event.wait(min(1.0, remaining))

    @staticmethod
    def _normalize_group_url(entry):
        entry = (entry or "").strip()
        if not entry:
            return None
        if entry.startswith("http://") or entry.startswith("https://"):
            return entry
        if entry.startswith("www.facebook.com") or entry.startswith("facebook.com") or entry.startswith("fb.com"):
            return "https://" + entry
        return f"https://www.facebook.com/groups/{entry.strip('/')}/"

    def _share_one_post(self, page, post_url):
        if not self.groups:
            self.log_signal.emit("⚠️ Danh sách Nhóm trống, bỏ qua Auto Share.", "warning")
            return

        self.log_signal.emit("🚀 Bắt đầu tiến trình Đăng bài soạn sẵn lên các Group...", "info")
        total_groups = len(self.groups)

        for idx, group_entry in enumerate(self.groups):
            if self._stop_event.is_set():
                self.log_signal.emit("⏹ Đã dừng Auto Share theo yêu cầu.", "warning")
                break

            group_url = self._normalize_group_url(group_entry)
            if not group_url:
                self.log_signal.emit(f"[{idx+1}/{total_groups}] Bỏ qua dòng trống/không hợp lệ.", "warning")
                continue

            if self.posts:
                chosen_content = random.choice(self.posts)
            else:
                chosen_content = post_url

            self.progress_signal.emit(f"Đang mở Cốc Cốc – Đăng bài {idx+1}/{total_groups} (nhóm: {group_url})...")
            self.log_signal.emit(f"[{idx+1}/{total_groups}] Tiến hành đăng bài lên Group: {group_url}", "info")

            try:
                page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
                self._sleep_interruptible(random.uniform(2.5, 4.5))
                if self._stop_event.is_set():
                    break

                composer = page.locator(
                    "//span[contains(text(),'Bạn viết gì') or contains(text(),'Viết gì đó') "
                    "or contains(text(),'Write something') or contains(text(),'Write something to the group')]"
                ).first

                if not composer.is_visible():
                    self.log_signal.emit(
                        f"⚠️ Không tìm thấy ô đăng bài trong nhóm {group_url} (chưa tham gia hoặc nhóm riêng tư).",
                        "warning",
                    )
                    continue

                composer.click()
                self._sleep_interruptible(random.uniform(2.0, 3.5))

                text_box = page.locator("//div[@role='dialog']//div[@role='textbox']").first
                if not text_box.is_visible():
                    self.log_signal.emit(f"⚠️ Không tìm thấy khung soạn bài cho nhóm {group_url}.", "warning")
                    continue

                text_box.click()
                page.keyboard.press("Control+KeyA")
                page.keyboard.press("Backspace")
                
                # Copy toàn bộ nội dung bài viết vào Clipboard rồi Ctrl+V để không bị ăn bớt chữ hay lỗi emoji
                page.evaluate("text => navigator.clipboard.writeText(text)", chosen_content)
                self._sleep_interruptible(0.5)
                page.keyboard.press("Control+KeyV")

                self._sleep_interruptible(random.uniform(3.5, 5.5))
                if self._stop_event.is_set():
                    break

                submit_btn = page.locator(
                    "//div[@role='dialog']//div[@aria-label='Đăng' or @aria-label='Post']"
                ).first

                if submit_btn.is_visible():
                    submit_btn.click()
                    self._sleep_interruptible(random.uniform(2.0, 3.0))
                    self.log_signal.emit(f"✅ Đã ĐĂNG BÀI SOẠN SẴN thành công lên {group_url}", "success")
                else:
                    self.log_signal.emit(f"⚠️ Không tìm thấy nút Đăng cho nhóm {group_url}.", "warning")

            except Exception as err:
                self.log_signal.emit(f"❌ Lỗi khi đăng bài nhóm {group_url}: {err}", "error")

            if idx < total_groups - 1 and not self._stop_event.is_set():
                sleep_time = random.uniform(self.delay_min, self.delay_max)
                self.log_signal.emit(f"⏳ Nghỉ anti-bot {sleep_time:.1f} giây trước khi đăng nhóm tiếp theo...", "info")
                self._countdown_sleep(sleep_time, label="nghỉ anti-bot")

    def _cleanup_stale_browser_profile(self):
        if sys.platform.startswith("win"):
            try:
                self.log_signal.emit("🧹 Dọn dẹp tiến trình Cốc Cốc cũ còn treo ngầm (nếu có)...", "info")
                subprocess.run(
                    ["taskkill", "/F", "/IM", "browser.exe", "/T"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
                time.sleep(1.0)
            except Exception as e:
                self.log_signal.emit(f"Không thể dọn tiến trình Cốc Cốc cũ (bỏ qua): {e}", "warning")

        if self.profile_path and os.path.isdir(self.profile_path):
            lock_path = os.path.join(self.profile_path, "SingletonLock")
            try:
                if os.path.exists(lock_path) or os.path.islink(lock_path):
                    os.remove(lock_path)
                    self.log_signal.emit("🧹 Đã xóa file khóa Profile (SingletonLock) thành công.", "info")
            except Exception as e:
                self.log_signal.emit(f"Không thể xóa file khóa Profile (bỏ qua): {e}", "warning")

    def run(self):
        if not PLAYWRIGHT_AVAILABLE:
            self.log_signal.emit("❌ Chưa cài Playwright. Chạy: pip install playwright && playwright install chromium", "error")
            self.finished_signal.emit()
            return

        if self.queue.empty():
            self.finished_signal.emit()
            return

        self.log_signal.emit("🚀 Mở DUY NHẤT 1 trình duyệt Cốc Cốc để xử lý hàng đợi Auto Share Group...", "info")

        browser = None
        processed = 0
        try:
            with sync_playwright() as p:
                user_data = self.profile_path if self.profile_path and os.path.exists(self.profile_path) else None
                coccoc_path = self.coccoc_exe if self.coccoc_exe and os.path.exists(self.coccoc_exe) else None

                if coccoc_path:
                    self.log_signal.emit("🌐 Đã kết nối đường dẫn trình duyệt Cốc Cốc.", "info")
                else:
                    self.log_signal.emit("⚠️ Không tìm thấy Cốc Cốc, tự động chuyển sang Chromium mặc định.", "warning")

                if user_data:
                    self._cleanup_stale_browser_profile()
                    launch_kwargs = dict(
                        user_data_dir=user_data,
                        headless=False,
                        args=["--disable-notifications", "--start-maximized"]
                    )
                    if coccoc_path:
                        launch_kwargs["executable_path"] = coccoc_path
                    
                    browser = p.chromium.launch_persistent_context(**launch_kwargs)
                    page = browser.pages[0] if browser.pages else browser.new_page()
                else:
                    launch_kwargs = dict(headless=False, args=["--disable-notifications"])
                    if coccoc_path:
                        launch_kwargs["executable_path"] = coccoc_path
                    browser = p.chromium.launch(**launch_kwargs)
                    page = browser.new_page()

                last_activity = time.time()
                while not self._stop_event.is_set():
                    try:
                        post_url = self.queue.get(timeout=self.POLL_INTERVAL)
                    except queue.Empty:
                        if time.time() - last_activity >= self.IDLE_CLOSE_TIMEOUT:
                            break
                        continue

                    processed += 1
                    remaining_in_queue = self.queue.qsize()
                    self.progress_signal.emit(
                        f"Đang xử lý lượt #{processed} trong hàng đợi Auto Share Group "
                        f"(còn {remaining_in_queue} lượt chờ)..."
                    )
                    self._share_one_post(page, post_url)
                    self.queue.task_done()
                    last_activity = time.time()

                if self._stop_event.is_set():
                    self.log_signal.emit("⏹ Đã dừng tiến trình Auto Share theo yêu cầu.", "warning")
                    self.progress_signal.emit("Đã dừng Auto Share.")
                elif processed:
                    self.log_signal.emit("🎉 Đã đăng thành công bài viết lên toàn bộ các Group!", "success")
                    self.progress_signal.emit("🎉 Hoàn tất Auto Share Group.")

        except Exception as e:
            self.log_signal.emit(f"❌ Lỗi điều khiển trình duyệt Cốc Cốc: {e}", "error")
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            self.finished_signal.emit()

# ==========================================================================
# Signals Bridge
# ==========================================================================
class Signals(QObject):
    log_sig = pyqtSignal(str, str)
    share_request_sig = pyqtSignal(list, dict)
    status_sig = pyqtSignal(str)
    running_state_sig = pyqtSignal(bool)
    countdown_visible_sig = pyqtSignal(bool)
    connection_status_sig = pyqtSignal(str)
    oauth_login_enable_sig = pyqtSignal(bool)
    oauth_reopen_enable_sig = pyqtSignal(bool)
    pages_loaded_sig = pyqtSignal(list, list)
    token_refreshed_sig = pyqtSignal(list)
    reply_running_sig = pyqtSignal(bool)
    reply_event_sig = pyqtSignal(dict)
    progress_sig = pyqtSignal(int, int, str)
    test_post_finished_sig = pyqtSignal()

# ==========================================================================
# Stylesheet ArtTools CSS
# ==========================================================================
CSS = """
QWidget            { background:#111113; color:#788cf0; font-size:13px; font-family:'Segoe UI',sans-serif; }
#sidebar           { background:#17171a; border-right:1.5px solid #232329; }
#brand             { color:#788cf0; font-size:16px; font-weight:700; padding:2px 4px; }
#brandSub          { color:#6b7280; font-size:10px; padding:0 4px 8px 4px; }
#navBtn            { background:transparent; color:#6b7280; border:none; border-radius:12px;
                     padding:10px 12px; text-align:left; font-size:13px; }
#navBtn:hover      { background:#1f1f24; color:#788cf0; }
#navBtn:checked    { background:#1f1f24; color:#788cf0; font-weight:600; border:1.5px solid #788cf0; }
#panel             { background:#17171a; color:#788cf0;
                     border:1.5px solid #272730; border-radius:14px; padding:10px; }
#card              { background:#17171a; border:1.5px solid #272730; border-radius:14px; }
#cardTitle         { color:#788cf0; font-size:14px; font-weight:700; }
#cardSub           { color:#6b7280; font-size:11px; }
#lineEdit          { background:#0d0d0f; color:#788cf0;
                     border:1.5px solid #272730; border-radius:10px; padding:7px 10px; }
#lineEdit:focus    { border:1.5px solid #788cf0; }
#primaryBtn        { background:#17171a; color:#788cf0; border:1.5px solid #788cf0; border-radius:12px; padding:8px 16px; font-weight:600; }
#primaryBtn:hover  { background:#1f1f24; }
#secondaryBtn      { background:#17171a; color:#788cf0; border:1.5px solid #272730; border-radius:12px; padding:8px 14px; font-weight:600; }
#secondaryBtn:hover{ background:#1f1f24; }
#dangerBtn         { background:#17171a; color:#f87171; border:1.5px solid #3a2323; border-radius:12px; padding:8px 14px; font-weight:600; }
#dangerBtn:hover   { background:#241717; }
#combo             { background:#0d0d0f; color:#788cf0; border:1.5px solid #272730; border-radius:10px; padding:5px 10px; }
#status            { color:#6b7280; font-size:11px; }
#statusRunning     { color:#39ff6a; font-size:13px; font-weight:700; }
#statusStopped     { color:#6b7280; font-size:13px; font-weight:700; }
#statusStopping    { color:#f87171; font-size:13px; font-weight:700; }
#countLabel        { color:#4b5563; font-size:10px; }
#progressLabel     { color:#788cf0; font-size:11px; }
QProgressBar       { background:#0d0d0f; color:#e5e7eb; border:1.5px solid #272730;
                     border-radius:8px; text-align:center; min-height:18px; max-height:18px; }
QProgressBar::chunk { background:#788cf0; border-radius:7px; }
QCheckBox          { color:#788cf0; spacing:6px; }
QCheckBox::indicator      { width:15px; height:15px; border:1.5px solid #272730; border-radius:4px; background:#0d0d0f; }
QCheckBox::indicator:checked { background:#788cf0; border-color:#788cf0; }
QTableWidget       { background:#0d0d0f; color:#788cf0; border:1.5px solid #272730; border-radius:10px; gridline-color:#232329; font-size:13px; }
QTableWidget::item { padding:8px; }
QTableWidget::item:selected { background:#272740; color:#a5b4fc; }
QHeaderView::section { background:#1f1f24; color:#788cf0; border:none; padding:8px; font-weight:600; font-size:13px; }
QScrollArea        { background: transparent; border: none; }
QScrollBar:vertical    { background:#111113; width:8px; border-radius:4px; }
QScrollBar::handle:vertical { background:#232329; border-radius:4px; }
QDialog            { background:#111113; }
QTabWidget::pane   { background:#17171a; border:1.5px solid #272730; border-radius:12px; top:-1px; }
QTabBar::tab       { background:#111113; color:#6b7280; border:1.5px solid #272730;
                     border-bottom:none; border-top-left-radius:10px; border-top-right-radius:10px;
                     padding:8px 14px; margin-right:4px; font-weight:600; }
QTabBar::tab:selected { background:#1f1f24; color:#788cf0; border-color:#788cf0; }
QTabBar::tab:hover    { color:#788cf0; }
#statChip          { background:#0d0d0f; color:#788cf0; border:1.5px solid #272730;
                     border-radius:10px; padding:8px 12px; font-size:12px; font-weight:600; }
#regionHint        { color:#6b7280; font-size:11px; }
"""

# ==========================================================================
# History Dialog
# ==========================================================================
class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lịch sử đăng bài")
        self.resize(680, 440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        rows = list(reversed(read_history()))
        layout.addWidget(QLabel(f"{len(rows)} lần đăng gần nhất"))

        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["Thời gian", "Page", "Kết quả", "Chi tiết"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for r, row in enumerate(rows):
            status_ok = row.get("status") == "success"
            status_text = "Thành công" if status_ok else "Lỗi"
            page_label = row.get("page_name") or row.get("page_id", "")
            detail = f'Post ID {row.get("post_id", "?")} - {row.get("message", "")}' if status_ok else f'{row.get("error", "")}'
            table.setItem(r, 0, QTableWidgetItem(row.get("time", "")))
            table.setItem(r, 1, QTableWidgetItem(str(page_label)))
            table.setItem(r, 2, QTableWidgetItem(status_text))
            table.setItem(r, 3, QTableWidgetItem(detail))

        layout.addWidget(table)

# ==========================================================================
# Main App Window (Giao diện chính điều hành)
# ==========================================================================
class FBAutoPosterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.saved_pages = self.config_data.get("pages") or []

        self.running = False
        self.worker_thread = None
        self.share_workers = []
        self._active_share_worker = None
        self.stop_event = threading.Event()
        self.last_posted_index_per_page = {}
        self.last_media_path_per_page = {}
        self.next_post_at = None
        self._token_refresh_done_for_cycle = True

        self.run_cfg = {}
        self.page_token_cache = {}
        self.reply_verify_token_cache = DEFAULT_REPLY_VERIFY_TOKEN

        self.oauth_last_auth_url = None
        self.oauth_secret_shown = False

        self.webhook_server = None
        self.webhook_thread = None
        self.reply_running = False
        self.msg_rules = self.config_data.get("reply_msg_rules") or list(DEFAULT_MSG_RULES)
        self.comment_rules = self.config_data.get("reply_comment_rules") or list(DEFAULT_COMMENT_RULES)
        self.default_message_reply = self.config_data.get("reply_default_message", DEFAULT_MESSAGE_REPLY)
        self.default_comment_reply = self.config_data.get("reply_default_comment", DEFAULT_COMMENT_REPLY)

        self.region_rules = copy.deepcopy(
            self.config_data.get("reply_region_rules") or DEFAULT_REGION_RULES)
        self.region_enabled = dict(self.config_data.get("reply_region_enabled") or {})
        for _k in REGION_ORDER:
            self.region_enabled.setdefault(_k, True)
        self.enable_message_reply = bool(self.config_data.get("reply_enable_message", True))
        self.enable_comment_reply = bool(self.config_data.get("reply_enable_comment", True))
        self.region_priority = bool(self.config_data.get("reply_region_priority", True))
        self.global_default_reply = self.config_data.get("reply_global_default", DEFAULT_GLOBAL_REPLY)
        self.reply_count_msg = 0
        self.reply_count_cmt = 0
        self.region_tables = {}
        self.region_enable_boxes = {}
        self.region_default_edits = {}
        self.region_count_labels = {}

        self.fb_user_token = self.config_data.get("fb_user_token", "")
        self.token_refresh_timer = QTimer(self)
        self.token_refresh_timer.setInterval(15 * 60 * 1000)
        self.token_refresh_timer.timeout.connect(self._auto_refresh_tokens)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)

        self.sig = Signals()
        self.sig.log_sig.connect(self._on_log_signal)
        self.sig.status_sig.connect(lambda s: self.status_label.setText(s))
        self.sig.running_state_sig.connect(self._on_running_state)
        self.sig.connection_status_sig.connect(self._on_connection_status)
        self.sig.oauth_login_enable_sig.connect(lambda en: self.oauth_login_btn.setEnabled(en))
        self.sig.oauth_reopen_enable_sig.connect(lambda en: self.oauth_reopen_btn.setEnabled(en))
        self.sig.pages_loaded_sig.connect(self._on_oauth_pages_loaded)
        self.sig.token_refreshed_sig.connect(self._on_tokens_auto_refreshed)
        self.sig.reply_running_sig.connect(self._on_reply_running_state)
        self.sig.reply_event_sig.connect(self._on_reply_event)
        self.sig.share_request_sig.connect(self._start_share_worker)
        self.sig.progress_sig.connect(self._on_progress)
        self.sig.test_post_finished_sig.connect(self._on_test_post_finished)

        self.init_ui()
        self._refresh_token_cache()
        self._snapshot_run_config()

        self.running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if self.fb_user_token:
            self.token_refresh_timer.start()
            threading.Thread(target=self._do_auto_refresh_tokens, daemon=True).start()

    def init_ui(self):
        self.setWindowTitle("FB Auto Poster & Share Group Pro")
        screen = QApplication.primaryScreen().geometry()
        w, h = int(screen.width() * 0.65), int(screen.height() * 0.85)
        self.resize(max(w, 1020), max(h, 750))
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 18, 12, 16)
        sl.setSpacing(4)

        brand = QLabel("Facebook Auto")
        brand.setObjectName("brand")
        sl.addWidget(brand)
        brand_sub = QLabel("Auto Poster & Share Group Pro | MaeAry™️")
        brand_sub.setObjectName("brandSub")
        brand_sub.setWordWrap(True)
        sl.addWidget(brand_sub)
        sl.addSpacing(10)

        pages = [
            ("📊", "Tổng quan"),
            ("📝", "Đăng bài tự động"),
            ("🚀", "Auto Share Group"),
            ("🔑", "Access Token"),
            ("💬", "Trả lời tự động"),
            ("ℹ️", "Giới thiệu"),
        ]
        self._nav = []
        for icon, name in pages:
            b = QPushButton(f"   {icon}   {name}")
            b.setObjectName("navBtn")
            b.setCheckable(True)
            b.clicked.connect(lambda _, n=name: self._go(n))
            sl.addWidget(b)
            self._nav.append((name, b))

        sl.addStretch()

        self.status_label = QLabel("Đang dừng")
        self.status_label.setObjectName("statusStopped")
        sl.addWidget(self.status_label)
        self.countdown_label = QLabel("")
        self.countdown_label.setObjectName("status")
        sl.addWidget(self.countdown_label)

        self.stack = QStackedWidget()
        self.p_overview = self._pg_overview()
        self.p_autopost = self._pg_autopost()
        self.p_autoshare = self._pg_autoshare()
        self.p_token = self._pg_token()
        self.p_autoreply = self._pg_autoreply()
        self.p_about = self._pg_about()

        for p in (self.p_overview, self.p_autopost, self.p_autoshare, self.p_token, self.p_autoreply, self.p_about):
            self.stack.addWidget(p)

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)

        self.setStyleSheet(CSS)
        self._go("Tổng quan")

    def _go(self, name):
        names = ["Tổng quan", "Đăng bài tự động", "Auto Share Group", "Access Token", "Trả lời tự động", "Giới thiệu"]
        idx = names.index(name)
        self.stack.setCurrentIndex(idx)
        for n, b in self._nav:
            b.setChecked(n == name)

    @staticmethod
    def _safe_float(text, default):
        try:
            return float(str(text).strip())
        except (TypeError, ValueError):
            return default

    def save(self, silent=False):
        if not silent:
            self.save_btn.setEnabled(False)
            self.save_btn.setText("💾 Đang lưu...")
            QApplication.processEvents()
        targets = []
        for i in range(MAX_TARGETS):
            targets.append({
                "enabled": bool(self.target_enabled_checks[i].isChecked()),
                "page_id": self.target_id_edits[i].text().strip(),
                "access_token": self.target_token_edits[i].text().strip(),
                "name": "",
            })
        
        data = {
            "targets": targets,
            "interval_minutes": self._safe_float(self.interval_edit.text(), 60.0),
            "jitter_minutes": self._safe_float(self.jitter_edit.text(), 0.0),
            "posts": self.get_posts(),
            "media_folder": self.media_folder_edit.text().strip(),
            "use_media": bool(self.use_media_check.isChecked()),
            "auto_share_enabled": bool(self.auto_share_check.isChecked()),
            "browser_profile_path": self.profile_path_edit.text().strip(),
            "group_list": self.group_list_edit.toPlainText().strip(),
            "share_delay_min": self._safe_float(self.share_delay_min_edit.text(), 15.0),
            "share_delay_max": self._safe_float(self.share_delay_max_edit.text(), 30.0),
        }
        save_config(data)
        self.config_data = data
        self._refresh_token_cache()
        if not silent:
            self.log("Đã lưu cấu hình thành công!", "success")
            self.save_btn.setText("💾 Lưu cấu hình")
            self.save_btn.setEnabled(True)
            QApplication.processEvents()
            QMessageBox.information(self, "Thông báo", "Đã lưu cấu hình thành công!")

    def _snapshot_run_config(self):
        try:
            d_min = float(self.share_delay_min_edit.text().strip() or 15)
            d_max = float(self.share_delay_max_edit.text().strip() or 30)
        except ValueError:
            d_min, d_max = 15.0, 30.0
        if d_max < d_min:
            d_min, d_max = d_max, d_min

        self.run_cfg = {
            "posts": self.get_posts(),
            "use_media": bool(self.use_media_check.isChecked()) if hasattr(self, 'use_media_check') else True,
            "media_folder": self.media_folder_edit.text().strip() if hasattr(self, 'media_folder_edit') else "",
            "auto_share": bool(self.auto_share_check.isChecked()) if hasattr(self, 'auto_share_check') else True,
            "group_list": self.group_list_edit.toPlainText().strip() if hasattr(self, 'group_list_edit') else "",
            "profile_path": self.profile_path_edit.text().strip() if hasattr(self, 'profile_path_edit') else "",
            "share_delay_min": d_min,
            "share_delay_max": d_max,
        }
        return self.run_cfg

    def _do_post_all(self, targets, posts, run_cfg=None):
        run_cfg = run_cfg or self.run_cfg
        success_count = 0
        posted_urls = []
        total = len(targets)

        for step, t in enumerate(targets, start=1):
            page_id = t["page_id"]
            display_name = t.get("name") or page_id
            self.sig.progress_sig.emit(
                step, total, f"Đang đăng bài {step}/{total} lên Page \"{display_name}\"..."
            )
            indices = list(range(len(posts)))
            last_idx = self.last_posted_index_per_page.get(page_id)
            if len(posts) > 1 and last_idx is not None and last_idx < len(posts):
                indices = [i for i in indices if i != last_idx] or list(range(len(posts)))
            chosen_idx = random.choice(indices)
            message = posts[chosen_idx]
            self.last_posted_index_per_page[page_id] = chosen_idx

            media_path, media_type = self._select_media(
                run_cfg, exclude_path=self.last_media_path_per_page.get(page_id)
            )
            if media_path:
                self.last_media_path_per_page[page_id] = media_path

            ok, post_id = self._do_post_one(page_id, t["access_token"], t["name"], message, media_path, media_type)
            if ok:
                success_count += 1
                if post_id:
                    post_url = f"https://www.facebook.com/{post_id}"
                    posted_urls.append(post_url)

        self.log(f"Hoàn tất lượt đăng: {success_count}/{len(targets)} Page thành công.", "info")
        self.sig.progress_sig.emit(
            total, total, f"Hoàn tất lượt đăng: {success_count}/{total} Page thành công."
        )

        if posted_urls and run_cfg.get("auto_share"):
            self.sig.share_request_sig.emit(posted_urls, dict(run_cfg))

    def _do_post_one(self, page_id, token, name, message, media_path=None, media_type=None):
        attempt = 0
        last_err = None
        while attempt <= MAX_RETRIES:
            try:
                ok, data = self.post_to_facebook(page_id, token, message, media_path, media_type)
                if ok:
                    post_id = data.get("id") or data.get("post_id", "")
                    self.log(f'[{name}] Đăng thành công. Post ID: {post_id}', "success")
                    append_history({
                        "time": datetime.datetime.now().isoformat(timespec="seconds"),
                        "status": "success", "page_id": page_id, "page_name": name,
                        "post_id": post_id, "message": message[:120],
                    })
                    return True, post_id
                else:
                    last_err = format_fb_error(data)
            except Exception as e:
                last_err = str(e)

            attempt += 1
            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

        self.log(f"[{name}] Đăng thất bại: {last_err}", "error")
        return False, None

    def _start_share_worker(self, post_urls, run_cfg):
        if not post_urls:
            return

        active = self._active_share_worker
        if active is not None and active.isRunning():
            active.enqueue(post_urls)
            self.log(f"Đã thêm {len(post_urls)} bài viết vào hàng đợi Auto Share đang xử lý.", "info")
            return

        posts_list = run_cfg.get("posts") or self.get_posts()

        worker = ShareQueueWorker(
            post_urls,
            run_cfg.get("group_list", ""),
            run_cfg.get("profile_path", ""),
            run_cfg.get("share_delay_min", 120.0),
            run_cfg.get("share_delay_max", 240.0),
            posts_list
        )
        worker.log_signal.connect(self.log)
        worker.progress_signal.connect(lambda text: self.sig.progress_sig.emit(0, 0, text))
        worker.finished_signal.connect(lambda: self._cleanup_worker(worker))
        self.share_workers.append(worker)
        self._active_share_worker = worker
        worker.start()

    def _cleanup_worker(self, worker):
        if worker in self.share_workers:
            self.share_workers.remove(worker)
        if self._active_share_worker is worker:
            self._active_share_worker = None

    def post_to_facebook(self, page_id, token, message, media_path=None, media_type=None):
        if media_type == "video" and media_path:
            url = f"https://graph-video.facebook.com/{GRAPH_API_VERSION}/{page_id}/videos"
            with open(media_path, "rb") as f:
                resp = requests.post(url, data={"description": message, "access_token": token}, files={"source": f}, timeout=600)
        elif media_type == "image" and media_path:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
            with open(media_path, "rb") as f:
                resp = requests.post(url, data={"caption": message, "access_token": token}, files={"source": f}, timeout=120)
        else:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
            resp = requests.post(url, data={"message": message, "access_token": token}, timeout=30)
        try:
            payload = resp.json() if resp.content else {}
        except ValueError:
            payload = {"error": {"message": (resp.text or "")[:300]}}
        return resp.ok, payload

    def _select_media(self, run_cfg=None, exclude_path=None):
        run_cfg = run_cfg or self.run_cfg
        if not run_cfg.get("use_media"):
            return None, None
        return pick_random_media(run_cfg.get("media_folder", ""), exclude_path=exclude_path)

    def log(self, msg, tag="info"):
        self.sig.log_sig.emit(msg, tag)

    def _on_log_signal(self, msg, tag):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        color = LOG_COLORS.get(tag, LOG_COLORS["info"])
        safe_msg = html.escape(f"[{ts}] {msg}")
        self.log_box.append(f'<span style="color:{color};">{safe_msg}</span>')
        QApplication.processEvents()

    def _on_progress(self, current, total, text):
        if total > 0:
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(max(0, min(current, total)))
        else:
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setRange(0, 0)
        if text:
            self.progress_label.setText(text)
        QApplication.processEvents()

    def _on_connection_status(self, text):
        self.connection_status_label.setText(text)
        QApplication.processEvents()

    def _on_test_post_finished(self):
        self.test_post_btn.setText("📨 Đăng thử ngay 1 bài")
        self.test_post_btn.setEnabled(True)
        self.log("✅ Đã hoàn tất đăng thử.", "success")
        QApplication.processEvents()

    def get_posts(self):
        if hasattr(self, "post_boxes"):
            return [box.toPlainText().strip() for box in self.post_boxes if box.toPlainText().strip()]
        return [p for p in self.config_data.get("posts", []) if p and p.strip()]

    def _update_count(self, idx):
        text = self.post_boxes[idx].toPlainText().strip()
        self.count_labels[idx].setText(f"{len(text)} ký tự")

    def _browse_media_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Chọn thư mục media", self.media_folder_edit.text())
        if chosen:
            self.media_folder_edit.setText(chosen)

    def _on_target_page_selected(self, row_idx):
        combo = self.target_combos[row_idx]
        idx = combo.currentIndex() - 1
        if idx < 0 or idx >= len(self.saved_pages):
            return
        page = self.saved_pages[idx]
        self.target_id_edits[row_idx].setText(page.get("id", ""))
        self.target_token_edits[row_idx].setText(page.get("access_token", ""))
        self.target_enabled_checks[row_idx].setChecked(True)

    def _collect_targets(self, only_enabled=True):
        result = []
        for i in range(MAX_TARGETS):
            if only_enabled and not self.target_enabled_checks[i].isChecked():
                continue
            page_id = self.target_id_edits[i].text().strip()
            token = self.target_token_edits[i].text().strip()
            if page_id and token:
                result.append({"page_id": page_id, "access_token": token, "name": page_id})
        return result

    def test_connection(self):
        targets = self._collect_targets(only_enabled=True)
        if not targets:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ít nhất 1 Page (Access Token/Page ID).")
            return
        self.connection_status_label.setText("Đang kiểm tra kết nối...")
        QApplication.processEvents()
        threading.Thread(target=self._do_test_connection, args=(targets,), daemon=True).start()

    def _do_test_connection(self, targets):
        ok_count = 0
        for t in targets:
            try:
                resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{t['page_id']}", params={"access_token": t["access_token"]}, timeout=10)
                if resp.status_code == 200:
                    ok_count += 1
            except Exception:
                pass
        self.sig.connection_status_sig.emit(f"Kiểm tra {len(targets)} Page: {ok_count} kết nối OK.")

    def post_now_test(self):
        targets = self._collect_targets(only_enabled=True)
        run_cfg = self._snapshot_run_config()
        posts = [p for p in run_cfg["posts"] if p]
        if not targets:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ít nhất 1 Page (Access Token/Page ID).")
            return
        if not posts:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập ít nhất 1 Nội dung bài viết.")
            return

        self.test_post_btn.setEnabled(False)
        self.test_post_btn.setText("📨 Đang đăng thử...")
        self.log("📨 Đã bắt đầu đăng thử 1 bài...", "info")
        QApplication.processEvents()

        def _run_and_restore():
            try:
                self._do_post_all(targets, posts, run_cfg)
            finally:
                self.sig.test_post_finished_sig.emit()

        threading.Thread(target=_run_and_restore, daemon=True).start()

    def start(self):
        if self.running:
            return
        if self.worker_thread is not None and self.worker_thread.is_alive():
            QMessageBox.information(
                self, "Thông báo",
                "Tiến trình trước vẫn đang dừng hẳn, vui lòng đợi giây lát rồi bấm Bắt đầu lại.",
            )
            return

        targets = self._collect_targets(only_enabled=True)
        run_cfg = self._snapshot_run_config()
        posts = [p for p in run_cfg["posts"] if p]
        if not targets:
            QMessageBox.warning(
                self, "Thiếu thông tin",
                "Vui lòng nhập/chọn ít nhất 1 Page (Access Token/Page ID) trước khi Bắt đầu.",
            )
            return
        if not posts:
            QMessageBox.warning(
                self, "Thiếu thông tin",
                "Vui lòng nhập ít nhất 1 Nội dung bài viết trước khi Bắt đầu.",
            )
            return

        interval_txt = self.interval_edit.text().strip() or "60"
        jitter_txt = self.jitter_edit.text().strip() or "0"
        try:
            interval = float(interval_txt)
            jitter = float(jitter_txt)
        except ValueError:
            QMessageBox.critical(self, "Lỗi", "Chu kỳ và độ lệch phải là số.")
            return
        if interval <= 0:
            QMessageBox.critical(self, "Lỗi", "Chu kỳ phải lớn hơn 0 phút.")
            return
        if jitter < 0:
            QMessageBox.critical(self, "Lỗi", "Độ lệch ngẫu nhiên không được âm.")
            return
        if jitter >= interval:
            QMessageBox.critical(self, "Lỗi", "Độ lệch phải nhỏ hơn chu kỳ.")
            return

        self.save(silent=True)
        self.running = True
        self.stop_event.clear()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, max(1, len(targets)))
        self.progress_bar.setValue(0)
        self.progress_label.setText("Đang chuẩn bị đăng bài...")
        self.sig.running_state_sig.emit(True)
        self.log("🚀 Đã bắt đầu tiến trình đăng bài tự động...", "success")
        QApplication.processEvents()

        self.worker_thread = threading.Thread(
            target=self._worker_loop, args=(targets, interval, jitter, run_cfg), daemon=True
        )
        self.worker_thread.start()

    def _worker_loop(self, targets, interval_minutes, jitter_minutes, run_cfg):
        try:
            while not self.stop_event.is_set():
                posts = [p for p in run_cfg.get("posts", []) if p]
                if not posts:
                    self.log("Không còn bài viết nào, dừng tiến trình.", "warning")
                    break
                try:
                    self.log("🔄 Bắt đầu đợt đăng bài mới...", "info")
                    self._do_post_all(targets, posts, run_cfg)
                except Exception as e:
                    self.log(f"Lỗi không mong muốn trong tiến trình đăng bài: {e}", "error")

                actual_interval = max(0.1, interval_minutes + random.uniform(-jitter_minutes, jitter_minutes)) if jitter_minutes else interval_minutes
                interval_seconds = actual_interval * 60
                self.next_post_at = time.time() + interval_seconds
                self._token_refresh_done_for_cycle = False
                self.stop_event.wait(interval_seconds)
        except Exception as e:
            self.log(f"Lỗi nghiêm trọng trong tiến trình nền: {e}", "error")
        finally:
            self.next_post_at = None
            self.sig.running_state_sig.emit(False)

    def stop(self):
        self.stop_btn.setEnabled(False)
        self._set_status_visual("Đang dừng", "statusStopping")
        self.log("⏹ Đã phát lệnh dừng tiến trình...", "warning")
        QApplication.processEvents()

        self.stop_event.set()
        active = self._active_share_worker
        if active is not None:
            try:
                active.request_stop()
            except Exception:
                pass
        self.sig.running_state_sig.emit(False)

    def _tick_countdown(self):
        if not self.running or self.next_post_at is None:
            return
        remaining = int(self.next_post_at - time.time())
        if remaining <= 0:
            if hasattr(self, 'countdown_label'):
                self.countdown_label.setText("Đang đăng bài...")
            if hasattr(self, 'countdown_label_big'):
                self.countdown_label_big.setText("Đang đăng bài...")
        else:
            mins, secs = divmod(remaining, 60)
            text = f"Bài tiếp theo sau: {mins:02d}:{secs:02d}"
            if hasattr(self, 'countdown_label'):
                self.countdown_label.setText(text)
            if hasattr(self, 'countdown_label_big'):
                self.countdown_label_big.setText(text)

            if remaining <= 60 and not self._token_refresh_done_for_cycle:
                self._token_refresh_done_for_cycle = True
                self.log(
                    "⏰ Còn 1 phút nữa đến đợt tác vụ mới, tự động làm mới Access Token...",
                    "info",
                )
                if hasattr(self, '_auto_refresh_tokens'):
                    self._auto_refresh_tokens()

    def _set_status_visual(self, text, obj_name):
        for lbl in (self.status_label, self.status_label_big):
            lbl.setText(text)
            lbl.setObjectName(obj_name)
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
        QApplication.processEvents()

    def _on_running_state(self, running):
        self.running = running
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        if running:
            self._set_status_visual("Đang chạy...", "statusRunning")
            self.countdown_timer.start(1000)
        else:
            self._set_status_visual("Đang dừng", "statusStopped")
            self.countdown_timer.stop()
            self.countdown_label.setText("")
            self.countdown_label_big.setText("")
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            self.progress_label.setText("")
        QApplication.processEvents()

    def _open_history(self):
        HistoryDialog(self).exec()

    def _refresh_reply_pages_table(self):
        if not hasattr(self, "reply_pages_table"):
            return
        pages = self.saved_pages or []
        self.reply_pages_table.setRowCount(len(pages))
        for r, p in enumerate(pages):
            has_token = bool(p.get("access_token"))
            self.reply_pages_table.setItem(r, 0, QTableWidgetItem(str(p.get("name", ""))))
            self.reply_pages_table.setItem(r, 1, QTableWidgetItem(str(p.get("id", ""))))
            state = "🟢 Đang lắng nghe" if (self.reply_running and has_token) else (
                "🟡 Sẵn sàng" if has_token else "🔴 Thiếu token")
            self.reply_pages_table.setItem(r, 2, QTableWidgetItem(state))
        if hasattr(self, "stat_page_label"):
            self.stat_page_label.setText(f"📄 Fanpage quản lý: {len(pages)}")

    def _refresh_pages_table(self):
        self._refresh_reply_pages_table()
        self.pages_table.setRowCount(len(self.saved_pages))
        for r, p in enumerate(self.saved_pages):
            self.pages_table.setItem(r, 0, QTableWidgetItem(str(p.get("name", ""))))
            self.pages_table.setItem(r, 1, QTableWidgetItem(str(p.get("id", ""))))

    def _browse_profile_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Chọn thư mục Profile", self.profile_path_edit.text() or "")
        if chosen:
            self.profile_path_edit.setText(chosen)

    def closeEvent(self, event):
        self.stop_event.set()
        self.countdown_timer.stop()
        self.token_refresh_timer.stop()

        if self.webhook_server is not None:
            try:
                self.webhook_server.shutdown()
                self.webhook_server.server_close()
            except Exception:
                pass
            self.webhook_server = None

        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3)

        for worker in list(self.share_workers):
            try:
                worker.request_stop()
            except Exception:
                pass
        for worker in list(self.share_workers):
            try:
                if not worker.wait(35000):
                    worker.terminate()
                    worker.wait(2000)
            except Exception:
                pass
        self.share_workers.clear()

        event.accept()

    # ------------------------------------------------------------------
    # TAB 1: TỔNG QUAN
    # ------------------------------------------------------------------
    def _pg_overview(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        outer.addWidget(QLabel("📊 Tổng quan - Quản lý chạy tự động"))

        card, cl = make_card(outer, "Trạng thái & điều khiển")
        row = QHBoxLayout()
        status_col = QVBoxLayout()
        self.status_label_big = QLabel("Đang dừng")
        self.status_label_big.setObjectName("statusStopped")
        status_col.addWidget(self.status_label_big)
        self.countdown_label_big = QLabel("")
        self.countdown_label_big.setObjectName("status")
        status_col.addWidget(self.countdown_label_big)
        row.addLayout(status_col)
        row.addStretch()

        self.save_btn = QPushButton("💾 Lưu cấu hình")
        self.save_btn.setObjectName("secondaryBtn")
        self.save_btn.clicked.connect(self.save)
        row.addWidget(self.save_btn)

        self.test_post_btn = QPushButton("📨 Đăng thử ngay 1 bài")
        self.test_post_btn.setObjectName("secondaryBtn")
        self.test_post_btn.clicked.connect(self.post_now_test)
        row.addWidget(self.test_post_btn)

        self.stop_btn = QPushButton("■ Dừng")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        row.addWidget(self.stop_btn)

        self.start_btn = QPushButton("▶ Bắt đầu")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self.start)
        row.addWidget(self.start_btn)
        cl.addLayout(row)

        progress_row = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        progress_row.addWidget(self.progress_bar)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressLabel")
        progress_row.addWidget(self.progress_label)
        cl.addLayout(progress_row)

        card_log, cll = make_card(outer, "Nhật ký hoạt động")
        top_row = QHBoxLayout()
        top_row.addStretch()
        hist_btn = QPushButton("🕘 Lịch sử đăng bài")
        hist_btn.setObjectName("secondaryBtn")
        hist_btn.clicked.connect(self._open_history)
        top_row.addWidget(hist_btn)
        cll.addLayout(top_row)

        self.log_box = QTextEdit()
        self.log_box.setObjectName("panel")
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Consolas", 9))
        cll.addWidget(self.log_box)

        outer.addWidget(card_log, 1)
        return page

    # ------------------------------------------------------------------
    # TAB 2: ĐĂNG BÀI TỰ ĐỘNG
    # ------------------------------------------------------------------
    def _pg_autopost(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        outer.addWidget(QLabel("📝 Đăng bài tự động - Fanpage, lịch đăng & nội dung"))

        card_conn, cc = make_card(outer, "Kết nối Fanpage", f'Tick chọn tối đa {MAX_TARGETS} Page để đăng bài CÙNG LÚC.')
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel("Dùng"), 0, 0)
        grid.addWidget(QLabel("Chọn Page đã lưu"), 0, 1)
        grid.addWidget(QLabel("Page ID"), 0, 2)
        grid.addWidget(QLabel("Access Token"), 0, 3)

        saved_pages = self.saved_pages
        self.combo_values = [f'{p.get("name")}  (ID: {p.get("id")})' for p in saved_pages]
        combo_placeholder = ["-- Chọn Page --"] + self.combo_values if saved_pages else ["(chưa có Page)"]

        targets = self.config_data.get("targets") or [_empty_target() for _ in range(MAX_TARGETS)]
        self.target_enabled_checks = []
        self.target_combos = []
        self.target_id_edits = []
        self.target_token_edits = []

        for i in range(MAX_TARGETS):
            t = targets[i] if i < len(targets) else _empty_target()
            row_i = i + 1

            chk = QCheckBox()
            chk.setChecked(bool(t.get("enabled")))
            grid.addWidget(chk, row_i, 0)
            self.target_enabled_checks.append(chk)

            combo = QComboBox()
            combo.setObjectName("combo")
            combo.addItems(combo_placeholder)
            grid.addWidget(combo, row_i, 1)
            self.target_combos.append(combo)

            id_edit = QLineEdit(t.get("page_id", ""))
            id_edit.setObjectName("lineEdit")
            grid.addWidget(id_edit, row_i, 2)
            self.target_id_edits.append(id_edit)

            token_edit = QLineEdit(t.get("access_token", ""))
            token_edit.setObjectName("lineEdit")
            token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            grid.addWidget(token_edit, row_i, 3)
            self.target_token_edits.append(token_edit)

            for p in saved_pages:
                if p.get("id") == t.get("page_id") and t.get("page_id"):
                    label = f'{p.get("name")}  (ID: {p.get("id")})'
                    if label in self.combo_values:
                        combo.setCurrentIndex(self.combo_values.index(label) + 1)
                    break

            combo.currentIndexChanged.connect(lambda _idx, r=i: self._on_target_page_selected(r))

        cc.addLayout(grid)

        conn_btn_row = QHBoxLayout()
        test_conn_btn = QPushButton("🔎 Kiểm tra kết nối")
        test_conn_btn.setObjectName("secondaryBtn")
        test_conn_btn.clicked.connect(self.test_connection)
        conn_btn_row.addWidget(test_conn_btn)
        conn_btn_row.addStretch()
        cc.addLayout(conn_btn_row)
        self.connection_status_label = QLabel("Chưa kiểm tra kết nối.")
        self.connection_status_label.setObjectName("status")
        cc.addWidget(self.connection_status_label)

        card_sched, cs = make_card(outer, "Lịch đăng bài")
        sched_grid = QGridLayout()
        sched_grid.addWidget(QLabel("Đăng mỗi (phút):"), 0, 0)
        self.interval_edit = QLineEdit(str(self.config_data.get("interval_minutes", 60)))
        self.interval_edit.setObjectName("lineEdit")
        interval_validator = QDoubleValidator(0.0, 99999.0, 2, self.interval_edit)
        interval_validator.setLocale(QLocale(QLocale.Language.C))
        interval_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.interval_edit.setValidator(interval_validator)
        sched_grid.addWidget(self.interval_edit, 0, 1)

        sched_grid.addWidget(QLabel("± lệch ngẫu nhiên (phút):"), 0, 2)
        self.jitter_edit = QLineEdit(str(self.config_data.get("jitter_minutes", 0)))
        self.jitter_edit.setObjectName("lineEdit")
        jitter_validator = QDoubleValidator(0.0, 99999.0, 2, self.jitter_edit)
        jitter_validator.setLocale(QLocale(QLocale.Language.C))
        jitter_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.jitter_edit.setValidator(jitter_validator)
        sched_grid.addWidget(self.jitter_edit, 0, 3)

        sched_grid.addWidget(QLabel("Thư mục ảnh/video:"), 1, 0)
        self.media_folder_edit = QLineEdit(self.config_data.get("media_folder", DEFAULT_MEDIA_FOLDER))
        self.media_folder_edit.setObjectName("lineEdit")
        sched_grid.addWidget(self.media_folder_edit, 1, 1, 1, 2)
        browse_btn = QPushButton("Chọn...")
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self._browse_media_folder)
        sched_grid.addWidget(browse_btn, 1, 3)
        cs.addLayout(sched_grid)

        self.use_media_check = QCheckBox("Kèm 1 ảnh/video ngẫu nhiên từ thư mục trên khi đăng")
        self.use_media_check.setChecked(bool(self.config_data.get("use_media", True)))
        cs.addWidget(self.use_media_check)

        card_posts, cp = make_card(outer, "Nội dung bài viết")
        self.post_boxes = []
        self.count_labels = []
        existing = self.config_data.get("posts", [""] * NUM_POSTS)
        for i in range(NUM_POSTS):
            cp.addWidget(QLabel(f"Bài viết {i + 1}:"))
            box = QPlainTextEdit()
            box.setObjectName("lineEdit")
            box.setFixedHeight(64)
            if i < len(existing):
                box.setPlainText(existing[i])
            box.textChanged.connect(lambda idx=i: self._update_count(idx))
            cp.addWidget(box)
            count_lbl = QLabel("0 ký tự")
            count_lbl.setObjectName("countLabel")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            cp.addWidget(count_lbl)
            self.post_boxes.append(box)
            self.count_labels.append(count_lbl)
            self._update_count(i)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    # ------------------------------------------------------------------
    # TAB 3: AUTO SHARE GROUP
    # ------------------------------------------------------------------
    def _pg_autoshare(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        outer.addWidget(QLabel("🚀 Auto Share Group - Giả lập Trình duyệt Anti-bot"))

        card_share, cs = make_card(
            outer, "Cấu hình Share Bài Viết Tự Động Vào Group",
            "Tự động điều khiển trình duyệt (Chrome/Cốc Cốc Profile) để share bài viết vừa đăng lên các Nhóm."
        )

        self.auto_share_check = QCheckBox("Kích hoạt tự động Share Group sau khi đăng bài thành công")
        self.auto_share_check.setChecked(bool(self.config_data.get("auto_share_enabled", False)))
        cs.addWidget(self.auto_share_check)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Đường dẫn Profile Cốc Cốc / Chrome:"), 0, 0)
        self.profile_path_edit = QLineEdit(self.config_data.get("browser_profile_path", ""))
        self.profile_path_edit.setObjectName("lineEdit")
        self.profile_path_edit.setPlaceholderText("C:\\Users\\Name\\AppData\\Local\\CocCoc\\Browser\\User Data\\Default")
        grid.addWidget(self.profile_path_edit, 0, 1)

        browse_prof_btn = QPushButton("Chọn Folder...")
        browse_prof_btn.setObjectName("secondaryBtn")
        browse_prof_btn.clicked.connect(self._browse_profile_folder)
        grid.addWidget(browse_prof_btn, 0, 2)

        grid.addWidget(QLabel("Delay giữa các lần Share (Min - Max giây):"), 1, 0)
        delay_layout = QHBoxLayout()
        self.share_delay_min_edit = QLineEdit(str(self.config_data.get("share_delay_min", 15)))
        self.share_delay_min_edit.setObjectName("lineEdit")
        self.share_delay_min_edit.setFixedWidth(60)
        delay_min_validator = QDoubleValidator(0.0, 99999.0, 2, self.share_delay_min_edit)
        delay_min_validator.setLocale(QLocale(QLocale.Language.C))
        delay_min_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.share_delay_min_edit.setValidator(delay_min_validator)
        delay_layout.addWidget(self.share_delay_min_edit)
        delay_layout.addWidget(QLabel("đến"))
        self.share_delay_max_edit = QLineEdit(str(self.config_data.get("share_delay_max", 30)))
        self.share_delay_max_edit.setObjectName("lineEdit")
        self.share_delay_max_edit.setFixedWidth(60)
        delay_max_validator = QDoubleValidator(0.0, 99999.0, 2, self.share_delay_max_edit)
        delay_max_validator.setLocale(QLocale(QLocale.Language.C))
        delay_max_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.share_delay_max_edit.setValidator(delay_max_validator)
        delay_layout.addWidget(self.share_delay_max_edit)
        delay_layout.addWidget(QLabel("giây (Random Anti-Spam)"))
        delay_layout.addStretch()
        grid.addLayout(delay_layout, 1, 1, 1, 2)

        cs.addLayout(grid)

        cs.addWidget(QLabel("Danh sách URL / ID Group Facebook (Mỗi dòng 1 nhóm):"))
        self.group_list_edit = QPlainTextEdit()
        self.group_list_edit.setObjectName("lineEdit")
        self.group_list_edit.setPlainText(self.config_data.get("group_list", ""))
        self.group_list_edit.setFixedHeight(180)
        cs.addWidget(self.group_list_edit)

        outer.addStretch()
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    # ------------------------------------------------------------------
    # TAB 4: ACCESS TOKEN
    # ------------------------------------------------------------------
    def _pg_token(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        outer.addWidget(QLabel("🔑 Access Token - Đăng nhập Facebook để tự lấy Token"))
        card, cl = make_card(outer, "Lấy Access Token tự động")
        grid = QGridLayout()
        grid.addWidget(QLabel("App ID:"), 0, 0)
        self.oauth_app_id_edit = QLineEdit(self.config_data.get("fb_app_id", ""))
        self.oauth_app_id_edit.setObjectName("lineEdit")
        grid.addWidget(self.oauth_app_id_edit, 0, 1)

        grid.addWidget(QLabel("App Secret:"), 1, 0)
        self.oauth_app_secret_edit = QLineEdit(self.config_data.get("fb_app_secret", ""))
        self.oauth_app_secret_edit.setObjectName("lineEdit")
        self.oauth_app_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self.oauth_app_secret_edit, 1, 1)

        toggle_secret_btn = QPushButton("Hiện")
        toggle_secret_btn.setObjectName("secondaryBtn")
        toggle_secret_btn.clicked.connect(self._toggle_oauth_secret)
        grid.addWidget(toggle_secret_btn, 1, 2)
        cl.addLayout(grid)

        btn_row = QHBoxLayout()
        self.oauth_login_btn = QPushButton("Đăng nhập Facebook & lấy Token")
        self.oauth_login_btn.setObjectName("primaryBtn")
        self.oauth_login_btn.clicked.connect(self.start_oauth)
        btn_row.addWidget(self.oauth_login_btn)

        self.oauth_reopen_btn = QPushButton("Mở lại trình duyệt")
        self.oauth_reopen_btn.setObjectName("secondaryBtn")
        self.oauth_reopen_btn.setEnabled(False)
        self.oauth_reopen_btn.clicked.connect(self._reopen_oauth_browser)
        btn_row.addWidget(self.oauth_reopen_btn)

        self.refresh_token_now_btn = QPushButton("🔄 Làm mới Token ngay")
        self.refresh_token_now_btn.setObjectName("secondaryBtn")
        self.refresh_token_now_btn.clicked.connect(self._manual_refresh_tokens)
        btn_row.addWidget(self.refresh_token_now_btn)
        btn_row.addStretch()
        cl.addLayout(btn_row)

        card_pages, cpg = make_card(outer, "Các Fanpage đã lấy Token")
        self.pages_table = QTableWidget(0, 2)
        self.pages_table.setHorizontalHeaderLabels(["Tên Page", "Page ID"])
        self.pages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pages_table.verticalHeader().setVisible(False)
        self.pages_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pages_table.setFixedHeight(280)
        self._refresh_pages_table()
        cpg.addWidget(self.pages_table)

        outer.addStretch()
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    # ------------------------------------------------------------------
    # TAB 5: TRẢ LỜI TỰ ĐỘNG
    # ------------------------------------------------------------------
    def _pg_autoreply(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        outer.addWidget(QLabel("💬 Trả lời tự động - Trung tâm điều hành 5 Khu Vực"))

        card_wh, cwh = make_card(
            outer, "Webhook nhận sự kiện từ Facebook",
            "Mở cổng nội bộ nhận phản hồi tự động từ Messenger và Bình luận bài viết."
        )
        wh_grid = QGridLayout()
        wh_grid.addWidget(QLabel("Cổng (port):"), 0, 0)
        self.reply_port_edit = QLineEdit(str(self.config_data.get("reply_webhook_port", DEFAULT_REPLY_WEBHOOK_PORT)))
        self.reply_port_edit.setObjectName("lineEdit")
        wh_grid.addWidget(self.reply_port_edit, 0, 1)

        wh_grid.addWidget(QLabel("Verify Token:"), 0, 2)
        self.reply_verify_edit = QLineEdit(self.config_data.get("reply_verify_token", DEFAULT_REPLY_VERIFY_TOKEN))
        self.reply_verify_edit.setObjectName("lineEdit")
        wh_grid.addWidget(self.reply_verify_edit, 0, 3)
        cwh.addLayout(wh_grid)

        wh_btn_row = QHBoxLayout()
        self.reply_start_btn = QPushButton("▶ Bật trả lời tự động")
        self.reply_start_btn.setObjectName("primaryBtn")
        self.reply_start_btn.clicked.connect(self.start_autoreply)
        wh_btn_row.addWidget(self.reply_start_btn)
        self.reply_stop_btn = QPushButton("■ Tắt")
        self.reply_stop_btn.setObjectName("dangerBtn")
        self.reply_stop_btn.setEnabled(False)
        self.reply_stop_btn.clicked.connect(self.stop_autoreply)
        wh_btn_row.addWidget(self.reply_stop_btn)
        wh_btn_row.addStretch()
        cwh.addLayout(wh_btn_row)

        self.reply_status_label = QLabel("Đang tắt")
        self.reply_status_label.setObjectName("statusStopped")
        cwh.addWidget(self.reply_status_label)

        card_dash, cdash = make_card(
            outer, "🧭 KHU VỰC TỔNG THỂ - Bảng điều khiển trung tâm",
            "Quản lý đồng thời Tin nhắn Messenger & Bình luận bài viết của TẤT CẢ Fanpage đã kết nối."
        )

        toggle_row = QHBoxLayout()
        self.reply_msg_enable_cb = QCheckBox("Trả lời Tin nhắn Messenger")
        self.reply_msg_enable_cb.setChecked(self.enable_message_reply)
        self.reply_msg_enable_cb.stateChanged.connect(self._sync_reply_flags)
        toggle_row.addWidget(self.reply_msg_enable_cb)

        self.reply_cmt_enable_cb = QCheckBox("Trả lời Bình luận bài viết")
        self.reply_cmt_enable_cb.setChecked(self.enable_comment_reply)
        self.reply_cmt_enable_cb.stateChanged.connect(self._sync_reply_flags)
        toggle_row.addWidget(self.reply_cmt_enable_cb)

        self.region_priority_cb = QCheckBox("Ưu tiên kịch bản theo Khu vực")
        self.region_priority_cb.setChecked(self.region_priority)
        self.region_priority_cb.stateChanged.connect(self._sync_reply_flags)
        toggle_row.addWidget(self.region_priority_cb)
        toggle_row.addStretch()
        cdash.addLayout(toggle_row)

        stat_row = QHBoxLayout()
        self.stat_keyword_label = QLabel("🔑 Từ khóa: 0")
        self.stat_keyword_label.setObjectName("statChip")
        stat_row.addWidget(self.stat_keyword_label)
        self.stat_region_label = QLabel("📍 Khu vực bật: 0/5")
        self.stat_region_label.setObjectName("statChip")
        stat_row.addWidget(self.stat_region_label)
        self.stat_page_label = QLabel("📄 Fanpage quản lý: 0")
        self.stat_page_label.setObjectName("statChip")
        stat_row.addWidget(self.stat_page_label)
        self.stat_msg_label = QLabel("💬 Đã trả lời tin nhắn: 0")
        self.stat_msg_label.setObjectName("statChip")
        stat_row.addWidget(self.stat_msg_label)
        self.stat_cmt_label = QLabel("📝 Đã trả lời bình luận: 0")
        self.stat_cmt_label.setObjectName("statChip")
        stat_row.addWidget(self.stat_cmt_label)
        stat_row.addStretch()
        cdash.addLayout(stat_row)

        cdash.addWidget(QLabel("Fanpage đang được quản lý đồng thời:"))
        self.reply_pages_table = QTableWidget(0, 3)
        self.reply_pages_table.setHorizontalHeaderLabels(["Tên Fanpage", "Page ID", "Trạng thái"])
        self.reply_pages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.reply_pages_table.verticalHeader().setVisible(False)
        self.reply_pages_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reply_pages_table.setFixedHeight(140)
        cdash.addWidget(self.reply_pages_table)

        cdash.addWidget(QLabel("Nhật ký trả lời tự động (Messenger & Bình luận - mọi Fanpage):"))
        self.reply_activity_table = QTableWidget(0, 6)
        self.reply_activity_table.setHorizontalHeaderLabels(
            ["Thời gian", "Fanpage", "Loại", "Khu vực", "Khách nói", "Tool trả lời"])
        self.reply_activity_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.reply_activity_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.reply_activity_table.setColumnWidth(0, 80)
        self.reply_activity_table.setColumnWidth(1, 130)
        self.reply_activity_table.setColumnWidth(2, 90)
        self.reply_activity_table.setColumnWidth(3, 120)
        self.reply_activity_table.verticalHeader().setVisible(False)
        self.reply_activity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reply_activity_table.setFixedHeight(190)
        cdash.addWidget(self.reply_activity_table)

        dash_btn_row = QHBoxLayout()
        clear_log_btn = QPushButton("🧹 Xóa nhật ký")
        clear_log_btn.setObjectName("secondaryBtn")
        clear_log_btn.clicked.connect(self._clear_reply_activity)
        dash_btn_row.addWidget(clear_log_btn)

        enable_all_btn = QPushButton("✅ Bật cả 5 khu vực")
        enable_all_btn.setObjectName("secondaryBtn")
        enable_all_btn.clicked.connect(lambda: self._set_all_regions(True))
        dash_btn_row.addWidget(enable_all_btn)

        disable_all_btn = QPushButton("⛔ Tắt cả 5 khu vực")
        disable_all_btn.setObjectName("secondaryBtn")
        disable_all_btn.clicked.connect(lambda: self._set_all_regions(False))
        dash_btn_row.addWidget(disable_all_btn)

        test_btn = QPushButton("🧪 Test câu khách nhắn")
        test_btn.setObjectName("secondaryBtn")
        test_btn.clicked.connect(self._test_region_match)
        dash_btn_row.addWidget(test_btn)
        dash_btn_row.addStretch()
        cdash.addLayout(dash_btn_row)

        test_row = QHBoxLayout()
        test_row.addWidget(QLabel("Câu thử:"))
        self.region_test_edit = QLineEdit("co xe di cao xanh ha long ko shop")
        self.region_test_edit.setObjectName("lineEdit")
        self.region_test_edit.returnPressed.connect(self._test_region_match)
        test_row.addWidget(self.region_test_edit)
        cdash.addLayout(test_row)

        card_reg, creg = make_card(
            outer, "🗺️ Kịch bản chi tiết theo Khu Vực Địa Lý",
            "Mỗi khu vực là một bộ từ khóa riêng. Nhấp đúp vào ô để Sửa, dùng cột ✔ để Kích hoạt / Tạm dừng từng dòng."
        )
        self.region_tabs = QTabWidget()
        for key in REGION_ORDER:
            self.region_tabs.addTab(self._build_region_tab(key), self.region_rules.get(key, {}).get(
                "label", region_label(key)))
        self.region_tabs.addTab(self._build_common_tab(), "⚙️ CHUNG & MẶC ĐỊNH")
        creg.addWidget(self.region_tabs)

        save_reply_btn = QPushButton("💾 Lưu toàn bộ kịch bản (5 khu vực + chung)")
        save_reply_btn.setObjectName("primaryBtn")
        save_reply_btn.clicked.connect(lambda: self.save_autoreply_rules())
        outer.addWidget(save_reply_btn, 0, Qt.AlignmentFlag.AlignRight)

        outer.addStretch()
        scroll.setWidget(content)
        page_layout.addWidget(scroll)

        self._refresh_reply_pages_table()
        self._refresh_region_stats()
        return page

    def _build_region_tab(self, key):
        reg = self.region_rules.get(key) or copy.deepcopy(DEFAULT_REGION_RULES[key])
        self.region_rules[key] = reg

        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        cb = QCheckBox("Kích hoạt khu vực này")
        cb.setChecked(bool(self.region_enabled.get(key, True)))
        cb.stateChanged.connect(lambda _s, k=key: self._on_region_toggled(k))
        self.region_enable_boxes[key] = cb
        head.addWidget(cb)

        count_lb = QLabel("")
        count_lb.setObjectName("regionHint")
        self.region_count_labels[key] = count_lb
        head.addWidget(count_lb)
        head.addStretch()

        head.addWidget(QLabel("Tìm:"))
        search = QLineEdit()
        search.setObjectName("lineEdit")
        search.setPlaceholderText("lọc theo từ khóa hoặc câu trả lời...")
        search.setFixedWidth(230)
        search.textChanged.connect(lambda t, k=key: self._filter_region_table(k, t))
        head.addWidget(search)
        lay.addLayout(head)

        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["✔", "Từ khóa (cách nhau bởi dấu phẩy)", "Câu trả lời"])
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 40)
        table.setColumnWidth(1, 300)
        table.verticalHeader().setVisible(False)
        table.setFixedHeight(360)
        table.setWordWrap(False)
        self.region_tables[key] = table
        self._fill_region_table(key)
        lay.addWidget(table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ Thêm")
        add_btn.setObjectName("secondaryBtn")
        add_btn.clicked.connect(lambda _c, k=key: self._add_region_row(k))
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("➖ Xóa dòng chọn")
        del_btn.setObjectName("secondaryBtn")
        del_btn.clicked.connect(lambda _c, k=key: self._del_region_row(k))
        btn_row.addWidget(del_btn)

        on_btn = QPushButton("✅ Bật tất cả dòng")
        on_btn.setObjectName("secondaryBtn")
        on_btn.clicked.connect(lambda _c, k=key: self._set_region_rows(k, True))
        btn_row.addWidget(on_btn)

        off_btn = QPushButton("⛔ Tắt tất cả dòng")
        off_btn.setObjectName("secondaryBtn")
        off_btn.clicked.connect(lambda _c, k=key: self._set_region_rows(k, False))
        btn_row.addWidget(off_btn)

        reset_btn = QPushButton("♻️ Khôi phục mặc định")
        reset_btn.setObjectName("dangerBtn")
        reset_btn.clicked.connect(lambda _c, k=key: self._reset_region(k))
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("Câu trả lời mặc định của khu vực (khi khách chỉ nhắc tên vùng):"))
        edit = QLineEdit(reg.get("default_reply", ""))
        edit.setObjectName("lineEdit")
        self.region_default_edits[key] = edit
        lay.addWidget(edit)
        return tab

    def _build_common_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Kịch bản CHUNG cho Tin nhắn Messenger:"))
        self.msg_rules_table = QTableWidget(0, 2)
        self.msg_rules_table.setHorizontalHeaderLabels(["Từ khóa (cách bởi dấu phẩy)", "Câu trả lời"])
        self.msg_rules_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.msg_rules_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.msg_rules_table.setColumnWidth(0, 260)
        self.msg_rules_table.setFixedHeight(160)
        self._fill_rules_table(self.msg_rules_table, self.msg_rules)
        lay.addWidget(self.msg_rules_table)

        msg_btn_row = QHBoxLayout()
        add_msg_btn = QPushButton("➕ Thêm dòng")
        add_msg_btn.setObjectName("secondaryBtn")
        add_msg_btn.clicked.connect(lambda: self._add_rule_row(self.msg_rules_table))
        msg_btn_row.addWidget(add_msg_btn)
        del_msg_btn = QPushButton("➖ Xóa dòng chọn")
        del_msg_btn.setObjectName("secondaryBtn")
        del_msg_btn.clicked.connect(lambda: self._del_rule_row(self.msg_rules_table))
        msg_btn_row.addWidget(del_msg_btn)
        msg_btn_row.addStretch()
        lay.addLayout(msg_btn_row)

        lay.addWidget(QLabel("Kịch bản CHUNG cho Bình luận bài viết:"))
        self.comment_rules_table = QTableWidget(0, 2)
        self.comment_rules_table.setHorizontalHeaderLabels(["Từ khóa (cách bởi dấu phẩy)", "Câu trả lời"])
        self.comment_rules_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.comment_rules_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.comment_rules_table.setColumnWidth(0, 260)
        self.comment_rules_table.setFixedHeight(150)
        self._fill_rules_table(self.comment_rules_table, self.comment_rules)
        lay.addWidget(self.comment_rules_table)

        cmt_btn_row = QHBoxLayout()
        add_cmt_btn = QPushButton("➕ Thêm dòng")
        add_cmt_btn.setObjectName("secondaryBtn")
        add_cmt_btn.clicked.connect(lambda: self._add_rule_row(self.comment_rules_table))
        cmt_btn_row.addWidget(add_cmt_btn)
        del_cmt_btn = QPushButton("➖ Xóa dòng chọn")
        del_cmt_btn.setObjectName("secondaryBtn")
        del_cmt_btn.clicked.connect(lambda: self._del_rule_row(self.comment_rules_table))
        cmt_btn_row.addWidget(del_cmt_btn)
        cmt_btn_row.addStretch()
        lay.addLayout(cmt_btn_row)

        grid = QGridLayout()
        grid.addWidget(QLabel("Trả lời mặc định tin nhắn:"), 0, 0)
        self.default_msg_edit = QLineEdit(self.default_message_reply)
        self.default_msg_edit.setObjectName("lineEdit")
        grid.addWidget(self.default_msg_edit, 0, 1)

        grid.addWidget(QLabel("Trả lời mặc định bình luận:"), 1, 0)
        self.default_cmt_edit = QLineEdit(self.default_comment_reply)
        self.default_cmt_edit.setObjectName("lineEdit")
        grid.addWidget(self.default_cmt_edit, 1, 1)

        grid.addWidget(QLabel("Câu chào TỔNG THỂ (không khớp khu vực nào):"), 2, 0)
        self.global_default_edit = QLineEdit(self.global_default_reply)
        self.global_default_edit.setObjectName("lineEdit")
        grid.addWidget(self.global_default_edit, 2, 1)
        lay.addLayout(grid)
        lay.addStretch()
        return tab

    def _fill_region_table(self, key):
        table = self.region_tables.get(key)
        if table is None:
            return
        rules = (self.region_rules.get(key) or {}).get("rules", [])
        table.setRowCount(len(rules))
        for r, rule in enumerate(rules):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if rule.get("enabled", True)
                              else Qt.CheckState.Unchecked)
            table.setItem(r, 0, chk)
            table.setItem(r, 1, QTableWidgetItem(rule.get("keywords", "")))
            table.setItem(r, 2, QTableWidgetItem(rule.get("reply", "")))
        self._refresh_region_stats()

    def _read_region_table(self, key):
        table = self.region_tables.get(key)
        rules = []
        if table is None:
            return rules
        for r in range(table.rowCount()):
            kw_item = table.item(r, 1)
            rep_item = table.item(r, 2)
            chk = table.item(r, 0)
            keywords = kw_item.text().strip() if kw_item else ""
            reply = rep_item.text().strip() if rep_item else ""
            if not keywords or not reply:
                continue
            rules.append({
                "enabled": bool(chk and chk.checkState() == Qt.CheckState.Checked),
                "keywords": keywords,
                "reply": reply,
            })
        return rules

    def _add_region_row(self, key):
        table = self.region_tables.get(key)
        if table is None:
            return
        row = table.rowCount()
        table.insertRow(row)
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Checked)
        table.setItem(row, 0, chk)
        table.setItem(row, 1, QTableWidgetItem(""))
        table.setItem(row, 2, QTableWidgetItem(""))
        table.scrollToBottom()
        table.setCurrentCell(row, 1)

    def _del_region_row(self, key):
        table = self.region_tables.get(key)
        if table is None:
            return
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)
            self._refresh_region_stats()

    def _set_region_rows(self, key, state):
        table = self.region_tables.get(key)
        if table is None:
            return
        for r in range(table.rowCount()):
            item = table.item(r, 0)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)

    def _reset_region(self, key):
        answer = QMessageBox.question(
            self, "Khôi phục mặc định",
            f"Khôi phục toàn bộ kịch bản mặc định cho khu vực {region_label(key)}?\n"
            "Các dòng bạn đã sửa trong khu vực này sẽ bị ghi đè.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.region_rules[key] = copy.deepcopy(DEFAULT_REGION_RULES[key])
        self._fill_region_table(key)
        if key in self.region_default_edits:
            self.region_default_edits[key].setText(self.region_rules[key].get("default_reply", ""))
        self.log(f"Đã khôi phục kịch bản mặc định khu vực {region_label(key)}.", "success")

    def _filter_region_table(self, key, text):
        table = self.region_tables.get(key)
        if table is None:
            return
        needle = normalize_text(text)
        for r in range(table.rowCount()):
            if not needle:
                table.setRowHidden(r, False)
                continue
            kw = table.item(r, 1).text() if table.item(r, 1) else ""
            rep = table.item(r, 2).text() if table.item(r, 2) else ""
            hay = normalize_text(kw + " " + rep)
            table.setRowHidden(r, needle not in hay)

    def _on_region_toggled(self, key):
        box = self.region_enable_boxes.get(key)
        if box is not None:
            self.region_enabled[key] = box.isChecked()
        self._refresh_region_stats()

    def _set_all_regions(self, state):
        for key, box in self.region_enable_boxes.items():
            box.setChecked(state)
            self.region_enabled[key] = state
        self._refresh_region_stats()

    def _sync_reply_flags(self):
        if hasattr(self, "reply_msg_enable_cb"):
            self.enable_message_reply = self.reply_msg_enable_cb.isChecked()
        if hasattr(self, "reply_cmt_enable_cb"):
            self.enable_comment_reply = self.reply_cmt_enable_cb.isChecked()
        if hasattr(self, "region_priority_cb"):
            self.region_priority = self.region_priority_cb.isChecked()

    def _refresh_region_stats(self):
        if not hasattr(self, "stat_keyword_label"):
            return
        total_rules = 0
        total_kw = 0
        for key in REGION_ORDER:
            table = self.region_tables.get(key)
            if table is not None:
                rows = table.rowCount()
                kws = 0
                for r in range(rows):
                    item = table.item(r, 1)
                    if item:
                        kws += len([k for k in item.text().split(",") if k.strip()])
            else:
                rules = (self.region_rules.get(key) or {}).get("rules", [])
                rows = len(rules)
                kws = sum(len([k for k in ru.get("keywords", "").split(",") if k.strip()])
                          for ru in rules)
            total_rules += rows
            total_kw += kws
            lb = self.region_count_labels.get(key)
            if lb is not None:
                lb.setText(f"{rows} dòng kịch bản · {kws} từ khóa")
        on_count = sum(1 for k in REGION_ORDER if self.region_enabled.get(k, True))
        self.stat_keyword_label.setText(f"🔑 Từ khóa: {total_kw} ({total_rules} dòng)")
        self.stat_region_label.setText(f"📍 Khu vực bật: {on_count}/{len(REGION_ORDER)}")

    def _clear_reply_activity(self):
        if hasattr(self, "reply_activity_table"):
            self.reply_activity_table.setRowCount(0)

    def _test_region_match(self):
        self.save_autoreply_rules(silent=True)
        text = self.region_test_edit.text().strip()
        if not text:
            return
        key, reply, kw = find_region_match(text, self.region_rules, self.region_enabled)
        if key:
            self.log(f'🧪 Thử "{text}" → khớp {region_label(key)} (từ khóa: "{kw}")', "success")
            self.log(f"    ↳ {reply}", "info")
        else:
            self.log(f'🧪 Thử "{text}" → không khớp khu vực nào, dùng câu mặc định tổng thể.', "warning")
            self.log(f"    ↳ {self.global_default_reply}", "info")

    def _on_reply_event(self, info):
        if info.get("kind") == "comment":
            self.reply_count_cmt += 1
        else:
            self.reply_count_msg += 1
        if hasattr(self, "stat_msg_label"):
            self.stat_msg_label.setText(f"💬 Đã trả lời tin nhắn: {self.reply_count_msg}")
            self.stat_cmt_label.setText(f"📝 Đã trả lời bình luận: {self.reply_count_cmt}")

        table = getattr(self, "reply_activity_table", None)
        if table is None:
            return
        table.insertRow(0)
        table.setItem(0, 0, QTableWidgetItem(datetime.datetime.now().strftime("%H:%M:%S")))
        table.setItem(0, 1, QTableWidgetItem(str(info.get("page", ""))))
        table.setItem(0, 2, QTableWidgetItem("💬 Tin nhắn" if info.get("kind") != "comment" else "📝 Bình luận"))
        table.setItem(0, 3, QTableWidgetItem(str(info.get("region", "Tổng thể"))))
        table.setItem(0, 4, QTableWidgetItem(str(info.get("incoming", ""))))
        table.setItem(0, 5, QTableWidgetItem(str(info.get("reply", ""))))
        while table.rowCount() > 300:
            table.removeRow(table.rowCount() - 1)

    def _pg_about(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        outer.addWidget(QLabel("ℹ️ Giới thiệu Tool"))

        card_info, cinfo = make_card(
            outer, "FB Auto Poster & Share Group Pro",
            "Giải pháp đăng bài Fanpage tự động, trả lời bình luận/tin nhắn và Share bài viết vào các nhóm Facebook."
        )

        cinfo.addWidget(QLabel("🏷️ Phiên bản: 2.1 Pro Fix UI"))
        cinfo.addWidget(QLabel("👤 Phát triển bởi: MaeAry™️"))
        cinfo.addWidget(QLabel("🐍 Ngôn ngữ: Python 3 + PyQt6 + Playwright"))

        card_art, cart = make_card(outer, "Thông tin tác quyền & Kênh liên hệ")
        
        info_text = (
            "Copyright by MaeAry™️\n\n"
            "My Youtube Channel : NyAry\n"
            "My Github Profile: https://github.com/NyArySadNight\n\n"
            "My Discord And Server:\n"
            "User name: aryna09851\n"
            "Server : https://discord.gg/kSHYuvJTud\n\n"
            "Thanks for using my tools and tools box"
        )
        
        info_box = QPlainTextEdit()
        info_box.setObjectName("panel")
        info_box.setReadOnly(True)
        info_box.setPlainText(info_text)
        info_box.setFixedHeight(220)
        info_box.setFont(QFont("Segoe UI", 10))
        
        cart.addWidget(info_box)

        outer.addStretch()
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    def _fill_rules_table(self, table, rules):
        table.setRowCount(len(rules))
        for r, rule in enumerate(rules):
            table.setItem(r, 0, QTableWidgetItem(rule.get("keywords", "")))
            table.setItem(r, 1, QTableWidgetItem(rule.get("reply", "")))

    def _add_rule_row(self, table):
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(""))
        table.setItem(row, 1, QTableWidgetItem(""))

    def _del_rule_row(self, table):
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def _read_rules_table(self, table):
        rules = []
        for r in range(table.rowCount()):
            kw_item = table.item(r, 0)
            reply_item = table.item(r, 1)
            keywords = kw_item.text().strip() if kw_item else ""
            reply = reply_item.text().strip() if reply_item else ""
            if keywords and reply:
                rules.append({"keywords": keywords, "reply": reply})
        return rules

    def save_autoreply_rules(self, silent=False):
        self.msg_rules = self._read_rules_table(self.msg_rules_table)
        self.comment_rules = self._read_rules_table(self.comment_rules_table)
        self.default_message_reply = self.default_msg_edit.text().strip()
        self.default_comment_reply = self.default_cmt_edit.text().strip()
        self.global_default_reply = self.global_default_edit.text().strip() or DEFAULT_GLOBAL_REPLY
        self._sync_reply_flags()

        for key in REGION_ORDER:
            reg = self.region_rules.setdefault(key, copy.deepcopy(DEFAULT_REGION_RULES[key]))
            reg["label"] = DEFAULT_REGION_RULES[key]["label"]
            reg["rules"] = self._read_region_table(key)
            edit = self.region_default_edits.get(key)
            if edit is not None:
                reg["default_reply"] = edit.text().strip()
            box = self.region_enable_boxes.get(key)
            if box is not None:
                self.region_enabled[key] = box.isChecked()

        save_config({
            "reply_msg_rules": self.msg_rules,
            "reply_comment_rules": self.comment_rules,
            "reply_default_message": self.default_message_reply,
            "reply_default_comment": self.default_comment_reply,
            "reply_region_rules": self.region_rules,
            "reply_region_enabled": self.region_enabled,
            "reply_enable_message": self.enable_message_reply,
            "reply_enable_comment": self.enable_comment_reply,
            "reply_region_priority": self.region_priority,
            "reply_global_default": self.global_default_reply,
            "reply_webhook_port": self.reply_port_edit.text().strip() or str(DEFAULT_REPLY_WEBHOOK_PORT),
            "reply_verify_token": self.reply_verify_edit.text().strip() or DEFAULT_REPLY_VERIFY_TOKEN,
        })
        self._refresh_region_stats()
        if not silent:
            total_rules, total_kw = count_region_keywords(self.region_rules)
            self.log(
                f"Đã lưu kịch bản: {total_kw} từ khóa / {total_rules} dòng trên 5 khu vực, "
                f"{len(self.msg_rules)} dòng chung (tin nhắn), {len(self.comment_rules)} dòng chung (bình luận).",
                "success")

    def _toggle_oauth_secret(self):
        self.oauth_secret_shown = not self.oauth_secret_shown
        self.oauth_app_secret_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if self.oauth_secret_shown else QLineEdit.EchoMode.Password
        )

    def start_oauth(self):
        app_id = self.oauth_app_id_edit.text().strip()
        app_secret = self.oauth_app_secret_edit.text().strip()
        if not app_id or not app_secret:
            QMessageBox.critical(self, "Lỗi", "Nhập App ID và App Secret trước.")
            return

        save_config({"fb_app_id": app_id, "fb_app_secret": app_secret})

        _OAuthCaptureHandler.captured_code = None
        _OAuthCaptureHandler.captured_error = None

        params = {
            "client_id": app_id,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "scope": OAUTH_SCOPES,
            "response_type": "code",
        }
        auth_url = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?" + urllib.parse.urlencode(params)
        self.oauth_last_auth_url = auth_url
        self.oauth_reopen_btn.setEnabled(True)
        self.oauth_login_btn.setEnabled(False)

        self.log("Đang mở trình duyệt để bạn đăng nhập & cấp quyền Facebook...", "info")
        webbrowser.open(auth_url)
        threading.Thread(target=self._run_oauth_local_server, args=(app_id, app_secret), daemon=True).start()

    def _reopen_oauth_browser(self):
        if self.oauth_last_auth_url:
            webbrowser.open(self.oauth_last_auth_url)
            self.log("Đã mở lại trang cấp quyền Facebook.", "info")

    def _run_oauth_local_server(self, app_id, app_secret):
        try:
            server = http.server.HTTPServer(("localhost", OAUTH_REDIRECT_PORT), _OAuthCaptureHandler)
        except OSError as e:
            self.sig.log_sig.emit(f"Không mở được cổng {OAUTH_REDIRECT_PORT}: {e}", "error")
            self.sig.oauth_login_enable_sig.emit(True)
            return

        server.timeout = 120
        deadline = time.monotonic() + server.timeout
        while _OAuthCaptureHandler.captured_code is None and _OAuthCaptureHandler.captured_error is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            server.timeout = remaining
            server.handle_request()
        server.server_close()
        self.sig.oauth_login_enable_sig.emit(True)

        if _OAuthCaptureHandler.captured_error:
            self.sig.log_sig.emit(f"Facebook trả lỗi: {_OAuthCaptureHandler.captured_error}", "error")
            return
        if not _OAuthCaptureHandler.captured_code:
            self.sig.log_sig.emit("Hết thời gian chờ, chưa nhận được quyền.", "warning")
            return

        self.sig.log_sig.emit("Đã nhận quyền, đang đổi lấy User Access Token dài hạn...", "success")
        self._exchange_and_load_pages(app_id, app_secret, _OAuthCaptureHandler.captured_code)

    def _exchange_and_load_pages(self, app_id, app_secret, code):
        try:
            r1 = requests.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token",
                params={"client_id": app_id, "redirect_uri": OAUTH_REDIRECT_URI, "client_secret": app_secret, "code": code},
                timeout=30,
            )
            r1_data = r1.json()
            if "access_token" not in r1_data:
                self.sig.log_sig.emit(f"Lỗi lấy token: {r1_data}", "error")
                return
            short_token = r1_data["access_token"]

            r2 = requests.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token",
                params={"grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret, "fb_exchange_token": short_token},
                timeout=30,
            )
            long_user_token = r2.json().get("access_token", short_token)

            r3 = requests.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts",
                params={"access_token": long_user_token},
                timeout=30,
            )
            pages = r3.json().get("data", [])
            if not pages:
                self.sig.log_sig.emit("Không tìm thấy Page nào thuộc quyền quản lý.", "warning")
                return

            new_pages = [{"id": p.get("id"), "name": p.get("name"), "access_token": p.get("access_token")} for p in pages]
            merged = {p["id"]: p for p in self.saved_pages}
            for p in new_pages:
                merged[p["id"]] = p
            merged_pages = list(merged.values())

            save_config({"pages": merged_pages, "fb_user_token": long_user_token})
            self.fb_user_token = long_user_token
            self.sig.pages_loaded_sig.emit(merged_pages, new_pages)
        except Exception as e:
            self.sig.log_sig.emit(f"Lỗi kết nối khi lấy token: {e}", "error")

    def _on_oauth_pages_loaded(self, merged_pages, new_pages):
        self.saved_pages = merged_pages
        self.combo_values = [f'{p.get("name")}  (ID: {p.get("id")})' for p in merged_pages]
        combo_items = ["-- Chọn Page --"] + self.combo_values

        for combo in self.target_combos:
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(combo_items)
            idx = combo.findText(cur)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        empty_rows = [i for i in range(MAX_TARGETS) if not self.target_id_edits[i].text().strip()]
        for i, page in zip(empty_rows, new_pages):
            self.target_id_edits[i].setText(page.get("id", ""))
            self.target_token_edits[i].setText(page.get("access_token", ""))
            self.target_enabled_checks[i].setChecked(True)

        self._refresh_pages_table()
        self.save(silent=True)
        if self.fb_user_token and not self.token_refresh_timer.isActive():
            self.token_refresh_timer.start()

        self.log(f"Đã lấy token cho {len(new_pages)} Page.", "success")

    def _manual_refresh_tokens(self):
        if not self.fb_user_token:
            QMessageBox.information(self, "Thông báo", "Vui lòng đăng nhập Facebook trước.")
            return
        self.log("Đang làm mới Access Token thủ công...", "info")
        threading.Thread(target=self._do_auto_refresh_tokens, daemon=True).start()

    def _auto_refresh_tokens(self):
        if self.fb_user_token:
            threading.Thread(target=self._do_auto_refresh_tokens, daemon=True).start()

    def _do_auto_refresh_tokens(self):
        if not self.fb_user_token:
            return
        try:
            resp = requests.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts",
                params={"access_token": self.fb_user_token},
                timeout=30,
            )
            data = resp.json()
            pages = data.get("data", [])
            if pages:
                refreshed = [{"id": p.get("id"), "name": p.get("name"), "access_token": p.get("access_token")} for p in pages]
                merged = {p["id"]: p for p in self.saved_pages}
                for p in refreshed:
                    merged[p["id"]] = p
                merged_pages = list(merged.values())
                save_config({"pages": merged_pages})
                self.sig.token_refreshed_sig.emit(merged_pages)
        except Exception as e:
            self.sig.log_sig.emit(f"Lỗi tự động làm mới Token: {e}", "error")

    def _on_tokens_auto_refreshed(self, merged_pages):
        self.saved_pages = merged_pages
        for i in range(MAX_TARGETS):
            page_id = self.target_id_edits[i].text().strip()
            if page_id:
                match = next((p for p in merged_pages if p.get("id") == page_id), None)
                if match and match.get("access_token"):
                    self.target_token_edits[i].setText(match["access_token"])
        self._refresh_pages_table()
        self.save(silent=True)
        self.log("Đã cập nhật Access Token mới nhất cho các Page.", "success")

    def _refresh_token_cache(self):
        cache = {}
        for p in self.saved_pages:
            if p.get("id") and p.get("access_token"):
                cache[str(p["id"])] = p["access_token"]
        for i in range(MAX_TARGETS):
            pid = self.target_id_edits[i].text().strip()
            tok = self.target_token_edits[i].text().strip()
            if pid and tok:
                cache[pid] = tok
        self.page_token_cache = cache
        self.reply_verify_token_cache = (
            self.reply_verify_edit.text().strip() or DEFAULT_REPLY_VERIFY_TOKEN
        )
        return cache

    def get_reply_verify_token(self):
        return self.reply_verify_token_cache or DEFAULT_REPLY_VERIFY_TOKEN

    def get_token_for_page(self, page_id):
        return self.page_token_cache.get(str(page_id))

    def start_autoreply(self):
        if self.reply_running:
            return
        try:
            port = int(self.reply_port_edit.text().strip())
        except ValueError:
            QMessageBox.critical(self, "Lỗi", "Port phải là số nguyên.")
            return

        self.save_autoreply_rules()
        self._refresh_token_cache()
        _ReplyWebhookHandler.app_ref = self

        try:
            self.webhook_server = http.server.ThreadingHTTPServer(("0.0.0.0", port), _ReplyWebhookHandler)
        except OSError as e:
            QMessageBox.critical(self, "Lỗi", f"Không mở được cổng {port}: {e}")
            return

        self.webhook_thread = threading.Thread(target=self.webhook_server.serve_forever, daemon=True)
        self.webhook_thread.start()
        self.sig.reply_running_sig.emit(True)
        self.log(f"Đã bật Trả lời tự động tại cổng {port}.", "success")

    def stop_autoreply(self):
        if self.webhook_server:
            threading.Thread(target=self._shutdown_webhook_server, daemon=True).start()

    def _shutdown_webhook_server(self):
        try:
            self.webhook_server.shutdown()
            self.webhook_server.server_close()
        except Exception:
            pass
        self.webhook_server = None
        self.sig.reply_running_sig.emit(False)
        self.sig.log_sig.emit("Đã tắt Trả lời tự động.", "info")

    def _on_reply_running_state(self, running):
        self.reply_running = running
        self._refresh_reply_pages_table()
        self.reply_start_btn.setEnabled(not running)
        self.reply_stop_btn.setEnabled(running)
        self.reply_port_edit.setEnabled(not running)
        if running:
            self.reply_status_label.setText("Đang chạy")
            self.reply_status_label.setObjectName("statusRunning")
        else:
            self.reply_status_label.setText("Đang tắt")
            self.reply_status_label.setObjectName("statusStopped")
        self.reply_status_label.style().unpolish(self.reply_status_label)
        self.reply_status_label.style().polish(self.reply_status_label)

    def _page_display_name(self, page_id):
        for p in self.saved_pages or []:
            if str(p.get("id")) == str(page_id):
                return p.get("name") or page_id
        return page_id

    def resolve_auto_reply(self, text, kind="message"):
        if self.region_priority:
            key, reply, _kw = find_region_match(text, self.region_rules, self.region_enabled)
            if key and reply:
                return reply, region_label(key)

        if kind == "comment":
            reply = find_reply(text, self.comment_rules, self.default_comment_reply)
        else:
            reply = find_reply(text, self.msg_rules, self.default_message_reply)
        if reply:
            return reply, "Chung"

        if kind == "message":
            return self.global_default_reply, "Tổng thể"
        return "", "Tổng thể"

    def handle_incoming_message(self, page_id, event):
        try:
            if not self.enable_message_reply:
                return
            message = event.get("message") or {}
            if message.get("is_echo"):
                return
            text = message.get("text")
            sender_id = (event.get("sender") or {}).get("id")
            if not text or not sender_id:
                return
            token = self.get_token_for_page(page_id)
            if not token:
                return

            reply, region_name = self.resolve_auto_reply(text, "message")
            if not reply:
                return

            resp = requests.post(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages",
                params={"access_token": token},
                json={"recipient": {"id": sender_id}, "message": {"text": reply}},
                timeout=20,
            )
            if resp.status_code == 200:
                self.sig.log_sig.emit(
                    f'💬 [{region_name}] Trả lời tin nhắn: "{text}" -> "{reply}"', "success")
                self.sig.reply_event_sig.emit({
                    "kind": "message",
                    "page": self._page_display_name(page_id),
                    "region": region_name,
                    "incoming": text,
                    "reply": reply,
                })
            else:
                self.sig.log_sig.emit(
                    f"Không gửi được tin nhắn trả lời: {format_fb_error(resp.json())}", "error")
        except Exception as e:
            self.sig.log_sig.emit(f"Lỗi xử lý tin nhắn: {e}", "error")

    def handle_incoming_comment(self, page_id, value):
        try:
            if not self.enable_comment_reply:
                return
            if value.get("item") != "comment" or value.get("verb") != "add":
                return
            if (value.get("from") or {}).get("id") == page_id:
                return

            comment_id = value.get("comment_id")
            text = value.get("message", "")
            if not comment_id:
                return
            token = self.get_token_for_page(page_id)
            if not token:
                return

            reply, region_name = self.resolve_auto_reply(text, "comment")
            if not reply:
                return

            resp = requests.post(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{comment_id}/comments",
                params={"access_token": token},
                data={"message": reply},
                timeout=20,
            )
            if resp.status_code == 200:
                self.sig.log_sig.emit(
                    f'📝 [{region_name}] Trả lời bình luận: "{text}" -> "{reply}"', "success")
                self.sig.reply_event_sig.emit({
                    "kind": "comment",
                    "page": self._page_display_name(page_id),
                    "region": region_name,
                    "incoming": text,
                    "reply": reply,
                })
            else:
                self.sig.log_sig.emit(
                    f"Không gửi được bình luận trả lời: {format_fb_error(resp.json())}", "error")
        except Exception as e:
            self.sig.log_sig.emit(f"Lỗi xử lý bình luận: {e}", "error")

# ==========================================================================
# Main Entrypoint
# ==========================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(CSS)
    w = FBAutoPosterApp()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()