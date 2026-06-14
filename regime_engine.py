# regime_engine.py
# ─────────────────────────────────────────────────────────────────────────────
# REGIME ENGINE — Rubric chấm điểm regime MINH BẠCH, ĐA THỊ TRƯỜNG (VN + US).
#
# Triết lý: không "tin admin", mà cho người dùng thấy ĐÚNG cách regime được tính.
#   1. Mỗi tín hiệu chấm điểm hướng rủi ro: -2 (rất xấu) … +2 (rất tốt).
#   2. Nhân trọng số, cộng lại, chuẩn hóa về "Risk-on Score" 0–100 (50 = trung tính).
#   3. Ngưỡng công khai:  >=66 Risk-on | 34–65 Mixed | <=33 Risk-off.
#   4. CAP  — chặn trần ở Mixed: chỉ Risk-on khi breadth MẠNH (rally phải có độ rộng).
#   5. VETO — ép thẳng Risk-off khi có trạng thái cực đoan ("biết địch").
#
# Mỗi thị trường có bộ tín hiệu riêng (REGIME_SIGNALS_BY_MARKET). Thêm thị trường
# mới chỉ là thêm một entry config — engine, store, UI dùng chung.
#
# Module THUẦN Python (không streamlit/DB) → test được, dùng lại cho automation.
# ─────────────────────────────────────────────────────────────────────────────

