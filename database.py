import sqlite3
import bcrypt
import os
import re
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")


# ─────────────────────────────────────────────────────────────────────────────
# DUAL-MODE DATABASE: tự động dùng Supabase (Postgres) nếu có cấu hình,
# nếu không thì fallback về SQLite (chạy local an toàn).
#
# Để bật Supabase: thêm vào Streamlit Secrets:
#     SUPABASE_DB_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
# ─────────────────────────────────────────────────────────────────────────────

def _get_secret(key):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key)


_SUPABASE_URL = _get_secret("SUPABASE_DB_URL")
USE_POSTGRES = bool(_SUPABASE_URL)


def _translate_sql(sql):
    """Chuyển cú pháp SQLite sang Postgres.
    Giữ cột thời gian dạng TEXT (như SQLite) — hàm datetime trả về text ISO
    để so sánh từ điển vẫn đúng theo thời gian."""
    TS = "'YYYY-MM-DD HH24:MI:SS'"
    # datetime('now', ?) -> to_char(NOW() + (?)::interval, ...)  [trước placeholder]
    sql = sql.replace(
        "datetime('now', ?)",
        f"to_char(NOW() + (?)::interval, {TS})",
    )
    # datetime('now', '-N days') (có/không khoảng trắng)
    sql = re.sub(
        r"datetime\('now',\s*'-(\d+)\s*days?'\)",
        lambda m: f"to_char(NOW() - INTERVAL '{m.group(1)} days', {TS})",
        sql,
    )
    # datetime('now') -> to_char(NOW(), ...)
    sql = sql.replace("datetime('now')", f"to_char(NOW(), {TS})")
    # DATE(col) trên cột text -> ép kiểu để Postgres hiểu
    sql = re.sub(r"\bDATE\((\w+)\)", r"(\1)::date", sql)
    # Kiểu khóa chính tự tăng
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    # INSERT OR IGNORE -> INSERT ... ON CONFLICT DO NOTHING
    has_insert_or_ignore = "INSERT OR IGNORE" in sql
    sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
    # Placeholder ? -> %s
    sql = sql.replace("?", "%s")
    if has_insert_or_ignore:
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return sql


if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
    except ImportError:
        USE_POSTGRES = False

    class _PGCursor:
        """Cursor bọc psycopg2, tự dịch SQL và hỗ trợ row dạng dict + index."""
        def __init__(self, cur):
            self._cur = cur

        def execute(self, sql, params=()):
            self._cur.execute(_translate_sql(sql), params)
            return self

        def fetchone(self):
            return self._cur.fetchone()

        def fetchall(self):
            return self._cur.fetchall()

        @property
        def lastrowid(self):
            try:
                row = self._cur.fetchone()
                return row[0] if row else None
            except Exception:
                return None

        def close(self):
            self._cur.close()

    class _PGConnection:
        """Connection bọc psycopg2 để hành xử giống sqlite3.Connection."""
        def __init__(self, dsn):
            self._conn = psycopg2.connect(dsn)
            self._conn.autocommit = False

        def cursor(self):
            return _PGCursor(self._conn.cursor(cursor_factory=DictCursor))

        def execute(self, sql, params=()):
            cur = self._conn.cursor(cursor_factory=DictCursor)
            cur.execute(_translate_sql(sql), params)
            return _PGCursor(cur)

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            self._conn.close()

    # Lỗi trùng khóa của Postgres — để code cũ bắt được như sqlite3.IntegrityError
    IntegrityError = psycopg2.IntegrityError

    def get_conn():
        return _PGConnection(_SUPABASE_URL)

