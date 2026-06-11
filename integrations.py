"""
Integrations: Welcome email (Gmail SMTP) + PayOS payment.

Configuration is read from Streamlit secrets or environment variables.
Both features degrade gracefully: if not configured, they do nothing
(or return a clear message) instead of crashing the app.

Required secrets/env for email (Gmail):
    GMAIL_ADDRESS          = "youremail@gmail.com"
    GMAIL_APP_PASSWORD     = "xxxx xxxx xxxx xxxx"   # Google App Password (NOT your login password)

Required secrets/env for PayOS:
    PAYOS_CLIENT_ID        = "..."
    PAYOS_API_KEY          = "..."
    PAYOS_CHECKSUM_KEY     = "..."
"""

import os
import smtplib
import hmac
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ─── CONFIG HELPERS ─────────────────────────────────────────────────────────────

def _get_secret(key, default=None):
    """Read from Streamlit secrets first, then environment variables."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


# ─── WELCOME EMAIL (Gmail SMTP) ──────────────────────────────────────────────────

def is_email_configured():
    return bool(_get_secret("GMAIL_ADDRESS") and _get_secret("GMAIL_APP_PASSWORD"))


def send_welcome_email(to_email, username, lang="vi"):
    """Send a welcome email via Gmail SMTP. Returns (success, message)."""
    gmail = _get_secret("GMAIL_ADDRESS")
    app_pw = _get_secret("GMAIL_APP_PASSWORD")

    if not gmail or not app_pw:
        return False, "email_not_configured"

    if lang == "vi":
        subject = "🛡️ Chào mừng đến với Investor Discipline!"
        body_html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1e293b">
  <h2 style="color:#1D4ED8">Xin chào {username}! 🛡️</h2>
  <p>Cảm ơn bạn đã đăng ký <strong>Investor Discipline</strong> — ứng dụng luyện tư duy đầu tư kỷ luật.</p>
  <p>App này <strong>không</strong> dạy bạn kiếm tiền nhanh. Nó dạy bạn <strong>sống sót lâu hơn</strong> trên thị trường.</p>
  <h3 style="color:#1D4ED8">Bắt đầu trong 3 bước:</h3>
  <ol>
    <li><strong>⚡ Daily Challenge</strong> — 1 câu hỏi mỗi ngày, chỉ 1 phút</li>
    <li><strong>📖 Bài học</strong> — nền tảng Risk First, Regime First, Evidence First</li>
    <li><strong>📜 Historical Simulator</strong> — luyện với thị trường thật (US + VN)</li>
  </ol>
  <p style="background:#EFF6FF;padding:12px 16px;border-radius:8px;border-left:4px solid #1D4ED8">
    <em>"Nhà đầu tư sống sót lâu không phải vì luôn đúng, mà vì sai nhưng không chết."</em>
  </p>
  <p>Chúc bạn luyện tập hiệu quả!</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
  <p style="font-size:12px;color:#64748b">
    Investor Discipline · Risk First · Regime First · Evidence First<br>
    © 2025 Nguyễn Thị Nguyệt Tâm
  </p>
</div>
"""
    else:
        subject = "🛡️ Welcome to Investor Discipline!"
        body_html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1e293b">
  <h2 style="color:#1D4ED8">Hello {username}! 🛡️</h2>
  <p>Thank you for joining <strong>Investor Discipline</strong> — the app that trains disciplined investing.</p>
  <p>This app does <strong>not</strong> teach you to make money fast. It teaches you to <strong>survive longer</strong> in the market.</p>
  <h3 style="color:#1D4ED8">Get started in 3 steps:</h3>
  <ol>
    <li><strong>⚡ Daily Challenge</strong> — 1 question a day, just 1 minute</li>
    <li><strong>📖 Lessons</strong> — Risk First, Regime First, Evidence First foundation</li>
    <li><strong>📜 Historical Simulator</strong> — practice with real markets (US + VN)</li>
  </ol>
  <p style="background:#EFF6FF;padding:12px 16px;border-radius:8px;border-left:4px solid #1D4ED8">
    <em>"Long-surviving investors aren't always right — they're wrong without dying."</em>
  </p>
  <p>Happy practicing!</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
  <p style="font-size:12px;color:#64748b">
    Investor Discipline · Risk First · Regime First · Evidence First<br>
    © 2025 Nguyễn Thị Nguyệt Tâm
  </p>
</div>
"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Investor Discipline <{gmail}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_pw)
            server.sendmail(gmail, to_email, msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)


# ─── ADMIN NOTIFICATION EMAIL ────────────────────────────────────────────────────