# ═══ THỊ TRƯỜNG VIỆT NAM ══════════════════════════════════════════════════════
REGIME_SIGNALS_VN = [
    {
        "key": "vn_vs_ma200", "label_vi": "VN-Index vs MA200", "label_en": "VN-Index vs MA200",
        "weight": 2.0, "type": "categorical", "options": ["Trên MA200", "Sát MA200", "Dưới MA200"],
        "map": {"Trên MA200": 2, "Above MA200": 2, "Sát MA200": 0, "At MA200": 0,
                "Dưới MA200": -2, "Below MA200": -2},
        "hint_vi": "Xu hướng chính của thị trường. Dưới MA200 = gió ngược.",
        "hint_en": "The market's primary trend. Below MA200 = headwind.",
    },
    {
        "key": "breadth", "label_vi": "Độ rộng (Breadth)", "label_en": "Breadth",
        "weight": 2.0, "type": "categorical", "options": ["Mạnh", "Trung tính", "Yếu", "Sụp đổ"],
        "map": {"Mạnh": 2, "Strong": 2, "Trung tính": 0, "Neutral": 0,
                "Yếu": -1, "Weak": -1, "Sụp đổ": -2, "Collapse": -2},
        "hint_vi": "% cổ phiếu trên MA50/MA200 (HOSE). Yếu = rally hẹp, dễ gãy.",
        "hint_en": "% of stocks above MA50/MA200 (HOSE). Weak = narrow, fragile rally.",
    },
    {
        "key": "foreign_flow", "label_vi": "Dòng tiền khối ngoại", "label_en": "Foreign flows",
        "weight": 1.5, "type": "categorical",
        "options": ["Mua ròng mạnh", "Mua ròng", "Trung tính", "Bán ròng", "Bán ròng mạnh kéo dài"],
        "map": {"Mua ròng mạnh": 2, "Strong net buy": 2, "Mua ròng": 1, "Net buy": 1,
                "Trung tính": 0, "Neutral": 0, "Bán ròng": -1, "Net sell": -1,
                "Bán ròng mạnh kéo dài": -2, "Heavy sustained net sell": -2},
        "hint_vi": "Khối ngoại trên HOSE. Bán ròng mạnh kéo dài đè chỉ số và tỷ giá.",
        "hint_en": "Foreign flows on HOSE. Heavy sustained selling pressures index and FX.",
    },
    {
        "key": "margin_status", "label_vi": "Margin CTCK", "label_en": "Broker margin",
        "weight": 1.5, "type": "categorical",
        "options": ["Bình thường", "Đang tăng", "Đang giảm chấp", "Force-sell đang xảy ra"],
        "map": {"Bình thường": 1, "Normal": 1, "Đang tăng": -1, "Rising": -1,
                "Đang giảm chấp": -2, "Deleveraging": -2,
                "Force-sell đang xảy ra": -2, "Force-sell happening": -2},
        "hint_vi": "Dư nợ margin toàn thị trường. Đang tăng = rủi ro tích tụ; giảm chấp = đang bị rũ.",
        "hint_en": "Market-wide margin debt. Rising = risk building; deleveraging = being shaken out.",
    },
    {
        "key": "liquidity", "label_vi": "Thanh khoản HOSE", "label_en": "HOSE liquidity",
        "weight": 1.0, "type": "categorical",
        "options": ["Tăng lành mạnh", "Bình thường", "Suy giảm", "Bùng nổ bất thường"],
        "map": {"Tăng lành mạnh": 1, "Healthy rising": 1, "Bình thường": 0, "Normal": 0,
                "Suy giảm": -1, "Declining": -1, "Bùng nổ bất thường": -1, "Abnormal spike": -1},
        "hint_vi": "Giá trị khớp lệnh. Suy giảm = phân phối; bùng nổ bất thường = hưng phấn đỉnh.",
        "hint_en": "Matched value. Declining = distribution; abnormal spike = euphoric top.",
    },
    {
        "key": "fx", "label_vi": "Tỷ giá USD/VND", "label_en": "USD/VND",
        "weight": 1.0, "type": "categorical", "options": ["Ổn định", "Áp lực nhẹ", "Căng thẳng"],
        "map": {"Ổn định": 1, "Stable": 1, "Áp lực nhẹ": 0, "Mild pressure": 0,
                "Căng thẳng": -2, "Stressed": -2},
        "hint_vi": "VND mất giá mạnh → khối ngoại rút vốn, SBV buộc siết.",
        "hint_en": "Sharp VND depreciation → foreign capital flight, SBV forced to tighten.",
    },
    {
        "key": "sbv_rates", "label_vi": "Lãi suất & chính sách SBV", "label_en": "Rates & SBV policy",
        "weight": 1.5, "type": "categorical",
        "options": ["Nới lỏng", "Ổn định", "Thắt chặt nhẹ", "Thắt chặt mạnh"],
        "map": {"Nới lỏng": 2, "Easing": 2, "Ổn định": 1, "Stable": 1,
                "Thắt chặt nhẹ": -1, "Mild tightening": -1, "Thắt chặt mạnh": -2, "Aggressive tightening": -2},
        "hint_vi": "Lãi suất liên ngân hàng, OMO, quan điểm SBV. Nới lỏng = gió thuận.",
        "hint_en": "Interbank rates, OMO, SBV stance. Easing = tailwind.",
    },
    {
        "key": "vix", "label_vi": "Bối cảnh toàn cầu (VIX)", "label_en": "Global backdrop (VIX)",
        "weight": 0.75, "type": "numeric", "num": {"min": 0.0, "default": 18.0, "step": 0.5},
        "bands": [(15, 2), (20, 1), (28, 0), (40, -1), (10**9, -2)], "fmt": lambda v: f"{v:g}",
        "hint_vi": "Tham chiếu rủi ro toàn cầu (phụ). Cao = ngoại né rủi ro, dễ rút khỏi VN.",
        "hint_en": "Global risk reference (secondary). High = foreigners avoid risk, flee VN.",
    },
]