else:
    IntegrityError = sqlite3.IntegrityError

    def get_conn():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    if not USE_POSTGRES:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT
        )
    """)

    # Journal entries
    c.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            ticker TEXT,
            decision TEXT,
            reason TEXT,
            invalidation TEXT,
            risk TEXT,
            emotion TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Challenge progress
    c.execute("""
        CREATE TABLE IF NOT EXISTS challenge_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            challenge TEXT NOT NULL,
            regime_correct INTEGER,
            decision_correct INTEGER,
            risk_correct INTEGER,
            score INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Historical simulator results
    c.execute("""
        CREATE TABLE IF NOT EXISTS historical_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            case_name TEXT NOT NULL,
            regime_correct INTEGER,
            decision_correct INTEGER,
            risk_correct INTEGER,
            score INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Learning memory snapshots
    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            snapshot_date TEXT NOT NULL,
            total_attempts INTEGER,
            regime_accuracy REAL,
            decision_accuracy REAL,
            risk_accuracy REAL,
            avg_score REAL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Curriculum completion
    c.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_completion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            item TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Payments / subscriptions
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            plan TEXT DEFAULT 'free',
            started_at TEXT,
            expires_at TEXT,
            payment_ref TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ─── AUTH ──────────────────────────────────────────────────────────────────────

def register_user(username, email, password):
    conn = get_conn()
    try:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username.strip().lower(), email.strip().lower(), pw_hash)
        )
        conn.commit()
        return True, "ok"
    except IntegrityError as e:
        try:
            conn.rollback()
        except Exception:
            pass
        msg = str(e).lower()
        if "username" in msg:
            return False, "username_taken"
        elif "email" in msg:
            return False, "email_taken"
        return False, "error"
    finally:
        conn.close()


def login_user(username_or_email, password):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? OR email=?",
        (username_or_email.strip().lower(), username_or_email.strip().lower())
    ).fetchone()
    conn.close()
    if not row:
        return None, "not_found"
    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return None, "wrong_password"
    # Update last login
    conn2 = get_conn()
    conn2.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now().isoformat(), row["id"]))
    conn2.commit()
    conn2.close()
    return dict(row), "ok"


def get_user_plan(user_id):
    conn = get_conn()
    row = conn.execute("SELECT plan FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row["plan"] if row else "free"


def upgrade_user_plan(user_id, plan="pro"):
    conn = get_conn()
    conn.execute("UPDATE users SET plan=? WHERE id=?", (plan, user_id))
    conn.commit()
    conn.close()


# ─── JOURNAL ───────────────────────────────────────────────────────────────────

def save_journal(user_id, ticker, decision, reason, invalidation, risk, emotion):
    conn = get_conn()
    conn.execute(
        "INSERT INTO journal (user_id, date, ticker, decision, reason, invalidation, risk, emotion) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, date.today().isoformat(), ticker, decision, reason, invalidation, risk, emotion)
    )
    conn.commit()
    conn.close()


def get_journal(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM journal WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── CHALLENGE PROGRESS ────────────────────────────────────────────────────────

def save_challenge(user_id, challenge, regime_correct, decision_correct, risk_correct, score):
    conn = get_conn()
    conn.execute(
        "INSERT INTO challenge_progress (user_id, date, challenge, regime_correct, decision_correct, risk_correct, score) VALUES (?,?,?,?,?,?,?)",
        (user_id, date.today().isoformat(), challenge, int(regime_correct), int(decision_correct), int(risk_correct), score)
    )
    conn.commit()
    conn.close()


def get_challenge_stats(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM challenge_progress WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── HISTORICAL ────────────────────────────────────────────────────────────────

def save_historical(user_id, case_name, regime_correct, decision_correct, risk_correct, score):
    conn = get_conn()
    conn.execute(
        "INSERT INTO historical_results (user_id, date, case_name, regime_correct, decision_correct, risk_correct, score) VALUES (?,?,?,?,?,?,?)",
        (user_id, date.today().isoformat(), case_name, int(regime_correct), int(decision_correct), int(risk_correct), score)
    )
    conn.commit()
    conn.close()


def get_historical_stats(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM historical_results WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── LEARNING MEMORY ───────────────────────────────────────────────────────────

def save_snapshot(user_id, total_attempts, regime_acc, decision_acc, risk_acc, avg_score):
    conn = get_conn()
    conn.execute(
        "INSERT INTO learning_memory (user_id, snapshot_date, total_attempts, regime_accuracy, decision_accuracy, risk_accuracy, avg_score) VALUES (?,?,?,?,?,?,?)",
        (user_id, datetime.now().isoformat(), total_attempts, regime_acc, decision_acc, risk_acc, avg_score)
    )
    conn.commit()
    conn.close()


def get_snapshots(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM learning_memory WHERE user_id=? ORDER BY snapshot_date ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── DISCIPLINE STATS ──────────────────────────────────────────────────────────

def get_discipline_stats(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT emotion, decision FROM journal WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    total = len(rows)
    fomo_count = sum(1 for r in rows if r["emotion"] == "FOMO")
    no_trade_count = sum(1 for r in rows if r["decision"] == "NO TRADE")
    discipline_score = max(0, 100 - fomo_count * 10)
    return {"total": total, "fomo": fomo_count, "no_trade": no_trade_count, "score": discipline_score}


# ─── ADMIN FUNCTIONS ───────────────────────────────────────────────────────────

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_ENV = "INVESTOR_ADMIN_PASSWORD"  # set via env var in production

def is_admin(username):
    return username.strip().lower() == ADMIN_USERNAME

def admin_get_all_users():
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.id, u.username, u.email, u.plan, u.created_at, u.last_login,
               COUNT(DISTINCT j.id) as journal_count,
               COUNT(DISTINCT h.id) as hist_count,
               COUNT(DISTINCT c.id) as challenge_count
        FROM users u
        LEFT JOIN journal j ON j.user_id = u.id
        LEFT JOIN historical_results h ON h.user_id = u.id
        LEFT JOIN challenge_progress c ON c.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def admin_get_stats():
    conn = get_conn()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    pro_users   = conn.execute("SELECT COUNT(*) FROM users WHERE plan='pro'").fetchone()[0]
    free_users  = total_users - pro_users
    total_journal = conn.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
    total_hist    = conn.execute("SELECT COUNT(*) FROM historical_results").fetchone()[0]
    total_challenges = conn.execute("SELECT COUNT(*) FROM challenge_progress").fetchone()[0]
    # New users last 7 days
    new_7d = conn.execute(
        "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
    ).fetchone()[0]
    # Active users last 7 days (have any activity)
    active_7d = conn.execute("""
        SELECT COUNT(DISTINCT user_id) FROM (
            SELECT user_id FROM journal WHERE created_at >= datetime('now','-7 days')
            UNION
            SELECT user_id FROM historical_results WHERE created_at >= datetime('now','-7 days')
            UNION
            SELECT user_id FROM challenge_progress WHERE created_at >= datetime('now','-7 days')
        )
    """).fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "pro_users": pro_users,
        "free_users": free_users,
        "total_journal": total_journal,
        "total_hist": total_hist,
        "total_challenges": total_challenges,
        "new_7d": new_7d,
        "active_7d": active_7d,
    }

def admin_set_plan(user_id, plan):
    conn = get_conn()
    conn.execute("UPDATE users SET plan=? WHERE id=?", (plan, user_id))
    conn.commit()
    conn.close()

def admin_delete_user(user_id):
    conn = get_conn()
    for tbl in ["journal", "historical_results", "challenge_progress",
                "learning_memory", "curriculum_completion", "subscriptions"]:
        conn.execute(f"DELETE FROM {tbl} WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def admin_get_daily_signups(days=30):
    conn = get_conn()
    rows = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM users
        WHERE created_at >= datetime('now', ?)
        GROUP BY DATE(created_at)
        ORDER BY day ASC
    """, (f"-{days} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def admin_get_activity_log(limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT 'journal' as type, u.username, j.created_at as ts, j.ticker as detail
        FROM journal j JOIN users u ON u.id=j.user_id
        UNION ALL
        SELECT 'historical' as type, u.username, h.created_at as ts, h.case_name as detail
        FROM historical_results h JOIN users u ON u.id=h.user_id
        UNION ALL
        SELECT 'challenge' as type, u.username, c.created_at as ts, c.challenge as detail
        FROM challenge_progress c JOIN users u ON u.id=c.user_id
        ORDER BY ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def admin_ensure_admin_user(password):
    """Create admin account if it doesn't exist, or reset password."""
    conn = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    if existing:
        conn.execute("UPDATE users SET password_hash=?, plan='pro' WHERE username='admin'", (pw_hash,))
    else:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, plan) VALUES ('admin','admin@investor-discipline.app',?,'pro')",
            (pw_hash,)
        )
    conn.commit()
    conn.close()

