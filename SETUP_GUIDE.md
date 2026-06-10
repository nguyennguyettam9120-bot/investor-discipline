# Hướng dẫn cấu hình PayOS + Welcome Email

App chạy bình thường **không cần** cấu hình gì — payment tự động và email sẽ tự tắt nếu chưa cấu hình. Khi bạn sẵn sàng bật chúng, làm theo hướng dẫn dưới.

Tất cả cấu hình đặt trong **Streamlit Secrets** (khi deploy) hoặc biến môi trường (khi chạy local).

---

## 1. Welcome Email qua Gmail (miễn phí)

Email chào mừng tự động gửi khi user đăng ký tài khoản mới.

### Bước 1 — Bật App Password cho Gmail

1. Vào tài khoản Google → **Security** (Bảo mật)
2. Bật **2-Step Verification** (Xác minh 2 bước) nếu chưa bật — bắt buộc
3. Vào **App passwords** (Mật khẩu ứng dụng): https://myaccount.google.com/apppasswords
4. Tạo app password mới, đặt tên "Investor Discipline"
5. Google cho bạn 1 chuỗi 16 ký tự dạng `xxxx xxxx xxxx xxxx` — **copy lại**

### Bước 2 — Thêm vào Secrets

```toml
GMAIL_ADDRESS = "nguyennguyettam9120@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
```

> Lưu ý: dùng **App Password 16 ký tự**, KHÔNG phải mật khẩu đăng nhập Gmail thường.

---

## 2. PayOS — Thanh toán tự động (VietQR)

PayOS cho phép user quét VietQR thanh toán và tự động lên Pro.

### Bước 1 — Đăng ký PayOS

1. Vào https://payos.vn → đăng ký tài khoản doanh nghiệp/cá nhân
2. Liên kết tài khoản ngân hàng nhận tiền
3. Tạo một **kênh thanh toán** (payment channel)
4. Lấy 3 thông tin: **Client ID**, **API Key**, **Checksum Key**

### Bước 2 — Thêm vào Secrets

```toml
PAYOS_CLIENT_ID = "..."
PAYOS_API_KEY = "..."
PAYOS_CHECKSUM_KEY = "..."
APP_URL = "https://ten-app-cua-ban.streamlit.app"
```

> `APP_URL` là link app thật của bạn — dùng để PayOS chuyển hướng user về sau khi thanh toán. Nếu chạy local thì để `http://localhost:8501`.

---

## 3. Cấu hình đầy đủ mẫu (Streamlit Secrets)

Vào app trên Streamlit Cloud → **Settings → Secrets**, dán toàn bộ:

```toml
# AI Coach + Daily Challenge tự động
ANTHROPIC_API_KEY = "sk-ant-..."

# Admin
INVESTOR_ADMIN_PASSWORD = "mat_khau_admin"

# Welcome Email
GMAIL_ADDRESS = "nguyennguyettam9120@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"

# PayOS
PAYOS_CLIENT_ID = "..."
PAYOS_API_KEY = "..."
PAYOS_CHECKSUM_KEY = "..."
APP_URL = "https://ten-app-cua-ban.streamlit.app"
```

---

## 4. Kiểm tra trạng thái

Đăng nhập bằng tài khoản **admin** → vào **Account Info** → mục "🔧 Admin" sẽ hiển thị:

- ✅/❌ Welcome Email (Gmail)
- ✅/❌ PayOS Payment

Nếu thấy ❌ nghĩa là chưa cấu hình đúng — kiểm tra lại Secrets.

---

## 5. Luồng thanh toán hoạt động thế nào

**Tự động (PayOS):**
1. User bấm "Nâng cấp Pro" → "Tạo link thanh toán"
2. App tạo mã VietQR + link checkout
3. User quét QR / bấm link → thanh toán
4. PayOS chuyển user về app với `?paid=...`
5. App tự kiểm tra → tự động lên Pro

**Thủ công (dự phòng):**
1. User chuyển khoản theo hướng dẫn, ghi nội dung `PRO_username`
2. Đơn xuất hiện trong panel admin "Đơn thanh toán đang chờ"
3. Admin bấm "✅ Xác nhận" → user lên Pro

---

## Lưu ý quan trọng về Database

Streamlit Cloud bản miễn phí **xóa database khi app restart**. Để giữ dữ liệu user và lịch sử thanh toán lâu dài, cần chuyển sang database online (Supabase miễn phí). Đây là việc nên làm sau khi test thành công.