REGIME_CAPS_VN = [
    {"signal": "breadth", "trigger": lambda v: v not in ("Mạnh", "Strong"),
     "reason_vi": "Breadth chưa MẠNH — rally chưa đủ độ rộng để gọi Risk-on. Uptrend thật cần nhiều cổ phiếu cùng dẫn.",
     "reason_en": "Breadth not STRONG — rally lacks the breadth to call Risk-on. A real uptrend needs many stocks leading."},
    {"signal": "vn_vs_ma200", "trigger": lambda v: v in ("Dưới MA200", "Below MA200"),
     "reason_vi": "VN-Index dưới MA200 — xu hướng chính chưa ủng hộ. Không gọi Risk-on khi index dưới trend.",
     "reason_en": "VN-Index below MA200 — primary trend not supportive. No Risk-on while index is below trend."},
    {"signal": "margin_status", "trigger": lambda v: v in ("Đang giảm chấp", "Deleveraging"),
     "reason_vi": "Thị trường đang giảm chấp — dòng tiền đòn bẩy rút lui, chưa phải lúc tăng rủi ro.",
     "reason_en": "Market deleveraging — leveraged money retreating, not the time to add risk."},
    {"signal": "foreign_flow", "trigger": lambda v: v in ("Bán ròng mạnh kéo dài", "Heavy sustained net sell"),
     "reason_vi": "Khối ngoại bán ròng mạnh kéo dài — lực bán cấu trúc, chưa nên gọi Risk-on dù nội đỡ.",
     "reason_en": "Foreigners selling heavily and persistently — structural selling, no Risk-on even if locals support."},
    {"signal": "fx", "trigger": lambda v: v in ("Căng thẳng", "Stressed"),
     "reason_vi": "Tỷ giá căng thẳng — rủi ro chính sách thắt chặt và rút vốn, chặn Risk-on.",
     "reason_en": "FX stress — risk of tightening and capital flight, caps Risk-on."},
]

REGIME_VETOES_VN = [
    {"signal": "margin_status", "trigger": lambda v: v in ("Force-sell đang xảy ra", "Force-sell happening"),
     "reason_vi": "FORCE-SELL đang diễn ra — giảm chấp dây chuyền, thanh khoản bị rút. Rẻ không phải lý do mua khi force-sell chưa dứt.",
     "reason_en": "FORCE-SELL in progress — margin-call chain reaction, liquidity drained. Cheap is not a reason to buy while it continues."},
    {"signal": "breadth", "trigger": lambda v: v in ("Sụp đổ", "Collapse"),
     "reason_vi": "Breadth SỤP ĐỔ — bán tháo trên diện rộng, không phải nhịp chỉnh thường.",
     "reason_en": "Breadth COLLAPSE — broad-based sell-off, not a normal pullback."},
    {"signal": "sbv_rates", "trigger": lambda v: v in ("Thắt chặt mạnh", "Aggressive tightening"),
     "reason_vi": "SBV thắt chặt mạnh — siết thanh khoản hệ thống, môi trường bảo toàn vốn.",
     "reason_en": "SBV tightening aggressively — system liquidity squeezed, capital-preservation environment."},
]