def send_admin_notification(event_type, username, email=None, extra=None):
    """Gửi email thông báo cho admin khi có sự kiện (user mới, upgrade Pro...).
    Gửi tới ADMIN_NOTIFY_EMAIL nếu có cấu hình, nếu không thì gửi về chính
    GMAIL_ADDRESS. Không bao giờ làm crash luồng chính — chỉ trả (ok, msg)."""
    gmail = _get_secret("GMAIL_ADDRESS")
    app_pw = _get_secret("GMAIL_APP_PASSWORD")
    if not gmail or not app_pw:
        return False, "email_not_configured"

    to_email = _get_secret("ADMIN_NOTIFY_EMAIL") or gmail

    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if event_type == "signup":
        subject = f"🆕 User mới đăng ký: {username}"
        title = "Có user mới đăng ký! 🎉"
        color = "#1D4ED8"
    elif event_type == "upgrade":
        subject = f"💎 Upgrade Pro: {username}"
        title = "Có user nâng cấp lên Pro! 💎"
        color = "#16a34a"
    else:
        subject = f"🔔 Thông báo: {event_type}"
        title = str(event_type)
        color = "#1D4ED8"

    rows = f"<p><strong>Username:</strong> {username}</p>"
    if email:
        rows += f"<p><strong>Email:</strong> {email}</p>"
    if extra:
        rows += f"<p><strong>Chi tiết:</strong> {extra}</p>"
    rows += f"<p><strong>Thời gian:</strong> {ts}</p>"

    body_html = f"""<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;color:#1e293b">
  <h2 style="color:{color}">{title}</h2>
  {rows}
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0">
  <p style="font-size:12px;color:#64748b">Investor Discipline — thông báo tự động</p>
</div>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Investor Discipline <{gmail}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_pw)
            server.sendmail(gmail, to_email, msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)


# ─── PAYOS PAYMENT ───────────────────────────────────────────────────────────────

def is_payos_configured():
    return bool(
        _get_secret("PAYOS_CLIENT_ID")
        and _get_secret("PAYOS_API_KEY")
        and _get_secret("PAYOS_CHECKSUM_KEY")
    )


def _payos_signature(data: dict, checksum_key: str) -> str:
    """Build PayOS HMAC-SHA256 signature from sorted key=value pairs."""
    sorted_keys = sorted(data.keys())
    sig_data = "&".join(f"{k}={data[k]}" for k in sorted_keys)
    return hmac.new(checksum_key.encode(), sig_data.encode(), hashlib.sha256).hexdigest()


def create_payos_payment_link(order_code, amount, description, return_url, cancel_url):
    """Create a PayOS payment link. Returns (success, result_dict_or_error).

    result_dict contains 'checkoutUrl' and 'qrCode' on success.
    """
    if not is_payos_configured():
        return False, "payos_not_configured"

    client_id = _get_secret("PAYOS_CLIENT_ID")
    api_key = _get_secret("PAYOS_API_KEY")
    checksum_key = _get_secret("PAYOS_CHECKSUM_KEY")

    try:
        import requests
    except ImportError:
        return False, "requests_not_installed"

    # PayOS requires description <= 25 chars
    description = (description or "")[:25]

    body = {
        "orderCode": int(order_code),
        "amount": int(amount),
        "description": description,
        "returnUrl": return_url,
        "cancelUrl": cancel_url,
    }
    # Signature uses specific fields
    sig_fields = {
        "amount": body["amount"],
        "cancelUrl": body["cancelUrl"],
        "description": body["description"],
        "orderCode": body["orderCode"],
        "returnUrl": body["returnUrl"],
    }
    body["signature"] = _payos_signature(sig_fields, checksum_key)

    headers = {
        "x-client-id": client_id,
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api-merchant.payos.vn/v2/payment-requests",
            json=body, headers=headers, timeout=15
        )
        data = resp.json()
        if data.get("code") == "00":
            return True, data["data"]
        return False, data.get("desc", "unknown_error")
    except Exception as e:
        return False, str(e)


def check_payos_payment(order_code):
    """Check status of a PayOS order. Returns (success, status_string)."""
    if not is_payos_configured():
        return False, "payos_not_configured"

    client_id = _get_secret("PAYOS_CLIENT_ID")
    api_key = _get_secret("PAYOS_API_KEY")

    try:
        import requests
    except ImportError:
        return False, "requests_not_installed"

    headers = {"x-client-id": client_id, "x-api-key": api_key}
    try:
        resp = requests.get(
            f"https://api-merchant.payos.vn/v2/payment-requests/{int(order_code)}",
            headers=headers, timeout=15
        )
        data = resp.json()
        if data.get("code") == "00":
            return True, data["data"].get("status", "PENDING")
        return False, data.get("desc", "unknown_error")
    except Exception as e:
        return False, str(e)
