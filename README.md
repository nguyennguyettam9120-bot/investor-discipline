# Investor Discipline App

Training investment mindset: **Risk First · Regime First · Evidence First · Governance**

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Architecture

```
investor_app/
├── app.py           # Main Streamlit app (UI + routing)
├── database.py      # SQLite backend (auth, per-user data)
├── content.py       # All bilingual content (lessons, quiz, cases)
├── requirements.txt
├── .streamlit/
│   └── config.toml  # Theme & server config
└── data/
    └── app.db       # SQLite database (auto-created)
```

## Key fixes vs original

| Issue | Fix |
|---|---|
| CSV shared across all users | SQLite per-user tables |
| No authentication | Register/Login with bcrypt hashing |
| No monetization | Free / Pro freemium model with paywalls |
| Personal info hard-coded | Moved to payment modal only |
| 1 quiz question per topic | 2-3 questions per topic (11 total) |
| No onboarding | Welcome screen + learning path |
| Flat 27-item menu | Grouped sections + progressive disclosure |
| No Pro gating | Feature gates on advanced analytics, unlimited journal, all cases |

## Deployment

Deploy on **Streamlit Community Cloud** (free):
1. Push to GitHub
2. Go to https://share.streamlit.io
3. Connect repo → `app.py`
4. Done — shareable URL instantly

For custom domain / VPS: use nginx + systemd service.

## Contact

Nguyễn Thị Nguyệt Tâm  
📧 nguyennguyettam9120@gmail.com  
📱 +84 943 620 253