# ═══ THỊ TRƯỜNG MỸ (US) ═══════════════════════════════════════════════════════
REGIME_SIGNALS_US = [
    {
        "key": "sp_vs_ma200", "label_vi": "S&P 500 vs MA200", "label_en": "S&P 500 vs MA200",
        "weight": 2.0, "type": "categorical", "options": ["Trên MA200", "Sát MA200", "Dưới MA200"],
        "map": {"Trên MA200": 2, "Above MA200": 2, "Sát MA200": 0, "At MA200": 0,
                "Dưới MA200": -2, "Below MA200": -2},
        "hint_vi": "Xu hướng chính của chứng khoán Mỹ. Dưới MA200 = gió ngược.",
        "hint_en": "Primary trend of US equities. Below MA200 = headwind.",
    },
    {
        "key": "breadth", "label_vi": "Độ rộng (% S&P trên MA200)", "label_en": "Breadth (% S&P > MA200)",
        "weight": 2.0, "type": "categorical", "options": ["Mạnh", "Trung tính", "Yếu", "Sụp đổ"],
        "map": {"Mạnh": 2, "Strong": 2, "Trung tính": 0, "Neutral": 0,
                "Yếu": -1, "Weak": -1, "Sụp đổ": -2, "Collapse": -2},
        "hint_vi": "Bao nhiêu cổ phiếu cùng tăng. Yếu = chỉ vài mã lớn kéo (rally hẹp).",
        "hint_en": "How many stocks rise together. Weak = a few megacaps carry it (narrow rally).",
    },
    {
        "key": "vix", "label_vi": "VIX (chỉ số sợ hãi)", "label_en": "VIX (fear index)",
        "weight": 1.5, "type": "numeric", "num": {"min": 0.0, "default": 16.0, "step": 0.5},
        "bands": [(15, 2), (20, 1), (28, 0), (40, -1), (10**9, -2)], "fmt": lambda v: f"{v:g}",
        "hint_vi": "Thước đo sợ hãi chính của Mỹ. >28 = căng; >40 = hoảng loạn.",
        "hint_en": "The primary US fear gauge. >28 = stress; >40 = panic.",
    },
    {
        "key": "credit_hy", "label_vi": "Chênh lệch tín dụng HY", "label_en": "High-yield credit spread",
        "weight": 1.5, "type": "categorical",
        "options": ["Hẹp (ổn định)", "Bình thường", "Đang nới rộng", "Khủng hoảng"],
        "map": {"Hẹp (ổn định)": 1, "Tight (stable)": 1, "Bình thường": 0, "Normal": 0,
                "Đang nới rộng": -2, "Widening": -2, "Khủng hoảng": -2, "Crisis": -2},
        "hint_vi": "Chênh lệch lợi suất trái phiếu rủi ro. Nới rộng = tiền tháo khỏi rủi ro.",
        "hint_en": "Risky-bond yield spread. Widening = money fleeing risk.",
    },
    {
        "key": "fed_policy", "label_vi": "Chính sách Fed / lãi suất", "label_en": "Fed policy / rates",
        "weight": 1.5, "type": "categorical",
        "options": ["Nới lỏng", "Trung lập", "Thắt chặt nhẹ", "Thắt chặt mạnh"],
        "map": {"Nới lỏng": 2, "Easing": 2, "Trung lập": 0, "Neutral": 0,
                "Thắt chặt nhẹ": -1, "Mild tightening": -1, "Thắt chặt mạnh": -2, "Aggressive tightening": -2},
        "hint_vi": "Quan điểm Fed. Cắt lãi suất/QE = gió thuận; nâng mạnh/QT = gió ngược.",
        "hint_en": "Fed stance. Cuts/QE = tailwind; aggressive hikes/QT = headwind.",
    },
    {
        "key": "yield_curve", "label_vi": "Đường cong lợi suất (10Y–2Y)", "label_en": "Yield curve (10Y–2Y)",
        "weight": 1.0, "type": "categorical",
        "options": ["Dốc lên (bình thường)", "Phẳng", "Đảo ngược", "Đảo ngược sâu"],
        "map": {"Dốc lên (bình thường)": 1, "Upward (normal)": 1, "Phẳng": 0, "Flat": 0,
                "Đảo ngược": -1, "Inverted": -1, "Đảo ngược sâu": -2, "Deeply inverted": -2},
        "hint_vi": "Đảo ngược = tín hiệu suy thoái kinh điển (thường đi trước nhiều tháng).",
        "hint_en": "Inversion = classic recession signal (often leads by many months).",
    },
]

REGIME_CAPS_US = [
    {"signal": "breadth", "trigger": lambda v: v not in ("Mạnh", "Strong"),
     "reason_vi": "Breadth chưa MẠNH — rally chưa đủ độ rộng để gọi Risk-on (cẩn thận rally chỉ vài megacap kéo).",
     "reason_en": "Breadth not STRONG — rally lacks breadth for Risk-on (beware a few megacaps carrying it)."},
    {"signal": "sp_vs_ma200", "trigger": lambda v: v in ("Dưới MA200", "Below MA200"),
     "reason_vi": "S&P 500 dưới MA200 — xu hướng chính chưa ủng hộ. Không gọi Risk-on khi index dưới trend.",
     "reason_en": "S&P 500 below MA200 — primary trend not supportive. No Risk-on while index is below trend."},
    {"signal": "credit_hy", "trigger": lambda v: v in ("Đang nới rộng", "Widening"),
     "reason_vi": "Chênh lệch tín dụng HY đang nới rộng — thị trường nợ cảnh báo rủi ro, chặn Risk-on.",
     "reason_en": "High-yield spreads widening — the credit market is flagging risk, caps Risk-on."},
]