# ─── REGIME RADAR ──────────────────────────────────────────────────────────────

def save_regime_radar(user_id, week_label, vix, vn_vs_ma200, breadth, credit, margin_status, regime_call, note_vi, note_en):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_radar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_label TEXT NOT NULL,
            vix REAL,
            vn_vs_ma200 TEXT,
            breadth TEXT,
            credit TEXT,
            margin_status TEXT,
            regime_call TEXT,
            note_vi TEXT,
            note_en TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # upsert by week_label
    existing = conn.execute(
        "SELECT id FROM regime_radar WHERE week_label=?", (week_label,)
    ).fetchone()
    if existing:
        conn.execute("""
            UPDATE regime_radar SET vix=?, vn_vs_ma200=?, breadth=?, credit=?,
            margin_status=?, regime_call=?, note_vi=?, note_en=?, user_id=?
            WHERE week_label=?
        """, (vix, vn_vs_ma200, breadth, credit, margin_status, regime_call, note_vi, note_en, user_id, week_label))
    else:
        conn.execute("""
            INSERT INTO regime_radar (user_id, week_label, vix, vn_vs_ma200, breadth, credit, margin_status, regime_call, note_vi, note_en)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (user_id, week_label, vix, vn_vs_ma200, breadth, credit, margin_status, regime_call, note_vi, note_en))
    conn.commit()
    conn.close()

def get_regime_radar_latest():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_radar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_label TEXT NOT NULL,
            vix REAL,
            vn_vs_ma200 TEXT,
            breadth TEXT,
            credit TEXT,
            margin_status TEXT,
            regime_call TEXT,
            note_vi TEXT,
            note_en TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    row = conn.execute(
        "SELECT * FROM regime_radar ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_regime_radar_history(limit=12):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_radar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_label TEXT NOT NULL,
            vix REAL,
            vn_vs_ma200 TEXT,
            breadth TEXT,
            credit TEXT,
            margin_status TEXT,
            regime_call TEXT,
            note_vi TEXT,
            note_en TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    rows = conn.execute(
        "SELECT * FROM regime_radar ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── DAILY CHALLENGE — CUSTOM & AI-GENERATED ──────────────────────────────────

def save_custom_challenge(user_id, date_str, q_vi, q_en, opts_vi, opts_en, answer_vi, answer_en, explain_vi, explain_en, source="admin"):
    import json
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date_str TEXT NOT NULL UNIQUE,
            q_vi TEXT, q_en TEXT,
            opts_vi TEXT, opts_en TEXT,
            answer_vi TEXT, answer_en TEXT,
            explain_vi TEXT, explain_en TEXT,
            source TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    existing = conn.execute("SELECT id FROM custom_daily_challenges WHERE date_str=?", (date_str,)).fetchone()
    if existing:
        conn.execute("""
            UPDATE custom_daily_challenges
            SET q_vi=?,q_en=?,opts_vi=?,opts_en=?,answer_vi=?,answer_en=?,explain_vi=?,explain_en=?,source=?
            WHERE date_str=?
        """, (q_vi, q_en, json.dumps(opts_vi, ensure_ascii=False), json.dumps(opts_en, ensure_ascii=False),
              answer_vi, answer_en, explain_vi, explain_en, source, date_str))
    else:
        conn.execute("""
            INSERT INTO custom_daily_challenges
            (user_id,date_str,q_vi,q_en,opts_vi,opts_en,answer_vi,answer_en,explain_vi,explain_en,source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (user_id, date_str, q_vi, q_en,
              json.dumps(opts_vi, ensure_ascii=False), json.dumps(opts_en, ensure_ascii=False),
              answer_vi, answer_en, explain_vi, explain_en, source))
    conn.commit()
    conn.close()

def get_custom_challenge(date_str):
    import json
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date_str TEXT NOT NULL UNIQUE,
            q_vi TEXT, q_en TEXT,
            opts_vi TEXT, opts_en TEXT,
            answer_vi TEXT, answer_en TEXT,
            explain_vi TEXT, explain_en TEXT,
            source TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    row = conn.execute(
        "SELECT * FROM custom_daily_challenges WHERE date_str=?", (date_str,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    r["opts_vi"] = json.loads(r["opts_vi"]) if r["opts_vi"] else []
    r["opts_en"] = json.loads(r["opts_en"]) if r["opts_en"] else []
    return r

def get_recent_custom_challenges(limit=10):
    import json
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_daily_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date_str TEXT NOT NULL UNIQUE,
            q_vi TEXT, q_en TEXT,
            opts_vi TEXT, opts_en TEXT,
            answer_vi TEXT, answer_en TEXT,
            explain_vi TEXT, explain_en TEXT,
            source TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    rows = conn.execute(
        "SELECT * FROM custom_daily_challenges ORDER BY date_str DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        r = dict(row)
        r["opts_vi"] = json.loads(r["opts_vi"]) if r["opts_vi"] else []
        r["opts_en"] = json.loads(r["opts_en"]) if r["opts_en"] else []
        result.append(r)
    return result

# ─── STREAK ────────────────────────────────────────────────────────────────────

def record_daily_activity(user_id):
    """Record that user was active today for streak tracking."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            UNIQUE(user_id, activity_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    from datetime import date
    today = date.today().isoformat()
    try:
        conn.execute("INSERT OR IGNORE INTO daily_activity (user_id, activity_date) VALUES (?,?)", (user_id, today))
        conn.commit()
    except: pass
    conn.close()

def get_streak(user_id):
    """Get current streak and longest streak."""
    from datetime import date, timedelta
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            UNIQUE(user_id, activity_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    rows = conn.execute(
        "SELECT activity_date FROM daily_activity WHERE user_id=? ORDER BY activity_date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return 0, 0
    dates = sorted([r[0] for r in rows], reverse=True)
    # Current streak
    current = 0
    today = date.today()
    for i, d in enumerate(dates):
        expected = (today - timedelta(days=i)).isoformat()
        if d == expected:
            current += 1
        else:
            break
    # Longest streak
    longest = 1
    temp = 1
    for i in range(1, len(dates)):
        d1 = date.fromisoformat(dates[i-1])
        d2 = date.fromisoformat(dates[i])
        if (d1 - d2).days == 1:
            temp += 1
            longest = max(longest, temp)
        else:
            temp = 1
    return current, max(current, longest)

def get_leaderboard(limit=10):
    """Get top users by streak."""
    from datetime import date, timedelta
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            UNIQUE(user_id, activity_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    rows = conn.execute("""
        SELECT u.id, u.username, u.plan,
               COUNT(DISTINCT da.activity_date) as total_days
        FROM users u
        LEFT JOIN daily_activity da ON da.user_id = u.id
        WHERE u.username != 'admin' AND u.username != 'demo'
        GROUP BY u.id
        ORDER BY total_days DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── REFERRAL ──────────────────────────────────────────────────────────────────

def get_referral_code(user_id, username):
    """Get or create referral code for user."""
    import hashlib
    return f"REF{hashlib.md5(f'{user_id}{username}'.encode()).hexdigest()[:6].upper()}"

def record_referral(referrer_user_id, new_user_id):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL UNIQUE,
            rewarded INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referred_id) REFERENCES users(id)
        )
    """)
    try:
        conn.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)",
                     (referrer_user_id, new_user_id))
        conn.commit()
    except: pass
    conn.close()

def get_referral_stats(user_id):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL UNIQUE,
            rewarded INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referred_id) REFERENCES users(id)
        )
    """)
    total = conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,)).fetchone()[0]
    pro_refs = conn.execute("""
        SELECT COUNT(*) FROM referrals r
        JOIN users u ON u.id = r.referred_id
        WHERE r.referrer_id=? AND u.plan='pro'
    """, (user_id,)).fetchone()[0]
    conn.close()
    return {"total": total, "pro": pro_refs}

