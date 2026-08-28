# Auto-Face-API

Công cụ desktop (tkinter) tự động đăng bài lên Fanpage Facebook theo lịch
tùy chỉnh — chọn ngẫu nhiên 1 trong các bài viết đã chuẩn bị, kèm ngẫu
nhiên 1 ảnh/video từ thư mục bạn chọn.

Dùng **Facebook Graph API chính thức** (không đăng nhập giả lập), nên
không vi phạm điều khoản Facebook và không có rủi ro khóa tài khoản vì
hành vi tự động hóa giả mạo.

> Cần có Page ID + Page Access Token trước khi dùng — dùng
> [Auto-Get-Face-Access-Token](../token-pkg) để lấy tự động (khuyến
> khích, vì 2 công cụ dùng chung 1 file cấu hình), hoặc lấy thủ công qua
> Graph API Explorer.

## Giao diện mới

Giao diện được làm lại hoàn toàn theo **tông màu xám - trắng**, chia
thành từng khối (card) rõ ràng: Kết nối Fanpage → Lịch đăng bài → Nội
dung bài viết → Điều khiển → Nhật ký. Cửa sổ có thanh cuộn nên vẫn dùng
tốt trên màn hình nhỏ.

## Tính năng mới so với bản gốc

- **Chọn Page trong danh sách xổ xuống**: nếu đã dùng
  `AutoTokenAPI.py` để lưu (một hoặc nhiều) Page, chỉ cần chọn Page
  muốn đăng — Page ID/Access Token tự điền, không cần nhập tay.
- **"Kiểm tra kết nối"**: gọi thẳng Graph API để xác nhận Access Token
  còn dùng được, hiển thị luôn tên Page đang trỏ tới.
- **Đếm số ký tự** ngay dưới mỗi ô nhập bài viết.
- **Xuất / nhập bài viết ra file `.txt`** để soạn/chỉnh sửa hàng loạt
  bên ngoài rồi nạp lại (các bài cách nhau bởi dòng `---`).
- **Đồng hồ đếm ngược** tới lần đăng kế tiếp khi đang chạy tự động.
- **Lệch giờ đăng ngẫu nhiên (±phút)**: bật tùy chọn này để lịch đăng
  không đúng y hệt mỗi X phút một cách máy móc, trông tự nhiên hơn.
- **Tự thử lại tối đa 2 lần** nếu đăng bài gặp lỗi mạng/API tạm thời,
  có nghỉ giữa các lần thử.
- **Tránh lặp lại đúng ảnh/video** vừa dùng ở lần đăng ngay trước (giống
  cách bản gốc đã tránh lặp bài viết).
- **Lịch sử đăng bài**: mỗi lần đăng (thành công hay lỗi) được ghi vào
  `post_history.log`, xem lại trực tiếp trong ứng dụng qua nút
  **"Lịch sử đăng bài"**.
- Nhật ký hoạt động có màu: xanh = thành công, đỏ = lỗi, cam = cảnh báo.

## Yêu cầu

- Python 3.9+ (tkinter thường có sẵn theo Python; trên Ubuntu/Debian nếu
  thiếu: `sudo apt install python3-tk`)
- Cài thư viện:

```bash
pip install requests
```

## Trước khi chạy

1. **Page ID** và **Page Access Token** cho Fanpage (dùng
   [Auto-Get-Face-Access-Token](../token-pkg) để lấy tự động, ghi thẳng
   vào file cấu hình dùng chung).
2. Một vài nội dung bài viết mẫu.
3. (Tùy chọn) Một thư mục chứa ảnh/video để đính kèm ngẫu nhiên.

> **Lưu ý:** 2 công cụ dùng chung file `fb_autopost_config.json` — hãy
> đặt `AutoTokenAPI.py` và `AutoFixFace.py` trong **cùng một thư mục**.

## Chạy

```bash
python3 AutoFixFace.py
```

Trong ứng dụng: chọn Page đã lưu (hoặc nhập tay Page ID + Access Token),
bấm **"Kiểm tra kết nối"** để chắc chắn Token còn hoạt động, điền nội
dung bài viết, chọn thư mục ảnh/video (nếu dùng), bấm **"Lưu cấu hình"**,
rồi **▶ Bắt đầu** để chạy vòng lặp đăng bài tự động. Có thể bấm
**"Đăng thử ngay 1 bài"** để kiểm tra trước khi chạy tự động.

## Cấu hình

Lưu trong `fb_autopost_config.json` (cùng thư mục với script, dùng
chung với `AutoTokenAPI.py`): `page_id`, `access_token`, `pages` (danh
sách Page đã lưu), khoảng thời gian đăng + độ lệch ngẫu nhiên (phút),
danh sách bài viết, thư mục media, có dùng media hay không.

Lịch sử đăng bài lưu riêng trong `post_history.log` (mỗi dòng 1 bản ghi
JSON: thời gian, kết quả, nội dung rút gọn).

## Bảo mật

- **Access Token** được lưu dạng văn bản thường trong
  `fb_autopost_config.json` — **không commit file này lên Git**. Thêm
  vào `.gitignore`:
  ```
  fb_autopost_config.json
  post_history.log
  ```
- Nếu token bị lộ, thu hồi ngay tại **Facebook → Cài đặt → Bảo mật →
  Ứng dụng và trang web**.

## Muốn Long-lived Page Token (không hết hạn sau 1-2 tiếng)?

Nếu lấy token thủ công (không qua Auto-Get-Face-Access-Token), đổi
short-lived token lấy long-lived:

```bash
curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"
```

Sau đó dùng long-lived **user** token gọi `/me/accounts` để lấy **Page**
token — Page token lấy theo cách này thường không tự hết hạn.

## Lưu ý khi dùng

- Đăng quá dày hoặc nội dung lặp lại có thể bị Facebook đánh giá là
  spam, ảnh hưởng lượt tiếp cận trang — nên đặt khoảng thời gian hợp lý,
  bật lệch giờ ngẫu nhiên, và đa dạng nội dung.