REGIME_VETOES_US = [
    {"signal": "breadth", "trigger": lambda v: v in ("Sụp đổ", "Collapse"),
     "reason_vi": "Breadth SỤP ĐỔ — bán tháo trên diện rộng, không phải nhịp chỉnh thường.",
     "reason_en": "Breadth COLLAPSE — broad-based sell-off, not a normal pullback."},
    {"signal": "credit_hy", "trigger": lambda v: v in ("Khủng hoảng", "Crisis"),
     "reason_vi": "Khủng hoảng tín dụng — thị trường nợ đóng băng, môi trường bảo toàn vốn tuyệt đối.",
     "reason_en": "Credit crisis — debt markets seizing, absolute capital-preservation environment."},
    {"signal": "fed_policy", "trigger": lambda v: v in ("Thắt chặt mạnh", "Aggressive tightening"),
     "reason_vi": "Fed thắt chặt mạnh — siết thanh khoản, môi trường bảo toàn vốn.",
     "reason_en": "Fed tightening aggressively — liquidity squeezed, capital-preservation environment."},
]


# ═══ REGISTRY ĐA THỊ TRƯỜNG ═══════════════════════════════════════════════════
REGIME_SIGNALS_BY_MARKET = {"vn": REGIME_SIGNALS_VN, "us": REGIME_SIGNALS_US}
CAPS_BY_MARKET = {"vn": REGIME_CAPS_VN, "us": REGIME_CAPS_US}
VETOES_BY_MARKET = {"vn": REGIME_VETOES_VN, "us": REGIME_VETOES_US}
MARKETS = ["vn", "us"]
MARKET_LABELS = {
    "vn": {"flag": "🇻🇳", "name_vi": "Việt Nam (VN)", "name_en": "Vietnam (VN)"},
    "us": {"flag": "🇺🇸", "name_vi": "Mỹ (US)", "name_en": "US"},
}

# Alias tương thích ngược (code cũ import REGIME_SIGNALS)
REGIME_SIGNALS = REGIME_SIGNALS_VN


def get_signals(market="vn"):
    return REGIME_SIGNALS_BY_MARKET.get(market, REGIME_SIGNALS_VN)


def _caps(market):
    return CAPS_BY_MARKET.get(market, REGIME_CAPS_VN)


def _vetoes(market):
    return VETOES_BY_MARKET.get(market, REGIME_VETOES_VN)


# Ngưỡng công khai
THRESH_RISK_ON = 66
THRESH_RISK_OFF = 34


# ─── HÀM TIỆN ÍCH ─────────────────────────────────────────────────────────────
def _score_numeric(value, bands):
    for upper, score in bands:
        if value < upper:
            return score
    return bands[-1][1]


def score_color(score):
    return {2: "#059669", 1: "#10B981", 0: "#D97706", -1: "#F97316", -2: "#DC2626"}.get(score, "#64748B")


def regime_color(regime):
    return {"Risk-on": "#059669", "Mixed": "#D97706", "Risk-off": "#DC2626"}.get(regime, "#64748B")


# ─── ĐỘNG CƠ CHÍNH ────────────────────────────────────────────────────────────
def compute_regime(inputs, market="vn"):
    """inputs: dict theo các key của thị trường. Trả scorecard minh bạch."""
    signals = get_signals(market)
    rows = []
    weighted_sum = 0.0
    max_abs = 0.0

    for sig in signals:
        raw = inputs.get(sig["key"])
        if sig["type"] == "numeric":
            try:
                val = float(raw)
            except (TypeError, ValueError):
                val = None
            score = _score_numeric(val, sig["bands"]) if val is not None else 0
            shown = sig["fmt"](val) if val is not None else "—"
        else:
            score = sig["map"].get(raw, 0)
            shown = raw if raw else "—"

        w = sig["weight"]
        weighted_sum += score * w
        max_abs += 2 * w
        rows.append({
            "key": sig["key"], "label_vi": sig["label_vi"], "label_en": sig["label_en"],
            "hint_vi": sig.get("hint_vi", ""), "hint_en": sig.get("hint_en", ""),
            "value": shown, "score": score, "weight": w,
            "contribution": round(score * w, 2), "color": score_color(score),
        })

    onscore = round(50 + 50 * weighted_sum / max_abs) if max_abs else 50
    onscore = max(0, min(100, onscore))

    if onscore >= THRESH_RISK_ON:
        regime = "Risk-on"
    elif onscore > THRESH_RISK_OFF:
        regime = "Mixed"
    else:
        regime = "Risk-off"
    base_regime = regime

    caps = [c for c in _caps(market) if c["trigger"](inputs.get(c["signal"]))]
    if caps and regime == "Risk-on":
        regime = "Mixed"

    vetoes = [v for v in _vetoes(market) if v["trigger"](inputs.get(v["signal"]))]
    if vetoes:
        regime = "Risk-off"

    return {
        "market": market, "rows": rows,
        "weighted_sum": round(weighted_sum, 2), "max_abs": max_abs,
        "onscore": onscore, "base_regime": base_regime, "regime": regime,
        "caps": caps, "vetoes": vetoes,
        "thresholds": {"risk_on": THRESH_RISK_ON, "risk_off": THRESH_RISK_OFF},
    }