# ─── AI USAGE TRACKING ─────────────────────────────────────────────────────────

def track_ai_usage(user_id, feature):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            feature TEXT NOT NULL,
            month_str TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            UNIQUE(user_id, feature, month_str),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    from datetime import date
    month_str = date.today().strftime("%Y-%m")
    conn.execute("""
        INSERT INTO ai_usage (user_id, feature, month_str, count) VALUES (?,?,?,1)
        ON CONFLICT(user_id, feature, month_str) DO UPDATE SET count = count + 1
    """, (user_id, feature, month_str))
    conn.commit()
    conn.close()

def get_ai_usage(user_id, feature=None):
    from datetime import date
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            feature TEXT NOT NULL,
            month_str TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            UNIQUE(user_id, feature, month_str),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    month_str = date.today().strftime("%Y-%m")
    if feature:
        row = conn.execute(
            "SELECT count FROM ai_usage WHERE user_id=? AND feature=? AND month_str=?",
            (user_id, feature, month_str)
        ).fetchone()
        conn.close()
        return row[0] if row else 0
    else:
        rows = conn.execute(
            "SELECT feature, count FROM ai_usage WHERE user_id=? AND month_str=?",
            (user_id, month_str)
        ).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}

# ─── PAYMENT (PayOS + manual) ──────────────────────────────────────────────────

