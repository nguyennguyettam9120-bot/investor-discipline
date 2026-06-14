# bias_engine.py
# ─────────────────────────────────────────────────────────────────────────────
# TẤM GƯƠNG CÁ NHÂN — Engine dựng "bias profile" từ chính quyết định người dùng.
#
# Triết lý "biết ta": app không chỉ giảng về bias chung chung, mà phản chiếu
# CHÍNH BẠN — bias nào bạn lặp lại nhiều nhất, tháng này có khá hơn tháng trước không.
#
# Nguồn dữ liệu (đã có sẵn trong app, dùng hồi tố):
#   • Evening Routine: vi phạm kỷ luật, cảm xúc vào/thoát, quadrant kết quả/quy trình.
#   • AI Coach: cảm xúc, stop-loss, % size, đánh giá regime (suy ra bias xác định).
#
# Module THUẦN Python (không streamlit/DB) → test được.
# ─────────────────────────────────────────────────────────────────────────────

# ─── BỘ MÃ BIAS (mở rộng từ taxonomy của app) ─────────────────────────────────
# severity: high (đỏ) / med (cam) / low (hổ phách) — để tô màu & ưu tiên.
BIAS_META = {
    "FOMO": {
        "name_vi": "FOMO (sợ bỏ lỡ)", "name_en": "FOMO", "severity": "high",
        "fix_vi": "Trước khi mua, hỏi 'nếu sai mất bao nhiêu?'. Đang đuổi giá đã tăng mạnh = dừng lại. (Bài 1, Bài 9)",
        "fix_en": "Before buying, ask 'if wrong, how much do I lose?'. Chasing an already-extended move = stop. (Lessons 1, 9)",
    },
    "HERD": {
        "name_vi": "Theo đám đông", "name_en": "Herd mentality", "severity": "med",
        "fix_vi": "Quyết định theo bằng chứng của bạn, không theo room/đám đông. Đám đông sai ở đỉnh và đáy. (Bài 11)",
        "fix_en": "Decide on your own evidence, not the crowd/groups. The crowd is wrong at tops and bottoms. (Lesson 11)",
    },
    "OVERCONFIDENCE": {
        "name_vi": "Tự tin thái quá", "name_en": "Overconfidence", "severity": "med",
        "fix_vi": "Thị trường là xác suất. Khi thấy mình 'chắc chắn' — đó là lúc giảm size. (Bài 9)",
        "fix_en": "Markets are probabilities. Feeling 'certain' is the cue to cut size. (Lesson 9)",
    },
    "ACTION": {
        "name_vi": "Buộc phải hành động", "name_en": "Action bias", "severity": "low",
        "fix_vi": "No-Trade là quyết định hợp lệ. Không phải ngày nào cũng phải vào lệnh.",
        "fix_en": "No-Trade is a valid decision. You don't have to trade every day.",
    },
    "OUTCOME": {
        "name_vi": "Đánh giá theo kết quả", "name_en": "Outcome bias", "severity": "low",
        "fix_vi": "Đánh giá quyết định bằng QUY TRÌNH, không bằng lãi/lỗ. Lãi nhờ sai quy trình = rủi ro dài hạn.",
        "fix_en": "Judge decisions by PROCESS, not P&L. Profit from bad process = long-term risk.",
    },
    "REVENGE": {
        "name_vi": "Gỡ gạc (revenge)", "name_en": "Revenge trading", "severity": "high",
        "fix_vi": "Sau khi lỗ, DỪNG. Không vào lệnh khi đang tức. Đây là lỗi cảm xúc nguy hiểm nhất. (Bài 9)",
        "fix_en": "After a loss, STOP. Don't trade angry. The most dangerous emotional error. (Lesson 9)",
    },
    "NO_STOP": {
        "name_vi": "Không có stop-loss", "name_en": "No stop-loss", "severity": "high",
        "fix_vi": "Luôn xác định điểm thoát TRƯỚC khi vào lệnh. Không stop = lỗi quy trình nặng nhất.",
        "fix_en": "Always define your exit BEFORE entering. No stop = the most critical process error.",
    },
    "OVERSIZE": {
        "name_vi": "Size quá lớn", "name_en": "Oversizing", "severity": "high",
        "fix_vi": "Risk First: tối đa ~2% rủi ro mỗi lệnh. Cắt size xuống để sống sót qua chuỗi thua.",
        "fix_en": "Risk First: max ~2% risk per trade. Cut size to survive losing streaks.",
    },
    "IGNORE_REGIME": {
        "name_vi": "Bỏ qua regime", "name_en": "Ignored regime", "severity": "med",
        "fix_vi": "Regime First: luôn kiểm tra regime trước. Setup đẹp trong Risk-off vẫn là No-Trade. (Bài 2)",
        "fix_en": "Regime First: always check regime first. A great setup in Risk-off is still No-Trade. (Lesson 2)",
    },
    "GREED": {
        "name_vi": "Lòng tham (giữ quá lâu)", "name_en": "Greed (held too long)", "severity": "med",
        "fix_vi": "Chốt theo kế hoạch. Đừng để lòng tham biến lệnh lãi thành lệnh lỗ.",
        "fix_en": "Exit per plan. Don't let greed turn a winner into a loser.",
    },
    "PANIC": {
        "name_vi": "Hoảng loạn", "name_en": "Panic", "severity": "med",
        "fix_vi": "Phản ứng theo kế hoạch đã định, không bán tháo theo cảm xúc. Kiểm tra bằng chứng trước.",
        "fix_en": "React per your predefined plan, not panic-selling. Check evidence first.",
    },
}

SEV_COLOR = {"high": "#DC2626", "med": "#F97316", "low": "#D97706"}