def regime_rationale(result, lang="vi"):
    r = result["regime"]
    s = result["onscore"]
    if result["vetoes"]:
        return f"🚫 VETO → Risk-off. {result['vetoes'][0][f'reason_{lang}']}"
    if result["caps"] and result["base_regime"] == "Risk-on":
        why = result["caps"][0][f"reason_{lang}"]
        if lang == "vi":
            return f"Điểm {s}/100 đủ Risk-on, nhưng bị chặn xuống Mixed: {why}"
        return f"Score {s}/100 reaches Risk-on, but capped to Mixed: {why}"
    if lang == "vi":
        return f"Risk-on Score = {s}/100 → kết luận {r} theo ngưỡng công khai (≥66 / 34–65 / ≤33)."
    return f"Risk-on Score = {s}/100 → {r} per public thresholds (≥66 / 34–65 / ≤33)."


# ── Cầu nối bảng regime_radar cũ (CHỈ thị trường VN — Portfolio Risk Checker đọc) ──
def to_legacy_fields(inputs):
    """Trả (vix, vn_vs_ma200, breadth, credit, margin_status) cho save_regime_radar cũ."""
    return (
        inputs.get("vix", 0.0), inputs.get("vn_vs_ma200", ""), inputs.get("breadth", ""),
        inputs.get("sbv_rates", ""), inputs.get("margin_status", ""),
    )


# ─────────────────────────────────────────────────────────────────────────────
# PHÁT HIỆN "REGIME ĐANG XẤU ĐI" (cảnh báo sớm theo xu hướng điểm) — chung mọi TT.
# ─────────────────────────────────────────────────────────────────────────────
import math as _math

DETERIORATION_INFO = {
    "IMPROVING": {"color": "#059669", "label_vi": "Đang cải thiện", "label_en": "Improving",
        "action_vi": "Môi trường đang tốt lên. Vẫn giữ kỷ luật Risk First — đừng vì điểm tăng mà nới size quá tay.",
        "action_en": "Environment improving. Keep Risk First discipline — don't loosen sizing just because the score rose."},
    "STABLE": {"color": "#10B981", "label_vi": "Ổn định", "label_en": "Stable",
        "action_vi": "Chưa có dấu hiệu xấu đi. Duy trì kỷ luật hiện tại, không cần hành động phòng thủ thêm.",
        "action_en": "No signs of deterioration. Maintain current discipline; no extra defense needed."},
    "SOFTENING": {"color": "#D97706", "label_vi": "Bắt đầu mềm đi", "label_en": "Softening",
        "action_vi": "Cảnh giác sớm: NGỪNG mở vị thế mới, siết lại stop, rà soát mã yếu nhất. Chưa cần bán mạnh.",
        "action_en": "Early caution: STOP opening new positions, tighten stops, review your weakest names. No heavy selling yet."},
    "DETERIORATING": {"color": "#F97316", "label_vi": "Đang xấu đi", "label_en": "Deteriorating",
        "action_vi": "Giảm rủi ro DẦN: cắt bớt phần rủi ro nhất (vd ~1/3), không mở lệnh mới, ưu tiên nâng tiền mặt. Đừng chờ đổi màu mới phản ứng.",
        "action_en": "De-risk GRADUALLY: trim your riskiest exposure (e.g. ~1/3), no new entries, raise cash. Don't wait for a color flip to react."},
    "CRITICAL": {"color": "#DC2626", "label_vi": "Xấu đi nghiêm trọng", "label_en": "Critical",
        "action_vi": "Phòng thủ tối đa: hạ rủi ro mạnh, nâng tiền mặt. Coi như đang bước vào Risk-off — Risk First là phản ứng với XU HƯỚNG, không chờ nhãn.",
        "action_en": "Maximum defense: cut risk hard, raise cash. Treat it as entering Risk-off — Risk First means reacting to the TREND, not the label."},
    "RISK_OFF": {"color": "#DC2626", "label_vi": "Đã ở Risk-off", "label_en": "Already Risk-off",
        "action_vi": "Ưu tiên bảo toàn vốn. No-trade là quyết định hợp lệ. Chờ bằng chứng đảo chiều thật trước khi tăng rủi ro (Evidence First).",
        "action_en": "Capital preservation first. No-trade is a valid decision. Wait for real reversal evidence before adding risk (Evidence First)."},
}


