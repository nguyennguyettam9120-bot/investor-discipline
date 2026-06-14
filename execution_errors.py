# execution_errors.py
# ─────────────────────────────────────────────────────────────────────────────
# #5 — LỖI THỰC THI: thua dù luận điểm đúng.
#   • EXECUTION_LESSON: nội dung bài học (thêm vào dict LESSONS của app).
#   • EXECUTION_CHECKLIST: self-check tương tác (giống module "Bạn có là thanh khoản?").
#
# Mảng lỗi này khác với bias tâm lý: đây là lỗi HÀNH ĐỘNG — cách bạn vào/ra/quản
# lệnh khiến tài khoản bị bào mòn ngay cả khi nhận định đúng.
# ─────────────────────────────────────────────────────────────────────────────

# Khóa bài học — thêm vào LESSONS: LESSONS.update(EXECUTION_LESSON)
EXECUTION_LESSON = {
    "12. Lỗi thực thi: thua dù luận điểm đúng": {
        "vi": """
Nhiều người nhận định **đúng** mà vẫn lỗ. Vì sao? Không phải vì sai thị trường — mà vì **lỗi thực thi**: cách vào, ra, và quản lệnh. Đây là nơi tài khoản bị bào mòn âm thầm.

**1. Bình quân giá xuống (averaging down)**

Mua thêm khi cổ phiếu đang lỗ để "hạ giá vốn". Đây là cách biến lỗ nhỏ thành lỗ thảm họa — bạn đang ném tiền tốt theo tiền xấu, không có điểm dừng.
- Khác với *scaling-in có kế hoạch*: scaling-in định trước các mức mua VÀ điểm invalidation. Bình quân xuống cảm tính thì không có cả hai.

**2. Không có kế hoạch viết ra**

Vào lệnh vì hy vọng, ra lệnh vì hoảng loạn. Trước khi vào, hãy viết ra 4 thứ: **lý do vào · điểm invalidation (sai thì ở đâu) · mục tiêu · size**. Không viết được = chưa đủ rõ để vào.

**3. Phí, thuế & T+ bào mòn (đặc thù VN)**

Mỗi vòng mua-bán mất phí 2 chiều + thuế bán. Giao dịch càng nhiều, phí ăn càng sâu. T+ nghĩa là bạn không thể bán ngay — kẹt qua biến động.

| Tần suất | Phí+thuế/vòng (~0.4%) | 1 năm |
|---|---|---|
| 1 lệnh/tháng | 0.4% × 12 | ~5% vốn |
| 1 lệnh/tuần | 0.4% × 50 | ~20% vốn |
| 1 lệnh/ngày | 0.4% × 250 | ~**100% vốn** |

*(Số minh họa.)* Overtrading là cái chết bởi ngàn nhát cắt nhỏ.

**4. Đu phím hàng / room kèo**

Nếu một "kèo" được phát miễn phí và công khai — **bạn không phải khách hàng, bạn là thanh khoản thoát hàng** cho người vào trước. Ba lý do nó luôn thua: bạn nhận tin sau cùng (info đến muộn); không biết luận điểm nên không biết khi nào sai; không size được vì không hiểu rủi ro.

**5. Quá tập trung vs quá phân tán**

All-in 1 mã = rủi ro một điểm chí mạng. Ôm 30 mã không theo dõi nổi = "diworsification" — vừa không hiểu mã nào, vừa tốn phí. Cân bằng: đủ ít để HIỂU, đủ nhiều để SỐNG SÓT một cú nổ đơn lẻ.

**6. Dời stop-loss khi giá tới gần**

Lỗi nguy hiểm nhất: đặt stop rồi *nới ra xa* khi giá chạm vì "rồi nó sẽ hồi". Làm vậy là xóa sạch quản trị rủi ro. Stop đã đặt là cam kết — không dời theo cảm xúc.

**7. Giữ qua sự kiện mà không có kế hoạch**

ĐHCĐ, kết quả KD, tin vĩ mô — giữ qua sự kiện nhị phân mà không có kế hoạch cho CẢ HAI kịch bản = đánh bạc, không phải đầu tư.

> Luận điểm đúng mà thực thi sai vẫn cháy tài khoản. Phòng thủ trước: kế hoạch viết ra, stop không dời, size nhỏ, giao dịch ít mà chất.
""",
        "en": """
Many people are **right** about the market and still lose. Why? Not because of the thesis — but because of **execution errors**: how you enter, exit, and manage the trade. This is where accounts erode quietly.

**1. Averaging down into a loser**

Buying more of a losing stock to "lower your cost". This turns a small loss into a catastrophic one — throwing good money after bad, with no stopping point.
- Different from *planned scaling-in*: scaling-in predefines the buy levels AND an invalidation. Emotional averaging-down has neither.

**2. No written plan**

Enter on hope, exit on panic. Before entering, write four things: **entry reason · invalidation (where you're wrong) · target · size**. Can't write them = not clear enough to enter.

**3. Fees, tax & T+ erosion (VN-specific)**

Every round trip costs two-way fees + sell tax. The more you trade, the deeper costs bite. T+ settlement means you can't sell instantly — stuck through volatility.

| Frequency | Cost/round trip (~0.4%) | Per year |
|---|---|---|
| 1 trade/month | 0.4% × 12 | ~5% of capital |
| 1 trade/week | 0.4% × 50 | ~20% of capital |
| 1 trade/day | 0.4% × 250 | ~**100% of capital** |

*(Illustrative.)* Overtrading is death by a thousand small cuts.

**4. Following tips / signal groups**

If a "tip" is handed out free and publicly — **you're not the customer, you're the exit liquidity** for whoever entered earlier. Three reasons it always loses: you get the info last; you don't know the thesis so you can't know when it's wrong; you can't size it because you don't understand the risk.

**5. Over-concentration vs over-diversification**

All-in on one name = single point of catastrophic risk. Holding 30 names you can't track = "diworsification" — you understand none of them and pay more fees. Balance: few enough to KNOW, many enough to SURVIVE a single blow-up.

**6. Moving the stop-loss as price approaches**

The deadliest error: setting a stop then *widening it* when price hits, because "it'll come back". This erases all risk management. A placed stop is a commitment — don't move it on emotion.

**7. Holding through events with no plan**

AGMs, earnings, macro news — holding through a binary event with no plan for BOTH outcomes = gambling, not investing.

> A correct thesis with poor execution still blows up the account. Defend first: a written plan, a stop you don't move, small size, fewer but higher-quality trades.
"""
    }
}


