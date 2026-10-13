#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FB Auto Poster & Share Group Pro - ArtTools UI Edition
=====================================================
Tích hợp:
  1) Đăng bài Fanpage tự động qua Facebook Graph API.
  2) Tự động làm mới Access Token & Trả lời tự động Messenger / Bình luận.
  3) Auto Share Group: Điều khiển trình duyệt (Playwright Chrome/Cốc Cốc Profile)
     để giả lập người dùng thật DÁN NGUYÊN NỘI DUNG bài quảng cáo đã soạn sẵn
     (nhiều dòng, emoji, hotline, giá cước, hashtag...) vào các nhóm Facebook.

Chạy: python TOID.py (GUI)  |  python TOID.py --cli (test riêng Playwright)

Cài đặt phụ thuộc:
    pip install PyQt6 requests playwright
    playwright install chromium
"""

import argparse
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

# ==========================================================================
# KHO TU KHOA 5 KHU VUC DIA LY (240 tu khoa / cau thoai mac dinh)
# --------------------------------------------------------------------------
# ⚠️ ĐỔI SỐ HOTLINE DƯỚI ĐÂY THÀNH SỐ THẬT CỦA BẠN (mọi câu trả lời mặc
#    định đều tự động dùng số này).
# ==========================================================================
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
            {"enabled": True, "keywords": "ha khanh, khu ha khanh",
             "reply": "Dạ khu Hà Khánh bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "ha tu, ha phong, mo ha tu",
             "reply": "Dạ nhận khách tại Hà Tu - Hà Phong (Hạ Long) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 200.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "hung thang, ben doan, hung thang ha long",
             "reply": "Dạ bên em có xe chạy Hùng Thắng - Bến Đoan (Hạ Long) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "tuan chau, cang tuan chau, dao tuan chau",
             "reply": "Dạ Tuần Châu là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hạ Long ⇄ Hà Nội / Hải Phòng, lịch chạy: 5h00 - 7h00 - 9h00 - 11h00 - 13h00 - 15h00 - 17h00 - 19h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "cot 3, cot 5, cot 8, khu cot 5",
             "reply": "Dạ có xe qua Cột 3 - Cột 5 - Cột 8 ạ 🚙 Anh/chị đi ghép giá 200.000đ/khách, muốn đi riêng thì bao xe 1.000.000đ (4 chỗ) / 1.300.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "vung dang, yet kieu, cho vung dang",
             "reply": "Dạ khu Vựng Đâng - Yết Kiêu bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "cai dam, khu cai dam",
             "reply": "Dạ nhận khách tại Cái Dăm - Hùng Thắng (Hạ Long) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 200.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "benh vien bai chay, bv bai chay, benh vien tinh quang ninh",
             "reply": "Dạ bên em có xe chạy Bệnh viện Bãi Cháy / BV Đa khoa tỉnh (Hạ Long) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "sun world, cau tinh yeu, vong quay mat troi",
             "reply": "Dạ Sun World - Cầu Tình Yêu là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hạ Long ⇄ Hà Nội / Hải Phòng, lịch chạy: 5h00 - 7h00 - 9h00 - 11h00 - 13h00 - 15h00 - 17h00 - 19h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "cho ha long 1, vincom ha long, vincom bai chay",
             "reply": "Dạ có xe qua Chợ Hạ Long 1 - Vincom Hạ Long ạ 🚙 Anh/chị đi ghép giá 200.000đ/khách, muốn đi riêng thì bao xe 1.000.000đ (4 chỗ) / 1.300.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "ben xe bai chay, ben xe ha long",
             "reply": "Dạ khu Bến xe Bãi Cháy bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "viet hung, dai yen, ha long viet hung",
             "reply": "Dạ nhận khách tại Việt Hưng - Đại Yên (Hạ Long) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 200.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "gia xe ha long, bao nhieu tien ha long, gia ve ha long, ha long bao nhieu tien",
             "reply": "Dạ giá tuyến Hạ Long ⇄ Hà Nội / Hải Phòng bên em: xe ghép 200.000đ/khách - bao xe 4 chỗ 1.000.000đ - bao xe 7 chỗ 1.300.000đ ạ 🚗 Giá đã bao gồm đón trả tận nơi trong nội thành Hạ Long. Anh/chị cho em xin điểm đón cụ thể để em báo chính xác nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "xe ghep ha long, di ghep ha long, ghep xe ha long, con cho ghep ha long",
             "reply": "Dạ xe ghép Hạ Long bên em chạy liên tục trong ngày ạ 🚙 Giá 200.000đ/khách, xe đời mới 4-7 chỗ, tối đa 3-4 khách/chuyến nên rất thoáng. Anh/chị đi ngày nào để em giữ chỗ giúp mình ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "bao xe ha long, thue bao xe ha long, xe rieng ha long, bao ca xe ha long",
             "reply": "Dạ bao xe riêng tuyến Hạ Long ⇄ Hà Nội / Hải Phòng giá 1.000.000đ với xe 4 chỗ và 1.300.000đ với xe 7 chỗ ạ 🚘 Xe đón tận cửa, đi thẳng không đón thêm khách. Anh/chị cần đi giờ nào ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "xe 4 cho ha long, 4 cho ha long, xe con ha long",
             "reply": "Dạ bên em có xe 4 chỗ đời mới chạy Hạ Long ạ, giá bao xe 1.000.000đ, đi ghép 200.000đ/khách. Xe sạch sẽ, điều hòa mát, tài xế thuộc đường Hạ Long ạ 🚗"},
            {"enabled": True, "keywords": "xe 7 cho ha long, 7 cho ha long, xe gia dinh ha long",
             "reply": "Dạ xe 7 chỗ (Xpander/Innova/Fortuner) tuyến Hạ Long giá bao xe 1.300.000đ ạ 🚐 Rộng rãi cho gia đình 5-6 người kèm hành lý. Anh/chị đi mấy người để em bố trí xe phù hợp ạ?"},
            {"enabled": True, "keywords": "xe 16 cho ha long, xe 29 cho ha long, xe du lich ha long",
             "reply": "Dạ bên em có xe 16 chỗ và 29 chỗ phục vụ đoàn đi Hạ Long ạ 🚌 Anh/chị cho em xin số lượng khách, ngày đi và lịch trình để em gửi báo giá chi tiết nhất nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "don tan noi ha long, don tan nha ha long, don tai nha ha long, tra tan noi ha long",
             "reply": "Dạ bên em đón trả TẬN NƠI trong khu vực Hạ Long ạ, không phải ra bến 🥰 Anh/chị nhắn giúp em địa chỉ đón và địa chỉ trả, em sẽ báo giờ xe qua đón chính xác ạ!"},
            {"enabled": True, "keywords": "may gio co xe ha long, lich trinh ha long, gio chay ha long, khung gio ha long",
             "reply": "Dạ lịch xe chạy Hạ Long hàng ngày: 5h00 - 7h00 - 9h00 - 11h00 - 13h00 - 15h00 - 17h00 - 19h00 ạ ⏰ Ngoài ra bên em có xe linh động theo yêu cầu. Anh/chị muốn đi khung giờ nào để em xếp chỗ ạ?"},
            {"enabled": True, "keywords": "dat xe ha long, dat cho ha long, giu cho ha long, book xe ha long",
             "reply": "Dạ anh/chị cho em xin: Họ tên - SĐT - Điểm đón - Điểm trả - Giờ đi, em giữ chỗ tuyến Hạ Long ngay ạ ✅ Hoặc gọi trực tiếp hotline {hotline} cho nhanh mình nhé!"},
            {"enabled": True, "keywords": "con xe khong ha long, con cho khong ha long, con slot ha long, co xe ha long khong",
             "reply": "Dạ hiện tuyến Hạ Long vẫn còn chỗ ạ 🥰 Anh/chị đi mấy người và khoảng mấy giờ để em kiểm tra chuyến gần nhất giúp mình ạ?"},
            {"enabled": True, "keywords": "xe di ha long luon, di ngay ha long, xe chay ngay ha long, gap ha long",
             "reply": "Dạ bên em luôn có xe trực sẵn khu vực Hạ Long ạ 🚗 Anh/chị gọi ngay hotline {hotline}, xe có mặt sau 10-15 phút nếu trong nội thành ạ!"},
            {"enabled": True, "keywords": "san bay ha long, di san bay ha long, don san bay ha long",
             "reply": "Dạ tuyến đi/đón sân bay Nội Bài từ Hạ Long giá 1.100.000đ (xe 4 chỗ) - 1.400.000đ (xe 7 chỗ) ạ ✈️ Tài xế đón tận sảnh, có biển tên, theo dõi giờ hạ cánh miễn phí. Anh/chị cho em xin mã chuyến bay nhé!"},
            {"enabled": True, "keywords": "gui do ha long, gui hang ha long, ship hang ha long, gui giay to ha long",
             "reply": "Dạ bên em nhận gửi đồ - gửi hàng - gửi giấy tờ tuyến Hạ Long ạ 📦 Cước từ 50.000đ/kiện nhỏ, giao nhận tận nơi trong ngày. Anh/chị cho em xin địa chỉ gửi và địa chỉ nhận ạ!"},
            {"enabled": True, "keywords": "xe dem ha long, chuyen dem ha long, xe khuya ha long",
             "reply": "Dạ bên em có xe chạy đêm tuyến Hạ Long ạ 🌙 Chuyến khuya phụ thu 100.000đ - 200.000đ tùy giờ. Anh/chị cần đi lúc mấy giờ để em bố trí tài xế ạ?"},
            {"enabled": True, "keywords": "hop dong ha long, thue xe thang ha long, xe dua don nhan vien ha long",
             "reply": "Dạ bên em nhận hợp đồng đưa đón cố định theo tháng tại Hạ Long ạ 🤝 Có xuất hóa đơn VAT, tài xế cố định, giá ưu đãi theo số chuyến. Anh/chị để lại SĐT em gọi tư vấn ngay ạ!"},
            {"enabled": True, "keywords": "di vien ha long, benh vien ha long, cho benh nhan ha long",
             "reply": "Dạ bên em có xe đưa đón bệnh nhân đi viện tuyến Hạ Long ạ 🏥 Tài xế hỗ trợ dìu đỡ, xe rộng ghế ngả thoải mái. Anh/chị cho em xin giờ hẹn khám để em xếp xe sớm hơn 30 phút ạ!"},
            {"enabled": True, "keywords": "dam cuoi ha long, an hoi ha long, ruoc dau ha long",
             "reply": "Dạ bên em có xe cưới, xe rước dâu khu vực Hạ Long ạ 💒 Xe 4-7-16 chỗ, có trang trí theo yêu cầu. Anh/chị cho em xin ngày và lộ trình để em báo giá trọn gói nhé!"},
            {"enabled": True, "keywords": "tre em ha long, co ghe tre em ha long, di cung tre nho ha long",
             "reply": "Dạ xe tuyến Hạ Long có ghế cho bé và dây an toàn ạ 👶 Bé dưới 5 tuổi đi cùng bố mẹ miễn phí. Anh/chị cho em biết bé mấy tuổi để em chuẩn bị ghế phù hợp ạ!"},
            {"enabled": True, "keywords": "cho thu cung ha long, cho cho meo ha long, mang theo thu cung ha long",
             "reply": "Dạ bên em nhận chở thú cưng tuyến Hạ Long ạ 🐶 Thú cưng cần có lồng/balo riêng, phụ thu 50.000đ - 100.000đ tùy kích cỡ. Anh/chị cho em xin cân nặng của bé nhé!"},
            {"enabled": True, "keywords": "hanh ly ha long, do cong kenh ha long, nhieu do ha long, chuyen do ha long",
             "reply": "Dạ tuyến Hạ Long nhận cả hành lý cồng kềnh ạ 🧳 Nếu nhiều đồ em sẽ bố trí xe 7 chỗ gập ghế hoặc xe tải nhỏ. Anh/chị mô tả giúp em số kiện và kích thước ạ!"},
            {"enabled": True, "keywords": "thanh toan ha long, chuyen khoan ha long, tra tien ha long, coc xe ha long",
             "reply": "Dạ bên em nhận tiền mặt và chuyển khoản đều được ạ 💳 Khách đi ghép thanh toán khi lên xe, bao xe/hợp đồng cọc trước 20%. Anh/chị cần số tài khoản em gửi ngay ạ!"},
            {"enabled": True, "keywords": "hoa don ha long, xuat vat ha long, hoa don do ha long",
             "reply": "Dạ bên em xuất hóa đơn VAT đầy đủ cho chuyến Hạ Long ạ 🧾 Anh/chị gửi em thông tin công ty, mã số thuế, em xuất trong 24h nhé!"},
            {"enabled": True, "keywords": "tai xe ha long, lai xe ha long, bac tai ha long",
             "reply": "Dạ tài xế tuyến Hạ Long bên em đều trên 5 năm kinh nghiệm, thuộc đường, lái êm và hỗ trợ xách đồ ạ 🥰 Anh/chị yên tâm nhé!"},
            {"enabled": True, "keywords": "an toan ha long, co uy tin khong ha long, lua dao ha long",
             "reply": "Dạ nhà xe bên em chạy tuyến Hạ Long nhiều năm, có định vị và hợp đồng rõ ràng ạ 🥰 Anh/chị chỉ thanh toán khi xe đến đón, không cần cọc với khách đi ghép ạ!"},
            {"enabled": True, "keywords": "huy chuyen ha long, doi gio ha long, doi lich ha long",
             "reply": "Dạ anh/chị báo trước 2 tiếng là đổi giờ hoặc hủy chuyến Hạ Long miễn phí ạ 🥰 Em hỗ trợ sắp lại chuyến khác phù hợp giúp mình nhé!"},
            {"enabled": True, "keywords": "dia chi nha xe ha long, van phong ha long, o dau ha long",
             "reply": "Dạ văn phòng bên em có điểm trực tại khu vực Hạ Long ạ 📍 Anh/chị cần đến trực tiếp thì gọi hotline {hotline}, em gửi định vị chi tiết ngay nhé!"},
            {"enabled": True, "keywords": "sdt ha long, hotline ha long, so dien thoai ha long, lien he ha long",
             "reply": "Dạ hotline tuyến Hạ Long: {hotline} (gọi/Zalo 24/7) ạ ☎️ Anh/chị lưu số để tiện đặt xe những lần sau nhé!"},
            {"enabled": True, "keywords": "zalo ha long, ket ban ha long, nhan tin zalo ha long",
             "reply": "Dạ anh/chị kết bạn Zalo số {hotline} giúp em ạ 💬 Bên em gửi lịch xe tuyến Hạ Long và bảng giá chi tiết qua Zalo cho mình nhé!"},
            {"enabled": True, "keywords": "khuyen mai ha long, giam gia ha long, uu dai ha long, khach quen ha long",
             "reply": "Dạ khách đi tuyến Hạ Long từ lần thứ 5 được giảm 10% ạ 🎁 Nhóm từ 3 khách trở lên em cũng có giá ưu đãi riêng. Anh/chị đi mấy người ạ?"},
            {"enabled": True, "keywords": "nha dat ha long, ban dat ha long, mua nha ha long, ban nha ha long",
             "reply": "Dạ bên em đang có nhiều lô đất & nhà bán tại Hạ Long (Cao Xanh, Hà Khánh, Bãi Cháy, Hùng Thắng) ạ 🏠 Anh/chị cho em xin tầm ngân sách và diện tích mong muốn để em lọc đúng căn đẹp gửi mình nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "cho thue nha ha long, thue phong ha long, thue can ho ha long, thue mat bang ha long",
             "reply": "Dạ bên em có sẵn nhà nguyên căn, căn hộ và mặt bằng kinh doanh cho thuê tại Hạ Long (Cao Xanh, Hà Khánh, Bãi Cháy, Hùng Thắng) ạ 🔑 Anh/chị cần thuê loại nào và tầm giá bao nhiêu ạ?"},
            {"enabled": True, "keywords": "dat nen ha long, du an ha long, so do ha long, phap ly ha long",
             "reply": "Dạ các lô bên em giới thiệu tại Hạ Long (Cao Xanh, Hà Khánh, Bãi Cháy, Hùng Thắng) đều sổ đỏ chính chủ, pháp lý rõ ràng, công chứng ngay ạ 📑 Anh/chị muốn xem vị trí lô nào để em gửi sổ và hình ảnh thực tế ạ?"},
            {"enabled": True, "keywords": "ky gui ha long, can ban gap ha long, moi gioi ha long, xem nha ha long",
             "reply": "Dạ bên em nhận ký gửi mua - bán - cho thuê bất động sản khu vực Hạ Long (Cao Xanh, Hà Khánh, Bãi Cháy, Hùng Thắng) ạ 🤝 Anh/chị để lại địa chỉ và giá mong muốn, em cho khách xem nhà trong tuần này luôn ạ!"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Hạ Long ⇄ Hà Nội / Hải Phòng và hỗ trợ nhà đất khu vực Hạ Long ạ. Anh/chị cho em xin điểm đón và thời gian đi để em tư vấn chi tiết nhé! Hotline {hotline}",
    },
    "ha_noi": {
        "label": "🏙️ HÀ NỘI",
        "rules": [
            {"enabled": True, "keywords": "my dinh, ben xe my dinh, khu my dinh",
             "reply": "Dạ bên em có xe chạy Mỹ Đình (Hà Nội) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "giap bat, ben xe giap bat",
             "reply": "Dạ Giáp Bát là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh, lịch chạy: 4h30 - 6h30 - 8h30 - 10h30 - 12h30 - 14h30 - 16h30 - 18h30. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "nuoc ngam, ben xe nuoc ngam",
             "reply": "Dạ có xe qua Nước Ngầm ạ 🚙 Anh/chị đi ghép giá 200.000đ/khách, muốn đi riêng thì bao xe 1.000.000đ (4 chỗ) / 1.300.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "gia lam, ben xe gia lam",
             "reply": "Dạ khu Gia Lâm bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "noi bai, san bay noi bai, ga t1, ga t2",
             "reply": "Dạ nhận khách tại Sân bay Nội Bài (Hà Nội) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 200.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "long bien, cau chuong duong, cau vinh tuy",
             "reply": "Dạ bên em có xe chạy Long Biên - Cầu Chương Dương (Hà Nội) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "cau giay, dich vong, tran duy hung",
             "reply": "Dạ Cầu Giấy là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh, lịch chạy: 4h30 - 6h30 - 8h30 - 10h30 - 12h30 - 14h30 - 16h30 - 18h30. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "hoang mai, linh dam, phap van",
             "reply": "Dạ có xe qua Hoàng Mai - Linh Đàm ạ 🚙 Anh/chị đi ghép giá 200.000đ/khách, muốn đi riêng thì bao xe 1.000.000đ (4 chỗ) / 1.300.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "ha dong, to hieu ha dong, van quan",
             "reply": "Dạ khu Hà Đông bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "times city, ocean park, vinhomes ocean park",
             "reply": "Dạ nhận khách tại Times City - Vinhomes Ocean Park (Hà Nội) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 200.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "bach mai, viet duc, benh vien k, tan trieu",
             "reply": "Dạ bên em có xe chạy Bệnh viện Bạch Mai / Việt Đức / K Tân Triều (Hà Nội) ạ 🚗 Đón trả tận nơi, xe ghép 200.000đ/khách, bao xe 4 chỗ 1.000.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "hoan kiem, pho co, bo ho, ho guom",
             "reply": "Dạ Hoàn Kiếm - Phố cổ là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh, lịch chạy: 4h30 - 6h30 - 8h30 - 10h30 - 12h30 - 14h30 - 16h30 - 18h30. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "thanh xuan, nguyen trai, khuat duy tien",
             "reply": "Dạ có xe qua Thanh Xuân - Nguyễn Trãi ạ 🚙 Anh/chị đi ghép giá 200.000đ/khách, muốn đi riêng thì bao xe 1.000.000đ (4 chỗ) / 1.300.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "dong anh, yen vien, co loa",
             "reply": "Dạ khu Đông Anh - Yên Viên bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "ha noi di quang ninh, ha noi di ha long, tu ha noi ve quang ninh",
             "reply": "Dạ nhận khách tại Cao tốc Hà Nội - Hải Phòng - Quảng Ninh (Hà Nội) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 200.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "gia xe ha noi, bao nhieu tien ha noi, gia ve ha noi, ha noi bao nhieu tien",
             "reply": "Dạ giá tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh bên em: xe ghép 200.000đ/khách - bao xe 4 chỗ 1.000.000đ - bao xe 7 chỗ 1.300.000đ ạ 🚗 Giá đã bao gồm đón trả tận nơi trong nội thành Hà Nội. Anh/chị cho em xin điểm đón cụ thể để em báo chính xác nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "xe ghep ha noi, di ghep ha noi, ghep xe ha noi, con cho ghep ha noi",
             "reply": "Dạ xe ghép Hà Nội bên em chạy liên tục trong ngày ạ 🚙 Giá 200.000đ/khách, xe đời mới 4-7 chỗ, tối đa 3-4 khách/chuyến nên rất thoáng. Anh/chị đi ngày nào để em giữ chỗ giúp mình ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "bao xe ha noi, thue bao xe ha noi, xe rieng ha noi, bao ca xe ha noi",
             "reply": "Dạ bao xe riêng tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh giá 1.000.000đ với xe 4 chỗ và 1.300.000đ với xe 7 chỗ ạ 🚘 Xe đón tận cửa, đi thẳng không đón thêm khách. Anh/chị cần đi giờ nào ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "xe 4 cho ha noi, 4 cho ha noi, xe con ha noi",
             "reply": "Dạ bên em có xe 4 chỗ đời mới chạy Hà Nội ạ, giá bao xe 1.000.000đ, đi ghép 200.000đ/khách. Xe sạch sẽ, điều hòa mát, tài xế thuộc đường Hà Nội ạ 🚗"},
            {"enabled": True, "keywords": "xe 7 cho ha noi, 7 cho ha noi, xe gia dinh ha noi",
             "reply": "Dạ xe 7 chỗ (Xpander/Innova/Fortuner) tuyến Hà Nội giá bao xe 1.300.000đ ạ 🚐 Rộng rãi cho gia đình 5-6 người kèm hành lý. Anh/chị đi mấy người để em bố trí xe phù hợp ạ?"},
            {"enabled": True, "keywords": "xe 16 cho ha noi, xe 29 cho ha noi, xe du lich ha noi",
             "reply": "Dạ bên em có xe 16 chỗ và 29 chỗ phục vụ đoàn đi Hà Nội ạ 🚌 Anh/chị cho em xin số lượng khách, ngày đi và lịch trình để em gửi báo giá chi tiết nhất nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "don tan noi ha noi, don tan nha ha noi, don tai nha ha noi, tra tan noi ha noi",
             "reply": "Dạ bên em đón trả TẬN NƠI trong khu vực Hà Nội ạ, không phải ra bến 🥰 Anh/chị nhắn giúp em địa chỉ đón và địa chỉ trả, em sẽ báo giờ xe qua đón chính xác ạ!"},
            {"enabled": True, "keywords": "may gio co xe ha noi, lich trinh ha noi, gio chay ha noi, khung gio ha noi",
             "reply": "Dạ lịch xe chạy Hà Nội hàng ngày: 4h30 - 6h30 - 8h30 - 10h30 - 12h30 - 14h30 - 16h30 - 18h30 ạ ⏰ Ngoài ra bên em có xe linh động theo yêu cầu. Anh/chị muốn đi khung giờ nào để em xếp chỗ ạ?"},
            {"enabled": True, "keywords": "dat xe ha noi, dat cho ha noi, giu cho ha noi, book xe ha noi",
             "reply": "Dạ anh/chị cho em xin: Họ tên - SĐT - Điểm đón - Điểm trả - Giờ đi, em giữ chỗ tuyến Hà Nội ngay ạ ✅ Hoặc gọi trực tiếp hotline {hotline} cho nhanh mình nhé!"},
            {"enabled": True, "keywords": "con xe khong ha noi, con cho khong ha noi, con slot ha noi, co xe ha noi khong",
             "reply": "Dạ hiện tuyến Hà Nội vẫn còn chỗ ạ 🥰 Anh/chị đi mấy người và khoảng mấy giờ để em kiểm tra chuyến gần nhất giúp mình ạ?"},
            {"enabled": True, "keywords": "xe di ha noi luon, di ngay ha noi, xe chay ngay ha noi, gap ha noi",
             "reply": "Dạ bên em luôn có xe trực sẵn khu vực Hà Nội ạ 🚗 Anh/chị gọi ngay hotline {hotline}, xe có mặt sau 10-15 phút nếu trong nội thành ạ!"},
            {"enabled": True, "keywords": "san bay ha noi, di san bay ha noi, don san bay ha noi",
             "reply": "Dạ tuyến đi/đón sân bay Nội Bài từ Hà Nội giá 1.100.000đ (xe 4 chỗ) - 1.400.000đ (xe 7 chỗ) ạ ✈️ Tài xế đón tận sảnh, có biển tên, theo dõi giờ hạ cánh miễn phí. Anh/chị cho em xin mã chuyến bay nhé!"},
            {"enabled": True, "keywords": "gui do ha noi, gui hang ha noi, ship hang ha noi, gui giay to ha noi",
             "reply": "Dạ bên em nhận gửi đồ - gửi hàng - gửi giấy tờ tuyến Hà Nội ạ 📦 Cước từ 50.000đ/kiện nhỏ, giao nhận tận nơi trong ngày. Anh/chị cho em xin địa chỉ gửi và địa chỉ nhận ạ!"},
            {"enabled": True, "keywords": "xe dem ha noi, chuyen dem ha noi, xe khuya ha noi",
             "reply": "Dạ bên em có xe chạy đêm tuyến Hà Nội ạ 🌙 Chuyến khuya phụ thu 100.000đ - 200.000đ tùy giờ. Anh/chị cần đi lúc mấy giờ để em bố trí tài xế ạ?"},
            {"enabled": True, "keywords": "hop dong ha noi, thue xe thang ha noi, xe dua don nhan vien ha noi",
             "reply": "Dạ bên em nhận hợp đồng đưa đón cố định theo tháng tại Hà Nội ạ 🤝 Có xuất hóa đơn VAT, tài xế cố định, giá ưu đãi theo số chuyến. Anh/chị để lại SĐT em gọi tư vấn ngay ạ!"},
            {"enabled": True, "keywords": "di vien ha noi, benh vien ha noi, cho benh nhan ha noi",
             "reply": "Dạ bên em có xe đưa đón bệnh nhân đi viện tuyến Hà Nội ạ 🏥 Tài xế hỗ trợ dìu đỡ, xe rộng ghế ngả thoải mái. Anh/chị cho em xin giờ hẹn khám để em xếp xe sớm hơn 30 phút ạ!"},
            {"enabled": True, "keywords": "dam cuoi ha noi, an hoi ha noi, ruoc dau ha noi",
             "reply": "Dạ bên em có xe cưới, xe rước dâu khu vực Hà Nội ạ 💒 Xe 4-7-16 chỗ, có trang trí theo yêu cầu. Anh/chị cho em xin ngày và lộ trình để em báo giá trọn gói nhé!"},
            {"enabled": True, "keywords": "tre em ha noi, co ghe tre em ha noi, di cung tre nho ha noi",
             "reply": "Dạ xe tuyến Hà Nội có ghế cho bé và dây an toàn ạ 👶 Bé dưới 5 tuổi đi cùng bố mẹ miễn phí. Anh/chị cho em biết bé mấy tuổi để em chuẩn bị ghế phù hợp ạ!"},
            {"enabled": True, "keywords": "cho thu cung ha noi, cho cho meo ha noi, mang theo thu cung ha noi",
             "reply": "Dạ bên em nhận chở thú cưng tuyến Hà Nội ạ 🐶 Thú cưng cần có lồng/balo riêng, phụ thu 50.000đ - 100.000đ tùy kích cỡ. Anh/chị cho em xin cân nặng của bé nhé!"},
            {"enabled": True, "keywords": "hanh ly ha noi, do cong kenh ha noi, nhieu do ha noi, chuyen do ha noi",
             "reply": "Dạ tuyến Hà Nội nhận cả hành lý cồng kềnh ạ 🧳 Nếu nhiều đồ em sẽ bố trí xe 7 chỗ gập ghế hoặc xe tải nhỏ. Anh/chị mô tả giúp em số kiện và kích thước ạ!"},
            {"enabled": True, "keywords": "thanh toan ha noi, chuyen khoan ha noi, tra tien ha noi, coc xe ha noi",
             "reply": "Dạ bên em nhận tiền mặt và chuyển khoản đều được ạ 💳 Khách đi ghép thanh toán khi lên xe, bao xe/hợp đồng cọc trước 20%. Anh/chị cần số tài khoản em gửi ngay ạ!"},
            {"enabled": True, "keywords": "hoa don ha noi, xuat vat ha noi, hoa don do ha noi",
             "reply": "Dạ bên em xuất hóa đơn VAT đầy đủ cho chuyến Hà Nội ạ 🧾 Anh/chị gửi em thông tin công ty, mã số thuế, em xuất trong 24h nhé!"},
            {"enabled": True, "keywords": "tai xe ha noi, lai xe ha noi, bac tai ha noi",
             "reply": "Dạ tài xế tuyến Hà Nội bên em đều trên 5 năm kinh nghiệm, thuộc đường, lái êm và hỗ trợ xách đồ ạ 🥰 Anh/chị yên tâm nhé!"},
            {"enabled": True, "keywords": "an toan ha noi, co uy tin khong ha noi, lua dao ha noi",
             "reply": "Dạ nhà xe bên em chạy tuyến Hà Nội nhiều năm, có định vị và hợp đồng rõ ràng ạ 🥰 Anh/chị chỉ thanh toán khi xe đến đón, không cần cọc với khách đi ghép ạ!"},
            {"enabled": True, "keywords": "huy chuyen ha noi, doi gio ha noi, doi lich ha noi",
             "reply": "Dạ anh/chị báo trước 2 tiếng là đổi giờ hoặc hủy chuyến Hà Nội miễn phí ạ 🥰 Em hỗ trợ sắp lại chuyến khác phù hợp giúp mình nhé!"},
            {"enabled": True, "keywords": "dia chi nha xe ha noi, van phong ha noi, o dau ha noi",
             "reply": "Dạ văn phòng bên em có điểm trực tại khu vực Hà Nội ạ 📍 Anh/chị cần đến trực tiếp thì gọi hotline {hotline}, em gửi định vị chi tiết ngay nhé!"},
            {"enabled": True, "keywords": "sdt ha noi, hotline ha noi, so dien thoai ha noi, lien he ha noi",
             "reply": "Dạ hotline tuyến Hà Nội: {hotline} (gọi/Zalo 24/7) ạ ☎️ Anh/chị lưu số để tiện đặt xe những lần sau nhé!"},
            {"enabled": True, "keywords": "zalo ha noi, ket ban ha noi, nhan tin zalo ha noi",
             "reply": "Dạ anh/chị kết bạn Zalo số {hotline} giúp em ạ 💬 Bên em gửi lịch xe tuyến Hà Nội và bảng giá chi tiết qua Zalo cho mình nhé!"},
            {"enabled": True, "keywords": "khuyen mai ha noi, giam gia ha noi, uu dai ha noi, khach quen ha noi",
             "reply": "Dạ khách đi tuyến Hà Nội từ lần thứ 5 được giảm 10% ạ 🎁 Nhóm từ 3 khách trở lên em cũng có giá ưu đãi riêng. Anh/chị đi mấy người ạ?"},
            {"enabled": True, "keywords": "nha dat ha noi, ban dat ha noi, mua nha ha noi, ban nha ha noi",
             "reply": "Dạ bên em đang có nhiều lô đất & nhà bán tại Hà Nội (Hoàng Mai, Gia Lâm, Đông Anh, Hà Đông) ạ 🏠 Anh/chị cho em xin tầm ngân sách và diện tích mong muốn để em lọc đúng căn đẹp gửi mình nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "cho thue nha ha noi, thue phong ha noi, thue can ho ha noi, thue mat bang ha noi",
             "reply": "Dạ bên em có sẵn nhà nguyên căn, căn hộ và mặt bằng kinh doanh cho thuê tại Hà Nội (Hoàng Mai, Gia Lâm, Đông Anh, Hà Đông) ạ 🔑 Anh/chị cần thuê loại nào và tầm giá bao nhiêu ạ?"},
            {"enabled": True, "keywords": "dat nen ha noi, du an ha noi, so do ha noi, phap ly ha noi",
             "reply": "Dạ các lô bên em giới thiệu tại Hà Nội (Hoàng Mai, Gia Lâm, Đông Anh, Hà Đông) đều sổ đỏ chính chủ, pháp lý rõ ràng, công chứng ngay ạ 📑 Anh/chị muốn xem vị trí lô nào để em gửi sổ và hình ảnh thực tế ạ?"},
            {"enabled": True, "keywords": "ky gui ha noi, can ban gap ha noi, moi gioi ha noi, xem nha ha noi",
             "reply": "Dạ bên em nhận ký gửi mua - bán - cho thuê bất động sản khu vực Hà Nội (Hoàng Mai, Gia Lâm, Đông Anh, Hà Đông) ạ 🤝 Anh/chị để lại địa chỉ và giá mong muốn, em cho khách xem nhà trong tuần này luôn ạ!"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Hà Nội ⇄ Hạ Long / Quảng Ninh và hỗ trợ nhà đất khu vực Hà Nội ạ. Anh/chị cho em xin điểm đón và thời gian đi để em tư vấn chi tiết nhé! Hotline {hotline}",
    },
    "hai_phong": {
        "label": "⚓ HẢI PHÒNG",
        "rules": [
            {"enabled": True, "keywords": "cau rao, cau rao 1, cau rao 2",
             "reply": "Dạ bên em có xe chạy Cầu Rào (Hải Phòng) ạ 🚗 Đón trả tận nơi, xe ghép 150.000đ/khách, bao xe 4 chỗ 700.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "do son, bai bien do son, khu 1 do son",
             "reply": "Dạ Đồ Sơn là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hải Phòng ⇄ Hạ Long / Quảng Ninh, lịch chạy: 5h30 - 7h30 - 9h30 - 11h30 - 13h30 - 15h30 - 17h30 - 19h30. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "lach tray, san van dong lach tray",
             "reply": "Dạ có xe qua Lạch Tray ạ 🚙 Anh/chị đi ghép giá 150.000đ/khách, muốn đi riêng thì bao xe 700.000đ (4 chỗ) / 900.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "cat bi, san bay cat bi, nga 5 san bay",
             "reply": "Dạ khu Ngã 5 - Sân bay Cát Bi bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "thuy nguyen, nui deo, ben binh",
             "reply": "Dạ nhận khách tại Thủy Nguyên (Hải Phòng) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 150.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "an duong, an lao, quan toan",
             "reply": "Dạ bên em có xe chạy An Dương - An Lão (Hải Phòng) ạ 🚗 Đón trả tận nơi, xe ghép 150.000đ/khách, bao xe 4 chỗ 700.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "kien an, cau niem, tran nhan tong",
             "reply": "Dạ Kiến An là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hải Phòng ⇄ Hạ Long / Quảng Ninh, lịch chạy: 5h30 - 7h30 - 9h30 - 11h30 - 13h30 - 15h30 - 17h30 - 19h30. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "vinh bao, tien lang, dong quan",
             "reply": "Dạ có xe qua Vĩnh Bảo - Tiên Lãng ạ 🚙 Anh/chị đi ghép giá 150.000đ/khách, muốn đi riêng thì bao xe 700.000đ (4 chỗ) / 900.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "cat ba, ben got, pha got",
             "reply": "Dạ khu Cát Bà - Bến Gót bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "viet tiep, benh vien viet tiep, bv huu nghi viet tiep",
             "reply": "Dạ nhận khách tại Bệnh viện Việt Tiệp (Hải Phòng) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 150.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "cao toc 5b, 5b, cao toc ha noi hai phong",
             "reply": "Dạ bên em có xe chạy Cao tốc 5B (Hải Phòng) ạ 🚗 Đón trả tận nơi, xe ghép 150.000đ/khách, bao xe 4 chỗ 700.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "ben xe niem nghia, ben xe cau rao, ben xe thuong ly",
             "reply": "Dạ Bến xe Niệm Nghĩa - Cầu Rào là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Hải Phòng ⇄ Hạ Long / Quảng Ninh, lịch chạy: 5h30 - 7h30 - 9h30 - 11h30 - 13h30 - 15h30 - 17h30 - 19h30. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "imperia hai phong, le hong phong hai phong, vincom hai phong",
             "reply": "Dạ có xe qua Vincom Imperia - Lê Hồng Phong ạ 🚙 Anh/chị đi ghép giá 150.000đ/khách, muốn đi riêng thì bao xe 700.000đ (4 chỗ) / 900.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "hong bang, ngo quyen, so dau",
             "reply": "Dạ khu Hồng Bàng - Ngô Quyền bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "vsip hai phong, nomura, kcn trang due",
             "reply": "Dạ nhận khách tại Khu công nghiệp VSIP - Nomura (Hải Phòng) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 150.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "gia xe hai phong, bao nhieu tien hai phong, gia ve hai phong, hai phong bao nhieu tien",
             "reply": "Dạ giá tuyến Hải Phòng ⇄ Hạ Long / Quảng Ninh bên em: xe ghép 150.000đ/khách - bao xe 4 chỗ 700.000đ - bao xe 7 chỗ 900.000đ ạ 🚗 Giá đã bao gồm đón trả tận nơi trong nội thành Hải Phòng. Anh/chị cho em xin điểm đón cụ thể để em báo chính xác nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "xe ghep hai phong, di ghep hai phong, ghep xe hai phong, con cho ghep hai phong",
             "reply": "Dạ xe ghép Hải Phòng bên em chạy liên tục trong ngày ạ 🚙 Giá 150.000đ/khách, xe đời mới 4-7 chỗ, tối đa 3-4 khách/chuyến nên rất thoáng. Anh/chị đi ngày nào để em giữ chỗ giúp mình ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "bao xe hai phong, thue bao xe hai phong, xe rieng hai phong, bao ca xe hai phong",
             "reply": "Dạ bao xe riêng tuyến Hải Phòng ⇄ Hạ Long / Quảng Ninh giá 700.000đ với xe 4 chỗ và 900.000đ với xe 7 chỗ ạ 🚘 Xe đón tận cửa, đi thẳng không đón thêm khách. Anh/chị cần đi giờ nào ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "xe 4 cho hai phong, 4 cho hai phong, xe con hai phong",
             "reply": "Dạ bên em có xe 4 chỗ đời mới chạy Hải Phòng ạ, giá bao xe 700.000đ, đi ghép 150.000đ/khách. Xe sạch sẽ, điều hòa mát, tài xế thuộc đường Hải Phòng ạ 🚗"},
            {"enabled": True, "keywords": "xe 7 cho hai phong, 7 cho hai phong, xe gia dinh hai phong",
             "reply": "Dạ xe 7 chỗ (Xpander/Innova/Fortuner) tuyến Hải Phòng giá bao xe 900.000đ ạ 🚐 Rộng rãi cho gia đình 5-6 người kèm hành lý. Anh/chị đi mấy người để em bố trí xe phù hợp ạ?"},
            {"enabled": True, "keywords": "xe 16 cho hai phong, xe 29 cho hai phong, xe du lich hai phong",
             "reply": "Dạ bên em có xe 16 chỗ và 29 chỗ phục vụ đoàn đi Hải Phòng ạ 🚌 Anh/chị cho em xin số lượng khách, ngày đi và lịch trình để em gửi báo giá chi tiết nhất nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "don tan noi hai phong, don tan nha hai phong, don tai nha hai phong, tra tan noi hai phong",
             "reply": "Dạ bên em đón trả TẬN NƠI trong khu vực Hải Phòng ạ, không phải ra bến 🥰 Anh/chị nhắn giúp em địa chỉ đón và địa chỉ trả, em sẽ báo giờ xe qua đón chính xác ạ!"},
            {"enabled": True, "keywords": "may gio co xe hai phong, lich trinh hai phong, gio chay hai phong, khung gio hai phong",
             "reply": "Dạ lịch xe chạy Hải Phòng hàng ngày: 5h30 - 7h30 - 9h30 - 11h30 - 13h30 - 15h30 - 17h30 - 19h30 ạ ⏰ Ngoài ra bên em có xe linh động theo yêu cầu. Anh/chị muốn đi khung giờ nào để em xếp chỗ ạ?"},
            {"enabled": True, "keywords": "dat xe hai phong, dat cho hai phong, giu cho hai phong, book xe hai phong",
             "reply": "Dạ anh/chị cho em xin: Họ tên - SĐT - Điểm đón - Điểm trả - Giờ đi, em giữ chỗ tuyến Hải Phòng ngay ạ ✅ Hoặc gọi trực tiếp hotline {hotline} cho nhanh mình nhé!"},
            {"enabled": True, "keywords": "con xe khong hai phong, con cho khong hai phong, con slot hai phong, co xe hai phong khong",
             "reply": "Dạ hiện tuyến Hải Phòng vẫn còn chỗ ạ 🥰 Anh/chị đi mấy người và khoảng mấy giờ để em kiểm tra chuyến gần nhất giúp mình ạ?"},
            {"enabled": True, "keywords": "xe di hai phong luon, di ngay hai phong, xe chay ngay hai phong, gap hai phong",
             "reply": "Dạ bên em luôn có xe trực sẵn khu vực Hải Phòng ạ 🚗 Anh/chị gọi ngay hotline {hotline}, xe có mặt sau 10-15 phút nếu trong nội thành ạ!"},
            {"enabled": True, "keywords": "san bay hai phong, di san bay hai phong, don san bay hai phong",
             "reply": "Dạ tuyến đi/đón sân bay Cát Bi từ Hải Phòng giá 750.000đ (xe 4 chỗ) - 950.000đ (xe 7 chỗ) ạ ✈️ Tài xế đón tận sảnh, có biển tên, theo dõi giờ hạ cánh miễn phí. Anh/chị cho em xin mã chuyến bay nhé!"},
            {"enabled": True, "keywords": "gui do hai phong, gui hang hai phong, ship hang hai phong, gui giay to hai phong",
             "reply": "Dạ bên em nhận gửi đồ - gửi hàng - gửi giấy tờ tuyến Hải Phòng ạ 📦 Cước từ 50.000đ/kiện nhỏ, giao nhận tận nơi trong ngày. Anh/chị cho em xin địa chỉ gửi và địa chỉ nhận ạ!"},
            {"enabled": True, "keywords": "xe dem hai phong, chuyen dem hai phong, xe khuya hai phong",
             "reply": "Dạ bên em có xe chạy đêm tuyến Hải Phòng ạ 🌙 Chuyến khuya phụ thu 100.000đ - 200.000đ tùy giờ. Anh/chị cần đi lúc mấy giờ để em bố trí tài xế ạ?"},
            {"enabled": True, "keywords": "hop dong hai phong, thue xe thang hai phong, xe dua don nhan vien hai phong",
             "reply": "Dạ bên em nhận hợp đồng đưa đón cố định theo tháng tại Hải Phòng ạ 🤝 Có xuất hóa đơn VAT, tài xế cố định, giá ưu đãi theo số chuyến. Anh/chị để lại SĐT em gọi tư vấn ngay ạ!"},
            {"enabled": True, "keywords": "di vien hai phong, benh vien hai phong, cho benh nhan hai phong",
             "reply": "Dạ bên em có xe đưa đón bệnh nhân đi viện tuyến Hải Phòng ạ 🏥 Tài xế hỗ trợ dìu đỡ, xe rộng ghế ngả thoải mái. Anh/chị cho em xin giờ hẹn khám để em xếp xe sớm hơn 30 phút ạ!"},
            {"enabled": True, "keywords": "dam cuoi hai phong, an hoi hai phong, ruoc dau hai phong",
             "reply": "Dạ bên em có xe cưới, xe rước dâu khu vực Hải Phòng ạ 💒 Xe 4-7-16 chỗ, có trang trí theo yêu cầu. Anh/chị cho em xin ngày và lộ trình để em báo giá trọn gói nhé!"},
            {"enabled": True, "keywords": "tre em hai phong, co ghe tre em hai phong, di cung tre nho hai phong",
             "reply": "Dạ xe tuyến Hải Phòng có ghế cho bé và dây an toàn ạ 👶 Bé dưới 5 tuổi đi cùng bố mẹ miễn phí. Anh/chị cho em biết bé mấy tuổi để em chuẩn bị ghế phù hợp ạ!"},
            {"enabled": True, "keywords": "cho thu cung hai phong, cho cho meo hai phong, mang theo thu cung hai phong",
             "reply": "Dạ bên em nhận chở thú cưng tuyến Hải Phòng ạ 🐶 Thú cưng cần có lồng/balo riêng, phụ thu 50.000đ - 100.000đ tùy kích cỡ. Anh/chị cho em xin cân nặng của bé nhé!"},
            {"enabled": True, "keywords": "hanh ly hai phong, do cong kenh hai phong, nhieu do hai phong, chuyen do hai phong",
             "reply": "Dạ tuyến Hải Phòng nhận cả hành lý cồng kềnh ạ 🧳 Nếu nhiều đồ em sẽ bố trí xe 7 chỗ gập ghế hoặc xe tải nhỏ. Anh/chị mô tả giúp em số kiện và kích thước ạ!"},
            {"enabled": True, "keywords": "thanh toan hai phong, chuyen khoan hai phong, tra tien hai phong, coc xe hai phong",
             "reply": "Dạ bên em nhận tiền mặt và chuyển khoản đều được ạ 💳 Khách đi ghép thanh toán khi lên xe, bao xe/hợp đồng cọc trước 20%. Anh/chị cần số tài khoản em gửi ngay ạ!"},
            {"enabled": True, "keywords": "hoa don hai phong, xuat vat hai phong, hoa don do hai phong",
             "reply": "Dạ bên em xuất hóa đơn VAT đầy đủ cho chuyến Hải Phòng ạ 🧾 Anh/chị gửi em thông tin công ty, mã số thuế, em xuất trong 24h nhé!"},
            {"enabled": True, "keywords": "tai xe hai phong, lai xe hai phong, bac tai hai phong",
             "reply": "Dạ tài xế tuyến Hải Phòng bên em đều trên 5 năm kinh nghiệm, thuộc đường, lái êm và hỗ trợ xách đồ ạ 🥰 Anh/chị yên tâm nhé!"},
            {"enabled": True, "keywords": "an toan hai phong, co uy tin khong hai phong, lua dao hai phong",
             "reply": "Dạ nhà xe bên em chạy tuyến Hải Phòng nhiều năm, có định vị và hợp đồng rõ ràng ạ 🥰 Anh/chị chỉ thanh toán khi xe đến đón, không cần cọc với khách đi ghép ạ!"},
            {"enabled": True, "keywords": "huy chuyen hai phong, doi gio hai phong, doi lich hai phong",
             "reply": "Dạ anh/chị báo trước 2 tiếng là đổi giờ hoặc hủy chuyến Hải Phòng miễn phí ạ 🥰 Em hỗ trợ sắp lại chuyến khác phù hợp giúp mình nhé!"},
            {"enabled": True, "keywords": "dia chi nha xe hai phong, van phong hai phong, o dau hai phong",
             "reply": "Dạ văn phòng bên em có điểm trực tại khu vực Hải Phòng ạ 📍 Anh/chị cần đến trực tiếp thì gọi hotline {hotline}, em gửi định vị chi tiết ngay nhé!"},
            {"enabled": True, "keywords": "sdt hai phong, hotline hai phong, so dien thoai hai phong, lien he hai phong",
             "reply": "Dạ hotline tuyến Hải Phòng: {hotline} (gọi/Zalo 24/7) ạ ☎️ Anh/chị lưu số để tiện đặt xe những lần sau nhé!"},
            {"enabled": True, "keywords": "zalo hai phong, ket ban hai phong, nhan tin zalo hai phong",
             "reply": "Dạ anh/chị kết bạn Zalo số {hotline} giúp em ạ 💬 Bên em gửi lịch xe tuyến Hải Phòng và bảng giá chi tiết qua Zalo cho mình nhé!"},
            {"enabled": True, "keywords": "khuyen mai hai phong, giam gia hai phong, uu dai hai phong, khach quen hai phong",
             "reply": "Dạ khách đi tuyến Hải Phòng từ lần thứ 5 được giảm 10% ạ 🎁 Nhóm từ 3 khách trở lên em cũng có giá ưu đãi riêng. Anh/chị đi mấy người ạ?"},
            {"enabled": True, "keywords": "nha dat hai phong, ban dat hai phong, mua nha hai phong, ban nha hai phong",
             "reply": "Dạ bên em đang có nhiều lô đất & nhà bán tại Hải Phòng (Thủy Nguyên, Dương Kinh, An Dương) ạ 🏠 Anh/chị cho em xin tầm ngân sách và diện tích mong muốn để em lọc đúng căn đẹp gửi mình nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "cho thue nha hai phong, thue phong hai phong, thue can ho hai phong, thue mat bang hai phong",
             "reply": "Dạ bên em có sẵn nhà nguyên căn, căn hộ và mặt bằng kinh doanh cho thuê tại Hải Phòng (Thủy Nguyên, Dương Kinh, An Dương) ạ 🔑 Anh/chị cần thuê loại nào và tầm giá bao nhiêu ạ?"},
            {"enabled": True, "keywords": "dat nen hai phong, du an hai phong, so do hai phong, phap ly hai phong",
             "reply": "Dạ các lô bên em giới thiệu tại Hải Phòng (Thủy Nguyên, Dương Kinh, An Dương) đều sổ đỏ chính chủ, pháp lý rõ ràng, công chứng ngay ạ 📑 Anh/chị muốn xem vị trí lô nào để em gửi sổ và hình ảnh thực tế ạ?"},
            {"enabled": True, "keywords": "ky gui hai phong, can ban gap hai phong, moi gioi hai phong, xem nha hai phong",
             "reply": "Dạ bên em nhận ký gửi mua - bán - cho thuê bất động sản khu vực Hải Phòng (Thủy Nguyên, Dương Kinh, An Dương) ạ 🤝 Anh/chị để lại địa chỉ và giá mong muốn, em cho khách xem nhà trong tuần này luôn ạ!"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Hải Phòng ⇄ Hạ Long / Quảng Ninh và hỗ trợ nhà đất khu vực Hải Phòng ạ. Anh/chị cho em xin điểm đón và thời gian đi để em tư vấn chi tiết nhé! Hotline {hotline}",
    },
    "quang_ninh": {
        "label": "🚩 QUẢNG NINH",
        "rules": [
            {"enabled": True, "keywords": "uong bi, yen thanh uong bi, trung vuong uong bi",
             "reply": "Dạ bên em có xe chạy Uông Bí (Quảng Ninh) ạ 🚗 Đón trả tận nơi, xe ghép 180.000đ - 350.000đ/khách tùy tuyến, bao xe 4 chỗ 900.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "cam pha, cam thuy, cua ong",
             "reply": "Dạ Cẩm Phả là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Nội tỉnh Quảng Ninh & Quảng Ninh ⇄ Hà Nội / Hải Phòng, lịch chạy: 5h00 - 7h00 - 9h00 - 12h00 - 14h00 - 16h00 - 18h00 - 20h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "mong cai, cua khau mong cai, tra co",
             "reply": "Dạ có xe qua Móng Cái ạ 🚙 Anh/chị đi ghép giá 180.000đ - 350.000đ/khách tùy tuyến, muốn đi riêng thì bao xe 900.000đ (4 chỗ) / 1.200.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "dong trieu, mao khe, dong trieu quang ninh",
             "reply": "Dạ khu Đông Triều bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "quang yen, minh thanh, ha an",
             "reply": "Dạ nhận khách tại Quảng Yên (Quảng Ninh) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 180.000đ - 350.000đ/khách tùy tuyến, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "van don, san bay van don, cai rong",
             "reply": "Dạ bên em có xe chạy Vân Đồn - Sân bay Vân Đồn (Quảng Ninh) ạ 🚗 Đón trả tận nơi, xe ghép 180.000đ - 350.000đ/khách tùy tuyến, bao xe 4 chỗ 900.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "tien yen, ba che, dam ha",
             "reply": "Dạ Tiên Yên - Ba Chẽ là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Nội tỉnh Quảng Ninh & Quảng Ninh ⇄ Hà Nội / Hải Phòng, lịch chạy: 5h00 - 7h00 - 9h00 - 12h00 - 14h00 - 16h00 - 18h00 - 20h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "hai ha, dam ha, quang ha",
             "reply": "Dạ có xe qua Hải Hà - Đầm Hà ạ 🚙 Anh/chị đi ghép giá 180.000đ - 350.000đ/khách tùy tuyến, muốn đi riêng thì bao xe 900.000đ (4 chỗ) / 1.200.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "binh lieu, cua khau hoanh mo",
             "reply": "Dạ khu Bình Liêu bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "ba vang, yen tu, chua ba vang, chua dong",
             "reply": "Dạ nhận khách tại Chùa Ba Vàng - Yên Tử (Quảng Ninh) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 180.000đ - 350.000đ/khách tùy tuyến, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "viet nam thuy dien, bv uong bi, benh vien cam pha",
             "reply": "Dạ bên em có xe chạy Bệnh viện Bãi Cháy - BV Việt Nam Thụy Điển (Quảng Ninh) ạ 🚗 Đón trả tận nơi, xe ghép 180.000đ - 350.000đ/khách tùy tuyến, bao xe 4 chỗ 900.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "co to, cang cai rong di co to",
             "reply": "Dạ Cô Tô là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Nội tỉnh Quảng Ninh & Quảng Ninh ⇄ Hà Nội / Hải Phòng, lịch chạy: 5h00 - 7h00 - 9h00 - 12h00 - 14h00 - 16h00 - 18h00 - 20h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "dragon bay, ha long xanh, vinhomes quang ninh",
             "reply": "Dạ có xe qua Vinhomes Dragon Bay - Hạ Long Xanh ạ 🚙 Anh/chị đi ghép giá 180.000đ - 350.000đ/khách tùy tuyến, muốn đi riêng thì bao xe 900.000đ (4 chỗ) / 1.200.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "ben xe cam pha, ben xe mong cai, ben xe uong bi",
             "reply": "Dạ khu Bến xe Cẩm Phả - Bến xe Móng Cái bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "xe tien chuyen qn, xe ghep quang ninh, xe tien chuyen quang ninh",
             "reply": "Dạ nhận khách tại Xe tiện chuyến Quảng Ninh (Quảng Ninh) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 180.000đ - 350.000đ/khách tùy tuyến, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "gia xe quang ninh, bao nhieu tien quang ninh, gia ve quang ninh, quang ninh bao nhieu tien",
             "reply": "Dạ giá tuyến Nội tỉnh Quảng Ninh & Quảng Ninh ⇄ Hà Nội / Hải Phòng bên em: xe ghép 180.000đ - 350.000đ/khách tùy tuyến - bao xe 4 chỗ 900.000đ - bao xe 7 chỗ 1.200.000đ ạ 🚗 Giá đã bao gồm đón trả tận nơi trong nội thành Quảng Ninh. Anh/chị cho em xin điểm đón cụ thể để em báo chính xác nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "xe ghep quang ninh, di ghep quang ninh, ghep xe quang ninh, con cho ghep quang ninh",
             "reply": "Dạ xe ghép Quảng Ninh bên em chạy liên tục trong ngày ạ 🚙 Giá 180.000đ - 350.000đ/khách tùy tuyến, xe đời mới 4-7 chỗ, tối đa 3-4 khách/chuyến nên rất thoáng. Anh/chị đi ngày nào để em giữ chỗ giúp mình ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "bao xe quang ninh, thue bao xe quang ninh, xe rieng quang ninh, bao ca xe quang ninh",
             "reply": "Dạ bao xe riêng tuyến Nội tỉnh Quảng Ninh & Quảng Ninh ⇄ Hà Nội / Hải Phòng giá 900.000đ với xe 4 chỗ và 1.200.000đ với xe 7 chỗ ạ 🚘 Xe đón tận cửa, đi thẳng không đón thêm khách. Anh/chị cần đi giờ nào ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "xe 4 cho quang ninh, 4 cho quang ninh, xe con quang ninh",
             "reply": "Dạ bên em có xe 4 chỗ đời mới chạy Quảng Ninh ạ, giá bao xe 900.000đ, đi ghép 180.000đ - 350.000đ/khách tùy tuyến. Xe sạch sẽ, điều hòa mát, tài xế thuộc đường Quảng Ninh ạ 🚗"},
            {"enabled": True, "keywords": "xe 7 cho quang ninh, 7 cho quang ninh, xe gia dinh quang ninh",
             "reply": "Dạ xe 7 chỗ (Xpander/Innova/Fortuner) tuyến Quảng Ninh giá bao xe 1.200.000đ ạ 🚐 Rộng rãi cho gia đình 5-6 người kèm hành lý. Anh/chị đi mấy người để em bố trí xe phù hợp ạ?"},
            {"enabled": True, "keywords": "xe 16 cho quang ninh, xe 29 cho quang ninh, xe du lich quang ninh",
             "reply": "Dạ bên em có xe 16 chỗ và 29 chỗ phục vụ đoàn đi Quảng Ninh ạ 🚌 Anh/chị cho em xin số lượng khách, ngày đi và lịch trình để em gửi báo giá chi tiết nhất nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "don tan noi quang ninh, don tan nha quang ninh, don tai nha quang ninh, tra tan noi quang ninh",
             "reply": "Dạ bên em đón trả TẬN NƠI trong khu vực Quảng Ninh ạ, không phải ra bến 🥰 Anh/chị nhắn giúp em địa chỉ đón và địa chỉ trả, em sẽ báo giờ xe qua đón chính xác ạ!"},
            {"enabled": True, "keywords": "may gio co xe quang ninh, lich trinh quang ninh, gio chay quang ninh, khung gio quang ninh",
             "reply": "Dạ lịch xe chạy Quảng Ninh hàng ngày: 5h00 - 7h00 - 9h00 - 12h00 - 14h00 - 16h00 - 18h00 - 20h00 ạ ⏰ Ngoài ra bên em có xe linh động theo yêu cầu. Anh/chị muốn đi khung giờ nào để em xếp chỗ ạ?"},
            {"enabled": True, "keywords": "dat xe quang ninh, dat cho quang ninh, giu cho quang ninh, book xe quang ninh",
             "reply": "Dạ anh/chị cho em xin: Họ tên - SĐT - Điểm đón - Điểm trả - Giờ đi, em giữ chỗ tuyến Quảng Ninh ngay ạ ✅ Hoặc gọi trực tiếp hotline {hotline} cho nhanh mình nhé!"},
            {"enabled": True, "keywords": "con xe khong quang ninh, con cho khong quang ninh, con slot quang ninh, co xe quang ninh khong",
             "reply": "Dạ hiện tuyến Quảng Ninh vẫn còn chỗ ạ 🥰 Anh/chị đi mấy người và khoảng mấy giờ để em kiểm tra chuyến gần nhất giúp mình ạ?"},
            {"enabled": True, "keywords": "xe di quang ninh luon, di ngay quang ninh, xe chay ngay quang ninh, gap quang ninh",
             "reply": "Dạ bên em luôn có xe trực sẵn khu vực Quảng Ninh ạ 🚗 Anh/chị gọi ngay hotline {hotline}, xe có mặt sau 10-15 phút nếu trong nội thành ạ!"},
            {"enabled": True, "keywords": "san bay quang ninh, di san bay quang ninh, don san bay quang ninh",
             "reply": "Dạ tuyến đi/đón sân bay Vân Đồn / Nội Bài từ Quảng Ninh giá 800.000đ (Vân Đồn) - 1.300.000đ (Nội Bài) ạ ✈️ Tài xế đón tận sảnh, có biển tên, theo dõi giờ hạ cánh miễn phí. Anh/chị cho em xin mã chuyến bay nhé!"},
            {"enabled": True, "keywords": "gui do quang ninh, gui hang quang ninh, ship hang quang ninh, gui giay to quang ninh",
             "reply": "Dạ bên em nhận gửi đồ - gửi hàng - gửi giấy tờ tuyến Quảng Ninh ạ 📦 Cước từ 50.000đ/kiện nhỏ, giao nhận tận nơi trong ngày. Anh/chị cho em xin địa chỉ gửi và địa chỉ nhận ạ!"},
            {"enabled": True, "keywords": "xe dem quang ninh, chuyen dem quang ninh, xe khuya quang ninh",
             "reply": "Dạ bên em có xe chạy đêm tuyến Quảng Ninh ạ 🌙 Chuyến khuya phụ thu 100.000đ - 200.000đ tùy giờ. Anh/chị cần đi lúc mấy giờ để em bố trí tài xế ạ?"},
            {"enabled": True, "keywords": "hop dong quang ninh, thue xe thang quang ninh, xe dua don nhan vien quang ninh",
             "reply": "Dạ bên em nhận hợp đồng đưa đón cố định theo tháng tại Quảng Ninh ạ 🤝 Có xuất hóa đơn VAT, tài xế cố định, giá ưu đãi theo số chuyến. Anh/chị để lại SĐT em gọi tư vấn ngay ạ!"},
            {"enabled": True, "keywords": "di vien quang ninh, benh vien quang ninh, cho benh nhan quang ninh",
             "reply": "Dạ bên em có xe đưa đón bệnh nhân đi viện tuyến Quảng Ninh ạ 🏥 Tài xế hỗ trợ dìu đỡ, xe rộng ghế ngả thoải mái. Anh/chị cho em xin giờ hẹn khám để em xếp xe sớm hơn 30 phút ạ!"},
            {"enabled": True, "keywords": "dam cuoi quang ninh, an hoi quang ninh, ruoc dau quang ninh",
             "reply": "Dạ bên em có xe cưới, xe rước dâu khu vực Quảng Ninh ạ 💒 Xe 4-7-16 chỗ, có trang trí theo yêu cầu. Anh/chị cho em xin ngày và lộ trình để em báo giá trọn gói nhé!"},
            {"enabled": True, "keywords": "tre em quang ninh, co ghe tre em quang ninh, di cung tre nho quang ninh",
             "reply": "Dạ xe tuyến Quảng Ninh có ghế cho bé và dây an toàn ạ 👶 Bé dưới 5 tuổi đi cùng bố mẹ miễn phí. Anh/chị cho em biết bé mấy tuổi để em chuẩn bị ghế phù hợp ạ!"},
            {"enabled": True, "keywords": "cho thu cung quang ninh, cho cho meo quang ninh, mang theo thu cung quang ninh",
             "reply": "Dạ bên em nhận chở thú cưng tuyến Quảng Ninh ạ 🐶 Thú cưng cần có lồng/balo riêng, phụ thu 50.000đ - 100.000đ tùy kích cỡ. Anh/chị cho em xin cân nặng của bé nhé!"},
            {"enabled": True, "keywords": "hanh ly quang ninh, do cong kenh quang ninh, nhieu do quang ninh, chuyen do quang ninh",
             "reply": "Dạ tuyến Quảng Ninh nhận cả hành lý cồng kềnh ạ 🧳 Nếu nhiều đồ em sẽ bố trí xe 7 chỗ gập ghế hoặc xe tải nhỏ. Anh/chị mô tả giúp em số kiện và kích thước ạ!"},
            {"enabled": True, "keywords": "thanh toan quang ninh, chuyen khoan quang ninh, tra tien quang ninh, coc xe quang ninh",
             "reply": "Dạ bên em nhận tiền mặt và chuyển khoản đều được ạ 💳 Khách đi ghép thanh toán khi lên xe, bao xe/hợp đồng cọc trước 20%. Anh/chị cần số tài khoản em gửi ngay ạ!"},
            {"enabled": True, "keywords": "hoa don quang ninh, xuat vat quang ninh, hoa don do quang ninh",
             "reply": "Dạ bên em xuất hóa đơn VAT đầy đủ cho chuyến Quảng Ninh ạ 🧾 Anh/chị gửi em thông tin công ty, mã số thuế, em xuất trong 24h nhé!"},
            {"enabled": True, "keywords": "tai xe quang ninh, lai xe quang ninh, bac tai quang ninh",
             "reply": "Dạ tài xế tuyến Quảng Ninh bên em đều trên 5 năm kinh nghiệm, thuộc đường, lái êm và hỗ trợ xách đồ ạ 🥰 Anh/chị yên tâm nhé!"},
            {"enabled": True, "keywords": "an toan quang ninh, co uy tin khong quang ninh, lua dao quang ninh",
             "reply": "Dạ nhà xe bên em chạy tuyến Quảng Ninh nhiều năm, có định vị và hợp đồng rõ ràng ạ 🥰 Anh/chị chỉ thanh toán khi xe đến đón, không cần cọc với khách đi ghép ạ!"},
            {"enabled": True, "keywords": "huy chuyen quang ninh, doi gio quang ninh, doi lich quang ninh",
             "reply": "Dạ anh/chị báo trước 2 tiếng là đổi giờ hoặc hủy chuyến Quảng Ninh miễn phí ạ 🥰 Em hỗ trợ sắp lại chuyến khác phù hợp giúp mình nhé!"},
            {"enabled": True, "keywords": "dia chi nha xe quang ninh, van phong quang ninh, o dau quang ninh",
             "reply": "Dạ văn phòng bên em có điểm trực tại khu vực Quảng Ninh ạ 📍 Anh/chị cần đến trực tiếp thì gọi hotline {hotline}, em gửi định vị chi tiết ngay nhé!"},
            {"enabled": True, "keywords": "sdt quang ninh, hotline quang ninh, so dien thoai quang ninh, lien he quang ninh",
             "reply": "Dạ hotline tuyến Quảng Ninh: {hotline} (gọi/Zalo 24/7) ạ ☎️ Anh/chị lưu số để tiện đặt xe những lần sau nhé!"},
            {"enabled": True, "keywords": "zalo quang ninh, ket ban quang ninh, nhan tin zalo quang ninh",
             "reply": "Dạ anh/chị kết bạn Zalo số {hotline} giúp em ạ 💬 Bên em gửi lịch xe tuyến Quảng Ninh và bảng giá chi tiết qua Zalo cho mình nhé!"},
            {"enabled": True, "keywords": "khuyen mai quang ninh, giam gia quang ninh, uu dai quang ninh, khach quen quang ninh",
             "reply": "Dạ khách đi tuyến Quảng Ninh từ lần thứ 5 được giảm 10% ạ 🎁 Nhóm từ 3 khách trở lên em cũng có giá ưu đãi riêng. Anh/chị đi mấy người ạ?"},
            {"enabled": True, "keywords": "nha dat quang ninh, ban dat quang ninh, mua nha quang ninh, ban nha quang ninh",
             "reply": "Dạ bên em đang có nhiều lô đất & nhà bán tại Quảng Ninh (Uông Bí, Cẩm Phả, Quảng Yên, Vân Đồn) ạ 🏠 Anh/chị cho em xin tầm ngân sách và diện tích mong muốn để em lọc đúng căn đẹp gửi mình nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "cho thue nha quang ninh, thue phong quang ninh, thue can ho quang ninh, thue mat bang quang ninh",
             "reply": "Dạ bên em có sẵn nhà nguyên căn, căn hộ và mặt bằng kinh doanh cho thuê tại Quảng Ninh (Uông Bí, Cẩm Phả, Quảng Yên, Vân Đồn) ạ 🔑 Anh/chị cần thuê loại nào và tầm giá bao nhiêu ạ?"},
            {"enabled": True, "keywords": "dat nen quang ninh, du an quang ninh, so do quang ninh, phap ly quang ninh",
             "reply": "Dạ các lô bên em giới thiệu tại Quảng Ninh (Uông Bí, Cẩm Phả, Quảng Yên, Vân Đồn) đều sổ đỏ chính chủ, pháp lý rõ ràng, công chứng ngay ạ 📑 Anh/chị muốn xem vị trí lô nào để em gửi sổ và hình ảnh thực tế ạ?"},
            {"enabled": True, "keywords": "ky gui quang ninh, can ban gap quang ninh, moi gioi quang ninh, xem nha quang ninh",
             "reply": "Dạ bên em nhận ký gửi mua - bán - cho thuê bất động sản khu vực Quảng Ninh (Uông Bí, Cẩm Phả, Quảng Yên, Vân Đồn) ạ 🤝 Anh/chị để lại địa chỉ và giá mong muốn, em cho khách xem nhà trong tuần này luôn ạ!"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Nội tỉnh Quảng Ninh & Quảng Ninh ⇄ Hà Nội / Hải Phòng và hỗ trợ nhà đất khu vực Quảng Ninh ạ. Anh/chị cho em xin điểm đón và thời gian đi để em tư vấn chi tiết nhé! Hotline {hotline}",
    },
    "thai_nguyen": {
        "label": "⛰️ THÁI NGUYÊN",
        "rules": [
            {"enabled": True, "keywords": "thai nguyen, tp thai nguyen, xe thai nguyen",
             "reply": "Dạ bên em có xe chạy TP Thái Nguyên (Thái Nguyên) ạ 🚗 Đón trả tận nơi, xe ghép 250.000đ/khách, bao xe 4 chỗ 1.400.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "gang thep, khu gang thep, phu xa",
             "reply": "Dạ Gang Thép là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long / Quảng Ninh, lịch chạy: 4h00 - 6h00 - 8h00 - 10h00 - 13h00 - 15h00 - 17h00 - 19h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "cao dang cong nghiep, cdcn thai nguyen, truong cong nghiep thai nguyen",
             "reply": "Dạ có xe qua Cao đẳng Công nghiệp ạ 🚙 Anh/chị đi ghép giá 250.000đ/khách, muốn đi riêng thì bao xe 1.400.000đ (4 chỗ) / 1.700.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "dai hoc thai nguyen, dh nong lam, dh su pham thai nguyen",
             "reply": "Dạ khu Đại học Thái Nguyên bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "song cong, tp song cong, kcn song cong",
             "reply": "Dạ nhận khách tại Sông Công (Thái Nguyên) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 250.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "pho yen, samsung thai nguyen, kcn yen binh",
             "reply": "Dạ bên em có xe chạy Phổ Yên - Samsung (Thái Nguyên) ạ 🚗 Đón trả tận nơi, xe ghép 250.000đ/khách, bao xe 4 chỗ 1.400.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "dai tu, nui coc, ho nui coc",
             "reply": "Dạ Đại Từ là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long / Quảng Ninh, lịch chạy: 4h00 - 6h00 - 8h00 - 10h00 - 13h00 - 15h00 - 17h00 - 19h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "phu binh, phu luong, dinh hoa",
             "reply": "Dạ có xe qua Phú Bình - Phú Lương ạ 🚙 Anh/chị đi ghép giá 250.000đ/khách, muốn đi riêng thì bao xe 1.400.000đ (4 chỗ) / 1.700.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "ben xe thai nguyen, ben xe trung tam thai nguyen",
             "reply": "Dạ khu Bến xe Thái Nguyên bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "benh vien trung uong thai nguyen, bv a thai nguyen, bv gang thep",
             "reply": "Dạ nhận khách tại Bệnh viện Trung ương Thái Nguyên (Thái Nguyên) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 250.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "dong hy, vo nhai, trai cau",
             "reply": "Dạ bên em có xe chạy Đồng Hỷ - Võ Nhai (Thái Nguyên) ạ 🚗 Đón trả tận nơi, xe ghép 250.000đ/khách, bao xe 4 chỗ 1.400.000đ. Anh/chị đi lúc mấy giờ để em xếp chuyến gần nhất ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "quoc lo 3, cao toc thai nguyen, ql3 moi",
             "reply": "Dạ Quốc lộ 3 - Cao tốc Thái Nguyên là điểm đón quen thuộc của nhà xe bên em ạ 🥰 Tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long / Quảng Ninh, lịch chạy: 4h00 - 6h00 - 8h00 - 10h00 - 13h00 - 15h00 - 17h00 - 19h00. Anh/chị cho em xin số điện thoại để tài xế liên hệ đón tận nơi nhé!"},
            {"enabled": True, "keywords": "thai nguyen di ha noi, thai nguyen ve ha noi",
             "reply": "Dạ có xe qua Thái Nguyên đi Hà Nội ạ 🚙 Anh/chị đi ghép giá 250.000đ/khách, muốn đi riêng thì bao xe 1.400.000đ (4 chỗ) / 1.700.000đ (7 chỗ). Em giữ chỗ giúp mình luôn nhé? Hotline {hotline}"},
            {"enabled": True, "keywords": "thai nguyen di ha long, thai nguyen di quang ninh",
             "reply": "Dạ khu Thái Nguyên đi Hạ Long bên em có xe trực sẵn ạ ✅ Đón tận cửa, không phải ra bến, hỗ trợ xách hành lý. Anh/chị nhắn giúp em địa chỉ cụ thể và giờ đi ạ!"},
            {"enabled": True, "keywords": "tan long, quang vinh, thinh dan",
             "reply": "Dạ nhận khách tại Tân Long - Quang Vinh (Thái Nguyên) ạ 🚘 Xe đời mới, điều hòa mát, tài xế thuộc đường. Giá ghép 250.000đ/khách, trẻ nhỏ dưới 5 tuổi miễn phí. Anh/chị đi ngày nào ạ?"},
            {"enabled": True, "keywords": "gia xe thai nguyen, bao nhieu tien thai nguyen, gia ve thai nguyen, thai nguyen bao nhieu tien",
             "reply": "Dạ giá tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long / Quảng Ninh bên em: xe ghép 250.000đ/khách - bao xe 4 chỗ 1.400.000đ - bao xe 7 chỗ 1.700.000đ ạ 🚗 Giá đã bao gồm đón trả tận nơi trong nội thành Thái Nguyên. Anh/chị cho em xin điểm đón cụ thể để em báo chính xác nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "xe ghep thai nguyen, di ghep thai nguyen, ghep xe thai nguyen, con cho ghep thai nguyen",
             "reply": "Dạ xe ghép Thái Nguyên bên em chạy liên tục trong ngày ạ 🚙 Giá 250.000đ/khách, xe đời mới 4-7 chỗ, tối đa 3-4 khách/chuyến nên rất thoáng. Anh/chị đi ngày nào để em giữ chỗ giúp mình ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "bao xe thai nguyen, thue bao xe thai nguyen, xe rieng thai nguyen, bao ca xe thai nguyen",
             "reply": "Dạ bao xe riêng tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long / Quảng Ninh giá 1.400.000đ với xe 4 chỗ và 1.700.000đ với xe 7 chỗ ạ 🚘 Xe đón tận cửa, đi thẳng không đón thêm khách. Anh/chị cần đi giờ nào ạ? Hotline {hotline}"},
            {"enabled": True, "keywords": "xe 4 cho thai nguyen, 4 cho thai nguyen, xe con thai nguyen",
             "reply": "Dạ bên em có xe 4 chỗ đời mới chạy Thái Nguyên ạ, giá bao xe 1.400.000đ, đi ghép 250.000đ/khách. Xe sạch sẽ, điều hòa mát, tài xế thuộc đường Thái Nguyên ạ 🚗"},
            {"enabled": True, "keywords": "xe 7 cho thai nguyen, 7 cho thai nguyen, xe gia dinh thai nguyen",
             "reply": "Dạ xe 7 chỗ (Xpander/Innova/Fortuner) tuyến Thái Nguyên giá bao xe 1.700.000đ ạ 🚐 Rộng rãi cho gia đình 5-6 người kèm hành lý. Anh/chị đi mấy người để em bố trí xe phù hợp ạ?"},
            {"enabled": True, "keywords": "xe 16 cho thai nguyen, xe 29 cho thai nguyen, xe du lich thai nguyen",
             "reply": "Dạ bên em có xe 16 chỗ và 29 chỗ phục vụ đoàn đi Thái Nguyên ạ 🚌 Anh/chị cho em xin số lượng khách, ngày đi và lịch trình để em gửi báo giá chi tiết nhất nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "don tan noi thai nguyen, don tan nha thai nguyen, don tai nha thai nguyen, tra tan noi thai nguyen",
             "reply": "Dạ bên em đón trả TẬN NƠI trong khu vực Thái Nguyên ạ, không phải ra bến 🥰 Anh/chị nhắn giúp em địa chỉ đón và địa chỉ trả, em sẽ báo giờ xe qua đón chính xác ạ!"},
            {"enabled": True, "keywords": "may gio co xe thai nguyen, lich trinh thai nguyen, gio chay thai nguyen, khung gio thai nguyen",
             "reply": "Dạ lịch xe chạy Thái Nguyên hàng ngày: 4h00 - 6h00 - 8h00 - 10h00 - 13h00 - 15h00 - 17h00 - 19h00 ạ ⏰ Ngoài ra bên em có xe linh động theo yêu cầu. Anh/chị muốn đi khung giờ nào để em xếp chỗ ạ?"},
            {"enabled": True, "keywords": "dat xe thai nguyen, dat cho thai nguyen, giu cho thai nguyen, book xe thai nguyen",
             "reply": "Dạ anh/chị cho em xin: Họ tên - SĐT - Điểm đón - Điểm trả - Giờ đi, em giữ chỗ tuyến Thái Nguyên ngay ạ ✅ Hoặc gọi trực tiếp hotline {hotline} cho nhanh mình nhé!"},
            {"enabled": True, "keywords": "con xe khong thai nguyen, con cho khong thai nguyen, con slot thai nguyen, co xe thai nguyen khong",
             "reply": "Dạ hiện tuyến Thái Nguyên vẫn còn chỗ ạ 🥰 Anh/chị đi mấy người và khoảng mấy giờ để em kiểm tra chuyến gần nhất giúp mình ạ?"},
            {"enabled": True, "keywords": "xe di thai nguyen luon, di ngay thai nguyen, xe chay ngay thai nguyen, gap thai nguyen",
             "reply": "Dạ bên em luôn có xe trực sẵn khu vực Thái Nguyên ạ 🚗 Anh/chị gọi ngay hotline {hotline}, xe có mặt sau 10-15 phút nếu trong nội thành ạ!"},
            {"enabled": True, "keywords": "san bay thai nguyen, di san bay thai nguyen, don san bay thai nguyen",
             "reply": "Dạ tuyến đi/đón sân bay Nội Bài từ Thái Nguyên giá 550.000đ (xe 4 chỗ) - 750.000đ (xe 7 chỗ) ạ ✈️ Tài xế đón tận sảnh, có biển tên, theo dõi giờ hạ cánh miễn phí. Anh/chị cho em xin mã chuyến bay nhé!"},
            {"enabled": True, "keywords": "gui do thai nguyen, gui hang thai nguyen, ship hang thai nguyen, gui giay to thai nguyen",
             "reply": "Dạ bên em nhận gửi đồ - gửi hàng - gửi giấy tờ tuyến Thái Nguyên ạ 📦 Cước từ 50.000đ/kiện nhỏ, giao nhận tận nơi trong ngày. Anh/chị cho em xin địa chỉ gửi và địa chỉ nhận ạ!"},
            {"enabled": True, "keywords": "xe dem thai nguyen, chuyen dem thai nguyen, xe khuya thai nguyen",
             "reply": "Dạ bên em có xe chạy đêm tuyến Thái Nguyên ạ 🌙 Chuyến khuya phụ thu 100.000đ - 200.000đ tùy giờ. Anh/chị cần đi lúc mấy giờ để em bố trí tài xế ạ?"},
            {"enabled": True, "keywords": "hop dong thai nguyen, thue xe thang thai nguyen, xe dua don nhan vien thai nguyen",
             "reply": "Dạ bên em nhận hợp đồng đưa đón cố định theo tháng tại Thái Nguyên ạ 🤝 Có xuất hóa đơn VAT, tài xế cố định, giá ưu đãi theo số chuyến. Anh/chị để lại SĐT em gọi tư vấn ngay ạ!"},
            {"enabled": True, "keywords": "di vien thai nguyen, benh vien thai nguyen, cho benh nhan thai nguyen",
             "reply": "Dạ bên em có xe đưa đón bệnh nhân đi viện tuyến Thái Nguyên ạ 🏥 Tài xế hỗ trợ dìu đỡ, xe rộng ghế ngả thoải mái. Anh/chị cho em xin giờ hẹn khám để em xếp xe sớm hơn 30 phút ạ!"},
            {"enabled": True, "keywords": "dam cuoi thai nguyen, an hoi thai nguyen, ruoc dau thai nguyen",
             "reply": "Dạ bên em có xe cưới, xe rước dâu khu vực Thái Nguyên ạ 💒 Xe 4-7-16 chỗ, có trang trí theo yêu cầu. Anh/chị cho em xin ngày và lộ trình để em báo giá trọn gói nhé!"},
            {"enabled": True, "keywords": "tre em thai nguyen, co ghe tre em thai nguyen, di cung tre nho thai nguyen",
             "reply": "Dạ xe tuyến Thái Nguyên có ghế cho bé và dây an toàn ạ 👶 Bé dưới 5 tuổi đi cùng bố mẹ miễn phí. Anh/chị cho em biết bé mấy tuổi để em chuẩn bị ghế phù hợp ạ!"},
            {"enabled": True, "keywords": "cho thu cung thai nguyen, cho cho meo thai nguyen, mang theo thu cung thai nguyen",
             "reply": "Dạ bên em nhận chở thú cưng tuyến Thái Nguyên ạ 🐶 Thú cưng cần có lồng/balo riêng, phụ thu 50.000đ - 100.000đ tùy kích cỡ. Anh/chị cho em xin cân nặng của bé nhé!"},
            {"enabled": True, "keywords": "hanh ly thai nguyen, do cong kenh thai nguyen, nhieu do thai nguyen, chuyen do thai nguyen",
             "reply": "Dạ tuyến Thái Nguyên nhận cả hành lý cồng kềnh ạ 🧳 Nếu nhiều đồ em sẽ bố trí xe 7 chỗ gập ghế hoặc xe tải nhỏ. Anh/chị mô tả giúp em số kiện và kích thước ạ!"},
            {"enabled": True, "keywords": "thanh toan thai nguyen, chuyen khoan thai nguyen, tra tien thai nguyen, coc xe thai nguyen",
             "reply": "Dạ bên em nhận tiền mặt và chuyển khoản đều được ạ 💳 Khách đi ghép thanh toán khi lên xe, bao xe/hợp đồng cọc trước 20%. Anh/chị cần số tài khoản em gửi ngay ạ!"},
            {"enabled": True, "keywords": "hoa don thai nguyen, xuat vat thai nguyen, hoa don do thai nguyen",
             "reply": "Dạ bên em xuất hóa đơn VAT đầy đủ cho chuyến Thái Nguyên ạ 🧾 Anh/chị gửi em thông tin công ty, mã số thuế, em xuất trong 24h nhé!"},
            {"enabled": True, "keywords": "tai xe thai nguyen, lai xe thai nguyen, bac tai thai nguyen",
             "reply": "Dạ tài xế tuyến Thái Nguyên bên em đều trên 5 năm kinh nghiệm, thuộc đường, lái êm và hỗ trợ xách đồ ạ 🥰 Anh/chị yên tâm nhé!"},
            {"enabled": True, "keywords": "an toan thai nguyen, co uy tin khong thai nguyen, lua dao thai nguyen",
             "reply": "Dạ nhà xe bên em chạy tuyến Thái Nguyên nhiều năm, có định vị và hợp đồng rõ ràng ạ 🥰 Anh/chị chỉ thanh toán khi xe đến đón, không cần cọc với khách đi ghép ạ!"},
            {"enabled": True, "keywords": "huy chuyen thai nguyen, doi gio thai nguyen, doi lich thai nguyen",
             "reply": "Dạ anh/chị báo trước 2 tiếng là đổi giờ hoặc hủy chuyến Thái Nguyên miễn phí ạ 🥰 Em hỗ trợ sắp lại chuyến khác phù hợp giúp mình nhé!"},
            {"enabled": True, "keywords": "dia chi nha xe thai nguyen, van phong thai nguyen, o dau thai nguyen",
             "reply": "Dạ văn phòng bên em có điểm trực tại khu vực Thái Nguyên ạ 📍 Anh/chị cần đến trực tiếp thì gọi hotline {hotline}, em gửi định vị chi tiết ngay nhé!"},
            {"enabled": True, "keywords": "sdt thai nguyen, hotline thai nguyen, so dien thoai thai nguyen, lien he thai nguyen",
             "reply": "Dạ hotline tuyến Thái Nguyên: {hotline} (gọi/Zalo 24/7) ạ ☎️ Anh/chị lưu số để tiện đặt xe những lần sau nhé!"},
            {"enabled": True, "keywords": "zalo thai nguyen, ket ban thai nguyen, nhan tin zalo thai nguyen",
             "reply": "Dạ anh/chị kết bạn Zalo số {hotline} giúp em ạ 💬 Bên em gửi lịch xe tuyến Thái Nguyên và bảng giá chi tiết qua Zalo cho mình nhé!"},
            {"enabled": True, "keywords": "khuyen mai thai nguyen, giam gia thai nguyen, uu dai thai nguyen, khach quen thai nguyen",
             "reply": "Dạ khách đi tuyến Thái Nguyên từ lần thứ 5 được giảm 10% ạ 🎁 Nhóm từ 3 khách trở lên em cũng có giá ưu đãi riêng. Anh/chị đi mấy người ạ?"},
            {"enabled": True, "keywords": "nha dat thai nguyen, ban dat thai nguyen, mua nha thai nguyen, ban nha thai nguyen",
             "reply": "Dạ bên em đang có nhiều lô đất & nhà bán tại Thái Nguyên (Gang Thép, Sông Công, Phổ Yên, Túc Duyên) ạ 🏠 Anh/chị cho em xin tầm ngân sách và diện tích mong muốn để em lọc đúng căn đẹp gửi mình nhé! Hotline {hotline}"},
            {"enabled": True, "keywords": "cho thue nha thai nguyen, thue phong thai nguyen, thue can ho thai nguyen, thue mat bang thai nguyen",
             "reply": "Dạ bên em có sẵn nhà nguyên căn, căn hộ và mặt bằng kinh doanh cho thuê tại Thái Nguyên (Gang Thép, Sông Công, Phổ Yên, Túc Duyên) ạ 🔑 Anh/chị cần thuê loại nào và tầm giá bao nhiêu ạ?"},
            {"enabled": True, "keywords": "dat nen thai nguyen, du an thai nguyen, so do thai nguyen, phap ly thai nguyen",
             "reply": "Dạ các lô bên em giới thiệu tại Thái Nguyên (Gang Thép, Sông Công, Phổ Yên, Túc Duyên) đều sổ đỏ chính chủ, pháp lý rõ ràng, công chứng ngay ạ 📑 Anh/chị muốn xem vị trí lô nào để em gửi sổ và hình ảnh thực tế ạ?"},
            {"enabled": True, "keywords": "ky gui thai nguyen, can ban gap thai nguyen, moi gioi thai nguyen, xem nha thai nguyen",
             "reply": "Dạ bên em nhận ký gửi mua - bán - cho thuê bất động sản khu vực Thái Nguyên (Gang Thép, Sông Công, Phổ Yên, Túc Duyên) ạ 🤝 Anh/chị để lại địa chỉ và giá mong muốn, em cho khách xem nhà trong tuần này luôn ạ!"},
        ],
        "default_reply": "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe tuyến Thái Nguyên ⇄ Hà Nội / Hạ Long / Quảng Ninh và hỗ trợ nhà đất khu vực Thái Nguyên ạ. Anh/chị cho em xin điểm đón và thời gian đi để em tư vấn chi tiết nhé! Hotline {hotline}",
    },
}

REGION_ORDER = ["ha_long", "ha_noi", "hai_phong", "quang_ninh", "thai_nguyen"]

DEFAULT_GLOBAL_REPLY = (
    "Dạ em chào anh/chị 👋 Bên em chuyên xe ghép - xe tiện chuyến - bao xe "
    "tuyến Hạ Long / Hà Nội / Hải Phòng / Quảng Ninh / Thái Nguyên và hỗ trợ "
    "nhà đất các khu vực trên ạ. Anh/chị cho em xin ĐIỂM ĐÓN - ĐIỂM TRẢ - "
    "THỜI GIAN đi để em báo giá chi tiết nhé! Hotline {hotline}"
)


def _apply_hotline(value, hotline=None):
    """Thay the token {hotline} trong toan bo kich ban bang so hotline that."""
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
    """Dem tong so tu khoa (moi o tu khoa co the chua nhieu tu cach nhau dau phay)."""
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

def _find_coccoc_exe():
    """Tự dò đường dẫn Cốc Cốc phổ biến trên Windows (nếu chưa cấu hình)."""
    candidates = [
        r"C:\Program Files\CocCoc\Browser\Application\browser.exe",
        r"C:\Program Files (x86)\CocCoc\Browser\Application\browser.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\CocCoc\Browser\Application\browser.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


# Duong dan thuc thi trinh duyet Coc Coc (chuan; neu khong ton tai thi tu do) va Profile mac dinh
_COCCOC_DEFAULT_EXE = r"C:\Program Files\CocCoc\Browser\Application\browser.exe"
COCCOC_EXECUTABLE_PATH = (
    _COCCOC_DEFAULT_EXE if os.path.exists(_COCCOC_DEFAULT_EXE)
    else (_find_coccoc_exe() or _COCCOC_DEFAULT_EXE)
)
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

    # --- Kich ban 5 khu vuc dia ly ---
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
    data.setdefault("share_coccoc_exe", COCCOC_EXECUTABLE_PATH)
    data.setdefault("share_dry_run", False)
    data.setdefault("share_kill_all_browsers", True)

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
    """MATCHING ENGINE: duyet toan bo tu khoa cua 5 khu vuc.

    Tra ve (region_key, reply, matched_keyword). Neu khong khop khu vuc nao
    thi tra ve (None, "", "").

    Nguyen tac chon: uu tien luat khop NHIEU tu khoa nhat, sau do la tu khoa
    DAI NHAT (cu the nhat). Vi du "co xe di cao xanh ha long ko shop" se khop
    "cao xanh" -> Khu vuc HA LONG thay vi mot tu khoa chung chung.
    """
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


def region_fallback_reply(region_key, region_rules):
    reg = (region_rules or {}).get(region_key) or {}
    return reg.get("default_reply", "")


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
# Worker Auto Share Group (Playwright) - Hàng đợi xử lý TUẦN TỰ
# Mỗi phần tử trong hàng đợi là TOÀN BỘ NỘI DUNG bài viết quảng cáo
# (nhiều dòng, emoji, hotline, giá cước, hashtag...), được DÁN NGUYÊN KHỐI
# vào khung "Tạo bài viết" của từng Nhóm.
# ==========================================================================
_PASTE_MOD = "Meta" if sys.platform == "darwin" else "Control"


class ShareQueueWorker(QThread):
    """Dán NHIỀU bài quảng cáo (post_contents) vào NHIỀU Group, TUẦN TỰ.

    - CHỈ 1 trình duyệt (persistent_context) + CHỈ 1 Tab (`page`) cho toàn bộ
      hàng đợi `queue.Queue`.
    - Trước khi launch: dọn tiến trình browser.exe treo + file khóa Profile
      (SingletonLock...).
    - Nội dung bài viết được DÁN nguyên khối bằng 3 lớp dự phòng:
        1) Clipboard API (navigator.clipboard.writeText) + phím tắt Ctrl+V
        2) Sự kiện bàn phím/dán giả lập (ClipboardEvent 'paste' trên khung soạn)
        3) keyboard.insert_text từng dòng + Shift+Enter (giữ nguyên xuống dòng)
      Sau mỗi lớp có kiểm tra nội dung đã vào khung chưa; thiếu thì xóa và
      chuyển sang lớp kế tiếp.
    - Chờ nút Đăng sẵn sàng; chế độ dry-run (không bấm Đăng) / live.
    - `enqueue()` thread-safe; trả về False nếu worker đã đóng hẳn (khi đó GUI
      phải tạo worker mới) -> không bao giờ có 2 instance chạy cùng lúc và
      không bị mất bài do race lúc worker đang tự đóng.
    - Luôn đóng trình duyệt trong `finally`.
    """

    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(str)

    IDLE_CLOSE_TIMEOUT = 5.0   # giây rỗng hàng đợi trước khi tự đóng trình duyệt
    POLL_INTERVAL = 1.0        # chu kỳ poll hàng đợi (để bắt request_stop kịp)
    ELEMENT_TIMEOUT = 15000    # ms chờ phần tử UI xuất hiện
    PREVIEW_MAX_WAIT = 20.0    # giây tối đa chờ Link Preview / nút Đăng sẵn sàng
    PASTE_VERIFY_RATIO = 0.85  # % ký tự (không tính khoảng trắng) phải có trong khung sau khi dán

    LOCK_FILES = ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile")
    CLIPBOARD_ORIGINS = (
        "https://www.facebook.com",
        "https://facebook.com",
        "https://m.facebook.com",
    )

    def __init__(self, post_contents, group_list, profile_path, delay_min, delay_max,
                 coccoc_exe=None, dry_run=False, max_retries=1,
                 kill_all_browsers=True):
        """
        post_contents:      danh sách NỘI DUNG bài viết quảng cáo đầy đủ (mỗi phần tử
                            là 1 bài nhiều dòng) - được dán lần lượt vào các Nhóm.
        dry_run:            True -> dán nội dung nhưng KHÔNG bấm Đăng (đóng hộp thoại).
        max_retries:        số lần thử lại cho mỗi Group khi gặp lỗi.
        kill_all_browsers:  True  -> taskkill mọi browser.exe (đúng như bản cũ,
                                     sẽ tắt cả Cốc Cốc bạn đang dùng thường ngày).
                            False -> chỉ kill tiến trình có dùng đúng Profile này.
        """
        super().__init__()
        self.queue = queue.Queue()
        if isinstance(post_contents, str):
            post_contents = [post_contents]
        for content in (post_contents or []):
            content = self._clean_content(content)
            if content:
                self.queue.put(content)
        if isinstance(group_list, (list, tuple)):
            group_list = "\n".join(group_list)
        self.groups = [g.strip() for g in (group_list or "").split("\n") if g.strip()]
        self.profile_path = profile_path
        self.delay_min, self.delay_max = sorted((float(delay_min), float(delay_max)))
        self.coccoc_exe = coccoc_exe or COCCOC_EXECUTABLE_PATH
        self.dry_run = dry_run
        self.max_retries = max(0, int(max_retries))
        self.kill_all_browsers = kill_all_browsers

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._closed = False  # True khi worker đã chốt đóng, không nhận thêm bài
        self.stats = {"ok": 0, "fail": 0, "skipped": 0}

    # ------------------------------------------------------------------ API
    def enqueue(self, post_contents):
        """Nạp thêm bài (nội dung đầy đủ) vào hàng đợi (thread-safe).

        Trả về True nếu worker còn nhận; False nếu đã đóng / đã bị yêu cầu dừng
        -> GUI tạo worker mới.
        """
        with self._lock:
            if self._closed or self._stop_event.is_set():
                return False
            if isinstance(post_contents, str):
                post_contents = [post_contents]
            for content in (post_contents or []):
                content = self._clean_content(content)
                if content:
                    self.queue.put(content)
            return True

    def request_stop(self):
        """Yêu cầu dừng an toàn giữa các bước."""
        self._stop_event.set()

    # -------------------------------------------------------------- helpers
    def _log(self, msg, level="info"):
        self.log_signal.emit(msg, level)

    def _sleep_interruptible(self, seconds):
        self._stop_event.wait(seconds)

    def _human_pause(self, lo, hi):
        self._sleep_interruptible(random.uniform(lo, hi))

    def _countdown_sleep(self, seconds, label="nghỉ anti-bot"):
        """Nghỉ có đếm ngược, phát progress_signal mỗi giây."""
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
    def _clean_content(content):
        """Chuẩn hóa nội dung bài: CRLF/CR -> LF, bỏ khoảng trắng thừa đầu/cuối.

        KHÔNG đụng vào các dòng trống ở giữa bài (giữ nguyên bố cục xuống dòng).
        """
        if content is None:
            return ""
        text = str(content).replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()

    @staticmethod
    def _summarize_content(content):
        """Tóm tắt ngắn gọn để ghi log: dòng đầu + số dòng + số ký tự."""
        first = next((ln.strip() for ln in content.split("\n") if ln.strip()), "")
        if len(first) > 60:
            first = first[:57] + "..."
        return f"\"{first}\" ({len(content.splitlines())} dòng, {len(content)} ký tự)"

    @staticmethod
    def _normalize_group_url(entry):
        """URL đầy đủ / ID số / slug -> https://www.facebook.com/groups/<id>/"""
        entry = (entry or "").strip()
        if not entry:
            return None
        low = entry.lower()
        if low.startswith(("http://", "https://")):
            return entry
        if low.startswith(("www.facebook.com", "facebook.com", "m.facebook.com", "fb.com")):
            return "https://" + entry
        return f"https://www.facebook.com/groups/{entry.strip('/')}/"

    @staticmethod
    def _is_visible(locator, timeout_ms):
        """Chờ phần tử hiện ra (khác với .is_visible() không hề chờ)."""
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    # ------------------------------------------- DÁN NỘI DUNG 3 LỚP DỰ PHÒNG
    @staticmethod
    def _squash(text):
        """Bỏ mọi khoảng trắng/xuống dòng để so sánh độ dài nội dung."""
        return "".join((text or "").split())

    def _get_box_text(self, text_box):
        try:
            return text_box.inner_text(timeout=3000) or ""
        except Exception:
            return ""

    def _paste_looks_complete(self, text_box, content):
        """Đã có (gần) đủ nội dung trong khung soạn bài chưa?"""
        expected = len(self._squash(content))
        if expected == 0:
            return True
        got = len(self._squash(self._get_box_text(text_box)))
        return got >= expected * self.PASTE_VERIFY_RATIO

    def _clear_text_box(self, page, text_box):
        """Xóa sạch khung soạn bài trước khi thử lớp dán kế tiếp."""
        try:
            text_box.click()
            page.keyboard.press(f"{_PASTE_MOD}+A")
            page.keyboard.press("Delete")
            self._stop_event.wait(0.3)
        except Exception:
            pass

    def _grant_clipboard_permissions(self, context):
        """Cấp quyền clipboard cho facebook.com để lớp dán số 1 hoạt động."""
        for origin in self.CLIPBOARD_ORIGINS:
            try:
                context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
            except Exception:
                # Một số trình duyệt không hỗ trợ đủ quyền -> các lớp dự phòng sẽ lo
                pass

    def _paste_via_clipboard_api(self, page, text_box, content):
        """LỚP 1: ghi vào Clipboard bằng Clipboard API rồi nhấn Ctrl+V."""
        text_box.click()
        page.evaluate("async (t) => { await navigator.clipboard.writeText(t); }", content)
        page.keyboard.press(f"{_PASTE_MOD}+V")

    def _paste_via_keyboard_event(self, page, text_box, content):
        """LỚP 2: bắn sự kiện 'paste' (kèm DataTransfer) thẳng vào khung soạn bài."""
        text_box.click()
        text_box.evaluate(
            """(el, text) => {
                el.focus();
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                const ev = new ClipboardEvent('paste', {
                    clipboardData: dt, bubbles: true, cancelable: true
                });
                el.dispatchEvent(ev);
            }""",
            content,
        )

    def _paste_via_insert_text(self, page, text_box, content):
        """LỚP 3: keyboard.insert_text từng dòng, Shift+Enter giữa các dòng
        (giữ nguyên xuống dòng & dòng trống, không bị mất định dạng)."""
        text_box.click()
        lines = content.split("\n")
        last = len(lines) - 1
        for i, line in enumerate(lines):
            if line:
                page.keyboard.insert_text(line)
            if i < last:
                page.keyboard.press("Shift+Enter")

    def _paste_post_content(self, page, text_box, content):
        """Dán nguyên khối nội dung bài viết; trả về tên lớp thành công hoặc None."""
        layers = (
            ("Clipboard API + Ctrl+V", self._paste_via_clipboard_api),
            ("Sự kiện bàn phím/dán (ClipboardEvent)", self._paste_via_keyboard_event),
            ("keyboard.insert_text", self._paste_via_insert_text),
        )
        for idx, (label, paste_fn) in enumerate(layers, start=1):
            if self._stop_event.is_set():
                return None
            try:
                if idx > 1:
                    self._clear_text_box(page, text_box)
                paste_fn(page, text_box, content)
                self._stop_event.wait(0.8)  # cho Facebook xử lý xong nội dung vừa dán
                if self._paste_looks_complete(text_box, content):
                    self._log(f"📋 Đã dán nội dung bài viết bằng lớp {idx}: {label}", "info")
                    return label
                self._log(f"⚠️ Lớp dán {idx} ({label}) chưa đủ nội dung -> thử lớp kế tiếp.", "warning")
            except Exception as err:
                self._log(f"⚠️ Lớp dán {idx} ({label}) lỗi: {err} -> thử lớp kế tiếp.", "warning")
        return None

    # ------------------------------------------------------ dọn khóa Profile
    def _kill_stale_browsers(self):
        if not sys.platform.startswith("win"):
            return
        try:
            if self.kill_all_browsers:
                self._log("🧹 taskkill toàn bộ browser.exe (Cốc Cốc) còn treo ngầm...", "info")
                subprocess.run(["taskkill", "/F", "/IM", "browser.exe", "/T"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            elif self.profile_path:
                self._log("🧹 Kill browser.exe đang giữ Profile này (nếu có)...", "info")
                safe_path = self.profile_path.replace("'", "''")
                ps = (
                    "Get-CimInstance Win32_Process -Filter \"Name='browser.exe'\" | "
                    f"Where-Object {{ $_.CommandLine -like '*{safe_path}*' }} | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            time.sleep(1.0)  # chờ OS nhả file khóa
        except Exception as e:
            self._log(f"Không thể dọn tiến trình trình duyệt cũ (bỏ qua): {e}", "warning")

    def _remove_lock_files(self):
        if not (self.profile_path and os.path.isdir(self.profile_path)):
            return
        for name in self.LOCK_FILES:
            lock_path = os.path.join(self.profile_path, name)
            try:
                if os.path.lexists(lock_path):  # lexists: bắt cả symlink hỏng (Linux/macOS)
                    os.remove(lock_path)
                    self._log(f"🧹 Đã xóa file khóa Profile ({name}) còn sót lại.", "info")
            except Exception as e:
                self._log(f"Không thể xóa {name} (bỏ qua): {e}", "warning")

    def _cleanup_stale_browser_profile(self):
        self._kill_stale_browsers()
        self._remove_lock_files()

    # ----------------------------------------------------- share 1 group
    def _wait_post_button_ready(self, submit_btn):
        """Chờ Link Preview tải xong: nút Đăng hiện và không còn aria-disabled."""
        deadline = time.time() + self.PREVIEW_MAX_WAIT
        while time.time() < deadline and not self._stop_event.is_set():
            try:
                if submit_btn.is_visible() and submit_btn.get_attribute("aria-disabled") != "true":
                    return True
            except Exception:
                pass
            self._stop_event.wait(0.5)
        return False

    def _share_to_group(self, page, post_content, group_url):
        """Trả về 'ok' | 'skipped' | 'stopped'; ném Exception nếu lỗi (để retry)."""
        page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
        self._human_pause(2.5, 4.5)
        if self._stop_event.is_set():
            return "stopped"

        composer = page.locator(
            "//span[contains(text(),'Bạn viết gì') or contains(text(),'Viết gì đó') "
            "or contains(text(),'Write something')]"
        ).first
        if not self._is_visible(composer, self.ELEMENT_TIMEOUT):
            self._log(f"⚠️ Không thấy ô đăng bài ở {group_url} (chưa là thành viên / nhóm riêng tư?).", "warning")
            return "skipped"
        composer.click()
        self._human_pause(2, 3.5)

        text_box = page.locator("//div[@role='dialog']//div[@role='textbox']").first
        if not self._is_visible(text_box, self.ELEMENT_TIMEOUT):
            self._log(f"⚠️ Không thấy khung soạn bài ở {group_url}.", "warning")
            return "skipped"
        text_box.click()

        # DÁN nguyên khối nội dung bài viết (3 lớp dự phòng)
        pasted_by = self._paste_post_content(page, text_box, post_content)
        if self._stop_event.is_set():
            return "stopped"
        if pasted_by is None:
            raise RuntimeError("Không dán được nội dung bài viết vào khung soạn bài (đã thử cả 3 lớp).")

        # Chờ Facebook dựng Link Preview (nếu bài có link)
        self._human_pause(3.5, 5.5)
        if self._stop_event.is_set():
            return "stopped"

        submit_btn = page.locator(
            "//div[@role='dialog']//div[@aria-label='Đăng' or @aria-label='Post']"
        ).first
        if not self._is_visible(submit_btn, self.ELEMENT_TIMEOUT):
            self._log(f"⚠️ Không thấy nút Đăng ở {group_url}.", "warning")
            return "skipped"
        if not self._wait_post_button_ready(submit_btn):
            self._log("⚠️ Nút Đăng chưa sẵn sàng sau thời gian chờ, vẫn thử bấm...", "warning")

        if self.dry_run:
            self._log(f"🧪 [DRY-RUN] Đã dán nội dung & thấy nút Đăng ở {group_url} - KHÔNG bấm Đăng.", "info")
            page.keyboard.press("Escape")
            self._human_pause(1, 2)
            # Facebook có thể hỏi "Bỏ bài viết?" -> thử bấm xác nhận bỏ
            try:
                discard = page.locator(
                    "//div[@role='dialog']//div[@aria-label='Bỏ' or @aria-label='Discard']"
                ).first
                if discard.is_visible():
                    discard.click()
            except Exception:
                pass
            return "ok"

        submit_btn.click()
        # Hộp thoại đóng lại = bài đã được gửi đi
        try:
            page.locator("//div[@role='dialog']//div[@role='textbox']").first.wait_for(
                state="hidden", timeout=20000)
        except Exception:
            self._log(f"⚠️ Hộp thoại chưa đóng sau khi bấm Đăng ({group_url}) - chưa xác nhận được.", "warning")
        self._human_pause(2, 3)
        return "ok"

    def _share_one_post(self, page, post_content):
        """Dán 1 bài quảng cáo vào tất cả Group, dùng chung 1 `page`."""
        if not self.groups:
            self._log("Danh sách Nhóm trống, bỏ qua Auto Share.", "warning")
            return

        self._log(f"🚀 Bắt đầu đăng bài quảng cáo: {self._summarize_content(post_content)}", "info")
        total = len(self.groups)

        for idx, entry in enumerate(self.groups):
            if self._stop_event.is_set():
                self._log("Đã dừng Auto Share theo yêu cầu.", "warning")
                break

            group_url = self._normalize_group_url(entry)
            if not group_url:
                self.stats["skipped"] += 1
                continue

            self.progress_signal.emit(f"Đang đăng bài vào nhóm {idx+1}/{total}: {group_url}")
            self._log(f"[{idx+1}/{total}] Đăng bài lên Group: {group_url}", "info")

            result = None
            for attempt in range(self.max_retries + 1):
                try:
                    result = self._share_to_group(page, post_content, group_url)
                    break
                except Exception as err:
                    self._log(f"Lỗi đăng bài {group_url} (lần {attempt+1}/{self.max_retries+1}): {err}", "error")
                    result = "error"
                    if attempt < self.max_retries and not self._stop_event.is_set():
                        self._human_pause(3, 6)

            if result == "ok":
                self.stats["ok"] += 1
                if not self.dry_run:
                    self._log(f"✅ Đăng bài thành công lên {group_url}", "success")
            elif result == "skipped":
                self.stats["skipped"] += 1
            elif result == "error":
                self.stats["fail"] += 1
            elif result == "stopped":
                break

            if idx < total - 1 and not self._stop_event.is_set():
                sleep_time = random.uniform(self.delay_min, self.delay_max)
                self._log(f"⏳ Nghỉ anti-bot {sleep_time:.1f} giây trước nhóm tiếp theo...", "info")
                self._countdown_sleep(sleep_time)

    # ------------------------------------------------------------------ run
    def run(self):
        if not PLAYWRIGHT_AVAILABLE:
            self._log("Chưa cài Playwright. Chạy: pip install playwright && playwright install chromium", "error")
            self._finish()
            return

        if self.queue.empty():
            self._finish()
            return

        self._log("🚀 Mở DUY NHẤT 1 trình duyệt để xử lý hàng đợi Auto Share...", "info")

        browser = None   # chỉ dùng khi chạy phiên tạm (không có Profile)
        context = None
        processed = 0
        try:
            with sync_playwright() as p:
                user_data = self.profile_path if self.profile_path and os.path.exists(self.profile_path) else None
                coccoc_path = self.coccoc_exe if self.coccoc_exe and os.path.exists(self.coccoc_exe) else None

                if self.profile_path and not user_data:
                    self._log(f"⚠️ Không thấy thư mục Profile: {self.profile_path} -> dùng phiên tạm.", "warning")
                if coccoc_path:
                    self._log(f"Dùng Cốc Cốc: {coccoc_path}", "info")
                else:
                    self._log("Không thấy Cốc Cốc, dùng Chromium mặc định của Playwright.", "warning")

                if user_data:
                    self._cleanup_stale_browser_profile()
                    kwargs = dict(
                        user_data_dir=user_data,
                        headless=False,
                        no_viewport=True,
                        args=["--disable-notifications", "--start-maximized"],
                    )
                    if coccoc_path:
                        kwargs["executable_path"] = coccoc_path
                    context = p.chromium.launch_persistent_context(**kwargs)
                    page = context.pages[0] if context.pages else context.new_page()
                else:
                    kwargs = dict(headless=False, args=["--disable-notifications"])
                    if coccoc_path:
                        kwargs["executable_path"] = coccoc_path
                    browser = p.chromium.launch(**kwargs)
                    context = browser.new_context(no_viewport=True)
                    page = context.new_page()

                self._grant_clipboard_permissions(context)

                last_activity = time.time()
                while not self._stop_event.is_set():
                    try:
                        post_content = self.queue.get(timeout=self.POLL_INTERVAL)
                    except queue.Empty:
                        if time.time() - last_activity >= self.IDLE_CLOSE_TIMEOUT:
                            # Chốt đóng dưới lock: nếu GUI vừa enqueue kịp thì tiếp tục
                            with self._lock:
                                if self.queue.empty():
                                    self._closed = True
                                    break
                            continue
                        continue

                    processed += 1
                    self.progress_signal.emit(
                        f"Đang xử lý bài #{processed} (còn {self.queue.qsize()} bài chờ)..."
                    )
                    try:
                        self._share_one_post(page, post_content)
                    finally:
                        self.queue.task_done()
                    last_activity = time.time()

                if self._stop_event.is_set():
                    self._log("Đã dừng Auto Share theo yêu cầu.", "warning")
                    self.progress_signal.emit("Đã dừng Auto Share theo yêu cầu.")
                elif processed:
                    s = self.stats
                    self._log(f"🎉 Xong {processed} bài | thành công: {s['ok']}, "
                              f"bỏ qua: {s['skipped']}, lỗi: {s['fail']}", "success")
                    self.progress_signal.emit(f"🎉 Hoàn tất {processed} bài trong hàng đợi.")
        except Exception as e:
            self._log(f"Lỗi trình duyệt: {e}", "error")
        finally:
            with self._lock:
                self._closed = True
            for closable in (context, browser):
                if closable is not None:
                    try:
                        closable.close()
                    except Exception:
                        pass
            self._finish()

    def _finish(self):
        with self._lock:
            self._closed = True
        self.finished_signal.emit()

# ==========================================================================
# Signals Bridge
# ==========================================================================
class Signals(QObject):
    log_sig = pyqtSignal(str, str)
    # Truyen CA DANH SACH noi dung bai cua 1 dot dang bai (khong phai tung bai
    # rieng le), de dua het vao MOT hang doi xu ly tuan tu ben duoi.
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
    # Bao 1 luot tra loi tu dong vua thuc hien -> do len Bang dieu khien
    reply_event_sig = pyqtSignal(dict)
    # Bao tien do dang bai / share: (buoc_hien_tai, tong_so_buoc, nhan_text).
    # Neu tong_so_buoc <= 0 nghia la khong xac dinh so buoc cu the (vd:
    # dang dem nguoc thoi gian nghi) -> GUI se hien progress bar dang
    # "busy" (khong xac dinh %) va chi cap nhat nhan text.
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
# Main App Window
# ==========================================================================
class FBAutoPosterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.saved_pages = self.config_data.get("pages") or []

        self.running = False
        self.worker_thread = None
        self.share_workers = []
        # Worker Auto Share (Coc Coc) dang chay hien tai, neu co - dam bao
        # tai moi thoi diem CHI CO 1 instance trinh duyet duoc mo.
        self._active_share_worker = None
        # Cac dot bai moi den dung luc worker cu da chot dong (enqueue() tra
        # ve False) - cho worker cu ket thuc roi mo worker moi xu ly tiep.
        self._pending_share_batches = []
        self.stop_event = threading.Event()
        self.last_posted_index_per_page = {}
        self.last_media_path_per_page = {}
        self.next_post_at = None
        # Danh dau da tu dong lam moi Access Token cho chu ky nghi hien tai
        # hay chua (tranh goi lap lai moi giay khi con <= 1 phut).
        self._token_refresh_done_for_cycle = True

        # Snapshot cau hinh doc tu GUI thread, dung cho cac thread phu
        # (Qt KHONG cho phep doc/ghi widget ngoai GUI thread)
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

        # --- Trung tam kich ban 5 khu vuc ---
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

        # MO KHOA giao dien ngay khi ung dung khoi dong xong: dam bao nut
        # "Bat dau" luon o trang thai san sang bam (Enabled) va nut "Dung"
        # o trang thai Disabled, tranh truong hop bi ket giao dien tu lan
        # chay/crash truoc do sot lai (vd: config cu bi luu sai trang thai).
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

        # Sidebar Navigation
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
            b = QPushButton(f"  {icon}  {name}")
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

        # Main Page Stack
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

        # ==============================================================
        # CARD 1: Webhook nhận sự kiện
        # ==============================================================
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

        # ==============================================================
        # CARD 2: KHU VỰC TỔNG THỂ - Bảng điều khiển trung tâm
        # ==============================================================
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

        # ==============================================================
        # CARD 3: 5 KHU VỰC CON (QTabWidget)
        # ==============================================================
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

    # ==================================================================
    # Dựng Tab con cho từng Khu Vực
    # ==================================================================
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
        """Tab kịch bản chung (dùng khi không khớp khu vực nào)."""
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

    # ==================================================================
    # Thao tác bảng Khu Vực
    # ==================================================================
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
        """Dong bo cac cong tac tu GUI sang bien thuong (thread webhook doc duoc)."""
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
        """Thu nghiem Matching Engine ngay tren giao dien."""
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
        """Do 1 luot tra loi tu dong len Bang dieu khien tong the."""
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

    # ------------------------------------------------------------------
    # TAB 6: GIỚI THIỆU (Thông tin Bản quyền & Kênh Liên Hệ MaeAry)
    # ------------------------------------------------------------------
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

    # ==================================================================
    # Xử lý Logic Bảng Kịch bản
    # ==================================================================
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
        """Đọc toàn bộ giao diện (5 khu vực + kịch bản chung) và ghi vào config."""
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

    # ==================================================================
    # Xử lý OAuth Facebook
    # ==================================================================
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

    # ==================================================================
    # Xử lý Webhook Server (Trả lời tự động)
    # ==================================================================
    def _snapshot_run_config(self):
        """Doc TAT CA gia tri widget mot lan tai GUI thread.

        Moi thread phu chi duoc dung ban snapshot nay, khong cham vao widget.
        """
        try:
            d_min = float(self.share_delay_min_edit.text().strip() or 15)
            d_max = float(self.share_delay_max_edit.text().strip() or 30)
        except ValueError:
            d_min, d_max = 15.0, 30.0
        if d_max < d_min:
            d_min, d_max = d_max, d_min
        share_cfg = load_config()

        self.run_cfg = {
            "posts": [box.toPlainText().strip() for box in self.post_boxes],
            "use_media": bool(self.use_media_check.isChecked()),
            "media_folder": self.media_folder_edit.text().strip(),
            "auto_share": bool(self.auto_share_check.isChecked()),
            "group_list": self.group_list_edit.toPlainText().strip(),
            "profile_path": self.profile_path_edit.text().strip(),
            "share_delay_min": d_min,
            "share_delay_max": d_max,
            # Tham so Playwright doc tu fb_autopost_config.json (khong co widget rieng)
            "coccoc_exe": str(share_cfg.get("share_coccoc_exe") or "").strip(),
            "dry_run": bool(share_cfg.get("share_dry_run", False)),
            "kill_all_browsers": bool(share_cfg.get("share_kill_all_browsers", True)),
        }
        return self.run_cfg

    def _refresh_token_cache(self):
        """Cache token theo page_id de webhook thread khong phai doc widget."""
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
        """MATCHING ENGINE TỔNG THỂ.

        Thứ tự ưu tiên:
          1) Duyệt toàn bộ từ khóa của 5 khu vực -> lấy khu vực khớp nhất.
          2) Nếu không khớp khu vực nào -> kịch bản chung (tin nhắn/bình luận).
          3) Nếu vẫn trống -> câu trả lời mặc định tổng thể.

        Trả về (reply, region_name).
        """
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

    # ==================================================================
    # Thực thi Đăng Bài & Share Group
    # ==================================================================
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

    def _do_post_all(self, targets, posts, run_cfg=None):
        run_cfg = run_cfg or self.run_cfg
        success_count = 0
        posted_messages = []  # noi dung bai da dang Fanpage thanh cong (de dan vao Group)
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
            # Chon theo CHI SO, khong dung posts.index() vi bai trung noi dung
            # se luon tra ve vi tri dau tien -> logic tranh lap chay sai.
            chosen_idx = random.choice(indices)
            message = posts[chosen_idx]
            self.last_posted_index_per_page[page_id] = chosen_idx

            media_path, media_type = self._select_media(
                run_cfg, exclude_path=self.last_media_path_per_page.get(page_id)
            )
            if media_path:
                self.last_media_path_per_page[page_id] = media_path

            ok, _post_id = self._do_post_one(page_id, t["access_token"], t["name"], message, media_path, media_type)
            if ok:
                success_count += 1
                # Auto Share se DAN NGUYEN NOI DUNG bai nay (khong gõ link) vao Group.
                # Bo trung de nhieu Page dang cung 1 bai khong bi dan lap nhieu lan.
                if message and message not in posted_messages:
                    posted_messages.append(message)

        self.log(f"Hoàn tất lượt đăng: {success_count}/{len(targets)} Page thành công.", "info")
        self.sig.progress_sig.emit(
            total, total, f"Hoàn tất lượt đăng: {success_count}/{total} Page thành công."
        )

        if posted_messages and run_cfg.get("auto_share"):
            # QThread phai duoc tao/khoi dong tu GUI thread -> di qua signal.
            # Gui CA DANH SACH noi dung 1 lan (khong emit tung bai rieng) de gom
            # vao MOT hang doi xu ly tuan tu, tranh mo nhieu instance Coc Coc.
            self.sig.share_request_sig.emit(posted_messages, dict(run_cfg))

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

    def _start_share_worker(self, post_contents, run_cfg):
        """Nhận danh sách NỘI DUNG bài viết (đã soạn sẵn) và đưa vào hàng đợi Auto Share.

        - Nếu đã có 1 ShareQueueWorker đang chạy và còn nhận bài: chỉ `enqueue()`
          thêm nội dung vào hàng đợi của worker đó (chỉ 1 trình duyệt hoạt động).
        - Nếu worker đó đã chốt đóng (`enqueue()` trả về False): xếp bài vào
          danh sách chờ, đợi worker cũ đóng xong rồi mới mở worker mới
          (không bao giờ có 2 instance chạy cùng lúc, không mất bài).
        - Nếu chưa có worker nào: tạo 1 worker mới cho cả danh sách.
        """
        if not post_contents:
            return

        active = self._active_share_worker
        if active is not None and active.isRunning():
            if active.enqueue(post_contents):
                self.log(
                    f"Đã thêm {len(post_contents)} bài quảng cáo vào hàng đợi Auto Share đang xử lý.",
                    "info",
                )
            else:
                self._pending_share_batches.append((list(post_contents), dict(run_cfg)))
                self.log(
                    f"Worker Auto Share cũ đang đóng trình duyệt - {len(post_contents)} bài mới "
                    "sẽ được xử lý ngay khi nó đóng xong.",
                    "info",
                )
            return

        worker = ShareQueueWorker(
            post_contents=post_contents,
            group_list=run_cfg.get("group_list", ""),
            profile_path=run_cfg.get("profile_path", ""),
            delay_min=run_cfg.get("share_delay_min", 15.0),
            delay_max=run_cfg.get("share_delay_max", 30.0),
            coccoc_exe=run_cfg.get("coccoc_exe") or None,
            dry_run=bool(run_cfg.get("dry_run", False)),
            kill_all_browsers=bool(run_cfg.get("kill_all_browsers", True)),
        )
        if worker.dry_run:
            self.log("🧪 Auto Share đang ở chế độ DRY-RUN: chỉ dán nội dung, sẽ KHÔNG bấm nút Đăng trong Group.", "warning")
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

        # Còn bài đang chờ vì worker cũ đã đóng -> mở worker mới xử lý gộp.
        if self._pending_share_batches and self._active_share_worker is None:
            batches = self._pending_share_batches
            self._pending_share_batches = []
            contents = []
            for batch_contents, _cfg in batches:
                contents.extend(batch_contents)
            self._start_share_worker(contents, batches[-1][1])

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
        # Ep GUI ve ngay lap tuc de log khong bi "don" lai thanh 1 cuc khi
        # nhieu dong log ban ra lien tiep trong thoi gian rat ngan.
        QApplication.processEvents()

    def _on_progress(self, current, total, text):
        """Nhan tien do tu ca 2 nguon: dang bai Fanpage (_do_post_all) va
        Auto Share Group (ShareQueueWorker.progress_signal, gom vao day
        qua share_progress -> progress_sig voi total<=0)."""
        if total > 0:
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(max(0, min(current, total)))
        else:
            # Khong ro tong so buoc (vd: dang dem nguoc thoi gian nghi) ->
            # hien thanh "busy" indeterminate, chi text la co nghia.
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
        return [box.toPlainText().strip() for box in self.post_boxes]

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

        # Phan hoi visual NGAY LAP TUC khi bam nut, truoc khi tac vu nen
        # (mang, IO) bat dau chay trong thread phu.
        self.test_post_btn.setEnabled(False)
        self.test_post_btn.setText("📨 Đang đăng thử...")
        self.log("📨 Đã bắt đầu đăng thử 1 bài...", "info")
        QApplication.processEvents()

        def _run_and_restore():
            try:
                self._do_post_all(targets, posts, run_cfg)
            finally:
                # Cap nhat widget GUI (nut) phai qua signal vi day la thread phu,
                # tuyet doi khong goi truc tiep phuong thuc GUI tu day.
                self.sig.test_post_finished_sig.emit()

        threading.Thread(target=_run_and_restore, daemon=True).start()

    def start(self):
        if self.running:
            return
        # Neu luong worker truoc van con dang thoat dot ngot (vua bam Dung
        # xong, GUI da mo khoa nhung thread nen chua kip ket thuc han) thi
        # bao nguoi dung cho 1 chut thay vi cho chay 2 vong lap song song.
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

        # Validate so truoc khi chay: truoc day float("abc") nem ValueError
        # ngay tren GUI thread va lam sap app.
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
        # Phat tin hieu NGAY LAP TUC (cung GUI thread -> ket noi truc tiep,
        # xu ly dong bo) de doi nhan Trang thai + khoa/mo nut TRUOC KHI
        # thread nen thuc su bat dau chay - dam bao nguoi dung luon thay
        # phan hoi tuc thi khi bam nut, du tac vu ben duoi co the mat vai
        # giay de khoi chay (vd: doc file, mo ket noi mang).
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
                    # BAT moi ngoai le xay ra trong 1 dot dang bai de luong
                    # nen KHONG BAO GIO "chet lang" - neu khong bat, thread
                    # se ket thuc dot ngot ma khong emit running_state_sig(False),
                    # khien nut "Bat dau" bi khoa vinh vien.
                    self.log(f"Lỗi không mong muốn trong tiến trình đăng bài: {e}", "error")

                actual_interval = max(0.1, interval_minutes + random.uniform(-jitter_minutes, jitter_minutes)) if jitter_minutes else interval_minutes
                interval_seconds = actual_interval * 60
                self.next_post_at = time.time() + interval_seconds
                # Reset co danh dau cho chu ky nghi MOI: cho phep _tick_countdown()
                # tu dong goi lai _auto_refresh_tokens() khi con 1 phut cuoi cua
                # CHU KY NAY (thay vi chi goi 1 lan duy nhat cho toan bo tien trinh).
                self._token_refresh_done_for_cycle = False
                # Cho theo moc thoi gian thay vi dem 1 giay/lan: dung ngay khi
                # bam Stop, khong tre toi 1 giay va khong bi troi nhip.
                self.stop_event.wait(interval_seconds)
        except Exception as e:
            # Luoi an toan cuoi cung: bat ca cac loi khong luong truoc duoc
            # (vd: loi ngay tai buoc tinh interval) de van roi vao finally.
            self.log(f"Lỗi nghiêm trọng trong tiến trình nền: {e}", "error")
        finally:
            # LUON thuc thi (thanh cong, loi, hay break) de dam bao nut "Bat
            # dau" luon duoc phuc hoi ve Enabled, khong bao gio bi ket giao dien.
            self.next_post_at = None
            self.sig.running_state_sig.emit(False)

    def stop(self):
        # Phan hoi VISUAL NGAY LAP TUC ngay khi bam nut, truoc bat ky thao
        # tac nao khac ben duoi (dat co dung, ngat worker...).
        self.stop_btn.setEnabled(False)
        self._set_status_visual("Đang dừng", "statusStopping")
        self.log("⏹ Đã phát lệnh dừng tiến trình...", "warning")
        QApplication.processEvents()

        self.stop_event.set()
        self._pending_share_batches.clear()
        # Ngat NGAY luong Worker Auto Share (Coc Coc) dang chay, khong doi
        # no xu ly het phan con lai trong hang doi.
        active = self._active_share_worker
        if active is not None:
            try:
                active.request_stop()
            except Exception:
                pass
        # Phuc hoi GIAO DIEN NGAY LAP TUC: chuyen nut "Bat dau" ve Enabled va
        # "Dung" ve Disabled ma khong doi luong nen thoat han, de nguoi dung
        # khong bi ket va co the kich hoat lai dot chay moi (start() se tu
        # kiem tra worker_thread con song hay khong truoc khi cho chay tiep).
        self.sig.running_state_sig.emit(False)

    def _tick_countdown(self):
        if not self.running or self.next_post_at is None:
            return
        remaining = int(self.next_post_at - time.time())
        if remaining <= 0:
            self.countdown_label.setText("Đang đăng bài...")
            self.countdown_label_big.setText("Đang đăng bài...")
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            text = f"Bài tiếp theo sau: {mins:02d}:{secs:02d}"
            self.countdown_label.setText(text)
            self.countdown_label_big.setText(text)

            # Con dung 1 phut cuoi cung truoc khi dot tac vu (dang bai) moi
            # bat dau -> tu dong lam moi Access Token cua Fanpage truoc,
            # dam bao token con hieu luc khi dot dang bai ke tiep chay.
            if remaining <= 60 and not self._token_refresh_done_for_cycle:
                self._token_refresh_done_for_cycle = True
                self.log(
                    "⏰ Còn 1 phút nữa đến đợt tác vụ mới, tự động làm mới Access Token...",
                    "info",
                )
                self._auto_refresh_tokens()

    def _set_status_visual(self, text, obj_name):
        """Cap nhat dong thoi ca 2 nhan Trang thai (thanh dieu huong +
        trang Tong quan) va bat Qt re-polish stylesheet ngay lap tuc, roi
        ep GUI ve de nguoi dung thay thay doi tuc thi thay vi doi den
        vong lap su kien tiep theo."""
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
        """Do danh sach Fanpage dang duoc quan ly vao Bang dieu khien tong the."""
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
        # Dong sach: dung vong lap dang, tat webhook, cho cac thread ket thuc.
        self.stop_event.set()
        self._pending_share_batches.clear()
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
                # Cho toi 35s de worker thoat sau buoc sleep/step hien tai
                # (che do nghi anti-bot toi da co the toi ~30s).
                if not worker.wait(35000):
                    worker.terminate()
                    worker.wait(2000)
            except Exception:
                pass
        self.share_workers.clear()

        event.accept()

# ==========================================================================
# Main Entrypoint (GUI)
# ==========================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(CSS)
    w = FBAutoPosterApp()
    w.show()
    sys.exit(app.exec())


# ==========================================================================
# TEST LOCAL ShareQueueWorker qua CLI (không mở GUI):  python TOID.py --cli
# ==========================================================================
# >>> SỬA NỘI DUNG MẪU NÀY, HOẶC TRUYỀN QUA --content / --content-file <<<
TEST_POST_CONTENT = (
    "🚗 XE GHÉP HẠ LONG ⇄ HÀ NỘI - ĐI MỖI NGÀY 🚗\n"
    "\n"
    "✅ Đón - trả tận nơi\n"
    "✅ Xe đời mới, sạch sẽ, lái xe thân thiện\n"
    "💰 Giá cước: liên hệ để được báo giá tốt nhất\n"
    "\n"
    f"📞 Hotline / Zalo: {CONTACT_HOTLINE}\n"
    "\n"
    "#xeghep #halong #hanoi #xeghepgiare"
)
TEST_GROUPS = [
    "1234567890",                                   # ID số
    "ten-nhom-slug",                                # slug
    "https://www.facebook.com/groups/abcdef/",      # URL đầy đủ
]
TEST_PROFILE_PATH = r"C:\Users\YourName\AppData\Local\CocCoc\Browser\User Data_Share"

_CLI_COLORS = {"info": "\033[36m", "success": "\033[32m", "warning": "\033[33m", "error": "\033[31m"}
_CLI_RESET = "\033[0m"
_cli_last_was_progress = False


def _console_log(msg, level):
    global _cli_last_was_progress
    if _cli_last_was_progress:
        print()  # xuống dòng sau dòng progress dùng \r
        _cli_last_was_progress = False
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    color = _CLI_COLORS.get(level, "") if sys.stdout.isatty() else ""
    reset = _CLI_RESET if color else ""
    print(f"{color}[{ts}] [{level.upper():7}] {msg}{reset}", flush=True)


def _console_progress(msg):
    global _cli_last_was_progress
    print(f"\r    {msg:<90}", end="", flush=True)
    _cli_last_was_progress = True


def share_cli_main(argv=None):
    ap = argparse.ArgumentParser(
        prog="TOID.py --cli",
        description="Test local ShareQueueWorker (Playwright) - dán nội dung bài quảng cáo "
                    "vào các Nhóm, không mở GUI PyQt6",
    )
    ap.add_argument("--content", action="append", default=None,
                    help="NỘI DUNG bài viết đầy đủ (có thể lặp lại nhiều lần = nhiều bài). "
                         "Dùng \\n để xuống dòng, hoặc dùng --content-file cho bài dài")
    ap.add_argument("--content-file", default=None,
                    help="Đường dẫn file .txt (UTF-8) chứa nội dung bài viết nhiều dòng")
    ap.add_argument("--groups", nargs="+", default=TEST_GROUPS, help="URL / ID / slug nhóm")
    ap.add_argument("--profile", default=TEST_PROFILE_PATH, help="Thư mục user-data-dir")
    ap.add_argument("--coccoc", default=None, help="Đường dẫn browser.exe của Cốc Cốc")
    ap.add_argument("--delay-min", type=float, default=8, help="Nghỉ tối thiểu giữa các nhóm (giây)")
    ap.add_argument("--delay-max", type=float, default=15, help="Nghỉ tối đa giữa các nhóm (giây)")
    ap.add_argument("--live", action="store_true", help="ĐĂNG THẬT (mặc định là dry-run, không bấm Đăng)")
    ap.add_argument("--kill-profile-only", action="store_true",
                    help="Chỉ kill browser.exe đang dùng Profile này thay vì tất cả browser.exe")
    ap.add_argument("--enqueue-later", nargs="*", default=None,
                    help="Nội dung bài thêm vào hàng đợi SAU 10 giây để test enqueue() lúc worker đang chạy")
    args = ap.parse_args(argv)

    # Console Windows cũ (cp1252/cp1258) không in được emoji -> ép UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not PLAYWRIGHT_AVAILABLE:
        print("Chưa cài Playwright:  pip install playwright && playwright install chromium")
        sys.exit(1)

    # Gom nội dung bài viết: --content-file + --content (+ mẫu nếu không truyền gì)
    contents = []
    if args.content_file:
        try:
            with open(args.content_file, "r", encoding="utf-8") as f:
                contents.append(f.read())
        except OSError as e:
            print(f"Không đọc được --content-file: {e}")
            sys.exit(1)
    for item in (args.content or []):
        contents.append(item.replace("\\n", "\n"))
    contents = [c.strip() for c in contents if c and c.strip()]
    if not contents:
        contents = [TEST_POST_CONTENT]

    # QThread thật cần QCoreApplication; dùng DirectConnection vì CLI không chạy event loop.
    from PyQt6.QtCore import QCoreApplication
    _app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])

    _console_log(f"Chế độ: {'ĐĂNG THẬT' if args.live else 'DRY-RUN (không bấm Đăng)'} | "
                 f"{len(contents)} bài x {len(args.groups)} nhóm", "info")

    worker = ShareQueueWorker(
        post_contents=contents,
        group_list="\n".join(args.groups),
        profile_path=args.profile,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        coccoc_exe=args.coccoc,
        dry_run=not args.live,
        kill_all_browsers=not args.kill_profile_only,
    )
    direct = Qt.ConnectionType.DirectConnection
    worker.log_signal.connect(_console_log, direct)
    worker.progress_signal.connect(_console_progress, direct)
    done = threading.Event()
    worker.finished_signal.connect(done.set, direct)

    worker.start()

    if args.enqueue_later:
        later_contents = [c.replace("\\n", "\n") for c in args.enqueue_later]

        def _late():
            time.sleep(10)
            ok = worker.enqueue(later_contents)
            _console_log(f"enqueue() lúc đang chạy -> {'đã nạp thêm' if ok else 'worker đã đóng, cần tạo mới'}", "info")
        threading.Thread(target=_late, daemon=True).start()

    try:
        while not done.is_set():
            done.wait(0.5)
    except KeyboardInterrupt:
        print()
        _console_log("Ctrl+C -> yêu cầu dừng an toàn...", "warning")
        worker.request_stop()
        done.wait(60)

    worker.wait(5000)
    print()
    _console_log(f"Kết quả: {worker.stats}", "success")


if __name__ == "__main__":
    # python TOID.py          -> mở GUI PyQt6
    # python TOID.py --cli .. -> test riêng Playwright (ShareQueueWorker) qua dòng lệnh
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        share_cli_main(sys.argv[2:])
    else:
        main()
