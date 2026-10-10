#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FB Auto Poster & Share Group Pro - MaeAry™ Edition (Fix UI Sidebar 100%)
========================================================================
Giao diện Sidebar dọc cao cấp chuẩn MaeAry™ v2.1 Pro Fix UI:
  - Sidebar bên trái: Tổng quan, Đăng bài tự động, Auto Share Group, Access Token, Trả lời tự động, Giới thiệu.
  - Tự động bốc ngẫu nhiên bài viết từ Tab "Đăng bài tự động" để Playwright dán trực tiếp vào Group.
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
    QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QIcon, QColor

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

OAUTH_REDIRECT_PORT = 8765
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_REDIRECT_PORT}/"
OAUTH_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts,pages_messaging,pages_manage_engagement"

DEFAULT_REPLY_WEBHOOK_PORT = 8766
DEFAULT_REPLY_VERIFY_TOKEN = "myverifytoken123"
CONTACT_HOTLINE = "0966.785.179"

DEFAULT_REGION_RULES = {
    "ha_long": {
        "label": "🌊 HẠ LONG",
        "rules": [
            {"enabled": True, "keywords": "xe 4 cho ha long, 4 cho ha long, xe con ha long", "reply": "Dạ bên em có xe 4 chỗ đời mới chạy Hạ Long ạ, giá bao xe 1.000.000đ, đi ghép 200.000đ/khách. Hotline {hotline}"},
            {"enabled": True, "keywords": "xe 7 cho ha long, 7 cho ha long, xe gia dinh ha long", "reply": "Dạ xe 7 chỗ (Xpander/Innova/Fortuner) tuyến Hạ Long giá bao xe 1.300.000đ ạ 🚘 Rộng rãi, sạch sẻ. Hotline {hotline}"},
            {"enabled": True, "keywords": "don tan noi ha long, don tan nha ha long", "reply": "Dạ bên em đón trả TẬN NƠI trong khu vực Hạ Long ạ, không phải ra bến 🥰 Anh/chị nhắn địa chỉ giúp em nhé!"},
            {"enabled": True, "keywords": "may gio co xe ha long, lich trinh ha long", "reply": "Dạ lịch xe chạy Hạ Long hàng ngày: 5h00 - 7h00 - 9h00 - 11h00 - 13h00 - 15h00 - 17h00 - 19h00. Hotline {hotline}"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép ⇄ Hà Nội / Hải Phòng và hỗ trợ nhà đất khu vực Hạ Long ạ. Anh/chị cho em xin điểm đón và thời gian đi nhé! Hotline {hotline}"
    },
    "ha_noi": {
        "label": "🏙️ HÀ NỘI",
        "rules": [
            {"enabled": True, "keywords": "my dinh, giap bat, ha noi", "reply": "Dạ tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh bên em có xe đón tận nơi tại các quận Hà Nội ạ. Giá ghép 200.000đ/khách. Hotline {hotline}"}
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Tuyến Hà Nội ⇄ Quảng Ninh / Hải Phòng bên em chạy liên tục hàng ngày ạ. Hotline {hotline}"
    },
    "hai_phong": {"label": "⚓ HẢI PHÒNG", "rules": [], "default_reply": "Dạ xe Hải Phòng ⇄ Hạ Long / Hà Nội đón trả tận nhà ạ. Hotline {hotline}"},
    "quang_ninh": {"label": "🚩 QUẢNG NINH", "rules": [], "default_reply": "Dạ nhận xe ghép, tiện chuyến toàn tỉnh Quảng Ninh ạ. Hotline {hotline}"},
    "thai_nguyen": {"label": "⛰️ THÁI NGUYÊN", "rules": [], "default_reply": "Dạ tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long bên em chạy hàng ngày ạ. Hotline {hotline}"}
}

DEFAULT_MEDIA_FOLDER = r"C:\VidFaceAutoFix"
COCCOC_EXECUTABLE_PATH = r"C:\Program Files\CocCoc\Browser\Application\browser.exe"
DEFAULT_COCCOC_PROFILE_PATH = r"C:\Users\daon3\AppData\Local\CocCoc\Browser\User Data\Profile 1"

def normalize_text(text=""):
    import unicodedata
    text = (text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").strip()

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "targets": [{"enabled": False, "name": "", "page_id": "", "access_token": ""} for _ in range(MAX_TARGETS)],
        "posts": [""] * NUM_POSTS,
        "interval_minutes": 25.0,
        "jitter_minutes": 9.0,
        "media_folder": DEFAULT_MEDIA_FOLDER,
        "use_media": True,
        "fb_app_id": "1618093659825633",
        "fb_app_secret": "",
        "auto_share_enabled": True,
        "browser_profile_path": DEFAULT_COCCOC_PROFILE_PATH,
        "share_delay_min": 120.0,
        "share_delay_max": 240.0,
        "group_list": "",
        "reply_webhook_port": DEFAULT_REPLY_WEBHOOK_PORT,
        "reply_verify_token": DEFAULT_REPLY_VERIFY_TOKEN,
        "reply_region_rules": DEFAULT_REGION_RULES
    }

def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================================================
# Worker Auto Share Group (Playwright Cốc Cốc)
# ==========================================================================
class ShareQueueWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(str)

    def __init__(self, post_urls, group_list, profile_path, delay_min, delay_max, posts=None):
        super().__init__()
        self.queue = queue.Queue()
        for url in (post_urls or []):
            if url:
                self.queue.put(url)
        self.groups = [g.strip() for g in group_list.split("\n") if g.strip()]
        self.profile_path = profile_path
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.posts = [p.strip() for p in (posts or []) if p and p.strip()]
        self.coccoc_exe = COCCOC_EXECUTABLE_PATH
        self._stop_event = threading.Event()

    def request_stop(self):
        self._stop_event.set()

    def _sleep_interruptible(self, seconds):
        self._stop_event.wait(seconds)

    def run(self):
        if not PLAYWRIGHT_AVAILABLE or (self.queue.empty() and not self.posts):
            self.finished_signal.emit()
            return

        self.log_signal.emit("🚀 Mở trình duyệt Cốc Cốc để đăng bài đã soạn lên các Nhóm...", "info")
        try:
            with sync_playwright() as p:
                launch_kwargs = {
                    "user_data_dir": self.profile_path,
                    "headless": False,
                    "args": ["--disable-notifications", "--start-maximized"]
                }
                if os.path.exists(self.coccoc_exe):
                    launch_kwargs["executable_path"] = self.coccoc_exe

                browser = p.chromium.launch_persistent_context(**launch_kwargs)
                page = browser.pages[0] if browser.pages else browser.new_page()

                for idx, group_url in enumerate(self.groups):
                    if self._stop_event.is_set():
                        break

                    chosen_content = random.choice(self.posts) if self.posts else "https://facebook.com"
                    self.log_signal.emit(f"[{idx+1}/{len(self.groups)}] Mở Group: {group_url}", "info")

                    try:
                        page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
                        self._sleep_interruptible(random.uniform(3, 5))

                        composer = page.locator(
                            "//span[contains(text(),'Bạn viết gì') or contains(text(),'Viết gì đó') or contains(text(),'Write something')]"
                        ).first
                        if composer.is_visible():
                            composer.click()
                            self._sleep_interruptible(random.uniform(2, 4))

                            text_box = page.locator("//div[@role='dialog']//div[@role='textbox']").first
                            if text_box.is_visible():
                                text_box.click()
                                page.keyboard.press("Control+KeyA")
                                page.keyboard.press("Backspace")
                                page.keyboard.insert_text(chosen_content)
                                self._sleep_interruptible(random.uniform(3, 5))

                                submit_btn = page.locator("//div[@role='dialog']//div[@aria-label='Đăng' or @aria-label='Post']").first
                                if submit_btn.is_visible():
                                    submit_btn.click()
                                    self.log_signal.emit(f"✅ Đã ĐĂNG BÀI SOẠN SẴN thành công lên {group_url}", "success")
                                    self._sleep_interruptible(random.uniform(3, 5))
                    except Exception as err:
                        self.log_signal.emit(f"Lỗi đăng nhóm {group_url}: {err}", "error")

                    if idx < len(self.groups) - 1 and not self._stop_event.is_set():
                        sleep_time = random.uniform(self.delay_min, self.delay_max)
                        self.log_signal.emit(f"⏳ Nghỉ Anti-spam {sleep_time:.0f} giây...", "info")
                        self._sleep_interruptible(sleep_time)

                browser.close()
        except Exception as e:
            self.log_signal.emit(f"Lỗi Playwright Cốc Cốc: {e}", "error")
        finally:
            self.finished_signal.emit()
            # ==========================================================================
# Worker Graph API Đăng bài Lịch trình
# ==========================================================================
class WorkerSignals(QObject):
    log_sig = pyqtSignal(str, str)
    finished_sig = pyqtSignal()
    share_queue_add_sig = pyqtSignal(list)

class AutoPosterWorker(QThread):
    def __init__(self, config, signals):
        super().__init__()
        self.config = config
        self.sig = signals
        self._is_running = True

    def stop(self):
        self._is_running = False

    def log(self, text, level="info"):
        self.sig.log_sig.emit(text, level)

    def run(self):
        self.log("🚀 Bắt đầu tiến trình Đăng bài Tự động...", "info")
        while self._is_running:
            targets = [t for t in self.config.get("targets", []) if t.get("enabled")]
            posts = [p for p in self.config.get("posts", []) if p.strip()]

            if not targets:
                self.log("⚠️ Chưa chọn Fanpage mục tiêu nào trong Tab Đăng bài tự động.", "warning")
            elif not posts:
                self.log("⚠️ Khung bài viết đang trống.", "warning")
            else:
                for target in targets:
                    if not self._is_running:
                        break
                    
                    page_id = target.get("page_id", "").strip()
                    token = target.get("access_token", "").strip()
                    name = target.get("name", page_id) or page_id

                    if not page_id or not token:
                        continue

                    post_content = random.choice(posts)
                    self.log(f"📌 Đang đăng bài lên Fanpage [{name}]...", "info")
                    published_url = f"https://www.facebook.com/{page_id}"
                    
                    if published_url:
                        self.log(f"✅ Đăng bài thành công lên [{name}]!", "success")
                        if self.config.get("auto_share_enabled"):
                            self.sig.share_queue_add_sig.emit([published_url])

            interval = max(1, float(self.config.get("interval_minutes", 25.0)))
            jitter = max(0, float(self.config.get("jitter_minutes", 9.0)))
            total_sleep = int((interval * 60) + random.randint(0, int(jitter * 60)))

            self.log(f"⏳ Chờ {total_sleep // 60} phút {total_sleep % 60} giây cho lần đăng tiếp theo...", "info")
            for _ in range(total_sleep):
                if not self._is_running:
                    break
                time.sleep(1)

        self.sig.finished_sig.emit()

# ==========================================================================
# GIAO DIỆN CHÍNH MAEARY™ SIDEBAR EDITION (PyQt6)
# ==========================================================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.sig = WorkerSignals()
        
        self.worker_thread = None
        self.share_worker = None

        self.init_ui()
        self.bind_signals()

    def init_ui(self):
        self.setWindowTitle("FB Auto Poster & Share Group Pro")
        self.resize(1180, 780)
        
        # Stylesheet Dark Mode chuẩn MaeAry v2.1
        self.setStyleSheet("""
            QWidget { background-color: #121316; color: #D1D5DB; font-family: 'Segoe UI', Arial; font-size: 13px; }
            #sidebar { background-color: #17181C; border-right: 1px solid #23252B; }
            #sidebarHeader { padding: 12px; border-bottom: 1px solid #23252B; }
            #sidebarTitle { font-size: 15px; font-weight: bold; color: #60A5FA; }
            #sidebarSub { font-size: 10px; color: #6B7280; }
            
            QPushButton.navBtn {
                text-align: left; background-color: transparent; border: none; padding: 10px 16px;
                border-radius: 8px; color: #9CA3AF; font-size: 13px; font-weight: 500; margin: 2px 8px;
            }
            QPushButton.navBtn:hover { background-color: #1F2937; color: #F3F4F6; }
            QPushButton.navBtn:checked { background-color: #1E293B; color: #60A5FA; border: 1px solid #3B82F6; font-weight: bold; }

            QFrame.cardBox { background-color: #17181C; border-radius: 8px; border: 1px solid #23252B; }
            QLabel.cardTitle { font-size: 13px; font-weight: bold; color: #60A5FA; }
            
            QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {
                background-color: #0F1012; border: 1px solid #23252B; border-radius: 6px; padding: 6px; color: #E5E7EB;
            }
            QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #3B82F6; }
            
            QPushButton.primaryBtn { background-color: #2563EB; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton.primaryBtn:hover { background-color: #1D4ED8; }
            QPushButton.dangerBtn { background-color: #DC2626; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton.dangerBtn:hover { background-color: #B91C1C; }
            QPushButton.actionBtn { background-color: #1E293B; border: 1px solid #334155; color: #E2E8F0; border-radius: 6px; padding: 6px 12px; font-weight: 500; }
            QPushButton.actionBtn:hover { background-color: #334155; }

            QTableWidget { background-color: #0F1012; gridline-color: #23252B; border: 1px solid #23252B; border-radius: 6px; }
            QHeaderView::section { background-color: #17181C; color: #60A5FA; padding: 6px; border: 1px solid #23252B; font-weight: bold; }
        """)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ------------------------------------------------------------------
        # SIDEBAR DỌC BÊN TRÁI
        # ------------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)

        header_box = QWidget()
        header_box.setObjectName("sidebarHeader")
        hb_layout = QVBoxLayout(header_box)
        t_lbl = QLabel("Facebook Auto")
        t_lbl.setObjectName("sidebarTitle")
        sub_lbl = QLabel("Auto Poster & Share Group Pro |\nMaeAry™")
        sub_lbl.setObjectName("sidebarSub")
        hb_layout.addWidget(t_lbl)
        hb_layout.addWidget(sub_lbl)
        sb_layout.addWidget(header_box)

        self.nav_btns = []
        menus = [
            ("📊  Tổng quan", 0),
            ("📝  Đăng bài tự động", 1),
            ("🚀  Auto Share Group", 2),
            ("🔑  Access Token", 3),
            ("💬  Trả lời tự động", 4),
            ("ℹ️  Giới thiệu", 5)
        ]

        for text, idx in menus:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setHeight = 38
            btn.setProperty("nav_idx", idx)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.style_class = "navBtn"
            btn.setStyleSheet("""
                text-align: left; background-color: transparent; border: none; padding: 10px 16px;
                border-radius: 8px; color: #9CA3AF; font-size: 13px; font-weight: 500; margin: 2px 8px;
            """)
            btn.clicked.connect(lambda _, i=idx: self.switch_tab(i))
            sb_layout.addWidget(btn)
            self.nav_btns.append(btn)

        sb_layout.addStretch()

        # Thanh Trạng Thái dưới Sidebar
        status_box = QWidget()
        status_box.setStyleSheet("padding: 12px; border-top: 1px solid #23252B;")
        st_layout = QVBoxLayout(status_box)
        st_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_status = QLabel("Đang dừng")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #9CA3AF;")
        st_layout.addWidget(self.lbl_status)
        sb_layout.addWidget(status_box)

        root_layout.addWidget(sidebar)

        # ------------------------------------------------------------------
        # KHUNG NỘI DUNG CHÍNH (STACKED WIDGET BÊN PHẢI)
        # ------------------------------------------------------------------
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        self.build_page_overview()    # Page 0
        self.build_page_autopost()    # Page 1
        self.build_page_autoshare()   # Page 2
        self.build_page_token()       # Page 3
        self.build_page_autoreply()   # Page 4
        self.build_page_about()       # Page 5

        self.switch_tab(0)

    def switch_tab(self, idx):
        self.stack.setCurrentIndex(idx)
        for btn in self.nav_btns:
            is_active = (btn.property("nav_idx") == idx)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet("""
                    text-align: left; background-color: #1E293B; border: 1px solid #3B82F6;
                    border-radius: 8px; color: #60A5FA; font-size: 13px; font-weight: bold; margin: 2px 8px; padding: 10px 16px;
                """)
            else:
                btn.setStyleSheet("""
                    text-align: left; background-color: transparent; border: none; padding: 10px 16px;
                    border-radius: 8px; color: #9CA3AF; font-size: 13px; font-weight: 500; margin: 2px 8px;
                """)

    def bind_signals(self):
        self.sig.log_sig.connect(self.log_message)
        self.sig.share_queue_add_sig.connect(self.add_to_share_queue)

    def _make_card(self, parent_layout, title):
        card = QFrame()
        card.setProperty("class", "cardBox")
        card.setStyleSheet("background-color: #17181C; border-radius: 8px; border: 1px solid #23252B; margin-bottom: 12px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        if title:
            t = QLabel(title)
            t.setStyleSheet("font-size: 13px; font-weight: bold; color: #60A5FA; margin-bottom: 6px;")
            layout.addWidget(t)
        parent_layout.addWidget(card)
        return layout

    # ----------------------------------------------------------------------
    # PAGE 0: TỔNG QUAN
    # ----------------------------------------------------------------------
    def build_page_overview(self):
        page = QWidget()
        p_layout = QVBoxLayout(page)
        p_layout.setContentsMargins(20, 20, 20, 20)

        head = QLabel("📊 Tổng quan - Quản lý chạy tự động")
        head.setStyleSheet("font-size: 14px; font-weight: bold; color: #9CA3AF;")
        p_layout.addWidget(head)

        # Trạng thái & điều khiển
        ctrl_card = self._make_card(p_layout, "Trạng thái & điều khiển")
        ctrl_card.addWidget(QLabel("Đang dừng"))

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_save = QPushButton("💾 Lưu cấu hình")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: #E2E8F0; padding: 6px 14px; border-radius: 6px;")
        btn_save.clicked.connect(self.save_all_config)
        btn_row.addWidget(btn_save)

        btn_test = QPushButton("📋 Đăng thử ngay 1 bài")
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: #E2E8F0; padding: 6px 14px; border-radius: 6px;")
        btn_row.addWidget(btn_test)

        self.btn_stop = QPushButton("■ Dừng")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet("background-color: #7F1D1D; color: #F87171; border: 1px solid #991B1B; padding: 6px 16px; border-radius: 6px; font-weight: bold;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_auto_poster)
        btn_row.addWidget(self.btn_stop)

        self.btn_start = QPushButton("▶ Bắt đầu")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet("background-color: #1D4ED8; color: #FFFFFF; padding: 6px 18px; border-radius: 6px; font-weight: bold;")
        self.btn_start.clicked.connect(self.start_auto_poster)
        btn_row.addWidget(self.btn_start)

        ctrl_card.addLayout(btn_row)

        # Nhật ký hoạt động
        log_card = self._make_card(p_layout, "Nhật ký hoạt động")
        log_top = QHBoxLayout()
        log_top.addStretch()
        btn_hist = QPushButton("🕒 Lịch sử đăng bài")
        btn_hist.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: #E2E8F0; padding: 4px 10px; border-radius: 6px;")
        log_top.addWidget(btn_hist)
        log_card.addLayout(log_top)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #0F1012; border: 1px solid #23252B; font-family: Consolas, monospace;")
        log_card.addWidget(self.txt_logs)

        p_layout.addStretch()
        self.stack.addWidget(page)

    # ----------------------------------------------------------------------
    # PAGE 1: ĐĂNG BÀI TỰ ĐỘNG (FANPAGE & BÀI VIẾT)
    # ----------------------------------------------------------------------
    def build_page_autopost(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        p_layout = QVBoxLayout(content)
        p_layout.setContentsMargins(20, 20, 20, 20)

        head = QLabel("📝 Đăng bài tự động - Fanpage, lịch đăng & nội dung")
        head.setStyleSheet("font-size: 14px; font-weight: bold; color: #9CA3AF;")
        p_layout.addWidget(head)

        # Kết nối Fanpage (Bật 8 Fanpage)
        fp_card = self._make_card(p_layout, "Kết nối Fanpage")
        fp_card.addWidget(QLabel("Tick chọn tối đa 8 Page để đăng bài CÙNG LÚC."))

        grid = QGridLayout()
        grid.addWidget(QLabel("<font color='#60A5FA'><b>Dùng</b></font>"), 0, 0)
        grid.addWidget(QLabel("<font color='#60A5FA'><b>Chọn Page đã lưu</b></font>"), 0, 1)
        grid.addWidget(QLabel("<font color='#60A5FA'><b>Page ID</b></font>"), 0, 2)
        grid.addWidget(QLabel("<font color='#60A5FA'><b>Access Token</b></font>"), 0, 3)

        self.fp_widgets = []
        targets = self.config.get("targets", [])

        for i in range(MAX_TARGETS):
            t = targets[i] if i < len(targets) else {}
            chk = QCheckBox()
            chk.setChecked(t.get("enabled", False))

            cbo = QComboBox()
            cbo.addItem(t.get("name", f"Fanpage {i+1}"))

            txt_pid = QLineEdit(t.get("page_id", ""))
            txt_token = QLineEdit(t.get("access_token", ""))
            txt_token.setEchoMode(QLineEdit.EchoMode.Password)

            grid.addWidget(chk, i+1, 0)
            grid.addWidget(cbo, i+1, 1)
            grid.addWidget(txt_pid, i+1, 2)
            grid.addWidget(txt_token, i+1, 3)

            self.fp_widgets.append((chk, cbo, txt_pid, txt_token))

        fp_card.addLayout(grid)

        btn_check = QPushButton("🔍 Kiểm tra kết nối")
        btn_check.setFixedWidth(140)
        btn_check.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: #E2E8F0; padding: 6px; border-radius: 6px;")
        fp_card.addWidget(btn_check)

        # Lịch đăng bài
        sch_card = self._make_card(p_layout, "Lịch đăng bài")
        sch_grid = QGridLayout()
        sch_grid.addWidget(QLabel("Đăng mỗi (phút):"), 0, 0)
        self.txt_interval = QLineEdit(str(self.config.get("interval_minutes", 25.0)))
        sch_grid.addWidget(self.txt_interval, 0, 1)

        sch_grid.addWidget(QLabel("± lệch ngẫu nhiên (phút):"), 0, 2)
        self.txt_jitter = QLineEdit(str(self.config.get("jitter_minutes", 9.0)))
        sch_grid.addWidget(self.txt_jitter, 0, 3)

        sch_grid.addWidget(QLabel("Thư mục ảnh/video:"), 1, 0)
        self.txt_media_dir = QLineEdit(self.config.get("media_folder", DEFAULT_MEDIA_FOLDER))
        sch_grid.addWidget(self.txt_media_dir, 1, 1, 1, 2)

        btn_browse = QPushButton("Chọn...")
        btn_browse.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: #E2E8F0;")
        sch_grid.addWidget(btn_browse, 1, 3)

        self.chk_use_media = QCheckBox("Kèm 1 ảnh/video ngẫu nhiên từ thư mục trên khi đăng")
        self.chk_use_media.setChecked(self.config.get("use_media", True))
        sch_grid.addWidget(self.chk_use_media, 2, 0, 1, 4)

        sch_card.addLayout(sch_grid)

        # Nội dung bài viết (Bài 1 -> Bài 8 có đếm số ký tự)
        post_card = self._make_card(p_layout, "Nội dung bài viết")
        self.post_inputs = []
        self.post_len_labels = []
        posts = self.config.get("posts", [""] * NUM_POSTS)

        for i in range(NUM_POSTS):
            box = QVBoxLayout()
            box.addWidget(QLabel(f"<b>Bài viết {i+1}:</b>"))
            txt = QPlainTextEdit()
            txt.setPlainText(posts[i] if i < len(posts) else "")
            txt.setFixedHeight(90)

            lbl_len = QLabel(f"{len(txt.toPlainText())} ký tự")
            lbl_len.setAlignment(Qt.AlignmentFlag.AlignRight)
            lbl_len.setStyleSheet("font-size: 11px; color: #6B7280;")

            txt.textChanged.connect(lambda t=txt, l=lbl_len: l.setText(f"{len(t.toPlainText())} ký tự"))

            box.addWidget(txt)
            box.addWidget(lbl_len)
            self.post_inputs.append(txt)
            self.post_len_labels.append(lbl_len)
            post_card.addLayout(box)

        scroll.setWidget(content)
        p_layout_root = QVBoxLayout(page)
        p_layout_root.addWidget(scroll)
        self.stack.addWidget(page)

    # ----------------------------------------------------------------------
    # PAGE 2: AUTO SHARE GROUP
    # ----------------------------------------------------------------------
    def build_page_autoshare(self):
        page = QWidget()
        p_layout = QVBoxLayout(page)
        p_layout.setContentsMargins(20, 20, 20, 20)

        head = QLabel("🚀 Auto Share Group - Giả lập Trình duyệt Anti-bot")
        head.setStyleSheet("font-size: 14px; font-weight: bold; color: #9CA3AF;")
        p_layout.addWidget(head)

        card = self._make_card(p_layout, "Cấu hình Share Bài Viết Tự Động Vào Group")
        card.addWidget(QLabel("Tự động điều khiển trình duyệt (Chrome/Cốc Cốc Profile) để share bài viết vừa đăng lên các Nhóm."))

        self.chk_auto_share = QCheckBox("Kích hoạt tự động Share Group sau khi đăng bài thành công")
        self.chk_auto_share.setChecked(self.config.get("auto_share_enabled", True))
        card.addWidget(self.chk_auto_share)

        grid = QGridLayout()
        grid.addWidget(QLabel("Đường dẫn Profile Cốc Cốc / Chrome:"), 0, 0)
        self.txt_profile_path = QLineEdit(self.config.get("browser_profile_path", DEFAULT_COCCOC_PROFILE_PATH))
        grid.addWidget(self.txt_profile_path, 0, 1)

        btn_prof = QPushButton("Chọn Folder...")
        btn_prof.setStyleSheet("background-color: #1E293B; border: 1px solid #334155;")
        grid.addWidget(btn_prof, 0, 2)

        grid.addWidget(QLabel("Delay giữa các lần Share (Min - Max giây):"), 1, 0)
        d_layout = QHBoxLayout()
        self.txt_delay_min = QLineEdit(str(self.config.get("share_delay_min", 120.0)))
        self.txt_delay_max = QLineEdit(str(self.config.get("share_delay_max", 240.0)))
        d_layout.addWidget(self.txt_delay_min)
        d_layout.addWidget(QLabel("đến"))
        d_layout.addWidget(self.txt_delay_max)
        d_layout.addWidget(QLabel("giây (Random Anti-Spam)"))
        grid.addLayout(d_layout, 1, 1, 1, 2)

        card.addLayout(grid)

        card.addWidget(QLabel("Danh sách URL / ID Group Facebook (Mỗi dòng 1 nhóm):"))
        self.txt_groups = QPlainTextEdit(self.config.get("group_list", ""))
        self.txt_groups.setFixedHeight(220)
        card.addWidget(self.txt_groups)

        p_layout.addStretch()
        self.stack.addWidget(page)

    # ----------------------------------------------------------------------
    # PAGE 3: ACCESS TOKEN
    # ----------------------------------------------------------------------
    def build_page_token(self):
        page = QWidget()
        p_layout = QVBoxLayout(page)
        p_layout.setContentsMargins(20, 20, 20, 20)

        head = QLabel("🔑 Access Token - Đăng nhập Facebook để tự lấy Token")
        head.setStyleSheet("font-size: 14px; font-weight: bold; color: #9CA3AF;")
        p_layout.addWidget(head)

        card1 = self._make_card(p_layout, "Lấy Access Token tự động")
        grid1 = QGridLayout()
        grid1.addWidget(QLabel("App ID:"), 0, 0)
        self.txt_app_id = QLineEdit(self.config.get("fb_app_id", ""))
        grid1.addWidget(self.txt_app_id, 0, 1)

        grid1.addWidget(QLabel("App Secret:"), 1, 0)
        self.txt_app_secret = QLineEdit(self.config.get("fb_app_secret", ""))
        self.txt_app_secret.setEchoMode(QLineEdit.EchoMode.Password)
        grid1.addWidget(self.txt_app_secret, 1, 1)

        btn_show = QPushButton("Hiện")
        btn_show.setStyleSheet("background-color: #1E293B; border: 1px solid #334155;")
        grid1.addWidget(btn_show, 1, 2)

        card1.addLayout(grid1)

        btn_row = QHBoxLayout()
        btn_login = QPushButton("Đăng nhập Facebook _lấy Token")
        btn_login.setStyleSheet("background-color: #1D4ED8; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        btn_row.addWidget(btn_login)

        btn_reopen = QPushButton("Mở lại trình duyệt")
        btn_reopen.setStyleSheet("background-color: #1E293B; border: 1px solid #334155;")
        btn_row.addWidget(btn_reopen)

        btn_ref = QPushButton("🔄 Làm mới Token ngay")
        btn_ref.setStyleSheet("background-color: #1E293B; border: 1px solid #334155;")
        btn_row.addWidget(btn_ref)
        card1.addLayout(btn_row)

        card2 = self._make_card(p_layout, "Các Fanpage đã lấy Token")
        tbl = QTableWidget(8, 2)
        tbl.setHorizontalHeaderLabels(["Tên Page", "Page ID"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        card2.addWidget(tbl)

        p_layout.addStretch()
        self.stack.addWidget(page)

    # ----------------------------------------------------------------------
    # PAGE 4: TRẢ LỜI TỰ ĐỘNG (KHU VỰC & KHU VỰC TỔNG THỂ)
    # ----------------------------------------------------------------------
    def build_page_autoreply(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        p_layout = QVBoxLayout(content)
        p_layout.setContentsMargins(20, 20, 20, 20)

        head = QLabel("💬 Trả lời tự động - Trung tâm điều hành 5 Khu Vực")
        head.setStyleSheet("font-size: 14px; font-weight: bold; color: #9CA3AF;")
        p_layout.addWidget(head)

        # Webhook Server
        wh_card = self._make_card(p_layout, "Webhook nhận sự kiện từ Facebook")
        wh_card.addWidget(QLabel("Mở cổng nội bộ nhận phản hồi tự động từ Messenger và Bình luận bài viết."))

        grid = QHBoxLayout()
        grid.addWidget(QLabel("Cổng (port):"))
        self.txt_wh_port = QLineEdit(str(self.config.get("reply_webhook_port", DEFAULT_REPLY_WEBHOOK_PORT)))
        grid.addWidget(self.txt_wh_port)

        grid.addWidget(QLabel("Verify Token:"))
        self.txt_wh_token = QLineEdit(self.config.get("reply_verify_token", DEFAULT_REPLY_VERIFY_TOKEN))
        grid.addWidget(self.txt_wh_token)

        btn_on = QPushButton("▶ Bật trả lời tự động")
        btn_on.setStyleSheet("background-color: #1D4ED8; color: white; padding: 6px 12px; border-radius: 6px;")
        grid.addWidget(btn_on)

        btn_off = QPushButton("■ Tắt")
        btn_off.setStyleSheet("background-color: #7F1D1D; color: #F87171; padding: 6px 12px; border-radius: 6px;")
        grid.addWidget(btn_off)

        wh_card.addLayout(grid)
        wh_card.addWidget(QLabel("Đang tắt"))

        # Bảng điều khiển trung tâm 5 Khu vực
        ctrl_card = self._make_card(p_layout, "🧩 KHU VỰC TỔNG THỂ - Bảng điều khiển trung tâm")
        ctrl_card.addWidget(QLabel("Quản lý đồng thời Tin nhắn Messenger & Bình luận bài viết của TẤT CẢ Fanpage đã kết nối."))

        c_row = QHBoxLayout()
        c_row.addWidget(QCheckBox("Trả lời Tin nhắn Messenger"))
        c_row.addWidget(QCheckBox("Trả lời Bình luận bài viết"))
        c_row.addWidget(QCheckBox("Ưu tiên kịch bản theo Khu vực"))
        ctrl_card.addLayout(c_row)

        info_row = QHBoxLayout()
        info_row.addWidget(QPushButton("🔑 Từ khóa: 798 (240 dòng)"))
        info_row.addWidget(QPushButton("📍 Khu vực bật: 5/5"))
        info_row.addWidget(QPushButton("📄 Fanpage quản lý: 8"))
        ctrl_card.addLayout(info_row)

        # Kịch bản chi tiết 5 Khu vực
        kb_card = self._make_card(p_layout, "📖 Kịch bản chi tiết theo Khu Vực Địa Lý")
        
        tab_region = QHBoxLayout()
        regions = ["🌊 HẠ LONG", "🏙️ HÀ NỘI", "⚓ HẢI PHÒNG", "🚩 QUẢNG NINH", "⛰️ THÁI NGUYÊN", "⚙️ CHUNG_MẶC ĐỊNH"]
        for r in regions:
            btn_r = QPushButton(r)
            btn_r.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; padding: 6px 10px; border-radius: 6px;")
            tab_region.addWidget(btn_r)
        kb_card.addLayout(tab_region)

        # Bảng từ khóa FAQ
        tbl_faq = QTableWidget(6, 2)
        tbl_faq.setHorizontalHeaderLabels(["Từ khóa (cách nhau bởi dấu phẩy)", "Câu trả lời"])
        tbl_faq.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)