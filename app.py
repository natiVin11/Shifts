import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime, timedelta

# --- הגדרות תצוגה ---
st.set_page_config(page_title="MGROUP | Shift Manager", layout="wide", initial_sidebar_state="expanded")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F0F2F6; }
    
    .stApp { background-color: var(--light-bg); }
    
    /* Header & Branding */
    .header-card {
        background: white; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        display: flex; flex-direction: column; align-items: center; margin-bottom: 30px;
        border-bottom: 5px solid var(--accent-orange);
    }
    
    /* Stats & Metrics */
    div[data-testid="stMetric"] {
        background: white; padding: 15px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        border: 1px solid #eee;
    }
    
    /* Custom Card Style */
    .card {
        background: white; padding: 25px; border-radius: 18px; 
        box-shadow: 0 5px 15px rgba(0,0,0,0.04); margin-bottom: 20px;
        border-right: 6px solid var(--main-blue);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, var(--accent-orange), #e67e22);
        color: white; border: none; padding: 10px 20px; border-radius: 12px;
        font-weight: bold; width: 100%; transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,140,50,0.4); }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: white !important; border-left: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול בסיס נתונים ---
conn = sqlite3.connect('mgroup_master_v4.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, team TEXT, manager TEXT, plain_pwd TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS system_access (username TEXT PRIMARY KEY, full_name TEXT, status TEXT, crm INTEGER, telephony INTEGER, mail INTEGER, network INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS forecast (date TEXT, hour TEXT, required_agents INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS constraints (username TEXT, date TEXT, shift_start TEXT, shift_end TEXT, note TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS schedule (username TEXT, team TEXT, date TEXT, shift_range TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS it_files (file_name TEXT, file_data BLOB, upload_date TEXT)')
    
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', ("admin", admin_hash, "IT", "ניהול", "None", "admin123"))
    conn.commit()

create_tables()
local_css()