def create_payment_order(user_id, order_code, amount, plan="pro", method="payos"):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_code TEXT NOT NULL UNIQUE,
            amount INTEGER NOT NULL,
            plan TEXT DEFAULT 'pro',
            method TEXT DEFAULT 'payos',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute(
        "INSERT INTO payment_orders (user_id, order_code, amount, plan, method) VALUES (?,?,?,?,?)",
        (user_id, str(order_code), amount, plan, method)
    )
    conn.commit()
    conn.close()

def mark_payment_paid(order_code):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_code TEXT NOT NULL UNIQUE,
            amount INTEGER NOT NULL,
            plan TEXT DEFAULT 'pro',
            method TEXT DEFAULT 'payos',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    row = conn.execute("SELECT user_id, plan FROM payment_orders WHERE order_code=?", (str(order_code),)).fetchone()
    if row:
        conn.execute("UPDATE payment_orders SET status='paid', paid_at=datetime('now') WHERE order_code=?", (str(order_code),))
        conn.execute("UPDATE users SET plan=? WHERE id=?", (row["plan"], row["user_id"]))
        conn.commit()
        conn.close()
        return True, row["user_id"]
    conn.close()
    return False, None

def get_payment_status(order_code):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_code TEXT NOT NULL UNIQUE,
            amount INTEGER NOT NULL,
            plan TEXT DEFAULT 'pro',
            method TEXT DEFAULT 'payos',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    row = conn.execute("SELECT * FROM payment_orders WHERE order_code=?", (str(order_code),)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_pending_payments():
    """For admin: list pending manual payments."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_code TEXT NOT NULL UNIQUE,
            amount INTEGER NOT NULL,
            plan TEXT DEFAULT 'pro',
            method TEXT DEFAULT 'payos',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    rows = conn.execute("""
        SELECT p.*, u.username, u.email FROM payment_orders p
        JOIN users u ON u.id = p.user_id
        WHERE p.status='pending'
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_email(user_id):
    conn = get_conn()
    row = conn.execute("SELECT email, username FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ─── MORNING / EVENING ROUTINE ────────────────────────────────────────────────

def save_routine(user_id, routine_type, answers_json, score):
    """routine_type: 'morning' or 'evening'"""
    import json
    conn = get_conn()
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
    from datetime import date
    today = date.today().isoformat()
    # Allow one per type per day (upsert)
    existing = conn.execute(
        "SELECT id FROM routines WHERE user_id=? AND routine_type=? AND routine_date=?",
        (user_id, routine_type, today)
    ).fetchone()
    payload = json.dumps(answers_json, ensure_ascii=False)
    if existing:
        conn.execute("UPDATE routines SET answers=?, score=? WHERE id=?",
                     (payload, score, existing[0]))
    else:
        conn.execute(
            "INSERT INTO routines (user_id, routine_type, routine_date, answers, score) VALUES (?,?,?,?,?)",
            (user_id, routine_type, today, payload, score)
        )
    conn.commit()
    conn.close()

def get_routine_today(user_id, routine_type):
    import json
    conn = get_conn()
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
    from datetime import date
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT * FROM routines WHERE user_id=? AND routine_type=? AND routine_date=?",
        (user_id, routine_type, today)
    ).fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    try: r["answers"] = json.loads(r["answers"]) if r["answers"] else {}
    except: r["answers"] = {}
    return r

def get_routine_streak(user_id, routine_type):
    from datetime import date, timedelta
    conn = get_conn()
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
        "SELECT routine_date FROM routines WHERE user_id=? AND routine_type=? ORDER BY routine_date DESC",
        (user_id, routine_type)
    ).fetchall()
    conn.close()
    if not rows:
        return 0
    dates = [r[0] for r in rows]
    streak = 0
    today = date.today()
    for i in range(len(dates)):
        expected = (today - timedelta(days=i)).isoformat()
        if dates[i] == expected:
            streak += 1
        else:
            break
    return streak

