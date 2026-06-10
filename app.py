import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from database import (
    init_db, register_user, login_user, get_user_plan, upgrade_user_plan,
    save_journal, get_journal, save_challenge, get_challenge_stats,
    save_historical, get_historical_stats, save_snapshot, get_snapshots,
    get_discipline_stats,
    is_admin, admin_get_all_users, admin_get_stats, admin_set_plan,
    admin_delete_user, admin_get_daily_signups, admin_get_activity_log,
    admin_ensure_admin_user,
    save_regime_radar, get_regime_radar_latest, get_regime_radar_history,
    save_custom_challenge, get_custom_challenge, get_recent_custom_challenges,
    record_daily_activity, get_streak, get_leaderboard,
    get_referral_code, record_referral, get_referral_stats,
    track_ai_usage, get_ai_usage,
    create_payment_order, mark_payment_paid, get_payment_status,
    get_pending_payments, get_user_email,
    save_routine, get_routine_today, get_routine_streak,
    save_feed_event, get_community_feed, get_community_stats,
    save_market_news, get_market_news_latest
)
import integrations
import anthropic
from content import (
    LESSONS, QUIZ, BIAS_EXPLANATIONS, REGIME_CASES, POST_MORTEM_CASES,
    DECISION_CHALLENGES, HISTORICAL_CASES, TAXONOMY, FREEMIUM_LIMITS,
    DAILY_CHALLENGES, LIQUIDITY_CHECKLIST
)

# ─── APP CONFIG ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Investor Discipline",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Investor Discipline App — Risk First · Regime First · Evidence First"}
)

init_db()

# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Brand accent color */
    :root { --brand: #1D4ED8; --brand-light: #EFF6FF; }

    /* Cleaner sidebar */
    [data-testid="stSidebar"] { background: #0F172A; }
    [data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    [data-testid="stSidebar"] .stSelectbox label { color: #94A3B8 !important; font-size: 12px; }
    [data-testid="stSidebar"] hr { border-color: #1E293B; }

    /* Metric cards - transparent for dark/light compatibility */
    [data-testid="stMetric"] {
        background: transparent !important;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid rgba(148,163,184,0.25);
    }
    [data-testid="stMetricLabel"] { font-size: 13px; opacity: 0.7; }
    [data-testid="stMetricValue"] { font-size: 22px; font-weight: 600; }
    [data-testid="stMetricDelta"] { font-size: 12px; }

    /* Fix white column boxes in dark mode */
    [data-testid="column"] { background: transparent !important; }
    [data-testid="stHorizontalBlock"] > div { background: transparent !important; }

    /* Remove default padding on main area */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* Better radio buttons */
    .stRadio > label { font-weight: 500; }

    /* Badge styles - works in dark mode */
    .badge-pro { background: rgba(217,119,6,0.25); color: #FCD34D; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-free { background: rgba(148,163,184,0.15); color: #94A3B8; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }

    /* Score pills */
    .score-good { color: #34D399; font-weight: 700; }
    .score-mid  { color: #FCD34D; font-weight: 700; }
    .score-bad  { color: #F87171; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ─────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "user": None,
        "lang": "vi",
        "onboarding_done": False,
        "quiz_index": {},
        "tour_step": 0,
        "tour_done": False,
        "show_share": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def t(vi, en):
    return vi if st.session_state.lang == "vi" else en

def is_pro():
    if not st.session_state.user:
        return False
    return get_user_plan(st.session_state.user["id"]) == "pro"

def gate_pro(feature_name=""):
    if not is_pro():
        st.warning(t(
            f"⭐ Tính năng này chỉ dành cho **Pro**. Nâng cấp để mở khóa toàn bộ app.",
            f"⭐ This feature requires **Pro**. Upgrade to unlock the full app."
        ))
        show_upgrade_cta()
        st.stop()

def show_upgrade_cta():
    # Social proof + urgency bar
    stats = get_community_stats()
    from datetime import datetime, timedelta
    # Create urgency: discount ends Sunday midnight
    now = datetime.now()
    days_left = 6 - now.weekday()  # days until Sunday
    if days_left <= 0: days_left = 7
    hours_left = days_left * 24 - now.hour

    col_sp1, col_sp2, col_sp3 = st.columns(3)
    col_sp1.metric(
        t("Đang hoạt động tuần này", "Active this week"),
        f"🟢 {stats['week_active']} " + t("người", "users")
    )
    col_sp2.metric(
        t("Đã là Pro", "Already Pro"),
        f"⭐ {stats['pro_count']} " + t("thành viên", "members")
    )
    col_sp3.metric(
        t("⏳ Ưu đãi còn lại", "⏳ Offer ends in"),
        f"{hours_left}h",
        t("Giá 99k, không tăng sớm", "99k price, won't increase soon"),
    )

    with st.container(border=True):
        st.markdown(t("### 🚀 Nâng cấp lên Pro", "### 🚀 Upgrade to Pro"))
        col1, col2 = st.columns([2, 1])
        with col1:
            lang = st.session_state.lang
            if lang == "vi":
                rows = [
                    ("Daily Challenge", "✅", "✅"),
                    ("Bài học (8 chủ đề)", "✅", "✅"),
                    ("Historical scenarios", "6 / 14", "✅ Tất cả 14"),
                    ("Quiz topics", "3 / 7", "✅ Tất cả 7"),
                    ("Decision challenges", "3 / 7", "✅ Tất cả 7"),
                    ("Decision journal", "20 entries", "✅ Không giới hạn"),
                    ("🤖 AI Coach", "❌", "✅ 20 lần/tháng"),
                    ("📡 Regime Radar lịch sử", "Tuần hiện tại", "✅ 12 tuần"),
                    ("📊 Portfolio Risk Checker", "❌", "✅"),
                    ("Mastery Score + Analytics", "❌", "✅"),
                    ("Behavior Diagnosis", "❌", "✅"),
                ]
                header = ("Tính năng", "Free", "⭐ Pro")
            else:
                rows = [
                    ("Daily Challenge", "✅", "✅"),
                    ("Lessons (8 topics)", "✅", "✅"),
                    ("Historical scenarios", "6 / 14", "✅ All 14"),
                    ("Quiz topics", "3 / 7", "✅ All 7"),
                    ("Decision challenges", "3 / 7", "✅ All 7"),
                    ("Decision journal", "20 entries", "✅ Unlimited"),
                    ("🤖 AI Coach", "❌", "✅ 20x/month"),
                    ("📡 Regime Radar history", "Current week", "✅ 12 weeks"),
                    ("📊 Portfolio Risk Checker", "❌", "✅"),
                    ("Mastery Score + Analytics", "❌", "✅"),
                    ("Behavior Diagnosis", "❌", "✅"),
                ]
                header = ("Feature", "Free", "⭐ Pro")
            df_cmp = pd.DataFrame(rows, columns=list(header))
            st.dataframe(df_cmp, use_container_width=True, hide_index=True)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.metric(
                t("Giá / tháng", "Price / month"), "99,000 ₫",
                t("Tiết kiệm 20% khi trả năm", "Save 20% annually")
            )
            if st.button(
                "🔓 " + t("Nâng cấp ngay", "Upgrade Now"),
                type="primary", use_container_width=True, key="upgrade_cta_btn"
            ):
                show_payment_modal()
            st.caption(t("✅ Hủy bất cứ lúc nào", "✅ Cancel anytime"))
    # Testimonials
    st.divider()
    st.markdown(t("**💬 Người dùng nói gì:**", "**💬 What users say:**"))
    testimonials_vi = [
        ("Sau 2 tuần dùng app, tôi nhận ra mình hay FOMO mua đuổi. Giờ tôi kiểm tra regime trước mỗi lệnh.", "Nhà đầu tư VN"),
        ("Historical Simulator giúp tôi hiểu COVID crash thật sự nguy hiểm thế nào. Lesson quý hơn học phí.", "Trader 3 năm kinh nghiệm"),
        ("AI Coach nói thẳng tôi đang revenge trade. Tôi không muốn nghe nhưng đó là sự thật.", "User Pro"),
    ]
    testimonials_en = [
        ("After 2 weeks I realized I was FOMO-chasing constantly. Now I check regime before every trade.", "VN investor"),
        ("The Historical Simulator showed me how dangerous the COVID crash really was. Worth more than any tuition.", "3-year trader"),
        ("AI Coach told me straight I was revenge trading. Didn't want to hear it but it was true.", "Pro user"),
    ]
    testimonials = testimonials_vi if st.session_state.lang == "vi" else testimonials_en
    for quote, author in testimonials:
        st.markdown('> *"' + quote + '"* — **' + author + '**')


def show_payment_modal():
    import random
    user = st.session_state.user
    PRICE = 99000

    # If demo user, prompt to register
    if not user or user.get("id", -1) == -1:
        st.warning(t(
            "Bạn cần đăng ký tài khoản trước khi nâng cấp Pro.",
            "You need to register an account before upgrading to Pro."
        ))
        return

    tab_auto, tab_manual = st.tabs([
        t("💳 Thanh toán tự động (PayOS)", "💳 Auto payment (PayOS)"),
        t("🏦 Chuyển khoản thủ công", "🏦 Manual bank transfer"),
    ])

    with tab_auto:
        if integrations.is_payos_configured():
            st.markdown(t(
                f"Nâng cấp **Pro** — **{PRICE:,} ₫/tháng**. Thanh toán qua VietQR/ngân hàng, tự động kích hoạt.",
                f"Upgrade to **Pro** — **{PRICE:,} ₫/month**. Pay via VietQR/bank, auto-activated."
            ))
            if st.button(t("🔗 Tạo link thanh toán", "🔗 Create payment link"), type="primary", key="payos_create"):
                order_code = int(f"{user['id']}{random.randint(1000,9999)}")
                base_url = _get_secret_safe("APP_URL", "https://your-app.streamlit.app")
                with st.spinner(t("Đang tạo link...", "Creating link...")):
                    ok, result = integrations.create_payos_payment_link(
                        order_code=order_code,
                        amount=PRICE,
                        description=f"PRO {user['username']}"[:25],
                        return_url=f"{base_url}?paid={order_code}",
                        cancel_url=f"{base_url}?cancel={order_code}",
                    )
                if ok:
                    create_payment_order(user["id"], order_code, PRICE, "pro", "payos")
                    st.success(t("✅ Link đã tạo! Quét QR hoặc bấm link bên dưới.", "✅ Link created! Scan QR or click below."))
                    if result.get("qrCode"):
                        st.code(result["qrCode"], language=None)
                        st.caption(t("Mã VietQR — mở app ngân hàng và quét.", "VietQR code — open your banking app and scan."))
                    if result.get("checkoutUrl"):
                        st.link_button(t("➡️ Mở trang thanh toán", "➡️ Open payment page"), result["checkoutUrl"], use_container_width=True)
                    st.session_state["pending_order"] = order_code
                    st.info(t(
                        "Sau khi thanh toán xong, bấm nút bên dưới để kiểm tra.",
                        "After paying, click the button below to verify."
                    ))
                else:
                    st.error(t(f"Lỗi tạo link: {result}", f"Link creation error: {result}"))

            # Verify payment
            if st.session_state.get("pending_order"):
                if st.button(t("🔄 Tôi đã thanh toán — Kiểm tra", "🔄 I've paid — Verify"), key="payos_verify"):
                    oc = st.session_state["pending_order"]
                    with st.spinner(t("Đang kiểm tra...", "Checking...")):
                        ok, status = integrations.check_payos_payment(oc)
                    if ok and status == "PAID":
                        mark_payment_paid(oc)
                        st.session_state.user["plan"] = "pro"
                        del st.session_state["pending_order"]
                        st.success(t("🎉 Thanh toán thành công! Bạn đã là Pro.", "🎉 Payment successful! You're now Pro."))
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning(t(f"Chưa nhận được thanh toán (trạng thái: {status}). Thử lại sau giây lát.", f"Payment not received yet (status: {status}). Try again shortly."))
        else:
            st.info(t(
                "💳 Thanh toán tự động chưa được kích hoạt. Vui lòng dùng chuyển khoản thủ công ở tab bên cạnh.",
                "💳 Auto payment not yet configured. Please use manual bank transfer in the next tab."
            ))

    with tab_manual:
        st.info(t(
            f"""
**Hướng dẫn thanh toán thủ công:**

Chuyển khoản ngân hàng — **{PRICE:,} ₫/tháng**:
- **Ngân hàng:** MB Bank
- **Số TK:** 1234567890
- **Chủ TK:** NGUYEN THI NGUYET TAM
- **Nội dung CK:** `PRO_{user['username']}`

Sau khi chuyển khoản, liên hệ để kích hoạt:
📧 **nguyennguyettam9120@gmail.com**
📱 **0943 620 253**

Tài khoản sẽ được kích hoạt trong vòng 24h.
            """,
            f"""
**Manual payment instructions:**

Bank transfer — **{PRICE:,} ₫/month**:
- **Bank:** MB Bank
- **Account:** 1234567890
- **Name:** NGUYEN THI NGUYET TAM
- **Reference:** `PRO_{user['username']}`

After transfer, contact us to activate:
📧 **nguyennguyettam9120@gmail.com**
📱 **+84 943 620 253**

Your account will be activated within 24h.
            """
        ))


def _get_secret_safe(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    import os
    return os.environ.get(key, default)


def score_color(s, max_s=3):
    pct = s / max_s
    if pct >= 0.8: return "🟢"
    if pct >= 0.5: return "🟡"
    return "🔴"

def accuracy_badge(acc):
    if acc >= 70: return f"🟢 {acc:.0f}%"
    if acc >= 50: return f"🟡 {acc:.0f}%"
    return f"🔴 {acc:.0f}%"

# ─── AUTH PAGES ────────────────────────────────────────────────────────────────

def page_auth():
    st.title("🛡️ Investor Discipline")
    st.caption(t(
        "Luyện tư duy đầu tư: Risk First · Regime First · Evidence First",
        "Train your investment mindset: Risk First · Regime First · Evidence First"
    ))

    # Language toggle
    lang_choice = st.selectbox(t("Ngôn ngữ", "Language"), ["Tiếng Việt", "English"], key="lang_selector_auth")
    st.session_state.lang = "vi" if lang_choice == "Tiếng Việt" else "en"

    st.divider()

    tab_login, tab_register, tab_demo = st.tabs([
        t("Đăng nhập", "Sign in"),
        t("Đăng ký", "Sign up"),
        t("Demo không cần tài khoản", "Try without account"),
    ])

    with tab_login:
        with st.form("login_form"):
            ue = st.text_input(t("Tên đăng ký hoặc email", "Username or email"))
            pw = st.text_input(t("Mật khẩu", "Password"), type="password")
            submitted = st.form_submit_button(t("Đăng nhập", "Sign in"), type="primary", use_container_width=True)
            if submitted:
                if not ue or not pw:
                    st.error(t("Vui lòng điền đầy đủ.", "Please fill in all fields."))
                else:
                    user, code = login_user(ue, pw)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    elif code == "not_found":
                        st.error(t("Tài khoản không tồn tại.", "Account not found."))
                    else:
                        st.error(t("Sai mật khẩu.", "Wrong password."))

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input(t("Tên đăng ký", "Username"), placeholder="vd: nguyen_tam")
            new_email = st.text_input("Email", placeholder="email@example.com")
            new_pw = st.text_input(t("Mật khẩu (ít nhất 6 ký tự)", "Password (at least 6 chars)"), type="password")
            new_pw2 = st.text_input(t("Xác nhận mật khẩu", "Confirm password"), type="password")
            submitted2 = st.form_submit_button(t("Tạo tài khoản", "Create account"), type="primary", use_container_width=True)
            if submitted2:
                if not new_user or not new_email or not new_pw:
                    st.error(t("Vui lòng điền đầy đủ.", "Please fill in all fields."))
                elif len(new_pw) < 6:
                    st.error(t("Mật khẩu tối thiểu 6 ký tự.", "Password must be at least 6 characters."))
                elif new_pw != new_pw2:
                    st.error(t("Mật khẩu không khớp.", "Passwords do not match."))
                elif "@" not in new_email:
                    st.error(t("Email không hợp lệ.", "Invalid email."))
                else:
                    ok, code = register_user(new_user, new_email, new_pw)
                    if ok:
                        # Send welcome email (silent fail if not configured)
                        try:
                            if integrations.is_email_configured():
                                integrations.send_welcome_email(new_email.strip().lower(), new_user, st.session_state.lang)
                        except Exception:
                            pass
                        st.success(t("Tạo tài khoản thành công! Hãy đăng nhập.", "Account created! Please sign in."))
                    elif code == "username_taken":
                        st.error(t("Tên đăng ký đã tồn tại.", "Username already taken."))
                    elif code == "email_taken":
                        st.error(t("Email đã được dùng.", "Email already in use."))
                    else:
                        st.error(t("Lỗi. Thử lại.", "Error. Please try again."))

    with tab_demo:
        st.info(t(
            """Chế độ demo — dùng thử **không cần đăng ký**:
\n- 6 historical market scenarios
\n- 3 investment challenges
\n- 3 quiz topics · 20 journal entries
\n- Dữ liệu không được lưu lại.""",
            """Demo mode — try **without registering**:
\n- 6 historical market scenarios
\n- 3 investment challenges
\n- 3 quiz topics · 20 journal entries
\n- Data is not saved."""
        ))
        if st.button(t("🚀 Vào Demo", "🚀 Enter Demo"), type="primary", use_container_width=True):
            st.session_state.user = {
                "id": -1,
                "username": "demo",
                "email": "demo@demo.com",
                "plan": "free",
            }
            st.rerun()

    st.divider()
    st.markdown("""
<div style="text-align:center; padding: 1rem 0 0.5rem; border-top: 1px solid rgba(148,163,184,0.15); margin-top: 1rem;">
    <p style="color:#64748B; font-size:12px; margin:0">
        © 2025 <strong>Nguyễn Thị Nguyệt Tâm</strong>. All rights reserved.
    </p>
    <p style="color:#475569; font-size:11px; margin:4px 0 0">
        Investor Discipline App · Bảo hộ theo Luật Sở hữu trí tuệ Việt Nam
    </p>
    <p style="color:#475569; font-size:11px; margin:4px 0 0">
        📧 nguyennguyettam9120@gmail.com &nbsp;·&nbsp; 📱 +84 943 620 253
    </p>
</div>
""", unsafe_allow_html=True)


# ─── ONBOARDING ────────────────────────────────────────────────────────────────

def page_onboarding():
    user = st.session_state.user
    step = st.session_state.get("tour_step", 0)

    # Custom CSS for tour
    st.markdown("""
<style>
.tour-card { background: linear-gradient(135deg,#1e3a5f 0%,#0F172A 100%);
    border-radius:16px; padding:2rem; text-align:center; margin:1rem 0; }
.tour-step { background:rgba(29,78,216,0.12); border-radius:10px;
    padding:1rem 1.25rem; margin:0.5rem 0; border-left:3px solid #3B82F6; }
.tour-progress { display:flex; justify-content:center; gap:8px; margin:1rem 0; }
.tour-dot { width:10px; height:10px; border-radius:50%; background:#1E293B; }
.tour-dot-active { background:#3B82F6; }
.tour-dot-done { background:#059669; }
</style>
""", unsafe_allow_html=True)

    STEPS = [
        {
            "icon": "🛡️",
            "title_vi": f"Chào mừng, {user['username']}!",
            "title_en": f"Welcome, {user['username']}!",
            "body_vi": """App này **không** dạy bạn kiếm tiền nhanh.

Nó dạy bạn **sống sót lâu hơn** — bằng cách tránh những sai lầm nghiêm trọng nhất:

- 🚫 All-in vào 1 cổ phiếu
- 🚫 FOMO mua đỉnh
- 🚫 Không có stop-loss
- 🚫 Giao dịch khi thị trường xấu""",
            "body_en": """This app **doesn't** teach you to make money fast.

It teaches you to **survive longer** — by avoiding the most critical mistakes:

- 🚫 Going all-in on one stock
- 🚫 FOMO buying at the top
- 🚫 Trading without a stop-loss
- 🚫 Trading in a bad market""",
            "cta_vi": "Tiếp theo →",
            "cta_en": "Next →",
        },
        {
            "icon": "📡",
            "title_vi": "4 nguyên tắc cốt lõi",
            "title_en": "4 Core Principles",
            "body_vi": """| | Nguyên tắc | Ý nghĩa |
|---|---|---|
| 🛡️ | Risk First | Hỏi "nếu sai mất bao nhiêu?" trước tiên |
| 📡 | Regime First | Thị trường không phải lúc nào cũng đáng tham gia |
| 🔬 | Evidence First | Chỉ hành động khi có đủ bằng chứng |
| ⚖️ | Governance | Lớp kiểm soát cuối — ngăn FOMO và oversizing |""",
            "body_en": """| | Principle | Meaning |
|---|---|---|
| 🛡️ | Risk First | Ask "how much do I lose if wrong?" first |
| 📡 | Regime First | The market is not always worth participating in |
| 🔬 | Evidence First | Only act when evidence is sufficient |
| ⚖️ | Governance | Final control layer — prevents FOMO and oversizing |""",
            "cta_vi": "Tiếp theo →",
            "cta_en": "Next →",
        },
        {
            "icon": "🗺️",
            "title_vi": "Lộ trình học đề xuất",
            "title_en": "Recommended Learning Path",
            "body_vi": """Làm theo thứ tự này để tiến bộ nhanh nhất:

**Bước 1 — Mỗi ngày:** ⚡ Daily Challenge (1 phút)

**Bước 2 — Tuần đầu:**
- 📖 Đọc 8 Bài học
- 📝 Quiz để kiểm tra hiểu bài

**Bước 3 — Thực hành:**
- 📜 Historical Simulator — luyện với thị trường thật
- 🎯 Investment Challenge — luyện quy trình đầy đủ

**Bước 4 — Pro features:**
- 🤖 AI Coach — phân tích quyết định thật của bạn
- 📡 Regime Radar — theo dõi thị trường tuần này
- 📊 Portfolio Risk Checker — kiểm tra danh mục""",
            "body_en": """Follow this order for fastest progress:

**Step 1 — Daily:** ⚡ Daily Challenge (1 minute)

**Step 2 — First week:**
- 📖 Read 8 Lessons
- 📝 Quiz to test understanding

**Step 3 — Practice:**
- 📜 Historical Simulator — train with real markets
- 🎯 Investment Challenge — practice full process

**Step 4 — Pro features:**
- 🤖 AI Coach — analyze your real decisions
- 📡 Regime Radar — follow this week's market
- 📊 Portfolio Risk Checker — check your portfolio""",
            "cta_vi": "Tiếp theo →",
            "cta_en": "Next →",
        },
        {
            "icon": "🚀",
            "title_vi": "Sẵn sàng chưa?",
            "title_en": "Ready to start?",
            "body_vi": """Mục tiêu không phải giao dịch nhiều hơn.

Mục tiêu là **tránh những quyết định tệ.**

> *"Nhà đầu tư sống sót lâu không phải vì luôn đúng, mà vì sai nhưng không chết."*

⚡ Bắt đầu với **Daily Challenge** hôm nay — chỉ 1 câu hỏi, 1 phút.""",
            "body_en": """The goal is not to trade more.

The goal is to **avoid bad decisions.**

> *"Long-surviving investors aren't always right — they're wrong without dying."*

⚡ Start with today's **Daily Challenge** — just 1 question, 1 minute.""",
            "cta_vi": "🚀 Bắt đầu!",
            "cta_en": "🚀 Let's go!",
        },
    ]

    total = len(STEPS)
    s = STEPS[min(step, total - 1)]
    lang = st.session_state.lang

    # Progress dots
    dots_html = '<div class="tour-progress">'
    for i in range(total):
        if i < step:
            dots_html += '<div class="tour-dot tour-dot-done"></div>'
        elif i == step:
            dots_html += '<div class="tour-dot tour-dot-active"></div>'
        else:
            dots_html += '<div class="tour-dot"></div>'
    dots_html += '</div>'
    st.markdown(dots_html, unsafe_allow_html=True)

    # Step content
    st.markdown(f"<div style='text-align:center;font-size:48px;margin:0.5rem 0'>{s['icon']}</div>",
                unsafe_allow_html=True)
    st.title(s[f"title_{lang}"])
    st.markdown(s[f"body_{lang}"])

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if step > 0:
            if st.button(t("← Quay lại", "← Back"), key="tour_back"):
                st.session_state.tour_step = step - 1
                st.rerun()
    with col2:
        cta = s[f"cta_{lang}"]
        if st.button(f"{cta}", type="primary", use_container_width=True, key="tour_next"):
            if step < total - 1:
                st.session_state.tour_step = step + 1
                st.rerun()
            else:
                st.session_state.onboarding_done = True
                st.session_state.tour_done = True
                st.rerun()
    with col3:
        if st.button(t("Bỏ qua", "Skip"), key="tour_skip"):
            st.session_state.onboarding_done = True
            st.session_state.tour_done = True
            st.rerun()

    st.caption(f"{step + 1} / {total}")



# ─── SIDEBAR ───────────────────────────────────────────────────────────────────

def show_sidebar():
    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"
    badge = "badge-pro" if plan == "pro" else "badge-free"
    badge_text = "PRO ⭐" if plan == "pro" else "FREE"

    with st.sidebar:
        # Streak counter
        if user["id"] != -1:
            streak, longest = get_streak(user["id"])
            if streak >= 3:
                streak_emoji = "🔥" if streak >= 7 else "⚡"
                st.markdown(f"**{user['username']}** <span class='{badge}'>{badge_text}</span> {streak_emoji}**{streak}**", unsafe_allow_html=True)
            else:
                st.markdown(f"**{user['username']}** <span class='{badge}'>{badge_text}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"**{user['username']}** <span class='{badge}'>{badge_text}</span>", unsafe_allow_html=True)

        lang_choice = st.selectbox(
            t("Ngôn ngữ", "Language"),
            ["Tiếng Việt", "English"],
            index=0 if st.session_state.lang == "vi" else 1,
            key="lang_sidebar"
        )
        st.session_state.lang = "vi" if lang_choice == "Tiếng Việt" else "en"

        st.divider()

        section = st.selectbox(
            t("Nhóm", "Module"),
            [
                t("📚 Học tập", "📚 Learn"),
                t("🧪 Thực hành", "🧪 Practice"),
                t("🔍 Phân tích", "🔍 Analyze"),
                t("📈 Tiến độ", "📈 Progress"),
                t("⚙️ Tài khoản", "⚙️ Account"),
            ]
        )

        if section in [t("📚 Học tập", "📚 Learn"), "📚 Học tập", "📚 Learn"]:
            menu_items = [
                t("Bắt đầu từ đây", "Start Here"),
                t("⚡ Daily Challenge", "⚡ Daily Challenge"),
                t("🌅 Routine sáng", "🌅 Morning Routine"),
                t("🌙 Routine tối", "🌙 Evening Routine"),
                t("📰 Góc thị trường", "📰 Market Corner"),
                t("Bài học", "Lessons"),
                t("Market Regime Training", "Market Regime Training"),
                t("Regime Taxonomy", "Regime Taxonomy"),
                t("Vì sao cần app này?", "Why This App?"),
            ]
        elif section in [t("🧪 Thực hành", "🧪 Practice"), "🧪 Thực hành", "🧪 Practice"]:
            menu_items = [
                "Quiz",
                t("Checklist trước khi mua", "Pre-Buy Checklist"),
                t("🎣 Bạn có là thanh khoản?", "🎣 Are You the Liquidity?"),
                t("Decision Simulator", "Decision Simulator"),
                t("Historical Simulator", "Historical Simulator"),
                t("Investment Challenge", "Investment Challenge"),
                t("Post-Mortem Trainer", "Post-Mortem Trainer"),
            ]
        elif section in [t("🔍 Phân tích", "🔍 Analyze"), "🔍 Phân tích", "🔍 Analyze"]:
            menu_items = [
                t("🤖 AI Coach", "🤖 AI Coach"),
                t("📡 Regime Radar", "📡 Regime Radar"),
                t("📊 Portfolio Risk", "📊 Portfolio Risk"),
                t("Behavior Diagnosis", "Behavior Diagnosis"),
                t("Bias Engine", "Bias Engine"),
                t("Adaptive Curriculum", "Adaptive Curriculum"),
                t("Learning Forecast", "Learning Forecast"),
            ]
        elif section in [t("📈 Tiến độ", "📈 Progress"), "📈 Tiến độ", "📈 Progress"]:
            menu_items = [
                t("Progress Dashboard", "Progress Dashboard"),
                t("🏆 Leaderboard", "🏆 Leaderboard"),
                t("👥 Cộng đồng", "👥 Community"),
                t("Mastery Score", "Mastery Score"),
                t("Learning Memory", "Learning Memory"),
                t("Learning Trend", "Learning Trend"),
                t("Scenario Coverage", "Scenario Coverage"),
                t("Historical Dashboard", "Historical Dashboard"),
                t("Gamification", "Gamification"),
                t("Nhật ký quyết định", "Decision Journal"),
                t("Điểm kỷ luật", "Discipline Score"),
            ]
        else:
            menu_items = [
                t("Thông tin tài khoản", "Account Info"),
                t("Nâng cấp Pro", "Upgrade to Pro"),
                t("🎁 Giới thiệu bạn bè", "🎁 Refer Friends"),
            ]

        menu = st.radio(t("Menu", "Menu"), menu_items, key="main_menu")

        if plan == "free" and section not in [t("⚙️ Tài khoản", "⚙️ Account"), "⚙️ Tài khoản", "⚙️ Account"]:
            st.divider()
            st.markdown(t(
                "⭐ **Nâng cấp Pro** để mở khóa toàn bộ tính năng",
                "⭐ **Upgrade to Pro** for full access"
            ))
            if st.button(t("Xem chi tiết", "See details"), key="sidebar_upgrade"):
                st.session_state["show_upgrade"] = True

        # Admin dashboard button
        if is_admin(user.get("username", "")):
            st.divider()
            if st.button("🛠️ Admin Dashboard", key="admin_dash_btn", use_container_width=True, type="primary"):
                st.session_state["show_admin"] = True
                st.rerun()

        st.divider()
        if st.button(t("🚪 Đăng xuất", "🚪 Sign out"), key="logout"):
            st.session_state.user = None
            st.session_state.onboarding_done = False
            st.rerun()
        st.markdown("""
<p style="color:#475569;font-size:10px;margin:8px 0 0;line-height:1.5">
© 2025 Nguyễn Thị Nguyệt Tâm<br>
All rights reserved.<br>
Bảo hộ SHTT Việt Nam.
</p>""", unsafe_allow_html=True)

    return menu


# ─── PAGES ─────────────────────────────────────────────────────────────────────

def page_start_here():
    st.header(t("🧭 Bắt đầu từ đây", "🧭 Start Here"))
    st.markdown(t("""
App này **không** được thiết kế để giúp bạn kiếm tiền nhanh.

Mục tiêu chính là giúp bạn:

- Tránh FOMO và all-in
- Nhận diện thị trường xấu
- Giảm quyết định cảm tính
- Luyện tư duy Risk First

### Nên dùng theo thứ tự:

1. **Bài học** → nền tảng tư duy
2. **Market Regime Training** → học phân loại Risk-on / Mixed / Risk-off
3. **Historical Simulator** → luyện với thị trường quá khứ
4. **Quiz** → kiểm tra hiểu bài
5. **Investment Challenge** → luyện quy trình đầy đủ
6. **Progress Dashboard** → theo dõi tiến bộ tổng thể
""", """
This app is **not** designed to help you make money fast.

Its main goal is to help you:

- Avoid FOMO and all-in positions
- Recognize bad market regimes
- Reduce emotional decisions
- Build Risk First thinking

### Recommended order:

1. **Lessons** → build the mindset foundation
2. **Market Regime Training** → learn Risk-on / Mixed / Risk-off
3. **Historical Simulator** → practice with historical markets
4. **Quiz** → test your understanding
5. **Investment Challenge** → practice the full process
6. **Progress Dashboard** → track overall progress
"""))


def page_lessons():
    st.header(t("📖 Bài học", "📖 Lessons"))
    lesson_name = st.selectbox(t("Chọn bài học", "Select lesson"), list(LESSONS.keys()))
    st.divider()
    st.markdown(LESSONS[lesson_name][st.session_state.lang])


def page_quiz():
    st.header("📝 Quiz")

    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"
    limits = FREEMIUM_LIMITS[plan]

    all_topics = list(QUIZ.keys())
    available_topics = all_topics[:limits["max_quiz_topics"]]

    if len(available_topics) < len(all_topics):
        st.info(t(
            f"Gói Free có {limits['max_quiz_topics']}/{len(all_topics)} chủ đề. ⭐ Nâng cấp Pro để mở khóa tất cả.",
            f"Free plan includes {limits['max_quiz_topics']}/{len(all_topics)} topics. ⭐ Upgrade to Pro for all."
        ))

    topic = st.selectbox(t("Chọn chủ đề", "Select topic"), available_topics)
    questions = QUIZ[topic]

    for i, item in enumerate(questions):
        st.markdown(f"**Q{i+1}:** {item[f'q_{st.session_state.lang}']}")
        options = item[f"options_{st.session_state.lang}"]
        answer = item[f"answer_{st.session_state.lang}"]
        bias_map = item.get(f"bias_map_{st.session_state.lang}", {})

        key = f"quiz_{topic}_{i}"
        choice = st.radio("", options, key=key, label_visibility="collapsed")

        if st.button(t("Kiểm tra", "Check"), key=f"check_{topic}_{i}"):
            if choice == answer:
                st.success(t("✅ Đúng! Tư duy phòng thủ tốt.", "✅ Correct! Sound defensive thinking."))
            else:
                st.error(t(f"❌ Sai. Đáp án: **{answer}**", f"❌ Wrong. Answer: **{answer}**"))
                bias = bias_map.get(choice)
                if bias and bias in BIAS_EXPLANATIONS:
                    st.warning(BIAS_EXPLANATIONS[bias][st.session_state.lang])

        st.divider()

    if len(available_topics) < len(all_topics):
        show_upgrade_cta()


def page_checklist():
    st.header(t("✅ Checklist trước khi mua", "✅ Pre-Buy Checklist"))
    st.caption(t("Chạy checklist này trước mỗi quyết định mua.", "Run this checklist before every buy decision."))

    items_vi = [
        "Tôi biết rõ vì sao mình mua",
        "Tôi biết điểm sai ở đâu (invalidation)",
        "Tôi biết mức lỗ tối đa",
        "Tôi không mua vì FOMO",
        "Thị trường không ở trạng thái Risk-off",
        "Size phù hợp với mức độ chắc chắn",
        "Tôi có stop-loss rõ ràng",
        "Volume xác nhận setup",
    ]
    items_en = [
        "I clearly know why I'm buying",
        "I know where I would be wrong (invalidation)",
        "I know the maximum loss",
        "I am not buying because of FOMO",
        "Market is not in Risk-off state",
        "Size matches my level of conviction",
        "I have a clear stop-loss",
        "Volume confirms the setup",
    ]
    items = items_vi if st.session_state.lang == "vi" else items_en

    checks = [st.checkbox(item, key=f"cl_{i}") for i, item in enumerate(items)]
    passed = sum(checks)

    st.subheader(t(f"Kết quả: {passed}/{len(items)}", f"Result: {passed}/{len(items)}"))

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=passed,
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, len(items)]},
                "bar": {"color": "#1D4ED8"},
                "steps": [
                    {"range": [0, 3], "color": "#FEE2E2"},
                    {"range": [3, 6], "color": "#FEF9C3"},
                    {"range": [6, 8], "color": "#DCFCE7"},
                ],
                "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 6}
            },
            title={"text": t("Điểm checklist", "Checklist Score")}
        ))
        fig.update_layout(height=250, margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if passed <= 3:
            st.error(t("🚫 Không nên mua. Quyết định còn quá yếu.", "🚫 Do not buy. Decision is too weak."))
        elif passed <= 5:
            st.warning(t("⚠️ Chỉ nên quan sát hoặc test-size tối thiểu.", "⚠️ Observe only or minimal test size."))
        elif passed == len(items):
            st.success(t("✅ Tất cả tiêu chí đạt. Có thể xem xét với quản trị rủi ro.", "✅ All criteria met. Consider with risk management."))
        else:
            st.success(t("🟡 Khá ổn. Vẫn phải giới hạn size và stop-loss chặt.", "🟡 Decent. Still limit size and enforce stop-loss."))


def page_decision_simulator():
    st.header(t("⚙️ Decision Simulator", "⚙️ Decision Simulator"))
    st.caption(t("Mô phỏng rủi ro thực tế trước khi vào lệnh", "Simulate real risk before entering a trade"))

    col1, col2 = st.columns(2)

    with col1:
        account_size = st.number_input(t("Tổng tài khoản ($)", "Account size ($)"), min_value=0.0, value=10000.0, step=500.0)
        entry_price = st.number_input(t("Giá mua dự kiến", "Expected entry price"), min_value=0.01, value=100.0, step=0.5)
        stop_price = st.number_input(t("Giá cắt lỗ (stop-loss)", "Stop-loss price"), min_value=0.01, value=95.0, step=0.5)
        shares = st.number_input(t("Số lượng cổ phiếu", "Number of shares"), min_value=0, value=100, step=5)

    with col2:
        if stop_price >= entry_price:
            st.error(t("⛔ Giá cắt lỗ phải thấp hơn giá mua.", "⛔ Stop-loss must be below entry price."))
        elif account_size > 0:
            position_value = entry_price * shares
            risk_per_share = entry_price - stop_price
            total_risk = risk_per_share * shares
            risk_pct = total_risk / account_size * 100
            position_pct = position_value / account_size * 100

            st.metric(t("Giá trị vị thế", "Position value"), f"${position_value:,.0f}", f"{position_pct:.1f}% " + t("tài khoản", "of account"))
            st.metric(t("Tổng rủi ro nếu sai", "Total risk if wrong"), f"${total_risk:,.0f}", f"{risk_pct:.2f}% " + t("tài khoản", "of account"))

            if risk_pct > 5:
                st.error(t(f"🚫 **BLOCK TRADE** — Rủi ro {risk_pct:.1f}% quá lớn. Giảm size xuống.", f"🚫 **BLOCK TRADE** — Risk {risk_pct:.1f}% is too large. Reduce size."))
            elif risk_pct > 2:
                st.warning(t(f"⚠️ Rủi ro {risk_pct:.1f}% — Nên dùng test-size hoặc giảm số lượng.", f"⚠️ Risk {risk_pct:.1f}% — Use test size or reduce quantity."))
            else:
                max_shares_2pct = int((account_size * 0.02) / max(risk_per_share, 0.01))
                st.success(t(f"✅ Rủi ro {risk_pct:.1f}% — Chấp nhận được nếu bằng chứng đủ mạnh.", f"✅ Risk {risk_pct:.1f}% — Acceptable if evidence is strong."))
                st.info(t(f"Để giữ đúng 2% risk, nên dùng tối đa **{max_shares_2pct} cổ phiếu**.", f"To stay at exactly 2% risk, use max **{max_shares_2pct} shares**."))


def page_market_regime():
    st.header(t("📡 Market Regime Training", "📡 Market Regime Training"))

    case_names = [c["name"] for c in REGIME_CASES]
    selected = st.selectbox(t("Chọn tình huống", "Select scenario"), case_names)
    case = next(c for c in REGIME_CASES if c["name"] == selected)

    st.subheader(case["name"])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("VIX", case["vix"])
    col2.metric("S&P 500 vs MA200", case["sp500_ma200"])
    col3.metric("Breadth", case["breadth"])
    col4.metric("Credit", case["credit"])

    answer = st.radio(t("Bạn phân loại regime này là gì?", "How do you classify this regime?"), ["Risk-on", "Mixed", "Risk-off"])

    if st.button(t("Kiểm tra", "Check"), type="primary"):
        if answer == case["correct"]:
            st.success(t("✅ Đúng!", "✅ Correct!"))
        else:
            st.error(t(f"❌ Sai. Đáp án: **{case['correct']}**", f"❌ Wrong. Answer: **{case['correct']}**"))
        st.info(case[f"explain_{st.session_state.lang}"])


def page_post_mortem():
    st.header(t("🔍 Post-Mortem Trainer", "🔍 Post-Mortem Trainer"))

    case_names = [c[f"name_{st.session_state.lang}"] for c in POST_MORTEM_CASES]
    selected = st.selectbox(t("Chọn tình huống", "Select scenario"), case_names)
    case = next(c for c in POST_MORTEM_CASES if c[f"name_{st.session_state.lang}"] == selected)

    st.info(case[f"trade_{st.session_state.lang}"])

    opts_vi = ["Quy trình tốt", "Quy trình xấu", "Kết quả tốt nhưng quy trình xấu", "Kết quả xấu nhưng quy trình tốt"]
    opts_en = ["Good process", "Bad process", "Good outcome but bad process", "Bad outcome but good process"]
    opts = opts_vi if st.session_state.lang == "vi" else opts_en
    answer = st.radio(t("Bạn đánh giá là?", "Your assessment:"), opts)

    if st.button(t("Kiểm tra post-mortem", "Check post-mortem"), type="primary"):
        correct = case[f"correct_{st.session_state.lang}"]
        if answer == correct:
            st.success(t("✅ Đúng!", "✅ Correct!"))
        else:
            st.error(t(f"❌ Sai. Đáp án: **{correct}**", f"❌ Wrong. Answer: **{correct}**"))
        st.info(case[f"explain_{st.session_state.lang}"])


def page_investment_challenge():
    st.header(t("🎯 Investment Decision Challenge", "🎯 Investment Decision Challenge"))

    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"
    limits = FREEMIUM_LIMITS[plan]

    available_challenges = DECISION_CHALLENGES[:limits["challenges"]]
    if len(available_challenges) < len(DECISION_CHALLENGES):
        st.info(t(
            f"Gói Free: {limits['challenges']}/{len(DECISION_CHALLENGES)} challenges. Đăng ký ⭐ Pro để mở tất cả.",
            f"Free plan: {limits['challenges']}/{len(DECISION_CHALLENGES)} challenges. ⭐ Pro for all."
        ))

    case_names = [c[f"name_{st.session_state.lang}"] for c in available_challenges]
    selected = st.selectbox(t("Chọn challenge", "Select challenge"), case_names)
    case = next(c for c in available_challenges if c[f"name_{st.session_state.lang}"] == selected)

    col1, col2, col3 = st.columns(3)
    col1.metric("VIX", case["vix"])
    col2.metric("Trend", case[f"trend_{st.session_state.lang}"])
    col3.metric("Breadth", case["breadth"])

    st.info(t("**Setup:** ", "**Setup:** ") + case[f"stock_setup_{st.session_state.lang}"])
    st.divider()

    st.subheader(t("Bước 1: Phân loại regime", "Step 1: Classify regime"))
    regime_ans = st.radio(t("Regime?", "Regime?"), ["Risk-on", "Mixed", "Risk-off"], key="ch_regime")

    st.subheader(t("Bước 2: Quyết định", "Step 2: Decision"))
    decision_ans = st.radio(t("Action?", "Action?"), ["Buy Normal Size", "Buy Test Size", "No Trade"], key="ch_decision")

    st.subheader(t("Bước 3: Mức rủi ro tối đa", "Step 3: Max risk"))
    risk_ans = st.radio(t("Risk %?", "Risk %?"), ["0%", "1%", "1-2%", "5%", "10%+"], key="ch_risk")

    if st.button(t("Chấm điểm", "Score"), type="primary"):
        r_ok = regime_ans == case["correct_regime"]
        d_ok = decision_ans == case["correct_decision"]
        ri_ok = risk_ans == case["correct_risk"]
        score = sum([r_ok, d_ok, ri_ok])

        # Save to DB
        if user["id"] != -1:
            save_challenge(user["id"], case[f"name_{st.session_state.lang}"], r_ok, d_ok, ri_ok, score)
            save_feed_event(user["id"], "challenge_score",
                t(f"{case[f'name_vi']} — {score}/3", f"{case[f'name_en']} — {score}/3"))

        st.subheader(f"{score_color(score)} {t(f'Điểm: {score}/3', f'Score: {score}/3')}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Regime", "✅" if r_ok else "❌", case["correct_regime"])
        col2.metric("Decision", "✅" if d_ok else "❌", case["correct_decision"])
        col3.metric("Risk", "✅" if ri_ok else "❌", case["correct_risk"])

        st.info(case[f"explain_{st.session_state.lang}"])
        show_share_widget(score, 3, case[f"name_{st.session_state.lang}"])

    if len(available_challenges) < len(DECISION_CHALLENGES):
        st.divider()
        show_upgrade_cta()


def page_historical_simulator():
    st.header(t("📜 Historical Market Simulator", "📜 Historical Market Simulator"))

    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"
    limits = FREEMIUM_LIMITS[plan]

    available_cases = HISTORICAL_CASES[:limits["historical_cases"]]
    if len(available_cases) < len(HISTORICAL_CASES):
        st.info(t(
            f"Gói Free: {limits['historical_cases']}/{len(HISTORICAL_CASES)} cases. ⭐ Pro để mở tất cả.",
            f"Free plan: {limits['historical_cases']}/{len(HISTORICAL_CASES)} cases. ⭐ Pro for all."
        ))

    case_names = [c["name"] for c in available_cases]
    selected = st.selectbox(t("Chọn giai đoạn lịch sử", "Select historical period"), case_names)
    case = next(c for c in available_cases if c["name"] == selected)

    st.subheader(f"{case['year']} — {case['headline']}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("VIX", case["vix"])
    col2.metric("Trend", case["trend"])
    col3.metric("Breadth", case["breadth"])
    col4.metric("Credit", case["credit"])

    st.divider()
    regime_ans = st.radio(t("Regime?", "Regime?"), ["Risk-on", "Mixed", "Risk-off"], key="hist_regime")
    decision_ans = st.radio(t("Decision?", "Decision?"), ["Buy Normal Size", "Buy Test Size", "No Trade"], key="hist_decision")
    risk_ans = st.radio(t("Risk?", "Risk?"), ["0%", "1%", "1-2%", "5%"], key="hist_risk")

    if st.button(t("Xem kết quả thực tế", "Reveal Outcome"), type="primary"):
        r_ok = regime_ans == case["correct_regime"]
        d_ok = decision_ans == case["correct_decision"]
        ri_ok = risk_ans == case["correct_risk"]
        score = sum([r_ok, d_ok, ri_ok])

        if user["id"] != -1:
            save_historical(user["id"], case["name"], r_ok, d_ok, ri_ok, score)
        save_feed_event(user["id"], "simulator_score",
            t(f"{case['name']} — {score}/3", f"{case['name']} — {score}/3"))

        st.subheader(t("📰 Điều thực sự xảy ra", "📰 What Actually Happened"))
        st.success(case[f"outcome_{st.session_state.lang}"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Regime", "✅" if r_ok else "❌", case["correct_regime"])
        col2.metric("Decision", "✅" if d_ok else "❌", case["correct_decision"])
        col3.metric("Risk", "✅" if ri_ok else "❌", case["correct_risk"])

        st.subheader(f"{score_color(score)} Score: {score}/3")
        show_share_widget(score, 3, case["name"], f"https://your-app.streamlit.app")

    if len(available_cases) < len(HISTORICAL_CASES):
        st.divider()
        show_upgrade_cta()


def page_historical_dashboard():
    st.header(t("📊 Historical Dashboard", "📊 Historical Dashboard"))
    user = st.session_state.user

    if user["id"] == -1:
        st.info(t("Demo không lưu dữ liệu. Đăng ký tài khoản để theo dõi tiến độ.", "Demo mode doesn't save data. Register to track progress."))
        return

    rows = get_historical_stats(user["id"])
    if not rows:
        st.info(t("Chưa có dữ liệu. Thử Historical Simulator trước.", "No data yet. Try the Historical Simulator first."))
        return

    df = pd.DataFrame(rows)
    total = len(df)
    avg = df["score"].mean()
    regime_acc = df["regime_correct"].mean() * 100
    decision_acc = df["decision_correct"].mean() * 100
    risk_acc = df["risk_correct"].mean() * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("Số lần thử", "Attempts"), total)
    col2.metric("Regime", accuracy_badge(regime_acc))
    col3.metric("Decision", accuracy_badge(decision_acc))
    col4.metric("Risk", accuracy_badge(risk_acc))

    st.divider()
    st.subheader(t("Độ phủ scenarios", "Scenario Coverage"))
    all_names = [c["name"] for c in HISTORICAL_CASES]
    done = set(df["case_name"].tolist())
    cov_df = pd.DataFrame([{"Scenario": n, "Status": "✅" if n in done else "—"} for n in all_names])
    st.dataframe(cov_df, use_container_width=True, hide_index=True)


def page_behavior_diagnosis():
    st.header(t("🧠 Behavior Diagnosis", "🧠 Behavior Diagnosis"))
    gate_pro(t("Chẩn đoán hành vi", "Behavior Diagnosis"))

    user = st.session_state.user
    rows = get_historical_stats(user["id"])
    if len(rows) < 5:
        st.warning(t("Cần ít nhất 5 historical attempts để phân tích.", "Need at least 5 historical attempts to analyze."))
        return

    df = pd.DataFrame(rows)
    regime_acc = df["regime_correct"].mean() * 100
    decision_acc = df["decision_correct"].mean() * 100
    risk_acc = df["risk_correct"].mean() * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Regime", accuracy_badge(regime_acc))
    col2.metric("Decision", accuracy_badge(decision_acc))
    col3.metric("Risk", accuracy_badge(risk_acc))

    st.divider()
    if regime_acc < 50:
        st.error(t("🔴 Khó khăn nhận diện market regime.", "🔴 Difficulty recognizing market regimes."))
    if decision_acc < 50:
        st.error(t("🔴 Quyết định thường không phù hợp bối cảnh.", "🔴 Decisions often misaligned with context."))
    if risk_acc < 50:
        st.error(t("🔴 Xu hướng sizing sai mức rủi ro.", "🔴 Tendency to size risk incorrectly."))
    if regime_acc >= 70:
        st.success(t("✅ Nhận diện regime tốt.", "✅ Good regime recognition."))
    if risk_acc >= 70:
        st.success(t("✅ Kỷ luật quản trị rủi ro tốt.", "✅ Good risk management discipline."))


def page_bias_engine():
    st.header(t("⚡ Behavioral Bias Engine", "⚡ Behavioral Bias Engine"))
    gate_pro(t("Bias Engine", "Bias Engine"))

    user = st.session_state.user
    rows = get_historical_stats(user["id"])
    if len(rows) < 5:
        st.warning(t("Cần ít nhất 5 attempts.", "Need at least 5 attempts."))
        return

    df = pd.DataFrame(rows)
    regime_acc = df["regime_correct"].mean()
    decision_acc = df["decision_correct"].mean()
    risk_acc = df["risk_correct"].mean()

    biases = []
    if regime_acc < 0.50: biases.append(("Early Risk-On Bias", t("Đánh giá thị trường tích cực quá sớm.", "Assessing the market too positively too early.")))
    if decision_acc < 0.50: biases.append(("Action Bias", t("Muốn giao dịch ngay cả khi không nên.", "Urge to trade even when you shouldn't.")))
    if risk_acc < 0.50: biases.append(("Oversizing Bias", t("Chọn mức risk lớn hơn mức nên dùng.", "Choosing risk levels larger than appropriate.")))
    if regime_acc < 0.50 and decision_acc < 0.50: biases.append(("FOMO Bias", t("Dễ bị hấp dẫn bởi cơ hội tăng giá.", "Easily attracted by upside opportunities.")))

    if not biases:
        st.success(t("✅ Chưa phát hiện bias đáng kể.", "✅ No significant biases detected."))
    else:
        for name, desc in biases:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.write(desc)


def page_adaptive_curriculum():
    st.header(t("📋 Adaptive Curriculum", "📋 Adaptive Curriculum"))
    gate_pro(t("Adaptive Curriculum", "Adaptive Curriculum"))

    user = st.session_state.user
    rows = get_historical_stats(user["id"])
    if len(rows) < 5:
        st.warning(t("Cần ít nhất 5 historical attempts.", "Need at least 5 historical attempts."))
        return

    df = pd.DataFrame(rows)
    regime_acc = df["regime_correct"].mean()
    decision_acc = df["decision_correct"].mean()
    risk_acc = df["risk_correct"].mean()

    curriculum = []
    if regime_acc < 0.5:
        curriculum += [t("Market Regime Training", "Market Regime Training"), t("COVID Crash case", "COVID Crash case"), t("Inflation Shock case", "Inflation Shock case")]
    if decision_acc < 0.5:
        curriculum += [t("Investment Decision Challenge", "Investment Decision Challenge"), t("Post-Mortem Trainer", "Post-Mortem Trainer")]
    if risk_acc < 0.5:
        curriculum += [t("Decision Simulator", "Decision Simulator"), t("Bài học Position Sizing", "Position Sizing Lesson")]
    curriculum = list(dict.fromkeys(curriculum))

    if not curriculum:
        st.success(t("Không có bài bổ sung. Tiếp tục luyện historical cases.", "No additional modules needed. Continue practicing historical cases."))
    else:
        st.subheader(t("Curriculum hôm nay", "Today's Curriculum"))
        for i, item in enumerate(curriculum, 1):
            st.checkbox(f"{i}. {item}", key=f"cur_{i}")


def page_learning_memory():
    st.header(t("💾 Learning Memory", "💾 Learning Memory"))
    gate_pro("Learning Memory")

    user = st.session_state.user
    rows = get_historical_stats(user["id"])
    if not rows:
        st.info(t("Chưa có dữ liệu historical.", "No historical data yet."))
        return

    df = pd.DataFrame(rows)
    total = len(df)
    regime_acc = df["regime_correct"].mean() * 100
    decision_acc = df["decision_correct"].mean() * 100
    risk_acc = df["risk_correct"].mean() * 100
    avg_score = df["score"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("Attempts", "Attempts"), total)
    col2.metric("Regime", f"{regime_acc:.0f}%")
    col3.metric("Decision", f"{decision_acc:.0f}%")
    col4.metric("Risk", f"{risk_acc:.0f}%")

    if st.button(t("💾 Lưu snapshot", "💾 Save snapshot"), type="primary"):
        save_snapshot(user["id"], total, regime_acc, decision_acc, risk_acc, avg_score)
        st.success(t("✅ Đã lưu snapshot.", "✅ Snapshot saved."))

    snapshots = get_snapshots(user["id"])
    if snapshots:
        st.divider()
        st.subheader(t("Lịch sử snapshots", "Snapshot history"))
        snap_df = pd.DataFrame(snapshots)
        st.dataframe(snap_df[["snapshot_date", "total_attempts", "regime_accuracy", "decision_accuracy", "risk_accuracy", "avg_score"]].rename(columns={
            "snapshot_date": "Date", "total_attempts": "Attempts",
            "regime_accuracy": "Regime%", "decision_accuracy": "Decision%",
            "risk_accuracy": "Risk%", "avg_score": "Avg Score"
        }), use_container_width=True, hide_index=True)


def page_learning_trend():
    st.header(t("📈 Learning Trend", "📈 Learning Trend"))
    gate_pro("Learning Trend")

    user = st.session_state.user
    snapshots = get_snapshots(user["id"])
    if len(snapshots) < 2:
        st.warning(t("Cần ít nhất 2 snapshots.", "Need at least 2 snapshots."))
        return

    snap_df = pd.DataFrame(snapshots)
    fig = go.Figure()
    for col, name in [("regime_accuracy", "Regime"), ("decision_accuracy", "Decision"), ("risk_accuracy", "Risk")]:
        fig.add_trace(go.Scatter(x=snap_df["snapshot_date"], y=snap_df[col], name=name, mode="lines+markers"))
    fig.update_layout(title=t("Xu hướng học tập theo thời gian", "Learning trend over time"), yaxis_title="%", height=350)
    st.plotly_chart(fig, use_container_width=True)


def page_learning_forecast():
    st.header(t("🔮 Learning Forecast", "🔮 Learning Forecast"))
    gate_pro("Learning Forecast")

    user = st.session_state.user
    snapshots = get_snapshots(user["id"])
    if len(snapshots) < 2:
        st.warning(t("Cần ít nhất 2 snapshots.", "Need at least 2 snapshots."))
        return

    snap_df = pd.DataFrame(snapshots).sort_values("snapshot_date")
    first, last = snap_df.iloc[0], snap_df.iloc[-1]
    n = len(snap_df) - 1
    TARGET = 70

    rows = []
    for col, name in [("regime_accuracy", "Regime"), ("decision_accuracy", "Decision"), ("risk_accuracy", "Risk")]:
        current = last[col]
        rate = (current - first[col]) / n
        if current >= TARGET:
            forecast = t("✅ Đã đạt", "✅ Achieved")
        elif rate <= 0:
            forecast = t("⚠️ Chưa cải thiện", "⚠️ Not improving")
        else:
            needed = (TARGET - current) / rate
            forecast = t(f"~{needed:.1f} snapshots nữa", f"~{needed:.1f} more snapshots")
        rows.append({"Skill": name, "Current": f"{current:.1f}%", "Target": f"{TARGET}%", "Rate/snapshot": f"{rate:+.1f}%", "Forecast": forecast})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_mastery_score():
    st.header(t("🏆 Mastery Score", "🏆 Mastery Score"))
    gate_pro("Mastery Score")

    user = st.session_state.user
    snapshots = get_snapshots(user["id"])
    if not snapshots:
        st.info(t("Cần ít nhất 1 learning memory snapshot.", "Need at least 1 learning memory snapshot."))
        return

    latest = snapshots[-1]
    regime = latest["regime_accuracy"]
    decision = latest["decision_accuracy"]
    risk = latest["risk_accuracy"]
    skill_score = regime * 0.35 + decision * 0.35 + risk * 0.30

    hist_rows = get_historical_stats(user["id"])
    attempts = len(hist_rows)
    coverage_factor = min(attempts / 50, 1.0)

    if hist_rows:
        df = pd.DataFrame(hist_rows)
        taxonomy_map = {c["name"]: c["taxonomy"] for c in HISTORICAL_CASES}
        covered = df["case_name"].map(taxonomy_map).dropna().nunique()
    else:
        covered = 0
    taxonomy_factor = covered / len(TAXONOMY)

    stability_factor = max(0.2, 1 - (pd.DataFrame(snapshots)["avg_score"].tail(10).std() / 3)) if len(snapshots) >= 5 else 0.2
    confidence = coverage_factor * taxonomy_factor * stability_factor * 100
    mastery = skill_score * confidence / 100

    st.metric("Effective Mastery", f"{mastery:.1f}%")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Regime", f"{regime:.0f}%")
    col2.metric("Decision", f"{decision:.0f}%")
    col3.metric("Risk", f"{risk:.0f}%")
    col4.metric("Skill", f"{skill_score:.0f}%")
    col5.metric("Confidence", f"{confidence:.0f}%")

    if mastery < 20: level = t("🌱 Novice", "🌱 Novice")
    elif mastery < 40: level = t("📗 Beginner", "📗 Beginner")
    elif mastery < 60: level = t("📘 Intermediate", "📘 Intermediate")
    elif mastery < 80: level = t("📙 Advanced", "📙 Advanced")
    elif mastery < 95: level = t("🏅 Professional", "🏅 Professional")
    else: level = t("👑 Governance Master", "👑 Governance Master")

    st.success(f"**{t('Cấp độ', 'Level')}:** {level}")

    fig = go.Figure(go.Bar(
        x=["Regime", "Decision", "Risk"],
        y=[regime, decision, risk],
        marker_color=["#1D4ED8", "#059669", "#D97706"]
    ))
    fig.update_layout(yaxis_range=[0, 100], height=280, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def page_scenario_coverage():
    st.header(t("🗺️ Scenario Coverage", "🗺️ Scenario Coverage"))

    user = st.session_state.user
    hist_rows = get_historical_stats(user["id"]) if user["id"] != -1 else []
    done = set(r["case_name"] for r in hist_rows)
    total = len(HISTORICAL_CASES)
    covered = len(done)
    pct = covered / total * 100

    col1, col2, col3 = st.columns(3)
    col1.metric(t("Đã hoàn thành", "Completed"), covered)
    col2.metric(t("Tổng", "Total"), total)
    col3.metric(t("Độ phủ", "Coverage"), f"{pct:.0f}%")

    rows = [{"Scenario": c["name"], "Year": c["year"], "Type": TAXONOMY.get(c["taxonomy"], {}).get(f"label_{st.session_state.lang}", c["taxonomy"]), "Status": "✅" if c["name"] in done else "—"} for c in HISTORICAL_CASES]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_regime_taxonomy():
    st.header(t("🌐 Regime Taxonomy", "🌐 Regime Taxonomy"))

    user = st.session_state.user
    hist_rows = get_historical_stats(user["id"]) if user["id"] != -1 else []
    done_cases = set(r["case_name"] for r in hist_rows)
    tax_map = {c["name"]: c["taxonomy"] for c in HISTORICAL_CASES}
    done_taxonomy = set(tax_map[n] for n in done_cases if n in tax_map)

    rows = []
    for key, info in TAXONOMY.items():
        examples = [c["name"] for c in HISTORICAL_CASES if c["taxonomy"] == key]
        done_ex = [e for e in examples if e in done_cases]
        rows.append({
            t("Loại regime", "Regime type"): info[f"label_{st.session_state.lang}"],
            t("Đã học", "Learned"): "✅" if key in done_taxonomy else "—",
            t("Ví dụ đã hoàn thành", "Completed examples"): ", ".join(done_ex) if done_ex else t("Chưa có", "None"),
        })

    covered = len(done_taxonomy)
    total = len(TAXONOMY)
    col1, col2, col3 = st.columns(3)
    col1.metric(t("Loại đã phủ", "Types covered"), covered)
    col2.metric(t("Tổng loại", "Total types"), total)
    col3.metric(t("Taxonomy coverage", "Taxonomy coverage"), f"{covered/total*100:.0f}%")

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_progress_dashboard():
    st.header(t("📊 Progress Dashboard", "📊 Progress Dashboard"))

    user = st.session_state.user
    if user["id"] == -1:
        st.info(t("Demo không lưu dữ liệu. Đăng ký để theo dõi tiến độ.", "Demo mode. Register to track progress."))
        return

    hist_rows = get_historical_stats(user["id"])
    challenge_rows = get_challenge_stats(user["id"])
    disc = get_discipline_stats(user["id"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("Historical attempts", "Historical attempts"), len(hist_rows))
    col2.metric(t("Challenges done", "Challenges done"), len(challenge_rows))
    col3.metric(t("Journal entries", "Journal entries"), disc["total"])
    col4.metric(t("Discipline score", "Discipline score"), disc["score"])

    if hist_rows:
        df = pd.DataFrame(hist_rows)
        regime_acc = df["regime_correct"].mean() * 100
        decision_acc = df["decision_correct"].mean() * 100
        risk_acc = df["risk_correct"].mean() * 100

        st.divider()
        st.subheader(t("Kỹ năng", "Skills"))
        fig = go.Figure(go.Bar(
            x=[t("Nhận diện Regime", "Regime Recognition"), t("Quyết định", "Decision"), t("Quản lý rủi ro", "Risk Management")],
            y=[regime_acc, decision_acc, risk_acc],
            marker_color=["#1D4ED8", "#059669", "#D97706"],
            text=[f"{v:.0f}%" for v in [regime_acc, decision_acc, risk_acc]],
            textposition="outside"
        ))
        fig.update_layout(yaxis_range=[0, 110], height=300, margin=dict(t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

        weakest = min({"Regime": regime_acc, "Decision": decision_acc, "Risk": risk_acc}, key=lambda k: {"Regime": regime_acc, "Decision": decision_acc, "Risk": risk_acc}[k])
        recs = {
            "Regime": t("➡️ Luyện Market Regime Training + Historical Simulator", "➡️ Train Market Regime Training + Historical Simulator"),
            "Decision": t("➡️ Luyện Investment Challenge + Post-Mortem Trainer", "➡️ Train Investment Challenge + Post-Mortem Trainer"),
            "Risk": t("➡️ Luyện Decision Simulator + Position Sizing", "➡️ Train Decision Simulator + Position Sizing"),
        }
        st.warning(t(f"⚠️ Điểm yếu: **{weakest}**  {recs[weakest]}", f"⚠️ Weakest: **{weakest}**  {recs[weakest]}"))


def page_gamification():
    st.header(t("🎮 Gamification", "🎮 Gamification"))

    user = st.session_state.user
    if user["id"] == -1:
        st.info(t("Demo không lưu dữ liệu.", "Demo mode — data not saved."))
        return

    rows = get_challenge_stats(user["id"])
    if not rows:
        st.info(t("Chưa có challenge data.", "No challenge data yet."))
        return

    df = pd.DataFrame(rows)
    total_xp = int(df["score"].sum() * 10)
    avg_score = df["score"].mean()
    total_attempts = len(df)
    unique_days = df["date"].nunique()

    if total_xp < 50: level = "Level 1 · Rookie"
    elif total_xp < 100: level = "Level 2 · Analyst"
    elif total_xp < 200: level = "Level 3 · Risk Manager"
    elif total_xp < 400: level = "Level 4 · Portfolio Manager"
    else: level = "Level 5 · Governance Master"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XP", total_xp)
    col2.metric(t("Số lần thử", "Attempts"), total_attempts)
    col3.metric(t("Ngày học", "Active days"), unique_days)
    col4.metric(t("Điểm TB", "Avg score"), f"{avg_score:.1f}/3")

    st.success(f"**{level}**")
    st.divider()

    badges = []
    if total_attempts >= 5: badges.append(t("🏅 5 challenges đầu tiên", "🏅 First 5 Challenges"))
    if total_attempts >= 20: badges.append(t("🏅 Veteran", "🏅 Challenge Veteran"))
    if avg_score >= 2.0: badges.append("🛡️ Risk Aware")
    if avg_score >= 2.5: badges.append("📡 Regime Master")
    if avg_score >= 2.8: badges.append("👑 Governance Elite")
    if unique_days >= 7: badges.append(t("🔥 7-day streak", "🔥 7-Day Streak"))
    if unique_days >= 30: badges.append(t("🔥🔥 30-day streak", "🔥🔥 30-Day Streak"))

    if badges:
        for b in badges:
            st.write(b)
    else:
        st.info(t("Chưa mở được badge nào. Tiếp tục luyện tập!", "No badges yet. Keep practicing!"))


def page_journal():
    st.header(t("📓 Nhật ký quyết định", "📓 Decision Journal"))

    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"
    limits = FREEMIUM_LIMITS[plan]

    if user["id"] != -1:
        existing = get_journal(user["id"])
        if len(existing) >= limits["max_journal"]:
            st.warning(t(
                f"Gói Free giới hạn {limits['max_journal']} entries. ⭐ Nâng cấp Pro để không giới hạn.",
                f"Free plan limit: {limits['max_journal']} entries. ⭐ Upgrade Pro for unlimited."
            ))
            show_upgrade_cta()
            return

    with st.form("journal_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input(t("Mã tài sản", "Asset / Ticker"), placeholder="VD: VNM, NVDA, BTC...")
            decision = st.selectbox(t("Quyết định", "Decision"), ["BUY", "SELL", "HOLD", "NO TRADE"])
            risk = st.text_input(t("Mức lỗ tối đa dự kiến", "Expected max loss"), placeholder="VD: -2% tài khoản")
        with col2:
            emotion_opts = (["Bình tĩnh", "FOMO", "Sợ hãi", "Tham lam", "Không chắc"] if st.session_state.lang == "vi"
                            else ["Calm", "FOMO", "Fear", "Greed", "Uncertain"])
            emotion = st.selectbox(t("Cảm xúc hiện tại", "Current emotion"), emotion_opts)
            reason = st.text_area(t("Lý do quyết định", "Reason"), height=80)
            invalidation = st.text_area(t("Khi nào quyết định này sai?", "When would this be wrong?"), height=80)

        submitted = st.form_submit_button(t("💾 Lưu nhật ký", "💾 Save journal"), type="primary", use_container_width=True)
        if submitted:
            if ticker and reason:
                if user["id"] != -1:
                    save_journal(user["id"], ticker, decision, reason, invalidation, risk, emotion)
                    st.success(t("✅ Đã lưu.", "✅ Saved."))
                else:
                    st.info(t("Demo mode — dữ liệu không được lưu. Đăng ký tài khoản để lưu.", "Demo mode — data not saved. Register to save."))
            else:
                st.error(t("Vui lòng điền mã tài sản và lý do.", "Please fill in ticker and reason."))

    if user["id"] != -1:
        entries = get_journal(user["id"])
        if entries:
            st.divider()
            st.subheader(t("Lịch sử quyết định", "Decision History"))
            df = pd.DataFrame(entries)[["date", "ticker", "decision", "emotion", "risk", "reason"]]
            st.dataframe(df, use_container_width=True, hide_index=True)


def page_discipline_score():
    st.header(t("⚖️ Điểm kỷ luật", "⚖️ Discipline Score"))

    user = st.session_state.user
    if user["id"] == -1:
        st.info(t("Demo không lưu dữ liệu.", "Demo mode — data not saved."))
        return

    disc = get_discipline_stats(user["id"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("Tổng quyết định", "Total logged"), disc["total"])
    col2.metric(t("Số lần FOMO", "FOMO count"), disc["fomo"])
    col3.metric(t("Số lần NO TRADE", "NO TRADE"), disc["no_trade"])
    col4.metric(t("Điểm kỷ luật", "Discipline Score"), disc["score"])

    if disc["score"] >= 80:
        st.success(t("✅ Kỷ luật tốt.", "✅ Good discipline."))
    elif disc["score"] >= 50:
        st.warning(t("⚠️ Cần kiểm soát cảm xúc tốt hơn.", "⚠️ Emotion control needs improvement."))
    else:
        st.error(t("🚨 Rủi ro hành vi cao. Không nên tăng size.", "🚨 High behavioral risk. Do not increase size."))


def page_account():
    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"

    st.header(t("👤 Tài khoản", "👤 Account"))
    with st.container(border=True):
        st.markdown(f"**{t('Tên đăng ký', 'Username')}:** {user['username']}")
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**{t('Gói', 'Plan')}:** {'⭐ Pro' if plan == 'pro' else '🆓 Free'}")

    if plan == "free":
        st.divider()
        show_upgrade_cta()

    # Admin shortcut — demo/dev only
    if user["username"] == "admin" and user["id"] != -1:
        st.divider()
        st.subheader("🔧 Admin")

        # Pending manual payments
        pending = get_pending_payments()
        manual_pending = [p for p in pending if p.get("method") == "manual" or True]
        if pending:
            st.markdown(t("**Đơn thanh toán đang chờ xác nhận:**", "**Pending payment orders:**"))
            for p in pending:
                cols = st.columns([3, 1])
                cols[0].markdown(f"`{p['order_code']}` — **{p['username']}** ({p['email']}) — {p['amount']:,}₫ — {p['method']}")
                if cols[1].button(t("✅ Xác nhận", "✅ Confirm"), key=f"confirm_{p['order_code']}"):
                    ok, uid = mark_payment_paid(p["order_code"])
                    if ok:
                        st.success(t(f"Đã kích hoạt Pro cho {p['username']}.", f"Activated Pro for {p['username']}."))
                        st.rerun()
        else:
            st.caption(t("Không có đơn nào đang chờ.", "No pending orders."))

        st.divider()
        target = st.text_input("Upgrade user ID to Pro (thủ công):")
        if st.button("Upgrade"):
            try:
                upgrade_user_plan(int(target), "pro")
                st.success(f"User {target} upgraded to Pro.")
            except Exception as e:
                st.error(str(e))

        # Integration status
        st.divider()
        st.markdown(t("**Trạng thái tích hợp:**", "**Integration status:**"))
        email_ok = integrations.is_email_configured()
        payos_ok = integrations.is_payos_configured()
        st.markdown(f"- {'✅' if email_ok else '❌'} Welcome Email (Gmail)")
        st.markdown(f"- {'✅' if payos_ok else '❌'} PayOS Payment")
        if not email_ok or not payos_ok:
            st.caption(t(
                "Cấu hình trong Streamlit Secrets để kích hoạt. Xem file SETUP_GUIDE.md.",
                "Configure in Streamlit Secrets to enable. See SETUP_GUIDE.md."
            ))



def _auto_generate_daily_challenge(today_str):
    """Auto-generate 1 shared daily challenge via AI, based on Regime Radar + US/VN market context.
    Called once per day by the first user who opens the app. Cost ~$0.006/day total.
    Returns True if generated, False if failed."""
    import json
    try:
        latest_radar = get_regime_radar_latest()
        if latest_radar:
            regime_ctx = latest_radar.get("regime_call", "Unknown")
            vix_ctx = latest_radar.get("vix", "?")
            vn_ctx = latest_radar.get("vn_vs_ma200", "?")
            note = latest_radar.get("note_vi", "")
            market_ctx = f"Regime hiện tại: {regime_ctx}. VIX: {vix_ctx}. VN-Index: {vn_ctx}. Ghi chú: {note}"
        else:
            market_ctx = "Chưa có dữ liệu Regime Radar. Tạo câu hỏi tình huống chung."

        client = anthropic.Anthropic()
        prompt = f"""Bạn là chuyên gia tâm lý & kỷ luật đầu tư. Tạo 1 câu hỏi "daily challenge" cho nhà đầu tư.

BỐI CẢNH THỊ TRƯỜNG HIỆN TẠI:
{market_ctx}

YÊU CẦU:
- Câu hỏi tình huống thực tế dựa trên 1 trong các nguyên tắc: Risk First, Regime First, Evidence First, Governance, hoặc nhận diện bẫy thị trường (stop hunt, bull trap, FOMO).
- BẮT BUỘC: dùng ví dụ/ngữ cảnh CỤ THỂ từ thị trường thật — có thể là TTCK Mỹ (S&P 500, VIX, Nasdaq, các giai đoạn lịch sử như 2008/2020/2022) HOẶC TTCK Việt Nam (VN-Index, margin call HOSE, ATO/ATC). Luân phiên giữa US và VN để đa dạng.
- 3 lựa chọn rõ ràng, chỉ 1 đúng.
- Giải thích ngắn gọn 1-2 câu, mang tính phòng thủ (không xúi mua bán cổ phiếu cụ thể, không dự đoán giá).
- Song ngữ Việt + Anh.

Trả về CHỈ JSON thuần (không markdown, không giải thích thêm):
{{"q_vi":"...","q_en":"...","opts_vi":["A","B","C"],"opts_en":["A","B","C"],"answer_vi":"...","answer_en":"...","explain_vi":"...","explain_en":"..."}}"""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "", 1).strip()
        data = json.loads(text)
        save_custom_challenge(
            -1, today_str,
            data["q_vi"], data["q_en"],
            data["opts_vi"], data["opts_en"],
            data["answer_vi"], data["answer_en"],
            data.get("explain_vi", ""), data.get("explain_en", ""),
            source="ai_auto"
        )
        return True
    except Exception:
        return False


def page_daily_challenge():
    import hashlib
    from datetime import date as date_cls

    st.header(t("⚡ Daily Challenge", "⚡ Daily Challenge"))
    st.caption(t(
        "1 câu hỏi mới mỗi ngày — luyện phản xạ quyết định đầu tư",
        "1 new question every day — train your investment decision reflexes"
    ))

    today = date_cls.today()
    today_str = today.isoformat()
    user = st.session_state.user

    # Priority: 1) Admin custom, 2) AI (auto or manual), 3) Auto-generate now, 4) Static bank fallback
    custom = get_custom_challenge(today_str)

    # Auto-generate once per day if no question exists yet (shared for all users)
    if not custom:
        with st.spinner(t("Đang chuẩn bị câu hỏi hôm nay...", "Preparing today's question...")):
            if _auto_generate_daily_challenge(today_str):
                custom = get_custom_challenge(today_str)

    if custom:
        challenge_data = {
            "q": custom[f"q_{st.session_state.lang}"],
            "options": custom[f"opts_{st.session_state.lang}"],
            "answer": custom[f"answer_{st.session_state.lang}"],
            "explain": custom[f"explain_{st.session_state.lang}"],
            "source": custom.get("source", "admin"),
        }
        src = custom.get("source", "admin")
        if src == "admin":
            st.info(t("✍️ Câu hỏi do Admin biên soạn hôm nay", "✍️ Admin-curated question for today"))
        else:
            st.info(t("🤖 Câu hỏi do AI tạo tự động theo bối cảnh thị trường", "🤖 AI auto-generated from current market context"))
    else:
        # Fall back to static bank if AI generation failed
        day_hash = int(hashlib.md5(today_str.encode()).hexdigest(), 16)
        q = DAILY_CHALLENGES[day_hash % len(DAILY_CHALLENGES)]
        challenge_data = {
            "q": q[f"q_{st.session_state.lang}"],
            "options": q[f"options_{st.session_state.lang}"],
            "answer": q[f"answer_{st.session_state.lang}"],
            "explain": q[f"explain_{st.session_state.lang}"],
            "source": "static",
        }

    st.divider()
    st.subheader(t(f"📅 Ngày {today.strftime('%d/%m/%Y')}", f"📅 {today.strftime('%B %d, %Y')}"))

    with st.container(border=True):
        st.markdown(f"**{challenge_data['q']}**")
        opts = challenge_data["options"]
        answer = challenge_data["answer"]

        choice = st.radio(
            t("Lựa chọn của bạn:", "Your choice:"),
            opts, key=f"daily_{today_str}"
        )

        if st.button(t("✅ Xác nhận", "✅ Confirm"), type="primary", key="daily_submit"):
            if choice == answer:
                st.success(t("🟢 Đúng! Tư duy kỷ luật.", "🟢 Correct! Disciplined thinking."))
                st.balloons()
                if user["id"] != -1:
                    save_feed_event(user["id"], "daily_correct",
                        t("Trả lời đúng Daily Challenge", "Answered Daily Challenge correctly"))
            else:
                st.error(t(f"🔴 Sai. Đáp án: **{answer}**", f"🔴 Wrong. Answer: **{answer}**"))
            st.info(challenge_data["explain"])

    st.divider()
    st.caption(t(
        "Câu hỏi mới mỗi ngày, tự động tạo bởi AI theo bối cảnh thị trường (US + VN). Quay lại mỗi ngày để luyện tập.",
        "A new AI-generated question every day based on market context (US + VN). Come back daily to practice."
    ))

    # Admin can force regenerate today's AI question
    if user.get("username") == "admin" and user["id"] != -1 and custom and custom.get("source") in ("ai_auto", "ai"):
        if st.button(t("🔄 Tạo lại câu AI hôm nay", "🔄 Regenerate today's AI question"), key="regen_ai_daily"):
            with st.spinner(t("Đang tạo lại...", "Regenerating...")):
                if _auto_generate_daily_challenge(today_str):
                    st.success(t("✅ Đã tạo câu mới!", "✅ New question generated!"))
                    st.rerun()
                else:
                    st.error(t("Tạo thất bại, thử lại.", "Generation failed, try again."))

    # Admin form
    if user.get("username") == "admin" and user["id"] != -1:
        st.divider()
        with st.expander(t("✍️ Admin — Tạo câu hỏi cho ngày cụ thể", "✍️ Admin — Create question for specific date"), expanded=False):
            from datetime import date as date_cls
            target_date = st.date_input(t("Ngày áp dụng:", "Target date:"), value=date_cls.today())
            target_str = target_date.isoformat()

            st.markdown(f"**{t('Câu hỏi tiếng Việt', 'Vietnamese question')}**")
            aq_vi = st.text_area("q_vi", height=60, key="adq_vi", label_visibility="collapsed", placeholder="Tình huống: ...")
            st.markdown(f"**{t('Câu hỏi tiếng Anh', 'English question')}**")
            aq_en = st.text_area("q_en", height=60, key="adq_en", label_visibility="collapsed", placeholder="Situation: ...")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Options VI** (mỗi dòng 1 lựa chọn)")
                opts_vi_raw = st.text_area("opts_vi", height=80, key="adopts_vi", label_visibility="collapsed", placeholder="Lựa chọn A / B / C")
                ans_vi = st.text_input(t("Đáp án đúng (VI)", "Correct answer (VI)"), key="adans_vi")
            with col2:
                st.markdown("**Options EN** (one per line)")
                opts_en_raw = st.text_area("opts_en", height=80, key="adopts_en", label_visibility="collapsed", placeholder="Option A / B / C")
                ans_en = st.text_input("Correct answer (EN)", key="adans_en")

            explain_vi = st.text_area(t("Giải thích (VI)", "Explanation (VI)"), height=60, key="adexp_vi")
            explain_en = st.text_area("Explanation (EN)", height=60, key="adexp_en")

            if st.button(t("💾 Lưu câu hỏi", "💾 Save question"), type="primary", key="save_admin_challenge"):
                opts_vi_list = [o.strip() for o in opts_vi_raw.strip().splitlines() if o.strip()]
                opts_en_list = [o.strip() for o in opts_en_raw.strip().splitlines() if o.strip()]
                if not aq_vi or not aq_en or not opts_vi_list or not ans_vi:
                    st.error(t("Vui lòng điền đầy đủ.", "Please fill in all fields."))
                else:
                    save_custom_challenge(
                        user["id"], target_str, aq_vi, aq_en,
                        opts_vi_list, opts_en_list, ans_vi, ans_en,
                        explain_vi, explain_en, source="admin"
                    )
                    st.success(t(f"✅ Đã lưu câu hỏi cho ngày {target_str}!", f"✅ Question saved for {target_str}!"))
                    st.rerun()

        # Show recent custom challenges
        recent = get_recent_custom_challenges(5)
        if recent:
            st.divider()
            st.markdown(t("**Câu hỏi tùy chỉnh gần nhất:**", "**Recent custom questions:**"))
            for r in recent:
                src_icon = "✍️" if r.get("source") == "admin" else "🤖"
                st.markdown(f"{src_icon} `{r['date_str']}` — {r['q_vi'][:60]}...")


def page_liquidity_check():
    st.header(t("🎣 Bạn có đang là thanh khoản không?", "🎣 Are You the Liquidity?"))
    st.caption(t(
        "Tự kiểm tra: bạn đang là 'cá con' bị săn, hay nhà đầu tư kỷ luật? Trả lời thật lòng.",
        "Self-check: are you the hunted 'small fish', or a disciplined investor? Answer honestly."
    ))

    st.divider()
    st.markdown(t(
        "**Đánh dấu những điều ĐÚNG với bạn:**",
        "**Check everything that is TRUE for you:**"
    ))

    checked = []
    for i, item in enumerate(LIQUIDITY_CHECKLIST):
        val = st.checkbox(item[st.session_state.lang], key=f"liq_{i}")
        if val:
            checked.append(i)

    st.divider()

    if st.button(t("🔍 Xem kết quả", "🔍 See Result"), type="primary", use_container_width=True):
        n = len(checked)
        total = len(LIQUIDITY_CHECKLIST)

        st.markdown("###  ")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(t("Dấu hiệu rủi ro", "Risk signals"), f"{n}/{total}")

        with col2:
            if n == 0:
                st.success(t(
                    "🟢 **Tuyệt vời.** Bạn không có dấu hiệu nào của 'cá con bị săn'. Hãy duy trì kỷ luật này.",
                    "🟢 **Excellent.** You show no signs of the 'hunted small fish'. Keep this discipline."
                ))
            elif n <= 2:
                st.info(t(
                    "🟡 **Khá tốt.** Bạn chỉ có vài thói quen rủi ro. Tập trung sửa chúng để không bị săn.",
                    "🟡 **Pretty good.** You have only a few risky habits. Focus on fixing them to avoid being hunted."
                ))
            elif n <= 5:
                st.warning(t(
                    "🟠 **Cảnh báo.** Bạn có nhiều thói quen khiến mình trở thành thanh khoản cho người khác. Cần sửa ngay.",
                    "🟠 **Warning.** You have several habits that make you liquidity for others. Fix them now."
                ))
            else:
                st.error(t(
                    "🔴 **Nguy hiểm.** Bạn đang là 'cá con' điển hình mà thị trường săn. Đây là lý do chính khiến tài khoản bị bào mòn.",
                    "🔴 **Dangerous.** You are a textbook 'small fish' the market hunts. This is the main reason accounts get eroded."
                ))

        if checked:
            st.divider()
            st.markdown(t("**Những điểm bạn cần sửa:**", "**What you need to fix:**"))
            # Map each checklist item to a fix
            fixes_vi = [
                "Đừng đuổi giá. Chờ điểm vào hợp lý hoặc bỏ qua. FOMO là cách nhanh nhất để mua đỉnh.",
                "Đặt stop theo cấu trúc riêng (dưới swing low thật, theo ATR), không phải chỗ tròn trịa ai cũng thấy.",
                "Margin khi Risk-off = tự biến mình thành mồi cho stop hunt. Chỉ dùng margin khi Risk-on rõ ràng.",
                "Tin đồn không phải bằng chứng. Luôn kiểm tra giá + volume + regime trước khi hành động.",
                "Định nghĩa điểm thoát (invalidation) TRƯỚC khi vào lệnh. Vào vì lý do, ra vì lý do — không vì cảm xúc.",
                "Đánh giá quyết định bằng quy trình, không phải cái tôi. Cắt lỗ theo kế hoạch, để lãi chạy theo cấu trúc.",
                "Đoán đỉnh/đáy là sân chơi của smart money. Cá con thắng bằng cách đi theo xác nhận, không phải dự đoán.",
                "Revenge trading là lỗi cảm xúc nguy hiểm nhất. Sau khi thua, dừng lại — không vào lệnh khi đang tức.",
                "Phá hỗ trợ có thể là bear trap. Đừng bán tháo theo hoảng loạn — kiểm tra bằng chứng trước.",
                "Regime First: luôn kiểm tra trạng thái thị trường trước. Setup đẹp trong Risk-off vẫn là No Trade.",
            ]
            fixes_en = [
                "Don't chase. Wait for a rational entry or skip it. FOMO is the fastest way to buy the top.",
                "Place stops by your own structure (below real swing lows, by ATR), not round numbers everyone sees.",
                "Margin in Risk-off = making yourself stop-hunt bait. Only use margin in clear Risk-on.",
                "Rumors aren't evidence. Always check price + volume + regime before acting.",
                "Define your exit (invalidation) BEFORE entering. Enter for a reason, exit for a reason — not emotion.",
                "Judge decisions by process, not ego. Cut losses per plan, let winners run by structure.",
                "Predicting tops/bottoms is smart money's game. Small fish win by following confirmation, not predicting.",
                "Revenge trading is the most dangerous emotional error. After a loss, stop — don't trade angry.",
                "A support break can be a bear trap. Don't panic-sell — check evidence first.",
                "Regime First: always check market state first. A great setup in Risk-off is still No Trade.",
            ]
            fixes = fixes_vi if st.session_state.lang == "vi" else fixes_en
            for idx in checked:
                st.markdown(f"- {fixes[idx]}")

        st.divider()
        st.info(t(
            "💡 Đọc Bài 11 — *Biết ta: Vì sao cá con bị săn* để hiểu sâu hơn cách sống sót.",
            "💡 Read Lesson 11 — *Know Yourself: Why Small Fish Get Hunted* to understand survival better."
        ))


def page_why():
    st.markdown("""
<style>
.pain-box { background: rgba(220,38,38,0.08); border-left: 4px solid #DC2626;
    padding: 1rem 1.25rem; border-radius: 0 8px 8px 0; margin: 0.5rem 0; }
.solution-box { background: rgba(5,150,105,0.08); border-left: 4px solid #059669;
    padding: 1rem 1.25rem; border-radius: 0 8px 8px 0; margin: 0.5rem 0; }
.stat-box { background: rgba(29,78,216,0.1); border-radius: 10px;
    padding: 1rem; text-align: center; margin: 0.25rem 0; }
.stat-num { font-size: 28px; font-weight: 700; color: #60A5FA; }
.stat-lbl { font-size: 13px; color: #94A3B8; margin-top: 4px; }
.testimonial { background: rgba(148,163,184,0.08); border-radius: 10px;
    padding: 1rem 1.25rem; margin: 0.5rem 0; font-style: italic; }
</style>
""", unsafe_allow_html=True)

    lang = st.session_state.lang

    if lang == "vi":
        st.title("Bạn đã từng mắc những lỗi này chưa?")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('''<div class="pain-box">
📌 Mua đỉnh vì sợ bỏ lỡ sóng, rồi ôm lỗ không dám cắt
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 All-in vào một mã, thị trường quay đầu, tài khoản -40%
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 Margin call lúc 10h sáng, forced sell đúng đáy
</div>''', unsafe_allow_html=True)

        with col2:
            st.markdown('''<div class="pain-box">
📌 Nghe tin nội bộ, mua vào, giá giảm ngay hôm sau
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 Lãi rồi không chốt, giá đảo chiều, lỗ thay vì lãi
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 Biết thị trường xấu nhưng vẫn FOMO theo đám đông
</div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Vấn đề không phải là bạn thiếu thông tin.")
        st.markdown("""
Internet có đầy **tin tức, phân tích, khuyến nghị, chỉ báo kỹ thuật.**

Nhưng không ai dạy bạn:

- **Khi nào KHÔNG nên mua** — dù setup trông rất đẹp
- **Khi nào nên đứng ngoài** — dù thấy cơ hội ở khắp nơi
- **Làm sao kiểm soát FOMO** — khi thấy người khác đang lãi
- **Tại sao lãi nhưng vẫn đang đi sai hướng**
""")

        st.markdown("---")
        st.subheader("App này dạy 4 nguyên tắc cốt lõi:")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown('''<div class="solution-box">
🛡️ **Risk First**<br>Trước khi hỏi "lãi bao nhiêu?", hỏi "nếu sai mất bao nhiêu?"
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="solution-box">
🔬 **Evidence First**<br>Chỉ hành động khi có đủ bằng chứng. Không có bằng chứng = không trade.
</div>''', unsafe_allow_html=True)
        with col4:
            st.markdown('''<div class="solution-box">
📡 **Regime First**<br>Thị trường không phải lúc nào cũng đáng tham gia. Học cách nhận biết.
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="solution-box">
⚖️ **Governance**<br>Lớp kiểm soát cuối — ngăn FOMO, ngăn oversizing, ngăn revenge trading.
</div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Mục tiêu thật sự:")
        st.markdown("""
Không phải trở thành người **dự đoán đúng nhiều nhất.**

Mà trở thành người:

> **Sống sót lâu nhất · Mắc ít sai lầm nghiêm trọng nhất · Duy trì kỷ luật trong dài hạn**
""")

        st.markdown("---")
        st.subheader("🔄 App động — cập nhật theo thị trường thật:")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.markdown('''<div class="solution-box">
🤖 <strong>AI Coach</strong><br>Phân tích quyết định giao dịch thật của bạn — chỉ ra bias và lỗi quy trình theo thời gian thực.
</div>''', unsafe_allow_html=True)
        with col_d2:
            st.markdown('''<div class="solution-box">
📡 <strong>Regime Radar</strong><br>Mỗi tuần admin cập nhật: VN-Index đang ở regime nào, tại sao, và nên làm gì.
</div>''', unsafe_allow_html=True)
        with col_d3:
            st.markdown('''<div class="solution-box">
📊 <strong>Portfolio Risk Checker</strong><br>Nhập danh mục đang nắm — app tính tổng rủi ro và cảnh báo concentrated bet ngay lập tức.
</div>''', unsafe_allow_html=True)

        st.markdown("---")
        col5, col6, col7 = st.columns(3)
        with col5:
            st.markdown('''<div class="stat-box"><div class="stat-num">11</div>
<div class="stat-lbl">Bài học nền tảng</div></div>''', unsafe_allow_html=True)
        with col6:
            st.markdown('''<div class="stat-box"><div class="stat-num">17</div>
<div class="stat-lbl">Historical scenarios (incl. VN)</div></div>''', unsafe_allow_html=True)
        with col7:
            st.markdown('''<div class="stat-box"><div class="stat-num">29+</div>
<div class="stat-lbl">Quiz questions thực chiến</div></div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
**Liên hệ & hỗ trợ**

📧 nguyennguyettam9120@gmail.com &nbsp;·&nbsp; 📱 +84 943 620 253

*© 2025 Nguyễn Thị Nguyệt Tâm. All rights reserved. Bảo hộ SHTT Việt Nam.*
""")

    else:
        st.title("Have you made these mistakes?")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('''<div class="pain-box">
📌 Bought the top out of FOMO, then couldn't cut the loss
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 Went all-in on one stock, market reversed, account down 40%
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 Margin call at 10am, force-sold exactly at the bottom
</div>''', unsafe_allow_html=True)
        with col2:
            st.markdown('''<div class="pain-box">
📌 Acted on insider tip, price dropped the next day
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 In profit but didn't take it — price reversed into a loss
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="pain-box">
📌 Knew the market was bad but FOMO'd in with the crowd anyway
</div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("The problem is not that you lack information.")
        st.markdown("""
The internet is full of **news, analysis, recommendations, and technical indicators.**

But nobody teaches you:

- **When NOT to buy** — even when the setup looks great
- **When to stay out** — even when opportunities seem everywhere
- **How to control FOMO** — when you see others making money
- **Why you can be profitable and still be doing it wrong**
""")

        st.markdown("---")
        st.subheader("This app teaches 4 core principles:")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown('''<div class="solution-box">
🛡️ **Risk First**<br>Before asking "how much can I gain?", ask "how much can I lose if wrong?"
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="solution-box">
🔬 **Evidence First**<br>Only act when evidence is sufficient. No evidence = no trade.
</div>''', unsafe_allow_html=True)
        with col4:
            st.markdown('''<div class="solution-box">
📡 **Regime First**<br>The market is not always worth participating in. Learn to recognize when.
</div>''', unsafe_allow_html=True)
            st.markdown('''<div class="solution-box">
⚖️ **Governance**<br>Final control layer — prevents FOMO, oversizing, and revenge trading.
</div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("The real goal:")
        st.markdown("""
Not to become the best predictor.

But to become the investor who:

> **Survives the longest · Makes the fewest catastrophic mistakes · Maintains discipline over time**
""")

        st.markdown("---")
        st.subheader("🔄 A live app — updated with real market data:")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.markdown('''<div class="solution-box">
🤖 <strong>AI Coach</strong><br>Analyzes your real trading decisions — identifies biases and process errors in real time.
</div>''', unsafe_allow_html=True)
        with col_d2:
            st.markdown('''<div class="solution-box">
📡 <strong>Regime Radar</strong><br>Updated weekly: what regime VN-Index is in, why, and what to do.
</div>''', unsafe_allow_html=True)
        with col_d3:
            st.markdown('''<div class="solution-box">
📊 <strong>Portfolio Risk Checker</strong><br>Enter your holdings — app calculates total risk and warns about concentrated bets instantly.
</div>''', unsafe_allow_html=True)

        st.markdown("---")
        col5, col6, col7 = st.columns(3)
        with col5:
            st.markdown('''<div class="stat-box"><div class="stat-num">11</div>
<div class="stat-lbl">Core lessons</div></div>''', unsafe_allow_html=True)
        with col6:
            st.markdown('''<div class="stat-box"><div class="stat-num">17</div>
<div class="stat-lbl">Historical scenarios (incl. VN)</div></div>''', unsafe_allow_html=True)
        with col7:
            st.markdown('''<div class="stat-box"><div class="stat-num">29+</div>
<div class="stat-lbl">Real-world quiz questions</div></div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
**Contact & Support**

📧 nguyennguyettam9120@gmail.com &nbsp;·&nbsp; 📱 +84 943 620 253

*© 2025 Nguyễn Thị Nguyệt Tâm. All rights reserved.*
""")



def page_admin():
    st.header("🛠️ Admin Dashboard")
    if st.button(t("← Quay lại app", "← Back to app"), key="admin_back"):
        st.session_state["show_admin"] = False
        st.rerun()

    stats = admin_get_stats()
    tab1, tab2, tab3, tab4 = st.tabs([
        t("📊 Tổng quan", "📊 Overview"),
        t("👤 Người dùng", "👤 Users"),
        t("💳 Thanh toán", "💳 Payments"),
        t("📡 Cập nhật tuần", "📡 Weekly Update"),
    ])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("Tổng user", "Total users"), stats["total_users"])
        c2.metric(t("Pro", "Pro"), stats["pro_users"])
        c3.metric(t("Free", "Free"), stats["free_users"])
        c4.metric(t("Mới (7 ngày)", "New (7d)"), stats["new_7d"])
        c5, c6, c7, c8 = st.columns(4)
        c5.metric(t("Active (7d)", "Active (7d)"), stats["active_7d"])
        c6.metric(t("Nhật ký", "Journals"), stats["total_journal"])
        c7.metric(t("Historical", "Historical"), stats["total_hist"])
        c8.metric(t("Challenges", "Challenges"), stats["total_challenges"])

        # Revenue estimate
        st.divider()
        mrr = stats["pro_users"] * 99000
        st.metric(t("Doanh thu ước tính/tháng (MRR)", "Est. Monthly Revenue (MRR)"), f"{mrr:,} ₫")

        # Signups chart
        signups = admin_get_daily_signups(30)
        if signups:
            st.subheader(t("Đăng ký mới (30 ngày)", "New signups (30 days)"))
            df_s = pd.DataFrame(signups)
            st.bar_chart(df_s.set_index("day")["count"])

    with tab2:
        users = admin_get_all_users()
        st.subheader(t(f"Danh sách {len(users)} người dùng", f"{len(users)} users"))
        df_u = pd.DataFrame(users)
        if not df_u.empty:
            show_cols = ["id", "username", "email", "plan", "created_at", "last_login", "journal_count"]
            show_cols = [c for c in show_cols if c in df_u.columns]
            st.dataframe(df_u[show_cols], use_container_width=True, hide_index=True)

        st.divider()
        st.markdown(t("**Quản lý user:**", "**Manage user:**"))
        col1, col2, col3 = st.columns(3)
        with col1:
            uid = st.number_input(t("User ID", "User ID"), min_value=1, step=1, key="admin_uid")
        with col2:
            new_plan = st.selectbox(t("Đặt gói", "Set plan"), ["free", "pro"], key="admin_plan")
            if st.button(t("Cập nhật gói", "Update plan"), key="admin_setplan"):
                admin_set_plan(int(uid), new_plan)
                st.success(f"User {uid} → {new_plan}")
                st.rerun()
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(t("🗑️ Xóa user", "🗑️ Delete user"), key="admin_del"):
                admin_delete_user(int(uid))
                st.warning(f"User {uid} deleted")
                st.rerun()

    with tab3:
        st.subheader(t("Đơn thanh toán chờ xác nhận", "Pending payment orders"))
        pending = get_pending_payments()
        if pending:
            for p in pending:
                cols = st.columns([3, 1])
                cols[0].markdown(f"`{p['order_code']}` — **{p['username']}** ({p['email']}) — {p['amount']:,}₫ — {p['method']}")
                if cols[1].button(t("✅ Xác nhận", "✅ Confirm"), key=f"adm_confirm_{p['order_code']}"):
                    ok, uid = mark_payment_paid(p["order_code"])
                    if ok:
                        st.success(t(f"Đã kích hoạt Pro cho {p['username']}", f"Activated Pro for {p['username']}"))
                        st.rerun()
        else:
            st.info(t("Không có đơn nào đang chờ.", "No pending orders."))

        st.divider()
        st.markdown(t("**Trạng thái tích hợp:**", "**Integration status:**"))
        st.markdown(f"- {'✅' if integrations.is_email_configured() else '❌'} Welcome Email (Gmail)")
        st.markdown(f"- {'✅' if integrations.is_payos_configured() else '❌'} PayOS Payment")

    with tab4:
        st.subheader(t("📡 Cập nhật Regime Radar", "📡 Update Regime Radar"))
        from datetime import date as date_cls
        today = date_cls.today()
        wk = today.isocalendar()[1]
        default_wk = f"Tuần {wk}/{today.year}"
        c1, c2 = st.columns(2)
        with c1:
            week_label = st.text_input(t("Nhãn tuần", "Week label"), value=default_wk, key="adm_rr_wk")
            vix_val = st.number_input("VIX", min_value=0.0, value=20.0, step=0.5, key="adm_rr_vix")
            vn_ma = st.selectbox("VN-Index vs MA200", ["Trên MA200", "Dưới MA200", "Sát MA200"], key="adm_rr_vn")
        with c2:
            breadth = st.selectbox("Breadth", ["Mạnh", "Trung tính", "Yếu", "Sụp đổ"], key="adm_rr_br")
            credit = st.selectbox(t("Tín dụng/Lãi suất", "Credit/Rates"), ["Ổn định", "Tăng nhẹ", "Căng thẳng", "Khủng hoảng"], key="adm_rr_cr")
            margin = st.selectbox("Margin", ["Bình thường", "Đang tăng", "Đang giảm chấp", "Force-sell đang xảy ra"], key="adm_rr_mg")
        regime_call = st.selectbox(t("🎯 Kết luận Regime", "🎯 Regime call"), ["Risk-on", "Mixed", "Risk-off"], key="adm_rr_rc")
        note_vi = st.text_area(t("Nhận xét (VI)", "Note (VI)"), height=80, key="adm_rr_nvi")
        note_en = st.text_area(t("Nhận xét (EN)", "Note (EN)"), height=80, key="adm_rr_nen")
        if st.button(t("💾 Lưu Regime Radar", "💾 Save Regime Radar"), type="primary", key="adm_rr_save"):
            save_regime_radar(st.session_state.user["id"], week_label, vix_val, vn_ma,
                              breadth, credit, margin, regime_call, note_vi, note_en)
            st.success(t("✅ Đã lưu!", "✅ Saved!"))



def main():
    if not st.session_state.user:
        page_auth()
        return

    if not st.session_state.onboarding_done:
        page_onboarding()
        return

    # Auto-verify PayOS payment from return URL (?paid=ORDERCODE)
    try:
        qp = st.query_params
        if "paid" in qp and st.session_state.user["id"] != -1:
            oc = qp["paid"]
            ps = get_payment_status(oc)
            if ps and ps["status"] != "paid":
                ok, status = integrations.check_payos_payment(oc)
                if ok and status == "PAID":
                    mark_payment_paid(oc)
                    st.session_state.user["plan"] = "pro"
                    st.success(t("🎉 Thanh toán thành công! Bạn đã là Pro.", "🎉 Payment successful! You're now Pro."))
                    st.balloons()
            st.query_params.clear()
    except Exception:
        pass

    # Track daily activity for streak + milestone feed
    if st.session_state.user["id"] != -1:
        record_daily_activity(st.session_state.user["id"])
        streak, _ = get_streak(st.session_state.user["id"])
        if streak in (7, 14, 30, 50, 100) and streak > 0:
            save_feed_event(st.session_state.user["id"], "streak_milestone",
                t(f"Đạt streak {streak} ngày 🔥", f"Hit {streak}-day streak 🔥"))

    # Admin dashboard override
    if st.session_state.get("show_admin") and is_admin(st.session_state.user.get("username","")):
        page_admin()
        return

    menu = show_sidebar()

    # Route
    routing = {
        t("Bắt đầu từ đây", "Start Here"): page_start_here,
        t("Bài học", "Lessons"): page_lessons,
        "Quiz": page_quiz,
        t("Checklist trước khi mua", "Pre-Buy Checklist"): page_checklist,
        t("Decision Simulator", "Decision Simulator"): page_decision_simulator,
        t("Market Regime Training", "Market Regime Training"): page_market_regime,
        t("Historical Simulator", "Historical Simulator"): page_historical_simulator,
        t("Investment Challenge", "Investment Challenge"): page_investment_challenge,
        t("Post-Mortem Trainer", "Post-Mortem Trainer"): page_post_mortem,
        t("Behavior Diagnosis", "Behavior Diagnosis"): page_behavior_diagnosis,
        t("Bias Engine", "Bias Engine"): page_bias_engine,
        t("Adaptive Curriculum", "Adaptive Curriculum"): page_adaptive_curriculum,
        t("Learning Forecast", "Learning Forecast"): page_learning_forecast,
        t("Progress Dashboard", "Progress Dashboard"): page_progress_dashboard,
        t("Mastery Score", "Mastery Score"): page_mastery_score,
        t("Learning Memory", "Learning Memory"): page_learning_memory,
        t("Learning Trend", "Learning Trend"): page_learning_trend,
        t("Scenario Coverage", "Scenario Coverage"): page_scenario_coverage,
        t("Historical Dashboard", "Historical Dashboard"): page_historical_dashboard,
        t("Regime Taxonomy", "Regime Taxonomy"): page_regime_taxonomy,
        t("Gamification", "Gamification"): page_gamification,
        t("Nhật ký quyết định", "Decision Journal"): page_journal,
        t("Điểm kỷ luật", "Discipline Score"): page_discipline_score,
        t("Thông tin tài khoản", "Account Info"): page_account,
        t("Nâng cấp Pro", "Upgrade to Pro"): lambda: (st.header(t("⭐ Nâng cấp Pro", "⭐ Upgrade to Pro")), show_upgrade_cta()),
        t("Vì sao cần app này?", "Why This App?"): page_why,
        t("⚡ Daily Challenge", "⚡ Daily Challenge"): page_daily_challenge,
        t("🏆 Leaderboard", "🏆 Leaderboard"): page_leaderboard,
        t("👥 Cộng đồng", "👥 Community"): page_community,
        t("🎁 Giới thiệu bạn bè", "🎁 Refer Friends"): page_referral,
        t("🎣 Bạn có là thanh khoản?", "🎣 Are You the Liquidity?"): page_liquidity_check,
        t("🌅 Routine sáng", "🌅 Morning Routine"): page_morning_routine,
        t("🌙 Routine tối", "🌙 Evening Routine"): page_evening_routine,
        t("📰 Góc thị trường", "📰 Market Corner"): page_market_news,
        t("🤖 AI Coach", "🤖 AI Coach"): page_ai_coach,
        t("📡 Regime Radar", "📡 Regime Radar"): page_regime_radar,
        t("📊 Portfolio Risk", "📊 Portfolio Risk"): page_portfolio_risk,
    }

    page_fn = routing.get(menu)
    if page_fn:
        page_fn()
    else:
        # Fallback: try matching by value
        for k, fn in routing.items():
            if k == menu:
                fn()
                break
        else:
            page_start_here()



# ─── AI COACH ──────────────────────────────────────────────────────────────────

def page_ai_coach():
    st.header(t("🤖 AI Coach", "🤖 AI Coach"))
    gate_pro("AI Coach")

    st.caption(t(
        "Mô tả quyết định giao dịch của bạn — AI sẽ phân tích bias, chỉ ra lỗi quy trình và gợi ý cải thiện.",
        "Describe your trading decision — AI will analyze bias, identify process errors, and suggest improvements."
    ))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input(t("Mã tài sản", "Asset / Ticker"), placeholder="VD: VNM, BTC, NVDA")
        action = st.selectbox(t("Hành động", "Action"), ["BUY", "SELL", "HOLD", "NO TRADE"])
        regime = st.selectbox(t("Bạn đánh giá regime hiện tại là?", "Your regime assessment?"), ["Risk-on", "Mixed", "Risk-off", t("Chưa kiểm tra", "Not checked")])
    with col2:
        reason = st.text_area(t("Lý do quyết định (càng chi tiết càng tốt)", "Reason for decision (more detail = better analysis)"), height=120, placeholder=t(
            "VD: Thấy cổ phiếu tăng mạnh 3 ngày liên tiếp, mọi người trên group đang mua, tôi sợ bỏ lỡ nên muốn vào...",
            "E.g. Stock surged 3 days, everyone in my group is buying, I'm afraid of missing out..."
        ))
        emotion = st.selectbox(t("Cảm xúc khi quyết định", "Emotion when deciding"), 
            [t("Bình tĩnh", "Calm"), "FOMO", t("Sợ hãi", "Fear"), t("Tham lam", "Greed"), t("Tức giận / Revenge", "Anger / Revenge"), t("Không chắc", "Uncertain")])
        stop_loss = st.text_input(t("Stop-loss đặt ở đâu?", "Where is your stop-loss?"), placeholder=t("VD: -5% hoặc dưới MA20", "E.g. -5% or below MA20"))

    risk_pct = st.slider(t("% tài khoản bạn định dùng", "% of account you plan to use"), 0, 100, 10, 5)

    # AI usage limit check
    user = st.session_state.user
    AI_LIMIT = 20
    ai_used = get_ai_usage(user["id"], "ai_coach") if user["id"] != -1 else 0
    if ai_used >= AI_LIMIT:
        st.warning(t(
            f"Bạn đã dùng {ai_used}/{AI_LIMIT} lần AI Coach tháng này. Giới hạn reset vào đầu tháng sau.",
            f"You've used {ai_used}/{AI_LIMIT} AI Coach calls this month. Limit resets next month."
        ))
    else:
        st.caption(t(f"Đã dùng: {ai_used}/{AI_LIMIT} lần tháng này", f"Used: {ai_used}/{AI_LIMIT} this month"))

    if st.button(t("🤖 Phân tích quyết định này", "🤖 Analyze this decision"), type="primary", use_container_width=True, disabled=(ai_used >= AI_LIMIT)):
        if not reason.strip():
            st.error(t("Vui lòng mô tả lý do quyết định.", "Please describe your reason."))
            return

        with st.spinner(t("AI đang phân tích...", "AI is analyzing...")):
            try:
                client = anthropic.Anthropic()
                lang = st.session_state.lang

                if lang == "vi":
                    system_prompt = """Bạn là AI Coach chuyên về tâm lý và kỷ luật đầu tư. 
Nhiệm vụ: phân tích quyết định giao dịch của nhà đầu tư và chỉ ra:
1. Bias tâm lý đang hiện diện (FOMO, Overconfidence, Herd Mentality, Revenge Trading, Action Bias...)
2. Lỗi quy trình (không kiểm tra regime, không có stop-loss, size quá lớn...)
3. Điểm mạnh nếu có
4. Gợi ý cụ thể để cải thiện

Luôn trả lời bằng tiếng Việt. Thẳng thắn nhưng mang tính xây dựng. 
Dùng format: 🔴 Bias phát hiện / 🟡 Cảnh báo / ✅ Điểm tốt / 💡 Gợi ý
Giữ phân tích ngắn gọn, thực tế, không hoa mỹ."""
                    user_msg = f"""Phân tích quyết định sau:
- Mã: {ticker or "không rõ"}
- Hành động: {action}
- Lý do: {reason}
- Cảm xúc: {emotion}
- Đánh giá regime: {regime}
- Stop-loss: {stop_loss or "chưa đặt"}
- % tài khoản: {risk_pct}%"""
                else:
                    system_prompt = """You are an AI Coach specializing in investment psychology and discipline.
Task: analyze the trader's decision and identify:
1. Psychological biases present (FOMO, Overconfidence, Herd Mentality, Revenge Trading, Action Bias...)
2. Process errors (not checking regime, no stop-loss, oversizing...)
3. Strengths if any
4. Specific improvement suggestions

Always respond in English. Be direct but constructive.
Use format: 🔴 Bias detected / 🟡 Warning / ✅ Strength / 💡 Suggestion
Keep analysis concise and practical."""
                    user_msg = f"""Analyze this decision:
- Asset: {ticker or "unspecified"}
- Action: {action}
- Reason: {reason}
- Emotion: {emotion}
- Regime assessment: {regime}
- Stop-loss: {stop_loss or "not set"}
- % of account: {risk_pct}%"""

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_msg}]
                )
                analysis = response.content[0].text
                track_ai_usage(user["id"], "ai_coach")

                st.divider()
                st.subheader(t("📋 Phân tích AI Coach", "📋 AI Coach Analysis"))
                st.markdown(analysis)

                # Risk warning overlay
                if risk_pct > 20:
                    st.error(t(
                        f"🚨 **CẢNH BÁO:** {risk_pct}% tài khoản là quá lớn. Nguyên tắc Risk First: tối đa 2% risk/lệnh.",
                        f"🚨 **WARNING:** {risk_pct}% of account is too large. Risk First principle: max 2% risk per trade."
                    ))
                if stop_loss.strip() == "" or stop_loss == t("chưa đặt", "not set"):
                    st.error(t(
                        "🚨 **KHÔNG CÓ STOP-LOSS** — Đây là lỗi quy trình nghiêm trọng nhất. Luôn biết mình sẽ thoát ở đâu trước khi vào.",
                        "🚨 **NO STOP-LOSS** — This is the most critical process error. Always know your exit before entering."
                    ))

            except Exception as e:
                st.error(t(
                    f"Lỗi kết nối AI: {str(e)}. Vui lòng thử lại.",
                    f"AI connection error: {str(e)}. Please try again."
                ))

    st.divider()
    st.caption(t(
        "AI Coach dùng Claude AI để phân tích. Đây là công cụ học tập, không phải tư vấn tài chính.",
        "AI Coach uses Claude AI for analysis. This is a learning tool, not financial advice."
    ))


# ─── REGIME RADAR ──────────────────────────────────────────────────────────────

def page_regime_radar():
    st.header(t("📡 Regime Radar — Tuần này", "📡 Regime Radar — This Week"))

    user = st.session_state.user
    plan = get_user_plan(user["id"]) if user["id"] != -1 else "free"

    # Show latest radar to everyone (read-only for free)
    latest = get_regime_radar_latest()

    if latest:
        # Regime color mapping
        regime_colors = {"Risk-on": "#059669", "Mixed": "#D97706", "Risk-off": "#DC2626"}
        rc = regime_colors.get(latest.get("regime_call", "Mixed"), "#D97706")

        st.markdown(f"""
<div style="background: rgba(29,78,216,0.08); border: 1px solid rgba(29,78,216,0.25);
border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
  <div>
    <span style="font-size:13px; color:#94A3B8">📅 {latest.get("week_label","")}</span><br>
    <span style="font-size:22px; font-weight:700; color:{rc}">
      {latest.get("regime_call","—")}
    </span>
  </div>
  <div style="text-align:right">
    <span style="font-size:11px; color:#64748B">Cập nhật bởi Admin</span>
  </div>
</div>
</div>
""", unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("VIX", f"{latest.get('vix','—')}")
        col2.metric("VN-Index vs MA200", latest.get("vn_vs_ma200", "—"))
        col3.metric("Breadth", latest.get("breadth", "—"))
        col4.metric("Credit/Lãi suất", latest.get("credit", "—"))
        col5.metric("Margin", latest.get("margin_status", "—"))

        st.divider()
        st.subheader(t("📝 Nhận xét tuần này", "📝 Weekly Commentary"))
        note = latest.get(f"note_{st.session_state.lang}", "")
        if note:
            st.markdown(note)
        else:
            st.info(t("Admin chưa thêm nhận xét cho tuần này.", "Admin hasn't added commentary for this week yet."))
    else:
        st.info(t(
            "📡 Regime Radar chưa có dữ liệu. Admin sẽ cập nhật mỗi đầu tuần.",
            "📡 Regime Radar has no data yet. Admin updates every start of week."
        ))

    # History chart - Pro only
    if plan == "pro":
        history = get_regime_radar_history(12)
        if len(history) >= 2:
            st.divider()
            st.subheader(t("📈 Lịch sử Regime (12 tuần)", "📈 Regime History (12 weeks)"))
            df_h = pd.DataFrame(history[::-1])
            regime_num = {"Risk-on": 3, "Mixed": 2, "Risk-off": 1}
            df_h["regime_num"] = df_h["regime_call"].map(regime_num)
            df_h["vix"] = pd.to_numeric(df_h["vix"], errors="coerce")

            fig = go.Figure()
            color_map = {3: "#059669", 2: "#D97706", 1: "#DC2626"}
            for _, row in df_h.iterrows():
                fig.add_trace(go.Bar(
                    x=[row["week_label"]], y=[row["regime_num"]],
                    marker_color=color_map.get(row["regime_num"], "#64748B"),
                    name=row["regime_call"],
                    showlegend=False,
                    text=row["regime_call"], textposition="inside",
                ))
            fig.update_layout(
                height=220, margin=dict(t=10, b=10),
                yaxis=dict(tickvals=[1,2,3], ticktext=["Risk-off","Mixed","Risk-on"]),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.divider()
        st.info(t(
            "⭐ **Pro** — Xem lịch sử Regime 12 tuần và nhận xét chi tiết mỗi tuần.",
            "⭐ **Pro** — View 12-week regime history and detailed weekly commentary."
        ))
        show_upgrade_cta()

    # Admin input section
    if user.get("username") == "admin" and user["id"] != -1:
        st.divider()
        with st.expander("⚙️ Admin — Cập nhật Regime Radar tuần này", expanded=False):
            from datetime import date as date_cls
            today = date_cls.today()
            week_num = today.isocalendar()[1]
            default_week = f"Tuần {week_num}/{today.year}"

            c1, c2 = st.columns(2)
            with c1:
                week_label = st.text_input("Nhãn tuần", value=default_week)
                vix_val = st.number_input("VIX", min_value=0.0, value=20.0, step=0.5)
                vn_ma = st.selectbox("VN-Index vs MA200", ["Trên MA200", "Dưới MA200", "Sát MA200"])
            with c2:
                breadth = st.selectbox("Breadth", ["Mạnh", "Trung tính", "Yếu", "Sụp đổ"])
                credit = st.selectbox("Credit/Lãi suất", ["Ổn định", "Tăng nhẹ", "Căng thẳng", "Khủng hoảng"])
                margin = st.selectbox("Margin", ["Bình thường", "Đang tăng", "Đang giảm chấp", "Force-sell đang xảy ra"])

            regime_call = st.selectbox("🎯 Kết luận Regime", ["Risk-on", "Mixed", "Risk-off"])
            note_vi = st.text_area("Nhận xét tiếng Việt", height=100, placeholder="Tuần này thị trường...")
            note_en = st.text_area("English commentary", height=100, placeholder="This week the market...")

            if st.button("💾 Lưu Regime Radar", type="primary"):
                save_regime_radar(
                    user["id"], week_label, vix_val, vn_ma,
                    breadth, credit, margin, regime_call, note_vi, note_en
                )
                st.success("✅ Đã lưu Regime Radar!")
                st.rerun()


# ─── PORTFOLIO RISK CHECKER ────────────────────────────────────────────────────

def page_portfolio_risk():
    st.header(t("📊 Portfolio Risk Checker", "📊 Portfolio Risk Checker"))
    gate_pro("Portfolio Risk Checker")

    st.caption(t(
        "Nhập danh mục đang nắm — app tính tổng rủi ro, cảnh báo concentrated bet và kiểm tra phù hợp với regime.",
        "Enter your current holdings — app calculates total risk, warns about concentrated bets, and checks regime fit."
    ))

    # Get current regime
    latest_radar = get_regime_radar_latest()
    current_regime = latest_radar.get("regime_call", "Unknown") if latest_radar else "Unknown"

    regime_colors = {"Risk-on": "#059669", "Mixed": "#D97706", "Risk-off": "#DC2626", "Unknown": "#64748B"}
    rc = regime_colors.get(current_regime, "#64748B")
    st.markdown(f"""
<div style="background:rgba(29,78,216,0.06); border-radius:8px; padding:10px 14px; margin-bottom:1rem; border-left:4px solid {rc}">
<span style="font-size:13px; color:#94A3B8">Regime hiện tại (Radar): </span>
<strong style="color:{rc}; font-size:16px">{current_regime}</strong>
</div>
""", unsafe_allow_html=True)

    st.subheader(t("📋 Nhập danh mục của bạn", "📋 Enter your portfolio"))

    account_size = st.number_input(
        t("Tổng giá trị tài khoản ($)", "Total account value ($)"),
        min_value=100.0, value=10000.0, step=500.0
    )

    st.markdown(t("Thêm từng vị thế:", "Add each position:"))

    if "portfolio_rows" not in st.session_state:
        st.session_state.portfolio_rows = 3

    positions = []
    headers = st.columns([2, 2, 2, 2, 1])
    headers[0].markdown(f"**{t('Mã/Tên', 'Ticker')}**")
    headers[1].markdown(f"**{t('Giá trị ($)', 'Value ($)')}**")
    headers[2].markdown(f"**{t('Stop-loss (%)', 'Stop-loss (%)')}**")
    headers[3].markdown(f"**{t('Ngành', 'Sector')}**")

    for i in range(st.session_state.portfolio_rows):
        cols = st.columns([2, 2, 2, 2, 1])
        ticker = cols[0].text_input("", key=f"pt_{i}", placeholder=f"#{i+1} ticker", label_visibility="collapsed")
        value = cols[1].number_input("", key=f"pv_{i}", min_value=0.0, value=0.0, step=100.0, label_visibility="collapsed")
        stop = cols[2].number_input("", key=f"ps_{i}", min_value=0.0, max_value=100.0, value=5.0, step=0.5, label_visibility="collapsed")
        sector_opts = ["Tech", "Finance/Bank", "Real Estate", "Consumer", "Energy", "Healthcare", "Other"]
        sector = cols[3].selectbox("", sector_opts, key=f"psc_{i}", label_visibility="collapsed")
        if ticker and value > 0:
            positions.append({"ticker": ticker, "value": value, "stop_pct": stop, "sector": sector})

    c1, c2 = st.columns(2)
    with c1:
        if st.button(t("+ Thêm hàng", "+ Add row"), key="add_row"):
            st.session_state.portfolio_rows += 1
            st.rerun()
    with c2:
        if st.button(t("🔍 Kiểm tra rủi ro", "🔍 Check Risk"), type="primary", key="check_risk"):
            if not positions:
                st.error(t("Vui lòng nhập ít nhất 1 vị thế.", "Please enter at least 1 position."))
            else:
                st.divider()
                st.subheader(t("📊 Kết quả phân tích", "📊 Analysis Results"))

                total_value = sum(p["value"] for p in positions)
                portfolio_pct = total_value / account_size * 100

                # Per-position risk
                results = []
                total_risk_dollar = 0
                for p in positions:
                    pos_pct = p["value"] / account_size * 100
                    risk_dollar = p["value"] * p["stop_pct"] / 100
                    risk_pct_acc = risk_dollar / account_size * 100
                    total_risk_dollar += risk_dollar
                    results.append({
                        t("Mã", "Ticker"): p["ticker"],
                        t("Giá trị", "Value"): f"${p['value']:,.0f}",
                        t("% TK", "% Acct"): f"{pos_pct:.1f}%",
                        t("Stop-loss", "Stop-loss"): f"{p['stop_pct']}%",
                        t("Risk $", "Risk $"): f"${risk_dollar:,.0f}",
                        t("Risk % TK", "Risk % Acct"): f"{risk_pct_acc:.2f}%",
                        t("Ngành", "Sector"): p["sector"],
                        t("Đánh giá", "Rating"): "🔴 Quá lớn" if pos_pct > 20 else ("🟡 Lớn" if pos_pct > 10 else "✅ OK"),
                    })

                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

                total_risk_pct = total_risk_dollar / account_size * 100

                m1, m2, m3, m4 = st.columns(4)
                m1.metric(t("Tổng vị thế", "Total invested"), f"${total_value:,.0f}", f"{portfolio_pct:.1f}% TK")
                m2.metric(t("Tổng rủi ro nếu tất cả sai", "Total risk if all wrong"), f"${total_risk_dollar:,.0f}", f"{total_risk_pct:.1f}% TK")
                m3.metric(t("Số vị thế", "Positions"), len(positions))
                m4.metric(t("Regime hiện tại", "Current Regime"), current_regime)

                st.divider()

                # Warnings
                warnings = []
                if total_risk_pct > 10:
                    warnings.append(("🔴", t(f"Tổng rủi ro {total_risk_pct:.1f}% tài khoản — QUÁ CAO. Nên dưới 6%.", f"Total risk {total_risk_pct:.1f}% — TOO HIGH. Should be under 6%.")))
                if portfolio_pct > 80:
                    warnings.append(("🟡", t(f"Đang dùng {portfolio_pct:.1f}% tài khoản — ít dự phòng tiền mặt.", f"Using {portfolio_pct:.1f}% of account — little cash reserve.")))

                # Sector concentration
                sector_values = {}
                for p in positions:
                    sector_values[p["sector"]] = sector_values.get(p["sector"], 0) + p["value"]
                for sec, val in sector_values.items():
                    sec_pct = val / account_size * 100
                    if sec_pct > 30:
                        warnings.append(("🟡", t(f"Tập trung cao vào {sec}: {sec_pct:.1f}% tài khoản.", f"High concentration in {sec}: {sec_pct:.1f}% of account.")))

                # Regime compatibility
                if current_regime == "Risk-off":
                    if portfolio_pct > 20:
                        warnings.append(("🔴", t(f"Regime Risk-off nhưng bạn đang giữ {portfolio_pct:.1f}% — cân nhắc giảm exposure.", f"Risk-off regime but holding {portfolio_pct:.1f}% — consider reducing exposure.")))
                elif current_regime == "Mixed":
                    if portfolio_pct > 50:
                        warnings.append(("🟡", t(f"Regime Mixed nhưng exposure {portfolio_pct:.1f}% — nên dưới 50%.", f"Mixed regime but {portfolio_pct:.1f}% exposure — consider keeping under 50%.")))

                # Big single position
                for p in positions:
                    if p["value"] / account_size * 100 > 25:
                        warnings.append(("🔴", t(f"{p['ticker']} chiếm >{25}% tài khoản — rủi ro concentrated bet.", f"{p['ticker']} is >{25}% of account — concentrated bet risk.")))

                if warnings:
                    st.subheader(t("⚠️ Cảnh báo", "⚠️ Warnings"))
                    for icon, msg in warnings:
                        if icon == "🔴":
                            st.error(f"{icon} {msg}")
                        else:
                            st.warning(f"{icon} {msg}")
                else:
                    st.success(t("✅ Danh mục có vẻ cân bằng với mức rủi ro hợp lý.", "✅ Portfolio appears balanced with reasonable risk levels."))

                # Sector chart
                if len(sector_values) > 1:
                    st.divider()
                    st.subheader(t("🥧 Phân bổ theo ngành", "🥧 Sector Allocation"))
                    fig_pie = go.Figure(go.Pie(
                        labels=list(sector_values.keys()),
                        values=list(sector_values.values()),
                        hole=0.4,
                    ))
                    fig_pie.update_layout(height=280, margin=dict(t=10, b=10),
                                         paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pie, use_container_width=True)

                # AI analysis
                if st.button(t("🤖 Phân tích sâu bằng AI Coach", "🤖 Deep AI Analysis"), key="portfolio_ai"):
                    with st.spinner(t("AI đang phân tích danh mục...", "AI analyzing portfolio...")):
                        try:
                            client = anthropic.Anthropic()
                            lang = st.session_state.lang
                            pos_summary = ", ".join([f"{p['ticker']} (${p['value']:,.0f}, stop {p['stop_pct']}%, {p['sector']})" for p in positions])

                            if lang == "vi":
                                msg = f"""Phân tích danh mục đầu tư:
- Tổng tài khoản: ${account_size:,.0f}
- Regime hiện tại: {current_regime}
- Các vị thế: {pos_summary}
- Tổng rủi ro: {total_risk_pct:.1f}% tài khoản
Đưa ra nhận xét ngắn gọn về rủi ro tổng thể, mức độ phù hợp với regime, và 3 gợi ý cụ thể."""
                                sys_p = "Bạn là AI Coach đầu tư. Phân tích danh mục ngắn gọn, thực tế. Dùng tiếng Việt."
                            else:
                                msg = f"""Analyze this investment portfolio:
- Account size: ${account_size:,.0f}
- Current regime: {current_regime}
- Positions: {pos_summary}
- Total risk: {total_risk_pct:.1f}% of account
Provide brief commentary on overall risk, regime fit, and 3 specific suggestions."""
                                sys_p = "You are an investment AI Coach. Be concise and practical."

                            resp = anthropic.Anthropic().messages.create(
                                model="claude-sonnet-4-20250514", max_tokens=800,
                                system=sys_p, messages=[{"role":"user","content":msg}]
                            )
                            st.markdown(resp.content[0].text)
                        except Exception as e:
                            st.error(str(e))



# ─── LEADERBOARD ───────────────────────────────────────────────────────────────

def page_leaderboard():
    st.header(t("🏆 Leaderboard", "🏆 Leaderboard"))
    st.caption(t(
        "Top nhà đầu tư kỷ luật nhất tuần này — xếp hạng theo số ngày hoạt động liên tiếp.",
        "Most disciplined investors this week — ranked by consecutive active days."
    ))

    user = st.session_state.user
    if user["id"] != -1:
        record_daily_activity(user["id"])

    board = get_leaderboard(10)

    if not board:
        st.info(t("Chưa có dữ liệu leaderboard.", "No leaderboard data yet."))
        return

    st.divider()

    # Highlight current user
    medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 7
    rows = []
    for i, u in enumerate(board):
        streak_disp, _ = get_streak(u["id"]) if u["id"] != -1 else (0, 0)
        is_me = user["id"] == u["id"]
        rows.append({
            t("Hạng", "Rank"): f"{medals[i]} #{i+1}",
            t("User", "User"): f"**{u['username']}**" + (" ← bạn" if is_me else ""),
            t("Gói", "Plan"): "⭐ Pro" if u["plan"] == "pro" else "Free",
            t("Ngày hoạt động", "Active days"): u["total_days"],
            t("Streak hiện tại", "Current streak"): f"🔥 {streak_disp}" if streak_disp >= 3 else str(streak_disp),
        })

    df_board = pd.DataFrame(rows)
    st.dataframe(df_board, use_container_width=True, hide_index=True)

    # Current user rank
    if user["id"] != -1:
        my_streak, my_longest = get_streak(user["id"])
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric(t("Streak của bạn", "Your streak"), f"🔥 {my_streak} ngày" if my_streak >= 1 else "0")
        c2.metric(t("Streak dài nhất", "Longest streak"), f"{my_longest} ngày")
        c3.metric(t("Badge streak", "Streak badge"),
                  "🔥🔥 30 ngày" if my_streak >= 30 else ("🔥 7 ngày" if my_streak >= 7 else "Chưa có"))

    # Share button
    if user["id"] != -1 and board and board[0]["id"] == user["id"]:
        st.success(t("🥇 Bạn đang đứng đầu leaderboard tuần này!", "🥇 You're leading this week's leaderboard!"))

    st.divider()
    st.info(t(
        "Leaderboard cập nhật khi bạn sử dụng bất kỳ tính năng nào trong app.",
        "Leaderboard updates whenever you use any feature in the app."
    ))


# ─── REFERRAL ──────────────────────────────────────────────────────────────────

def page_referral():
    st.header(t("🎁 Chương trình giới thiệu", "🎁 Referral Program"))
    st.caption(t(
        "Giới thiệu bạn bè — nhận thêm thời gian Pro miễn phí.",
        "Refer friends — earn free Pro time."
    ))

    user = st.session_state.user
    if user["id"] == -1:
        st.info(t("Đăng ký tài khoản để tham gia chương trình giới thiệu.", "Register to join the referral program."))
        return

    ref_code = get_referral_code(user["id"], user["username"])
    ref_stats = get_referral_stats(user["id"])

    # Referral link
    st.subheader(t("Link giới thiệu của bạn", "Your referral link"))
    ref_link = f"https://your-app.streamlit.app?ref={ref_code}"
    st.code(ref_link, language=None)

    col1, col2 = st.columns(2)
    col1.metric(t("Đã giới thiệu", "Referred"), ref_stats["total"])
    col2.metric(t("Đã nâng Pro", "Converted to Pro"), ref_stats["pro"])

    # Reward progress
    st.divider()
    st.subheader(t("🎁 Phần thưởng", "🎁 Rewards"))

    pro_needed = 3
    pro_current = ref_stats["pro"]
    progress = min(pro_current / pro_needed, 1.0)

    st.progress(progress)
    if pro_current >= pro_needed:
        st.success(t(
            f"✅ Bạn đủ điều kiện nhận **1 tháng Pro miễn phí**! Liên hệ admin để nhận thưởng.",
            f"✅ You qualify for **1 free month of Pro**! Contact admin to claim."
        ))
    else:
        remaining = pro_needed - pro_current
        st.info(t(
            f"Cần thêm **{remaining} người** nâng cấp Pro để nhận 1 tháng Pro miễn phí.",
            f"Need **{remaining} more** Pro upgrades to earn 1 free month of Pro."
        ))

    # How it works
    st.divider()
    st.subheader(t("Cách hoạt động", "How it works"))
    if st.session_state.lang == "vi":
        st.markdown("""
1. **Chia sẻ link** của bạn cho bạn bè/đồng nghiệp quan tâm đến đầu tư
2. Họ đăng ký qua link của bạn
3. Khi **3 người trong số họ nâng cấp Pro** → bạn được tặng **1 tháng Pro**
4. Không giới hạn số lần — giới thiệu 6 người Pro = 2 tháng miễn phí
""")
    else:
        st.markdown("""
1. **Share your link** with friends/colleagues interested in investing
2. They register through your link
3. When **3 of them upgrade to Pro** → you earn **1 free month of Pro**
4. No limit — refer 6 Pro users = 2 free months
""")

    # Share text
    st.divider()
    share_text = t(
        f"Tôi đang dùng Investor Discipline App để luyện tư duy đầu tư Risk First. Thử miễn phí: {ref_link}",
        f"I'm using Investor Discipline App to train my Risk First investing mindset. Try for free: {ref_link}"
    )
    st.text_area(t("Text để chia sẻ (copy và paste):", "Share text (copy and paste):"),
                 value=share_text, height=80)


# ─── SHARE RESULT ──────────────────────────────────────────────────────────────

def show_share_widget(score, max_score, context, extra=""):
    """Show share widget after completing a challenge/simulator."""
    pct = score / max_score * 100
    emoji = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
    share_vi = f"{emoji} Tôi vừa hoàn thành **{context}** với điểm {score}/{max_score} trên Investor Discipline App 🛡️\nLuyện tư duy Risk First · Regime First · Evidence First\n{extra}"
    share_en = f"{emoji} I just completed **{context}** scoring {score}/{max_score} on Investor Discipline App 🛡️\nTraining Risk First · Regime First · Evidence First mindset\n{extra}"
    share_text = share_vi if st.session_state.lang == "vi" else share_en

    with st.expander(t("📣 Chia sẻ kết quả", "📣 Share result"), expanded=False):
        st.text_area(
            t("Copy và dán vào Facebook/Zalo:", "Copy and paste to Facebook/Zalo:"),
            value=share_text, height=80, key=f"share_{context[:10]}"
        )
        st.caption(t(
            "Chia sẻ giúp nhiều nhà đầu tư khác biết đến app và luyện tập kỷ luật.",
            "Sharing helps more investors discover the app and practice discipline."
        ))



# ─── ROUTINE SÁNG ──────────────────────────────────────────────────────────────

def page_morning_routine():
    st.header(t("🌅 Routine sáng — Chuẩn bị giao dịch", "🌅 Morning Routine — Pre-Market Prep"))
    st.caption(t(
        "Hoàn thành 5 bước này trước khi đặt lệnh. Mất 2 phút.",
        "Complete these 5 steps before placing any order. Takes 2 minutes."
    ))

    user = st.session_state.user
    if user["id"] == -1:
        st.info(t("Đăng ký tài khoản để lưu routine hàng ngày.", "Register to save your daily routine."))
        return

    # Check already done today
    done_today = get_routine_today(user["id"], "morning")
    morning_streak = get_routine_streak(user["id"], "morning")

    if morning_streak > 0:
        streak_txt = f"🔥 {morning_streak} " + t("ngày liên tiếp", "days in a row")
        st.success(t(f"Streak routine sáng: {streak_txt}", f"Morning routine streak: {streak_txt}"))

    if done_today:
        st.success(t(
            "✅ Bạn đã hoàn thành routine sáng hôm nay!",
            "✅ You've completed today's morning routine!"
        ))
        ans = done_today.get("answers", {})
        st.markdown(t("**Câu trả lời của bạn sáng nay:**", "**Your answers this morning:**"))
        labels_vi = ["Cảm xúc", "Regime hôm nay", "Kế hoạch", "Rủi ro tối đa", "Cam kết"]
        labels_en = ["Emotion", "Today's regime", "Plan", "Max risk", "Commitment"]
        labels = labels_vi if st.session_state.lang == "vi" else labels_en
        for i, label in enumerate(labels):
            val = ans.get(str(i), "—")
            st.markdown(f"- **{label}:** {val}")
        return

    st.divider()

    QUESTIONS_VI = [
        ("Cảm xúc hiện tại của bạn là gì?",
         ["😌 Bình tĩnh, sẵn sàng", "😤 Đang bực / stress", "😰 Lo lắng", "🤑 Hào hứng thái quá"]),
        ("Regime thị trường hôm nay là gì?",
         ["Risk-on — có thể tham gia", "Mixed — thận trọng, chọn lọc", "Risk-off — bảo toàn vốn", "Chưa kiểm tra"]),
        ("Kế hoạch hôm nay của bạn là gì?",
         ["Không giao dịch — quan sát", "Test-size nếu có setup tốt", "Normal size theo kế hoạch", "Chưa có kế hoạch"]),
        ("Mức rủi ro tối đa bạn chấp nhận hôm nay là bao nhiêu?",
         ["0% — không giao dịch hôm nay", "Tối đa 1% tài khoản", "Tối đa 2% tài khoản", "Chưa xác định"]),
        ("Bạn cam kết điều gì trước khi giao dịch hôm nay?",
         ["Không giao dịch khi đang FOMO", "Không trade nếu regime xấu", "Luôn có stop-loss trước khi vào", "Tuân theo kế hoạch đã đặt"]),
    ]
    QUESTIONS_EN = [
        ("What is your current emotional state?",
         ["😌 Calm and ready", "😤 Stressed/frustrated", "😰 Anxious", "🤑 Overly excited"]),
        ("What is the market regime today?",
         ["Risk-on — can participate", "Mixed — cautious, selective", "Risk-off — preserve capital", "Haven't checked"]),
        ("What is your plan for today?",
         ["No trading — observe only", "Test-size if good setup appears", "Normal size per plan", "No plan yet"]),
        ("What is your maximum risk tolerance today?",
         ["0% — no trading today", "Max 1% of account", "Max 2% of account", "Not determined"]),
        ("What do you commit to before trading today?",
         ["No trading while feeling FOMO", "No trade if regime is bad", "Always have stop-loss before entry", "Follow the plan I've set"]),
    ]

    QUESTIONS = QUESTIONS_VI if st.session_state.lang == "vi" else QUESTIONS_EN

    # Scoring: some answers are "good" discipline choices
    GOOD_ANSWERS_VI = {0: 0, 1: {0,1,2}, 2: {0,1,2}, 3: {0,1,2}, 4: {0,1,2,3}}
    answers = {}
    all_answered = True

    for i, (q, opts) in enumerate(QUESTIONS):
        st.markdown(f"**{i+1}. {q}**")
        choice = st.radio("", opts, key=f"mr_{i}", label_visibility="collapsed")
        answers[str(i)] = choice

    st.divider()

    if st.button(t("✅ Hoàn thành Routine Sáng", "✅ Complete Morning Routine"), type="primary", use_container_width=True):
        # Score: penalize bad states
        score = 10
        if st.session_state.lang == "vi":
            if answers.get("0") in ["😤 Đang bực / stress", "🤑 Hào hứng thái quá"]: score -= 2
            if answers.get("1") == "Chưa kiểm tra": score -= 3
            if answers.get("2") == "Chưa có kế hoạch": score -= 2
            if answers.get("3") == "Chưa xác định": score -= 2
        score = max(0, score)

        save_routine(user["id"], "morning", answers, score)
        record_daily_activity(user["id"])
        save_feed_event(user["id"], "morning_routine",
            t(f"Hoàn thành routine sáng (điểm {score}/10)", f"Completed morning routine (score {score}/10)"))

        # Warnings
        if st.session_state.lang == "vi":
            if answers.get("0") in ["😤 Đang bực / stress", "😰 Lo lắng"]:
                st.warning("⚠️ Cảm xúc không ổn định. Hãy xem xét giảm size hoặc không giao dịch hôm nay.")
            if answers.get("1") in ["Risk-off — bảo toàn vốn", "Chưa kiểm tra"]:
                st.error("🛡️ Regime xấu hoặc chưa kiểm tra. Ưu tiên quan sát, không mua.")
            if answers.get("2") == "Chưa có kế hoạch":
                st.error("🚫 Không có kế hoạch = không nên giao dịch.")
        else:
            if answers.get("0") in ["😤 Stressed/frustrated", "😰 Anxious"]:
                st.warning("⚠️ Emotional state is unstable. Consider reducing size or not trading today.")
            if answers.get("1") in ["Risk-off — preserve capital", "Haven't checked"]:
                st.error("🛡️ Bad regime or unchecked. Prioritize observation, no buying.")
            if answers.get("2") == "No plan yet":
                st.error("🚫 No plan = should not trade.")

        st.success(t(f"✅ Routine sáng hoàn thành! Điểm kỷ luật: {score}/10", f"✅ Morning routine done! Discipline score: {score}/10"))
        st.rerun()


# ─── ROUTINE TỐI ───────────────────────────────────────────────────────────────

def page_evening_routine():
    st.header(t("🌙 Routine tối — Review cuối ngày", "🌙 Evening Routine — End-of-Day Review"))
    st.caption(t(
        "Review lại ngày hôm nay. Mất 3 phút. Bài học hôm nay là đầu tư tốt nhất cho ngày mai.",
        "Review your day. Takes 3 minutes. Today's lesson is the best investment for tomorrow."
    ))

    user = st.session_state.user
    if user["id"] == -1:
        st.info(t("Đăng ký tài khoản để lưu routine.", "Register to save your routine."))
        return

    done_today = get_routine_today(user["id"], "evening")
    evening_streak = get_routine_streak(user["id"], "evening")

    if evening_streak > 0:
        st.success(t(f"🌙 Streak routine tối: 🔥 {evening_streak} ngày", f"🌙 Evening routine streak: 🔥 {evening_streak} days"))

    if done_today:
        st.success(t("✅ Bạn đã hoàn thành routine tối hôm nay!", "✅ Evening routine completed today!"))
        ans = done_today.get("answers", {})
        if ans.get("lesson"):
            st.info(t(f"**Bài học hôm nay:** {ans['lesson']}", f"**Today's lesson:** {ans['lesson']}"))
        return

    st.divider()

    # Did they trade today?
    traded = st.radio(
        t("Hôm nay bạn có giao dịch không?", "Did you trade today?"),
        [t("Có", "Yes"), t("Không — tôi đứng ngoài", "No — I stayed out")],
        key="ev_traded"
    )

    if traded in ["Có", "Yes"]:
        emotion_entry = st.selectbox(
            t("Cảm xúc khi VÀO lệnh?", "Emotion when ENTERING?"),
            [t("Bình tĩnh", "Calm"), "FOMO", t("Lo lắng", "Anxious"), t("Tự tin", "Confident"), t("Tham lam", "Greedy")],
            key="ev_emo_entry"
        )
        emotion_exit = st.selectbox(
            t("Cảm xúc khi THOÁT lệnh?", "Emotion when EXITING?"),
            [t("Bình tĩnh — theo kế hoạch", "Calm — per plan"), t("Hoảng loạn", "Panic"), t("Tham lam — giữ quá lâu", "Greedy — held too long"), t("FOMO — cắt lời sớm", "FOMO — cut winner early")],
            key="ev_emo_exit"
        )
        violated = st.multiselect(
            t("Có vi phạm kỷ luật nào không?", "Any discipline violations?"),
            [t("Không có", "None"), t("Không có stop-loss", "No stop-loss"), t("FOMO mua đuổi", "FOMO chasing"), t("Revenge trading", "Revenge trading"), t("Size quá lớn", "Oversized"), t("Bỏ qua regime", "Ignored regime")],
            default=[t("Không có", "None")],
            key="ev_violated"
        )
        outcome = st.radio(
            t("Kết quả lệnh + quy trình?", "Result + process?"),
            [t("Lãi + quy trình tốt", "Profit + good process"),
             t("Lãi nhưng sai quy trình", "Profit but bad process"),
             t("Lỗ nhưng quy trình đúng", "Loss but correct process"),
             t("Lỗ + sai quy trình", "Loss + bad process")],
            key="ev_outcome"
        )
    else:
        st.success(t(
            "✅ Kỷ luật tốt — đứng ngoài cũng là một quyết định đúng.",
            "✅ Good discipline — staying out is also a correct decision."
        ))
        emotion_entry = t("Không giao dịch", "No trade")
        emotion_exit = t("Không giao dịch", "No trade")
        violated = [t("Không có", "None")]
        outcome = t("Không giao dịch — đứng ngoài đúng kỷ luật", "No trade — disciplined stay-out")

    lesson = st.text_area(
        t("Bài học lớn nhất hôm nay của bạn là gì?", "What's your biggest lesson from today?"),
        height=80, key="ev_lesson",
        placeholder=t("VD: Tôi đã FOMO và mua khi giá đã tăng 10%...", "E.g. I FOMO'd and bought after price was already up 10%...")
    )

    st.divider()
    if st.button(t("✅ Hoàn thành Routine Tối", "✅ Complete Evening Routine"), type="primary", use_container_width=True):
        answers = {
            "traded": traded,
            "emotion_entry": emotion_entry,
            "emotion_exit": emotion_exit,
            "violated": violated,
            "outcome": outcome,
            "lesson": lesson,
        }
        # Score discipline
        score = 10
        no_vio_vi = "Không có"
        no_vio_en = "None"
        no_vio = no_vio_vi if st.session_state.lang == "vi" else no_vio_en
        if no_vio not in violated:
            score -= min(len(violated) * 2, 6)
        if "FOMO" in str(emotion_entry): score -= 1
        if "Panic" in str(emotion_exit) or "Hoảng" in str(emotion_exit): score -= 1
        score = max(0, score)

        save_routine(user["id"], "evening", answers, score)
        record_daily_activity(user["id"])

        # Auto-save to journal if traded
        if traded in ["Có", "Yes"] and lesson.strip():
            save_journal(user["id"], "Review", outcome, lesson, "", "", emotion_entry)

        save_feed_event(user["id"], "evening_routine",
            t(f"Hoàn thành review tối", f"Completed evening review"))

        if violated and no_vio not in violated:
            st.warning(t(
                f"⚠️ Ghi nhận vi phạm: {', '.join([v for v in violated if v != no_vio])}. Chú ý tránh ngày mai.",
                f"⚠️ Violations noted: {', '.join([v for v in violated if v != no_vio])}. Avoid tomorrow."
            ))
        st.success(t(f"✅ Review tối hoàn thành! Điểm kỷ luật: {score}/10", f"✅ Evening review done! Score: {score}/10"))
        st.rerun()


# ─── COMMUNITY FEED ────────────────────────────────────────────────────────────

def page_community():
    st.header(t("👥 Cộng đồng học tập", "👥 Learning Community"))
    st.caption(t(
        "Xem những gì cộng đồng đang làm hôm nay — học cùng nhau, kỷ luật cùng nhau.",
        "See what the community is doing today — learn together, stay disciplined together."
    ))

    user = st.session_state.user
    stats = get_community_stats()

    # Social proof stats bar
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("User hoạt động tuần này", "Active this week"), stats["week_active"])
    col2.metric(t("Thành viên Pro", "Pro members"), stats["pro_count"])
    col3.metric(t("Tổng thành viên", "Total members"), stats["total_users"])
    col4.metric(t("Hoạt động ghi nhận", "Logged activities"), stats["total_events"])

    st.divider()

    # Live feed
    st.subheader(t("📣 Hoạt động gần đây", "📣 Recent Activity"))
    feed = get_community_feed(20)

    if not feed:
        st.info(t(
            "Chưa có hoạt động nào. Bạn hãy là người đầu tiên — làm Daily Challenge ngay!",
            "No activity yet. Be the first — do today's Daily Challenge now!"
        ))
        return

    EVENT_ICONS = {
        "daily_correct": "⚡",
        "morning_routine": "🌅",
        "evening_routine": "🌙",
        "simulator_score": "📜",
        "challenge_score": "🎯",
        "streak_milestone": "🔥",
    }
    EVENT_LABELS_VI = {
        "daily_correct": "trả lời đúng Daily Challenge",
        "morning_routine": "hoàn thành routine sáng",
        "evening_routine": "hoàn thành review tối",
        "simulator_score": "luyện Historical Simulator",
        "challenge_score": "hoàn thành Investment Challenge",
        "streak_milestone": "đạt mốc streak",
    }
    EVENT_LABELS_EN = {
        "daily_correct": "answered Daily Challenge correctly",
        "morning_routine": "completed morning routine",
        "evening_routine": "completed evening review",
        "simulator_score": "practiced Historical Simulator",
        "challenge_score": "completed Investment Challenge",
        "streak_milestone": "hit a streak milestone",
    }
    labels = EVENT_LABELS_VI if st.session_state.lang == "vi" else EVENT_LABELS_EN

    for item in feed:
        icon = EVENT_ICONS.get(item["event_type"], "✅")
        label = labels.get(item["event_type"], item["event_type"])
        plan_badge = " ⭐" if item["plan"] == "pro" else ""
        ts = item["created_at"][:16].replace("T", " ")
        detail = f" — *{item['detail']}*" if item.get("detail") else ""
        st.markdown(f"{icon} **{item['username']}**{plan_badge} {label}{detail} `{ts}`")

    st.divider()
    st.caption(t(
        "Tên hiển thị là username đã đăng ký. Không có thông tin cá nhân nào được chia sẻ.",
        "Display names are registered usernames. No personal information is shared."
    ))


# ─── MARKET NEWS (Góc thị trường) ──────────────────────────────────────────────

def _auto_generate_market_news(week_label):
    """Tự động sinh Góc thị trường bằng AI mỗi tuần, dựa trên Regime Radar.
    Gọi 1 lần/tuần bởi user đầu tiên. Chi phí ~$0.008/tuần."""
    try:
        latest_radar = get_regime_radar_latest()
        if latest_radar:
            ctx = (f"Regime hiện tại: {latest_radar.get('regime_call','?')}. "
                   f"VIX: {latest_radar.get('vix','?')}. "
                   f"VN-Index: {latest_radar.get('vn_vs_ma200','?')}. "
                   f"Ghi chú admin: {latest_radar.get('note_vi','')}")
        else:
            ctx = "Chưa có dữ liệu Regime Radar. Viết bài mang tính giáo dục chung về kỷ luật."

        client = anthropic.Anthropic()
        prompt = f"""Bạn viết mục "Góc thị trường" cho app luyện kỷ luật đầu tư (triết lý: Risk First, Regime First, Evidence First). Viết NGẮN (3-4 câu), mang tính giáo dục về kỷ luật, KHÔNG dự đoán giá, KHÔNG khuyến nghị mua bán cổ phiếu cụ thể, KHÔNG bịa số liệu chính xác.

BỐI CẢNH TUẦN NÀY:
{ctx}

Liên hệ với 1 nguyên tắc kỷ luật của app. Trả về CHỈ JSON thuần (không markdown):
{{"headline_vi":"...","headline_en":"...","body_vi":"...","body_en":"...","lesson_link":"VD: Bài 2 - Regime First"}}"""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=700,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        text = resp.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "", 1).strip()
        d = json.loads(text)
        save_market_news(
            -1, week_label,
            d["headline_vi"], d.get("headline_en", d["headline_vi"]),
            d["body_vi"], d.get("body_en", d["body_vi"]),
            d.get("lesson_link", ""),
        )
        return True
    except Exception:
        return False


def page_market_news():
    st.header(t("📰 Góc thị trường tuần này", "📰 This Week's Market Corner"))
    st.caption(t(
        "Sự kiện nổi bật tuần này — và chúng liên quan đến kỷ luật đầu tư như thế nào.",
        "Key events this week — and how they connect to investment discipline."
    ))

    user = st.session_state.user
    from datetime import date as _dcls
    _today = _dcls.today()
    _this_week = f"Tuần {_today.isocalendar()[1]}/{_today.year}"
    news_list = get_market_news_latest(3)

    # Tự động sinh bằng AI nếu tuần này chưa có bài (1 lần/tuần, dùng chung)
    has_this_week = any(n.get("week_label") == _this_week for n in news_list)
    if not has_this_week:
        with st.spinner(t("Đang chuẩn bị góc thị trường tuần này...", "Preparing this week's market corner...")):
            if _auto_generate_market_news(_this_week):
                news_list = get_market_news_latest(3)

    if news_list:
        for news in news_list:
            with st.container(border=True):
                st.markdown(f"### {news[f'headline_{st.session_state.lang}']}")
                src = news.get("user_id") == -1
                cap = f"📅 {news['week_label']}"
                if src:
                    cap += t("  ·  🤖 AI tự tạo", "  ·  🤖 AI-generated")
                st.caption(cap)
                st.markdown(news[f"body_{st.session_state.lang}"])
                if news.get("lesson_link"):
                    st.markdown(t(
                        f"📖 **Liên hệ bài học:** {news['lesson_link']}",
                        f"📖 **Related lesson:** {news['lesson_link']}"
                    ))
    else:
        st.info(t(
            "Chưa có tin tức tuần này. Admin sẽ cập nhật đầu mỗi tuần.",
            "No news yet this week. Admin updates every start of week."
        ))

    # Admin input
    if user.get("username") == "admin" and user["id"] != -1:
        st.divider()
        with st.expander(t("✍️ Admin — Thêm tin tức tuần này", "✍️ Admin — Add this week's news"), expanded=not news_list):
            from datetime import date as date_cls
            today = date_cls.today()
            wk = today.isocalendar()[1]
            default_wk = f"Tuần {wk}/{today.year}"
            week_lbl = st.text_input(t("Nhãn tuần", "Week label"), value=default_wk, key="news_wk")
            col1, col2 = st.columns(2)
            with col1:
                hl_vi = st.text_input(t("Tiêu đề (VI)", "Headline (VI)"), key="news_hl_vi")
                body_vi = st.text_area(t("Nội dung (VI)", "Body (VI)"), height=120, key="news_body_vi",
                    placeholder=t("VD: Fed giữ lãi suất, tín hiệu Mixed. VN-Index phản ứng...", "E.g. Fed holds rates, Mixed signal..."))
            with col2:
                hl_en = st.text_input("Headline (EN)", key="news_hl_en")
                body_en = st.text_area("Body (EN)", height=120, key="news_body_en")
            lesson_lnk = st.text_input(
                t("Liên kết bài học (tùy chọn)", "Related lesson (optional)"),
                placeholder=t("VD: Bài 2 — Regime First", "E.g. Lesson 2 — Regime First"),
                key="news_lesson"
            )
            if st.button(t("💾 Lưu tin tức", "💾 Save news"), type="primary", key="news_save"):
                if hl_vi and body_vi:
                    save_market_news(user["id"], week_lbl, hl_vi, hl_en or hl_vi, body_vi, body_en or body_vi, lesson_lnk)
                    st.success(t("✅ Đã lưu tin tức tuần này!", "✅ News saved!"))
                    st.rerun()
                else:
                    st.error(t("Vui lòng điền tiêu đề và nội dung.", "Please fill in headline and body."))


if __name__ == "__main__":
    main()
