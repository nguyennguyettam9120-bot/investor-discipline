# regime_store.py
# ─────────────────────────────────────────────────────────────────────────────
# Lưu/đọc regime "v2" ĐA THỊ TRƯỜNG (cột market: 'vn' | 'us').
#   • Bảng MỚI regime_v2 (signals_json + onscore + market).
#   • Cầu nối bảng cũ regime_radar CHỈ cho thị trường VN (Portfolio Risk Checker đọc).
# KHÔNG sửa database.py — chỉ mượn get_conn().
# ─────────────────────────────────────────────────────────────────────────────
import json
from database import get_conn, save_regime_radar
from regime_engine import to_legacy_fields


def _ensure_table(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regime_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_label TEXT NOT NULL,
                market TEXT DEFAULT 'vn',
                signals_json TEXT,
                regime_call TEXT,
                onscore INTEGER,
                note_vi TEXT,
                note_en TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    # Migration: thêm cột market cho DB cũ (đã có bảng nhưng chưa có cột).
    # Trên Postgres, lệnh lỗi (cột đã tồn tại) làm HỎNG transaction → phải rollback
    # để các truy vấn sau (SELECT) còn chạy được. SQLite thì rollback vô hại.
    try:
        conn.execute("ALTER TABLE regime_v2 ADD COLUMN market TEXT DEFAULT 'vn'")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def save_regime_v2(user_id, week_label, signals, regime_call, onscore, note_vi, note_en, market="vn"):
    conn = get_conn()
    _ensure_table(conn)
    sj = json.dumps(signals, ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM regime_v2 WHERE week_label=? AND market=?", (week_label, market)
    ).fetchone()
    if existing:
        conn.execute("""
            UPDATE regime_v2 SET signals_json=?, regime_call=?, onscore=?,
            note_vi=?, note_en=? WHERE week_label=? AND market=?
        """, (sj, regime_call, onscore, note_vi, note_en, week_label, market))
    else:
        conn.execute("""
            INSERT INTO regime_v2 (week_label, market, signals_json, regime_call, onscore, note_vi, note_en)
            VALUES (?,?,?,?,?,?,?)
        """, (week_label, market, sj, regime_call, onscore, note_vi, note_en))
    conn.commit()
    conn.close()

    # Cầu nối bảng cũ CHỈ cho VN (US không có Portfolio Risk Checker tương ứng)
    if market == "vn":
        vix, vn_ma, breadth, credit, margin = to_legacy_fields(signals)
        save_regime_radar(user_id, week_label, vix, vn_ma, breadth, credit, margin,
                          regime_call, note_vi, note_en)


def _row_to_dict(row):
    d = dict(row)
    try:
        d["signals"] = json.loads(d["signals_json"]) if d.get("signals_json") else {}
    except (ValueError, TypeError):
        d["signals"] = {}
    return d


def get_regime_v2_latest(market="vn"):
    conn = get_conn()
    _ensure_table(conn)
    row = conn.execute(
        "SELECT * FROM regime_v2 WHERE market=? ORDER BY created_at DESC, id DESC LIMIT 1",
        (market,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_regime_v2_history(limit=12, market="vn"):
    conn = get_conn()
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT * FROM regime_v2 WHERE market=? ORDER BY created_at DESC, id DESC LIMIT ?",
        (market, limit)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]
