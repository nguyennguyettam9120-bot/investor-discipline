# regime_training.py
# ─────────────────────────────────────────────────────────────────────────────
# Luyện tập phân loại regime — TÁCH THEO THỊ TRƯỜNG (VN / US).
# Mỗi tình huống là một bộ tín hiệu THẬT; đáp án do chính rubric (compute_regime)
# chấm → người dùng học đúng logic của Regime Radar, không phải bộ đáp án rời rạc.
# Kèm REGIME_TRANSITIONS: giải thích rõ các bước chuyển Risk-on ↔ Mixed ↔ Risk-off.
# ─────────────────────────────────────────────────────────────────────────────

TRAINING_CASES_VN = [
    {
        "name_vi": "Uptrend khỏe", "name_en": "Healthy uptrend",
        "signals": dict(vn_vs_ma200="Trên MA200", breadth="Mạnh", foreign_flow="Mua ròng",
                        margin_status="Bình thường", liquidity="Tăng lành mạnh", fx="Ổn định",
                        sbv_rates="Ổn định", vix=14),
        "note_vi": "Mọi tín hiệu đồng thuận và breadth MẠNH — đủ điều kiện Risk-on thật.",
        "note_en": "All signals aligned and breadth STRONG — genuine Risk-on conditions.",
    },
    {
        "name_vi": "Rally hẹp (breadth yếu)", "name_en": "Narrow rally (weak breadth)",
        "signals": dict(vn_vs_ma200="Trên MA200", breadth="Yếu", foreign_flow="Mua ròng",
                        margin_status="Bình thường", liquidity="Bình thường", fx="Ổn định",
                        sbv_rates="Ổn định", vix=16),
        "note_vi": "Index vẫn trên MA200 nhưng ít cổ phiếu dẫn dắt. Điểm có thể cao, nhưng CAP breadth chặn xuống Mixed: rally không độ rộng chưa phải uptrend thật.",
        "note_en": "Index above MA200 but few stocks lead. Score may be high, but the breadth CAP holds it to Mixed: a rally without breadth isn't a real uptrend.",
    },
    {
        "name_vi": "Khối ngoại xả ròng kéo dài", "name_en": "Sustained foreign selling",
        "signals": dict(vn_vs_ma200="Trên MA200", breadth="Mạnh", foreign_flow="Bán ròng mạnh kéo dài",
                        margin_status="Bình thường", liquidity="Tăng lành mạnh", fx="Ổn định",
                        sbv_rates="Ổn định", vix=15),
        "note_vi": "Nội đỡ tốt nhưng ngoại bán ròng mạnh kéo dài = lực bán cấu trúc. CAP chặn Risk-on dù điểm cao — đặc thù rất VN.",
        "note_en": "Locals support but foreigners sell heavily and persistently = structural selling. The CAP blocks Risk-on despite a high score — very VN-specific.",
    },
    {
        "name_vi": "Margin call / force-sell", "name_en": "Margin call / force-sell",
        "signals": dict(vn_vs_ma200="Sát MA200", breadth="Yếu", foreign_flow="Bán ròng",
                        margin_status="Force-sell đang xảy ra", liquidity="Suy giảm", fx="Áp lực nhẹ",
                        sbv_rates="Ổn định", vix=26),
        "note_vi": "Force-sell đang diễn ra → VETO ép thẳng Risk-off bất kể điểm số. Rẻ không phải lý do mua khi giảm chấp dây chuyền chưa dứt.",
        "note_en": "Force-selling in progress → VETO forces Risk-off regardless of score. Cheap is not a reason to buy while the margin-call cascade continues.",
    },
    {
        "name_vi": "Gấu kiểu 2022 (VN)", "name_en": "2022-style bear (VN)",
        "signals": dict(vn_vs_ma200="Dưới MA200", breadth="Yếu", foreign_flow="Bán ròng mạnh kéo dài",
                        margin_status="Đang giảm chấp", liquidity="Suy giảm", fx="Căng thẳng",
                        sbv_rates="Thắt chặt mạnh", vix=32),
        "note_vi": "Mọi thứ xấu cùng lúc + SBV thắt chặt mạnh (VETO). Môi trường bảo toàn vốn tuyệt đối.",
        "note_en": "Everything bad at once + SBV aggressive tightening (VETO). Absolute capital-preservation environment.",
    },
    {
        "name_vi": "Hồi phục đầu (Risk-off → Mixed)", "name_en": "Early recovery (Risk-off → Mixed)",
        "signals": dict(vn_vs_ma200="Sát MA200", breadth="Trung tính", foreign_flow="Trung tính",
                        margin_status="Bình thường", liquidity="Bình thường", fx="Ổn định",
                        sbv_rates="Ổn định", vix=20),
        "note_vi": "Đã ngừng xấu, index lấy lại sát MA200, không còn force-sell. Đủ để rời Risk-off lên Mixed — nhưng CHƯA đủ Risk-on (breadth chưa mạnh).",
        "note_en": "Stopped deteriorating, index back near MA200, no force-sell. Enough to leave Risk-off for Mixed — but NOT Risk-on yet (breadth not strong).",
    },
]

