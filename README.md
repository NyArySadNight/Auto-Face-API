# Auto-Face-API

Công cụ desktop (tkinter) đăng bài tự động lên Facebook Page (Fanpage) theo
chu kỳ thời gian tùy chỉnh — chọn ngẫu nhiên 1 trong 5 bài đã soạn sẵn, kèm
ngẫu nhiên 1 ảnh/video từ thư mục bạn chỉ định.

Dùng **Facebook Graph API chính thức** (không đăng nhập giả lập trình
duyệt), nên không vi phạm điều khoản Facebook và không có rủi ro bị khóa tài
khoản do hành vi tự động hóa giả mạo.

> Cần Page ID + Page Access Token trước khi dùng — dùng repo
> [Auto-Get-Face-Access-Token](../Auto-Get-Face-Access-Token) để lấy tự
> động, hoặc tự lấy thủ công qua Graph API Explorer.

## Tính năng

- Đăng bài lên Fanpage theo chu kỳ (phút) tự đặt.
- Soạn sẵn tối đa **5 nội dung bài viết**, mỗi lần đăng chọn ngẫu nhiên 1
  bài (tránh lặp lại bài vừa đăng ngay lần liền trước, nếu có nhiều hơn 1
  bài khả dụng).
- Tự động đính kèm 1 ảnh hoặc video **ngẫu nhiên** từ thư mục chỉ định
  (mặc định `~/Downloads/VidFaceAutoFix`) — có thể tắt nếu chỉ muốn đăng
  text.
- Hỗ trợ định dạng ảnh: `.jpg .jpeg .png .gif .bmp .webp`; video:
  `.mp4 .mov .avi .mkv .webm .m4v`.
- Nút "Đăng thử ngay 1 bài" để kiểm tra cấu hình trước khi bật chạy tự
  động.
- Nhật ký hoạt động hiển thị ngay trong app (thành công/thất bại từng lần
  đăng).

## Yêu cầu

- Python 3.9+ (tkinter thường có sẵn cùng Python; trên Ubuntu/Debian nếu
  thiếu: `sudo apt install python3-tk`)
- Thư viện:

```bash
pip install requests
```

## Chuẩn bị trước khi dùng

1. **Page ID** và **Page Access Token** của Fanpage (xem repo
   [Auto-Get-Face-Access-Token](../Auto-Get-Face-Access-Token) để lấy tự
   động và ghi thẳng vào file cấu hình dùng chung).
2. Tối đa 5 nội dung bài viết mẫu.
3. (Tùy chọn) Một thư mục chứa ảnh/video để đính kèm ngẫu nhiên.

## Chạy chương trình

```bash
python3 AutoFixFace.py
```

Trong app: nhập Page ID + Access Token (hoặc để trống nếu đã lưu sẵn từ
Auto-Get-Face-Access-Token), điền nội dung bài viết, chọn thư mục media (nếu
dùng), bấm **Lưu cấu hình**, rồi bấm **▶ Bắt đầu** để chạy vòng lặp đăng bài
tự động.

## Cấu hình

Lưu tại `fb_autopost_config.json` cùng thư mục chạy script, gồm `page_id`,
`access_token`, chu kỳ đăng (phút), danh sách bài viết, và thư mục media.

## Bảo mật

- **Access Token** lưu ở dạng plain text trong `fb_autopost_config.json` —
  **không commit file này lên Git**. Thêm vào `.gitignore`:
  ```
  fb_autopost_config.json
  ```
- Nếu token vô tình bị lộ, thu hồi ngay tại **Facebook → Cài đặt → Bảo mật →
  Ứng dụng và trang web**.

## Muốn Long-lived Page Token (không hết hạn sau 1-2 tiếng)?

Nếu tự lấy token thủ công (không dùng repo Auto-Get-Face-Access-Token), đổi
short-lived token sang long-lived bằng:

```bash
curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"
```

Sau đó dùng long-lived **user** token gọi `/me/accounts` để lấy **Page**
token — Page token lấy theo cách này thường không tự hết hạn.

## Lưu ý

- README bản gốc ghi lệnh chạy là `python3 fb_autopost.py` — tên file thật
  trong repo là **`AutoFixFace.py`**, README này đã sửa lại đúng lệnh chạy.
- Đăng bài với tần suất quá dày hoặc nội dung lặp lại nhiều có thể bị
  Facebook đánh giá là spam, ảnh hưởng phạm vi tiếp cận (reach) của Page —
  nên đặt chu kỳ hợp lý và soạn đa dạng nội dung.
