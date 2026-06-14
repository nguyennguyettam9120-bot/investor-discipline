# bias_store.py
# ─────────────────────────────────────────────────────────────────────────────
# Lưu/đọc dữ liệu cho Tấm gương cá nhân.
#   • bias_events: log bias suy ra từ AI Coach (bảng MỚI).
#   • get_evening_routines: đọc lại Evening Routine đã lưu (bảng routines sẵn có)
#     → tấm gương chạy hồi tố trên dữ liệu người dùng đã ghi, không cần chờ.
# KHÔNG sửa database.py — chỉ mượn get_conn().
# ─────────────────────────────────────────────────────────────────────────────
import json
from database import get_conn


def _ensure_events(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bias_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT,
                bias_code TEXT,
                detail TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def log_biases(user_id, source, codes, detail=""):
    """Ghi một dòng cho mỗi mã bias (vd từ một lần dùng AI Coach)."""
    if not codes:
        return
    conn = get_conn()
    _ensure_events(conn)
    for c in codes:
        conn.execute(
            "INSERT INTO bias_events (user_id, source, bias_code, detail) VALUES (?,?,?,?)",
            (user_id, source, c, detail)
        )
    conn.commit()
    conn.close()


def get_bias_events(user_id):
    """Trả list {date, source, code}. Mỗi dòng = 1 lần bias xuất hiện."""
    conn = get_conn()
    _ensure_events(conn)
    rows = conn.execute(
        "SELECT created_at, source, bias_code FROM bias_events WHERE user_id=? ORDER BY created_at",
        (user_id,)
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        out.append({"date": d.get("created_at", ""), "source": d.get("source", ""),
                    "code": d.get("bias_code", "")})
    return out


def get_evening_routines(user_id):
    """Đọc lại toàn bộ Evening Routine đã lưu. Trả list {date, answers(dict)}."""
    conn = get_conn()
    # bảng routines do database.save_routine tạo; đảm bảo tồn tại để query an toàn
    conn.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            routine_type TEXT NOT NULL,
            routine_date TEXT NOT NULL,
            answers TEXT,
            score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    rows = conn.execute(
        "SELECT routine_date, answers FROM routines WHERE user_id=? AND routine_type='evening' ORDER BY routine_date",
        (user_id,)
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            ans = json.loads(d["answers"]) if d.get("answers") else {}
        except (ValueError, TypeError):
            ans = {}
        out.append({"date": d.get("routine_date", ""), "answers": ans})
    return out