def make_hashes(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

# --- לוגו וכותרת ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-card"><img src="{logo_url}" width="180"><h3>MGROUP | משרד התחבורה - מרכז שליטה</h3></div>', unsafe_allow_html=True)

# --- מערכת התחברות ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔐 כניסה למערכת")
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type='password')
        if st.button("התחבר"):
            c.execute('SELECT password, role, team FROM users WHERE username = ?', (u,))
            data = c.fetchone()
            if data and make_hashes(p) == data[0]:
                st.session_state.update({"logged_in": True, "user": u, "role": data[1], "team": data[2]})
                st.rerun()
            else: st.error("פרטי גישה שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.image(logo_url, width=120)
    st.sidebar.markdown(f"**שלום, {st.session_state['user']}**")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT: המוח של המערכת ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה וניהול תשתיות (IT)")
        t1, t2, t3 = st.tabs(["🚦 צ'ק-ליסט קליטה/גריעה", "👥 ניהול משתמשים", "📂 העלאת קבצי סיסמאות"])
        
        with t1:
            st.subheader("טיפול בבקשות מש\"א")
            pending = pd.read_sql("SELECT * FROM system_access", conn)
            for i, row in pending.iterrows():
                with st.expander(f"📍 עובד: {row['full_name']} | {row['status']}"):
                    c1, c2, c3, c4 = st.columns(4)
                    crm = c1.checkbox("CRM", value=row['crm'], key=f"c_{i}")
                    tel = c2.checkbox("טלפוניה", value=row['telephony'], key=f"t_{i}")
                    ml = c3.checkbox("מייל", value=row['mail'], key=f"m_{i}")
                    nt = c4.checkbox("רשת", value=row['network'], key=f"n_{i}")
                    if st.button("סיום טיפול ועדכון סטטוס", key=f"up_{i}"):
                        c.execute("UPDATE system_access SET crm=?, telephony=?, mail=?, network=? WHERE username=?", (crm, tel, ml, nt, row['username']))
                        if all([crm, tel, ml, nt]):
                            if row['status'] == 'קליטה':
                                c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", (row['username'], make_hashes("123456"), "נציג", "כללי", "None", "123456"))
                                st.success("העובד הפך לפעיל!")
                            else:
                                c.execute("DELETE FROM users WHERE username=?", (row['username'],))
                                st.error("העובד הוסר!")
                        conn.commit()
                        st.rerun()

        with t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("הוספת משתמש ידנית או העלאת אקסל כפי שהוגדר בגרסה הקודמת.")
            st.dataframe(pd.read_sql("SELECT username, role, team FROM users", conn), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with t3:
            st.subheader("הפצת דפי פרטי גישה")
            it_f = st.file_uploader("העלה קובץ סיסמאות (Excel/CSV/PDF)", type=['xlsx','csv','pdf'])
            if it_f and st.button("פרסם למנהלים"):
                c.execute("INSERT INTO it_files VALUES (?, ?, ?)", (it_f.name, it_f.getvalue(), str(datetime.now().date())))
                conn.commit()
                st.success("הקובץ הופץ לכל הר\"צים ומנהלי המוקד.")

    # --- פאנל משא: חיזוי וכוח אדם ---
    elif role == "משא":
        st.header("📈 משאבי אנוש - תכנון וכוח אדם")
        m_t1, m_t2 = st.tabs(["גיוס וסיום העסקה", "הזנת חיזוי משמרות"])
        
        with m_t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("בקשת קליטה חדשה")
            fn = st.text_input("שם מלא של העובד")
            un = st.text_input("שם משתמש מבוקש (ללא רווחים)")
            if st.button("שלח ל-IT לפתיחת מערכות"):
                c.execute("INSERT INTO system_access VALUES (?, ?, 'קליטה', 0, 0, 0, 0)", (un, fn))
                conn.commit()
                st.success("הבקשה נשלחה")
            st.markdown('</div>', unsafe_allow_html=True)

        with m_t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            f_date = st.date_input("תאריך לחיזוי")
            f_hour = st.selectbox("שעה", [f"{i:02d}:00" for i in range(24)])
            f_req = st.number_input("נציגים דרושים", min_value=1)
            if st.button("שמור חיזוי"):
                c.execute("INSERT INTO forecast VALUES (?,?,?)", (str(f_date), f_hour, f_req))
                conn.commit()
                st.success("החיזוי עודכן")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ: שיבוץ חכם ---
    elif role == 'ר"צ':
        st.header(f"👥 ניהול צוות: {st.session_state['team']}")
        
        # מרכז קבצי IT
        with st.expander("🔑 לצפייה בפרטי גישה וסיסמאות נציגים (מ-IT)"):
            f_it = pd.read_sql("SELECT * FROM it_files ORDER BY upload_date DESC LIMIT 1", conn)
            if not f_it.empty:
                st.download_button(f"הורד קובץ מעודכן: {f_it.iloc[0]['file_name']}", f_it.iloc[0]['file_data'])
            else: st.info("אין קבצים זמינים")

        st.subheader("📅 לוח שיבוץ יומי")
        sel_d = st.date_input("בחר תאריך", datetime.now())
        ds = str(sel_d)
        
        # השוואת חיזוי
        f_val = pd.read_sql("SELECT SUM(required_agents) FROM forecast WHERE date=?", conn, params=(ds,)).iloc[0,0] or 0
        s_val = pd.read_sql("SELECT COUNT(*) FROM schedule WHERE date=? AND team=?", conn, params=(ds, st.session_state['team'])).iloc[0,0] or 0
        
        c1, c2 = st.columns(2)
        c1.metric("חיזוי משא", f_val)
        c2.metric("משובצים בצוות", s_val)
        
        st.divider()
        st.write("אילוצים ליום זה:")
        q_cons = "SELECT * FROM constraints WHERE date=?"
        day_cons = pd.read_sql(q_cons, conn, params=(ds,))
        for _, r in day_cons.iterrows():
            with st.expander(f"📌 {r['username']} ({r['shift_start']}-{r['shift_end']})"):
                if st.button(f"אשר ושיבץ ל-{r['username']}", key=f"b_{r['username']}"):
                    c.execute("INSERT INTO schedule VALUES (?,?,?,?)", (r['username'], st.session_state['team'], ds, f"{r['shift_start']}-{r['shift_end']}"))
                    conn.commit()
                    st.rerun()

    # --- פאנל נציג: פשוט ומהיר ---
    elif role == "נציג":
        st.header("📝 הגשת אילוצים")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        nd = st.date_input("תאריך")
        col1, col2 = st.columns(2)
        nst = col1.time_input("התחלה")
        net = col2.time_input("סיום")
        note = st.text_area("הערות")
        if st.button("שלח אילוץ"):
            c.execute("INSERT INTO constraints VALUES (?,?,?,?,?)", (st.session_state['user'], str(nd), str(nst), str(net), note))
            conn.commit()
            st.success("האילוץ נשלח למנהל")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד: דאשבורד מלא ---
    elif role == "מנהל מוקד":
        st.header("📊 דאשבורד מנהל מוקד")
        st.subheader("חיזוי שבועי מול שיבוץ בפועל")
        
        f_data = pd.read_sql("SELECT date, SUM(required_agents) as req FROM forecast GROUP BY date", conn)
        s_data = pd.read_sql("SELECT date, COUNT(*) as ass FROM schedule GROUP BY date", conn)
        
        if not f_data.empty:
            merged = pd.merge(f_data, s_data, on='date', how='left').fillna(0)
            fig = px.line(merged, x='date', y=['req', 'ass'], title="מגמות עומס מול שיבוץ", markers=True)
            st.plotly_chart(fig, use_container_width=True)