# ─── COMMUNITY FEED ────────────────────────────────────────────────────────────

def save_feed_event(user_id, event_type, detail=""):
    """event_type: 'daily_correct', 'simulator_score', 'challenge_score', 'streak_milestone'"""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS community_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            detail TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute(
        "INSERT INTO community_feed (user_id, event_type, detail) VALUES (?,?,?)",
        (user_id, event_type, detail)
    )
    conn.commit()
    conn.close()

def get_community_feed(limit=30):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS community_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            detail TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    rows = conn.execute("""
        SELECT f.event_type, f.detail, f.created_at,
               u.username, u.plan
        FROM community_feed f
        JOIN users u ON u.id = f.user_id
        WHERE u.username NOT IN ('admin','demo')
        ORDER BY f.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_community_stats():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS community_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            detail TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    week_active = conn.execute("""
        SELECT COUNT(DISTINCT user_id) FROM community_feed
        WHERE created_at >= datetime('now', '-7 days')
    """).fetchone()[0]
    total_events = conn.execute("SELECT COUNT(*) FROM community_feed").fetchone()[0]
    pro_count = conn.execute("SELECT COUNT(*) FROM users WHERE plan='pro'").fetchone()[0]
    free_count = conn.execute("SELECT COUNT(*) FROM users WHERE plan='free' AND username NOT IN ('admin','demo')").fetchone()[0]
    conn.close()
    return {
        "week_active": week_active,
        "total_events": total_events,
        "pro_count": pro_count,
        "free_count": free_count,
        "total_users": pro_count + free_count,
    }

# ─── MARKET NEWS (admin-curated weekly) ────────────────────────────────────────

def save_market_news(user_id, week_label, headline_vi, headline_en, body_vi, body_en, lesson_link=""):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_label TEXT NOT NULL,
            headline_vi TEXT,
            headline_en TEXT,
            body_vi TEXT,
            body_en TEXT,
            lesson_link TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    existing = conn.execute(
        "SELECT id FROM market_news WHERE week_label=?", (week_label,)
    ).fetchone()
    if existing:
        conn.execute("""
            UPDATE market_news SET headline_vi=?,headline_en=?,body_vi=?,body_en=?,lesson_link=?,user_id=?
            WHERE week_label=?
        """, (headline_vi, headline_en, body_vi, body_en, lesson_link, user_id, week_label))
    else:
        conn.execute("""
            INSERT INTO market_news (user_id,week_label,headline_vi,headline_en,body_vi,body_en,lesson_link)
            VALUES (?,?,?,?,?,?,?)
        """, (user_id, week_label, headline_vi, headline_en, body_vi, body_en, lesson_link))
    conn.commit()
    conn.close()

def get_market_news_latest(n=3):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_label TEXT NOT NULL,
            headline_vi TEXT,
            headline_en TEXT,
            body_vi TEXT,
            body_en TEXT,
            lesson_link TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    rows = conn.execute(
        "SELECT * FROM market_news ORDER BY created_at DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