def bias_color(code):
    return SEV_COLOR.get(BIAS_META.get(code, {}).get("severity", "low"), "#64748B")


# ─── CHUẨN HÓA NHÃN (song ngữ) → MÃ BIAS ──────────────────────────────────────
_LABEL_TO_CODE = {
    # vi phạm kỷ luật (Evening Routine)
    "Không có stop-loss": "NO_STOP", "No stop-loss": "NO_STOP",
    "FOMO mua đuổi": "FOMO", "FOMO chasing": "FOMO",
    "Revenge trading": "REVENGE",
    "Size quá lớn": "OVERSIZE", "Oversized": "OVERSIZE",
    "Bỏ qua regime": "IGNORE_REGIME", "Ignored regime": "IGNORE_REGIME",
    # cảm xúc
    "FOMO": "FOMO",
    "Tham lam": "GREED", "Greedy": "GREED",
    "Tham lam — giữ quá lâu": "GREED", "Greedy — held too long": "GREED",
    "FOMO — cắt lời sớm": "FOMO", "FOMO — cut winner early": "FOMO",
    "Hoảng loạn": "PANIC", "Panic": "PANIC",
    "Sợ hãi": "PANIC", "Fear": "PANIC",
    "Tức giận / Revenge": "REVENGE", "Anger / Revenge": "REVENGE",
}

_CLEAN_LABELS = {"Không có", "None"}
_TRADED_YES = {"Có", "Yes"}


def biases_from_evening(answers):
    """answers: dict đã lưu của Evening Routine.
    Trả (codes:list, clean:bool|None, traded:bool)."""
    codes = []
    traded = str(answers.get("traded", "")) in _TRADED_YES

    violated = answers.get("violated", []) or []
    if isinstance(violated, str):
        violated = [violated]
    real_violations = [v for v in violated if v not in _CLEAN_LABELS]
    for v in real_violations:
        c = _LABEL_TO_CODE.get(v)
        if c:
            codes.append(c)

    for emo_key in ("emotion_entry", "emotion_exit"):
        c = _LABEL_TO_CODE.get(str(answers.get(emo_key, "")))
        if c:
            codes.append(c)

    # quadrant kết quả: "lãi nhưng sai quy trình" = nguy cơ outcome bias
    outcome = str(answers.get("outcome", ""))
    if "sai quy trình" in outcome or "bad process" in outcome:
        if "Lãi" in outcome or "Profit" in outcome:
            codes.append("OUTCOME")

    # clean = có giao dịch nhưng không vi phạm gì
    if not traded:
        clean = None  # đứng ngoài — không tính vào tỷ lệ kỷ luật khi giao dịch
    else:
        clean = (len(real_violations) == 0)

    # khử trùng lặp, giữ thứ tự
    seen = set()
    codes = [c for c in codes if not (c in seen or seen.add(c))]
    return codes, clean, traded


def biases_from_ai_coach(emotion="", stop_loss="", risk_pct=0, regime=""):
    """Suy ra bias xác định từ input AI Coach (không cần phân tích văn bản AI)."""
    codes = []
    c = _LABEL_TO_CODE.get(str(emotion))
    if c:
        codes.append(c)
    if not str(stop_loss).strip():
        codes.append("NO_STOP")
    try:
        if float(risk_pct) > 20:
            codes.append("OVERSIZE")
    except (TypeError, ValueError):
        pass
    if str(regime) in ("Chưa kiểm tra", "Not checked"):
        codes.append("IGNORE_REGIME")
    seen = set()
    return [c for c in codes if not (c in seen or seen.add(c))]


# ─── TỔNG HỢP HỒ SƠ ───────────────────────────────────────────────────────────
def _d10(s):
    """Lấy 10 ký tự đầu (YYYY-MM-DD) từ date/datetime string."""
    return str(s)[:10] if s else ""


def build_profile(records, today_iso):
    """
    records: list dict {"date": "YYYY-MM-DD", "source": str, "biases": [codes], "clean": bool|None}
    today_iso: "YYYY-MM-DD" hôm nay.
    Trả tổng hợp cho dashboard (hoặc None nếu rỗng).
    """
    if not records:
        return None

    from datetime import date as _date
    y, m, d = map(int, today_iso.split("-"))
    today = _date(y, m, d)

    def _in_window(ds, lo, hi):
        try:
            yy, mm, dd = map(int, ds.split("-"))
            delta = (today - _date(yy, mm, dd)).days
            return lo <= delta <= hi
        except Exception:
            return False

    counts = {}
    recent = {}   # 0–29 ngày
    prior = {}    # 30–59 ngày
    for rec in records:
        ds = _d10(rec.get("date"))
        for c in rec.get("biases", []):
            counts[c] = counts.get(c, 0) + 1
            if _in_window(ds, 0, 29):
                recent[c] = recent.get(c, 0) + 1
            elif _in_window(ds, 30, 59):
                prior[c] = prior.get(c, 0) + 1

    # tỷ lệ kỷ luật khi giao dịch (clean / số lần có giao dịch được chấm)
    traded_recs = [r for r in records if r.get("clean") is not None]
    clean_n = sum(1 for r in traded_recs if r.get("clean"))
    clean_rate = round(100 * clean_n / len(traded_recs)) if traded_recs else None

    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # cải thiện theo từng bias: recent vs prior
    improvement = {}
    for c in counts:
        improvement[c] = {"recent": recent.get(c, 0), "prior": prior.get(c, 0)}

    return {
        "n_records": len(records),
        "n_traded": len(traded_recs),
        "clean_rate": clean_rate,
        "counts": counts,
        "recent": recent,
        "prior": prior,
        "top": top,                 # list (code, total) đã sắp xếp
        "improvement": improvement,
        "total_flags": sum(counts.values()),
    }