def deterioration_action(status, lang="vi"):
    info = DETERIORATION_INFO.get(status, DETERIORATION_INFO["STABLE"])
    return info[f"action_{lang}"]


def _signal_scores(signals, market="vn"):
    res = compute_regime(signals or {}, market)
    return {r["key"]: r for r in res["rows"]}


def analyze_deterioration(history, market="vn"):
    """history: list snapshot CŨ → MỚI. Trả None nếu < 2 tuần."""
    pts = [h for h in history if h.get("onscore") is not None]
    if len(pts) < 2:
        return None

    scores = [int(p["onscore"]) for p in pts]
    current, prev = scores[-1], scores[-2]
    delta = current - prev

    streak = 0
    for i in range(len(scores) - 1, 0, -1):
        if scores[i] < scores[i - 1]:
            streak += 1
        else:
            break
    total_drop = (scores[len(scores) - 1 - streak] - current) if streak > 0 else 0

    window = scores[-5:] if len(scores) >= 5 else scores
    diffs = [window[i] - window[i - 1] for i in range(1, len(window))]
    avg_change = sum(diffs) / len(diffs) if diffs else 0.0

    weeks_to_riskoff = None
    if avg_change < 0 and current > THRESH_RISK_OFF:
        weeks_to_riskoff = _math.ceil((current - THRESH_RISK_OFF) / abs(avg_change))

    cur_sig = _signal_scores(pts[-1].get("signals", {}), market)
    prev_sig = _signal_scores(pts[-2].get("signals", {}), market)
    dropped = []
    for k, cur in cur_sig.items():
        p = prev_sig.get(k)
        if p and cur["score"] < p["score"]:
            dropped.append({"key": k, "label_vi": cur["label_vi"], "label_en": cur["label_en"],
                            "from": p["value"], "to": cur["value"], "delta": cur["score"] - p["score"]})
    dropped.sort(key=lambda d: d["delta"])

    near = current - THRESH_RISK_OFF

    if pts[-1].get("regime_call") == "Risk-off" or current <= THRESH_RISK_OFF:
        status = "RISK_OFF"
    elif (near <= 8 and (delta < 0 or streak >= 1)) or delta <= -12 or (streak >= 3 and near <= 15):
        status = "CRITICAL"
    elif streak >= 2 or delta <= -7 or total_drop >= 15:
        status = "DETERIORATING"
    elif (streak == 1 and delta <= -1) or (-6 <= delta <= -1):
        status = "SOFTENING"
    elif delta >= 5:
        status = "IMPROVING"
    else:
        status = "STABLE"

    return {"status": status, "current": current, "prev": prev, "delta": delta,
            "streak": streak, "total_drop": total_drop, "avg_change": round(avg_change, 1),
            "weeks_to_riskoff": weeks_to_riskoff, "near": near, "dropped": dropped, "n": len(pts)}