TRAINING_CASES_US = [
    {
        "name_vi": "Bull khỏe", "name_en": "Healthy bull",
        "signals": dict(sp_vs_ma200="Trên MA200", breadth="Mạnh", vix=14,
                        credit_hy="Hẹp (ổn định)", fed_policy="Nới lỏng",
                        yield_curve="Dốc lên (bình thường)"),
        "note_vi": "Trend tốt, breadth mạnh, tín dụng hẹp, Fed nới lỏng — Risk-on rõ ràng.",
        "note_en": "Good trend, strong breadth, tight credit, Fed easing — clear Risk-on.",
    },
    {
        "name_vi": "Megacap kéo (breadth yếu)", "name_en": "Megacaps carry it (weak breadth)",
        "signals": dict(sp_vs_ma200="Trên MA200", breadth="Yếu", vix=15,
                        credit_hy="Bình thường", fed_policy="Trung lập", yield_curve="Phẳng"),
        "note_vi": "S&P tăng nhưng chỉ vài siêu cổ phiếu kéo. CAP breadth chặn xuống Mixed — cảnh báo rally hẹp kinh điển của Mỹ.",
        "note_en": "S&P up but only a few megacaps lead. The breadth CAP holds it to Mixed — the classic US narrow-rally warning.",
    },
    {
        "name_vi": "Tín dụng HY nới rộng", "name_en": "High-yield spreads widening",
        "signals": dict(sp_vs_ma200="Trên MA200", breadth="Mạnh", vix=16,
                        credit_hy="Đang nới rộng", fed_policy="Trung lập", yield_curve="Phẳng"),
        "note_vi": "Cổ phiếu còn khỏe nhưng thị trường NỢ đang cảnh báo (spread nới rộng). CAP chặn Risk-on — tín dụng thường 'thấy' rủi ro trước cổ phiếu.",
        "note_en": "Stocks still firm but the DEBT market is flagging risk (spreads widening). The CAP blocks Risk-on — credit often 'sees' risk before equities.",
    },
    {
        "name_vi": "Fed thắt chặt mạnh", "name_en": "Fed tightening hard",
        "signals": dict(sp_vs_ma200="Sát MA200", breadth="Trung tính", vix=24,
                        credit_hy="Bình thường", fed_policy="Thắt chặt mạnh", yield_curve="Đảo ngược"),
        "note_vi": "Fed siết mạnh thanh khoản → VETO ép Risk-off. 'Don't fight the Fed' — đừng tăng rủi ro khi Fed đang hút tiền.",
        "note_en": "Fed squeezing liquidity hard → VETO forces Risk-off. 'Don't fight the Fed' — don't add risk while the Fed drains liquidity.",
    },
    {
        "name_vi": "Gấu 2022 (US)", "name_en": "2022 bear (US)",
        "signals": dict(sp_vs_ma200="Dưới MA200", breadth="Yếu", vix=32,
                        credit_hy="Đang nới rộng", fed_policy="Thắt chặt mạnh",
                        yield_curve="Đảo ngược sâu"),
        "note_vi": "Dưới MA200, tín dụng xấu, Fed thắt chặt mạnh, đường cong đảo ngược sâu — Risk-off toàn diện.",
        "note_en": "Below MA200, credit deteriorating, Fed tightening hard, deeply inverted curve — broad Risk-off.",
    },
    {
        "name_vi": "Hồi phục đầu (Risk-off → Mixed)", "name_en": "Early recovery (Risk-off → Mixed)",
        "signals": dict(sp_vs_ma200="Sát MA200", breadth="Trung tính", vix=19,
                        credit_hy="Bình thường", fed_policy="Trung lập", yield_curve="Phẳng"),
        "note_vi": "Áp lực giảm bớt, S&P về sát MA200, tín dụng ổn lại, Fed trung lập. Rời Risk-off lên Mixed — chờ breadth mạnh mới lên Risk-on.",
        "note_en": "Pressure easing, S&P back near MA200, credit stabilizing, Fed neutral. Leaving Risk-off for Mixed — wait for strong breadth before Risk-on.",
    },
]

TRAINING_BY_MARKET = {"vn": TRAINING_CASES_VN, "us": TRAINING_CASES_US}