# Self-check tương tác. Mỗi mục có cách sửa nhúng sẵn + bài học liên quan.
EXECUTION_CHECKLIST = [
    {
        "vi": "Tôi từng mua thêm cổ phiếu đang lỗ để 'hạ giá vốn' mà không có mức dừng",
        "en": "I've bought more of a losing stock to 'lower my cost' with no stopping point",
        "fix_vi": "Bình quân xuống cảm tính = ném tiền tốt theo tiền xấu. Chỉ scaling-in khi đã định trước các mức VÀ điểm invalidation.",
        "fix_en": "Emotional averaging-down = good money after bad. Only scale in with predefined levels AND an invalidation.",
        "lesson": "Bài 12 · §1",
    },
    {
        "vi": "Tôi vào lệnh mà không viết ra trước: lý do, invalidation, mục tiêu, size",
        "en": "I enter trades without writing down: reason, invalidation, target, size",
        "fix_vi": "Không viết được 4 thứ đó = chưa đủ rõ để vào. Vào vì lý do, ra vì lý do — không vì cảm xúc.",
        "fix_en": "If you can't write those four, it's not clear enough to enter. Enter for a reason, exit for a reason.",
        "lesson": "Bài 12 · §2",
    },
    {
        "vi": "Tôi giao dịch khá thường xuyên (nhiều lần mỗi tuần)",
        "en": "I trade fairly often (several times a week)",
        "fix_vi": "Phí + thuế mỗi vòng ~0.4%. Giao dịch nhiều = chết bởi ngàn nhát cắt. Ít mà chất.",
        "fix_en": "Fees + tax ~0.4% per round trip. Frequent trading = death by a thousand cuts. Fewer, higher quality.",
        "lesson": "Bài 12 · §3",
    },
    {
        "vi": "Tôi từng mua theo phím hàng / room kèo mà không hiểu luận điểm",
        "en": "I've bought on tips / signal groups without understanding the thesis",
        "fix_vi": "Kèo miễn phí công khai = bạn là thanh khoản thoát hàng. Không biết luận điểm thì không biết khi nào sai.",
        "fix_en": "Free public tips = you're the exit liquidity. Not knowing the thesis means not knowing when it's wrong.",
        "lesson": "Bài 12 · §4",
    },
    {
        "vi": "Tôi dồn phần lớn tài khoản vào 1–2 mã",
        "en": "I put most of my account into just 1–2 stocks",
        "fix_vi": "All-in 1 mã = rủi ro một điểm chí mạng. Đủ ít để hiểu, đủ nhiều để sống sót một cú nổ đơn lẻ.",
        "fix_en": "All-in one name = single point of catastrophic risk. Few enough to know, many enough to survive a blow-up.",
        "lesson": "Bài 12 · §5",
    },
    {
        "vi": "Tôi ôm quá nhiều mã đến mức không theo dõi nổi từng mã",
        "en": "I hold so many names I can't actually track each one",
        "fix_vi": "Quá phân tán = 'diworsification': không hiểu mã nào, lại tốn phí. Thu gọn về số mã bạn thật sự hiểu.",
        "fix_en": "Over-diversification = 'diworsification': you know none and pay more fees. Trim to names you truly understand.",
        "lesson": "Bài 12 · §5",
    },
    {
        "vi": "Tôi từng dời stop-loss ra xa hơn khi giá tới gần vì nghĩ 'rồi sẽ hồi'",
        "en": "I've moved my stop-loss further away as price approached, thinking 'it'll come back'",
        "fix_vi": "Dời stop = xóa sạch quản trị rủi ro. Stop đã đặt là cam kết — không dời theo cảm xúc.",
        "fix_en": "Moving the stop erases all risk management. A placed stop is a commitment — don't move it on emotion.",
        "lesson": "Bài 12 · §6",
    },
    {
        "vi": "Tôi giữ lệnh qua sự kiện (ĐHCĐ, KQKD, tin lớn) mà không có kế hoạch cho cả 2 kịch bản",
        "en": "I hold through events (AGM, earnings, big news) with no plan for both outcomes",
        "fix_vi": "Giữ qua sự kiện nhị phân không kế hoạch = đánh bạc. Định trước: nếu tốt làm gì, nếu xấu làm gì.",
        "fix_en": "Holding through a binary event with no plan = gambling. Predefine: what if good, what if bad.",
        "lesson": "Bài 12 · §7",
    },
    {
        "vi": "Tôi ít khi tính phí/thuế/T+ vào quyết định giao dịch",
        "en": "I rarely factor fees/tax/T+ settlement into my trade decisions",
        "fix_vi": "Chi phí là kẻ thù thầm lặng. Mỗi vòng phải bù được phí + thuế mới hòa vốn. Tính trước khi vào.",
        "fix_en": "Costs are the silent enemy. Each round trip must beat fees + tax just to break even. Account for it upfront.",
        "lesson": "Bài 12 · §3",
    },
    {
        "vi": "Tôi thường vào lệnh vì 'sợ bỏ lỡ', không phải vì setup theo kế hoạch",
        "en": "I often enter because of 'fear of missing out', not a planned setup",
        "fix_vi": "Hành động vì FOMO là lỗi thực thi gốc. No-Trade là lựa chọn hợp lệ. Chờ setup của BẠN.",
        "fix_en": "Acting on FOMO is the root execution error. No-Trade is valid. Wait for YOUR setup.",
        "lesson": "Bài 12 · §2",
    },
]