# ─── GIẢI THÍCH CHUYỂN TRẠNG THÁI (Risk-on ↔ Mixed ↔ Risk-off) ────────────────
REGIME_TRANSITIONS = [
    {
        "from": "Risk-off", "to": "Mixed", "color": "#D97706",
        "title_vi": "Risk-off → Mixed (đầu hồi phục)", "title_en": "Risk-off → Mixed (early recovery)",
        "trigger_vi": "Khi NGỪNG xấu đi: index lấy lại sát/trên MA200, breadth bớt yếu, force-sell dừng, tín dụng/lãi suất ổn lại. Điểm vượt 34. Đây chỉ là 'hết nguy hiểm cấp tính', CHƯA phải tín hiệu mua mạnh.",
        "trigger_en": "When deterioration STOPS: index reclaims near/above MA200, breadth recovers, force-selling ends, credit/rates stabilize. Score crosses 34. This is only 'acute danger over', NOT a strong buy signal.",
    },
    {
        "from": "Mixed", "to": "Risk-on", "color": "#059669",
        "title_vi": "Mixed → Risk-on (cần xác nhận độ rộng)", "title_en": "Mixed → Risk-on (needs breadth confirmation)",
        "trigger_vi": "Điểm phải vượt 66 VÀ breadth MẠNH (cổng bắt buộc). Đây là bước khó nhất: rất nhiều 'rally' kẹt ở Mixed vì breadth yếu — chỉ vài mã lớn kéo. Không có độ rộng = chưa Risk-on.",
        "trigger_en": "Score must exceed 66 AND breadth must be STRONG (mandatory gate). The hardest step: many 'rallies' stay stuck in Mixed on weak breadth — only a few big names lead. No breadth = no Risk-on.",
    },
    {
        "from": "Risk-on", "to": "Mixed", "color": "#D97706",
        "title_vi": "Risk-on → Mixed (suy yếu sớm)", "title_en": "Risk-on → Mixed (early weakening)",
        "trigger_vi": "Điểm tụt dưới 66, HOẶC một CAP kích hoạt (breadth không còn mạnh, một tín hiệu then chốt rớt: ngoại xả ròng kéo dài / credit nới rộng / tỷ giá căng). Đây là lúc GIẢM rủi ro dần — đừng chờ Risk-off.",
        "trigger_en": "Score falls below 66, OR a CAP triggers (breadth no longer strong, a key signal breaks: sustained foreign selling / widening credit / FX stress). This is when to de-risk gradually — don't wait for Risk-off.",
    },
    {
        "from": "Mixed", "to": "Risk-off", "color": "#DC2626",
        "title_vi": "Mixed → Risk-off (chuyển phòng thủ)", "title_en": "Mixed → Risk-off (defensive shift)",
        "trigger_vi": "Điểm tụt dưới 34, HOẶC một VETO kích hoạt: force-sell / khủng hoảng tín dụng / SBV (hoặc Fed) thắt chặt mạnh / breadth sụp đổ. Ưu tiên bảo toàn vốn, No-Trade là hợp lệ.",
        "trigger_en": "Score falls below 34, OR a VETO triggers: force-sell / credit crisis / SBV (or Fed) aggressive tightening / breadth collapse. Capital preservation first; No-Trade is valid.",
    },
    {
        "from": "Risk-on", "to": "Risk-off", "color": "#DC2626",
        "title_vi": "Risk-on → Risk-off (nhảy thẳng — cú sốc)", "title_en": "Risk-on → Risk-off (direct jump — a shock)",
        "trigger_vi": "Hiếm nhưng nguy hiểm nhất: chỉ xảy ra qua VETO (một sự kiện sốc: khủng hoảng tín dụng, force-sell dây chuyền, ngân hàng trung ương thắt chặt sốc). Bỏ qua Mixed. Vì sao cần stop & sizing: bạn không kịp 'giảm dần'.",
        "trigger_en": "Rare but most dangerous: only via a VETO (a shock event: credit crisis, cascading force-sell, central-bank shock tightening). Skips Mixed. This is why stops & sizing matter: there's no time to 'de-risk gradually'.",
    },
    {
        "from": "early", "to": "warning", "color": "#F97316",
        "title_vi": "⏱️ Cảnh báo SỚM: điểm trượt trước khi đổi nhãn", "title_en": "⏱️ EARLY warning: score drifts before the label changes",
        "trigger_vi": "Quan trọng nhất: regime thường KHÔNG đổi đột ngột. Điểm Risk-on Score trượt dần nhiều tuần (vd 86→78→71→67) TRƯỚC khi nhãn đổi màu. Panel 'Xu hướng regime' bắt đúng giai đoạn này — phản ứng với xu hướng, không chờ nhãn.",
        "trigger_en": "Most important: regime rarely flips abruptly. The Risk-on Score drifts down over weeks (e.g. 86→78→71→67) BEFORE the label changes color. The 'Regime Trend' panel catches exactly this phase — react to the trend, not the label.",
    },
]
