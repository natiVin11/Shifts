import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime, timedelta
import io

# --- הגדרות דף ועיצוב MGROUP ---
st.set_page_config(page_title="MGROUP | Enterprise Portal", layout="wide", initial_sidebar_state="expanded")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F0F2F6; }
    .stApp { background-color: var(--light-bg); }
    .header-card { background: white; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; border-bottom: 5px solid var(--accent-orange); }
    .card { background: white; padding: 25px; border-radius: 18px; box-shadow: 0 5px 15px rgba(0,0,0,0.04); margin-bottom: 20px; border-right: 6px solid var(--main-blue); }
    .stButton>button { background: linear-gradient(135deg, var(--accent-orange), #e67e22); color: white; border-radius: 12px; font-weight: bold; width: 100%; height: 3em; border: none; transition: 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,140,50,0.3); }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול בסיס נתונים ---
conn = sqlite3.connect('mgroup_final_system.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    # משתמשים וניהול IT
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, team TEXT, manager TEXT, plain_pwd TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS system_access (username TEXT PRIMARY KEY, full_name TEXT, status TEXT, crm INTEGER, telephony INTEGER, mail INTEGER, network INTEGER)')
    
    # משמרות וחיזוי
    c.execute('CREATE TABLE IF NOT EXISTS forecast (date TEXT, hour TEXT, required_agents INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS constraints (username TEXT, date TEXT, shift_start TEXT, shift_end TEXT, note TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS schedule (username TEXT, team TEXT, date TEXT, shift_range TEXT)')
    
    # HR וביצועים
    c.execute('CREATE TABLE IF NOT EXISTS sick_leaves (username TEXT, date TEXT, status TEXT, file_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS work_hours (username TEXT, month TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS daily_perf (date TEXT, metric TEXT, value REAL)')
    
    # מנהל מערכת ברירת מחדל
    admin_h = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', ("admin", admin_h, "IT", "ניהול", "None", "admin123"))
    conn.commit()

create_tables()
local_css()

def make_hashes(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

# --- רכיבי ממשק קבועים ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-card"><img src="{logo_url}" width="180"><h3>MGROUP | פורטל ארגוני משולב</h3></div>', unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# --- לוגיקת כניסה ---
if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_input = st.text_input("שם משתמש")
        p_input = st.text_input("סיסמה", type='password')
        if st.button("כניסה למערכת"):
            c.execute('SELECT password, role, team FROM users WHERE username = ?', (u_input,))
            user_data = c.fetchone()
            if user_data and make_hashes(p_input) == user_data[0]:
                st.session_state.update({"logged_in": True, "user": u_input, "role": user_data[1], "team": user_data[2]})
                st.rerun()
            else: st.error("פרטי התחברות שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.image(logo_url, width=120)
    st.sidebar.markdown(f"**משתמש:** {st.session_state['user']}\n\n**תפקיד:** {role}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT: המעטפת הטכנית ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        t1, t2, t3 = st.tabs(["👥 ניהול משתמשים (אקסל)", "🚦 צ'ק-ליסט מערכות", "📂 ניהול קבצי סיסמאות"])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("ייבוא משתמשים מרובי")
            up_xlsx = st.file_uploader("העלה קובץ אקסל (username, password, role, team)", type=['xlsx'])
            if up_xlsx and st.button("בצע ייבוא"):
                df_users = pd.read_excel(up_xlsx)
                for _, r in df_users.iterrows():
                    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', 
                             (str(r['username']), make_hashes(str(r['password'])), r['role'], r['team'], "None", str(r['password'])))
                conn.commit()
                st.success("המשתמשים נוספו בהצלחה!")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.subheader("בקשות פתיחה/סגירה של מש"א")
            requests = pd.read_sql("SELECT * FROM system_access", conn)
            for i, r in requests.iterrows():
                with st.expander(f"עובד: {r['full_name']} | {r['status']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    crm = col1.checkbox("CRM", value=r['crm'], key=f"it_crm_{i}")
                    tel = col2.checkbox("טלפוניה", value=r['telephony'], key=f"it_tel_{i}")
                    ml = col3.checkbox("מייל", value=r['mail'], key=f"it_ml_{i}")
                    nt = col4.checkbox("רשת", value=r['network'], key=f"it_nt_{i}")
                    if st.button("עדכן וסנכרן", key=f"it_up_{i}"):
                        c.execute("UPDATE system_access SET crm=?, telephony=?, mail=?, network=? WHERE username=?", (crm, tel, ml, nt, r['username']))
                        if all([crm, tel, ml, nt]) and r['status'] == 'קליטה':
                            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", (r['username'], make_hashes("123456"), "נציג", "כללי", "None", "123456"))
                        conn.commit()
                        st.rerun()

    # --- פאנל מש"א: חיזוי וגיוס ---
    elif role == "משא":
        st.header("📈 פאנל משאבי אנוש")
        t1, t2 = st.tabs(["גיוס וסיום העסקה", "הזנת חיזוי משמרות"])
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("בקשת קליטת עובד חדש")
            fn = st.text_input("שם מלא")
            un = st.text_input("שם משתמש מבוקש")
            if st.button("שלח ל-IT"):
                c.execute("INSERT INTO system_access VALUES (?, ?, 'קליטה', 0, 0, 0, 0)", (un, fn))
                conn.commit()
                st.success("הבקשה הועברה")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            f_d = st.date_input("תאריך לחיזוי")
            f_h = st.selectbox("שעה", [f"{i:02d}:00" for i in range(24)])
            f_r = st.number_input("נציגים דרושים", min_value=1)
            if st.button("שמור חיזוי"):
                c.execute("INSERT INTO forecast VALUES (?,?,?)", (str(f_d), f_h, f_r))
                conn.commit()
                st.success("החיזוי נשמר")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ: ניהול צוות ושעות ---
    elif role == 'ר"צ':
        st.header(f"👥 ניהול צוות: {st.session_state['team']}")
        t1, t2, t3 = st.tabs(["שיבוץ משמרות", "אישור מחלות", "דיווח שעות עבודה"])
        
        with t1:
            st.subheader("לוח שיבוץ יומי")
            sel_d = st.date_input("בחר תאריך")
            ds = str(sel_d)
            cons = pd.read_sql("SELECT * FROM constraints WHERE date=?", conn, params=(ds,))
            for _, r in cons.iterrows():
                with st.expander(f"📍 {r['username']} ({r['shift_start']}-{r['shift_end']})"):
                    if st.button(f"שבץ את {r['username']}", key=f"s_{r['username']}"):
                        c.execute("INSERT INTO schedule VALUES (?,?,?,?)", (r['username'], st.session_state['team'], ds, f"{r['shift_start']}-{r['shift_end']}"))
                        conn.commit()
                        st.rerun()
        
        with t2:
            st.subheader("טפסי מחלה ממתינים")
            sick_df = pd.read_sql("SELECT username, date, status FROM sick_leaves WHERE status='ממתין'", conn)
            st.table(sick_df)
            
        with t3:
            st.subheader("העלאת דוח שעות חודשי")
            up_h = st.file_uploader("העלה אקסל שעות צוות", type=['xlsx'])
            if up_h and st.button("שלח לנציגים לאישור"):
                st.success("הדיווח נשלח לפורטל הנציגים")

    # --- פאנל נציג: הפורטל האישי ---
    elif role == "נציג":
        st.header("👤 הפורטל האישי שלי")
        t1, t2, t3 = st.tabs(["אילוצים", "דיווח מחלה", "אישור שעות"])
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            d = st.date_input("תאריך")
            c1, c2 = st.columns(2)
            s = c1.time_input("התחלה")
            e = c2.time_input("סיום")
            if st.button("שלח אילוץ"):
                c.execute("INSERT INTO constraints VALUES (?,?,?,?,?)", (st.session_state['user'], str(d), str(s), str(e), ""))
                conn.commit()
                st.success("נשלח")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            sd = st.date_input("תאריך המחלה")
            sf = st.file_uploader("העלה אישור רפואי")
            if st.button("דווח מחלה"):
                c.execute("INSERT INTO sick_leaves VALUES (?,?,'ממתין',?)", (st.session_state['user'], str(sd), sf.name if sf else ""))
                conn.commit()
                st.success("דיווח המחלה התקבל")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד: דאשבורד ביצועים ---
    elif role == "מנהל מוקד":
        st.header("📊 דאשבורד ביצועי מוקד")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("הזנת דוח ביצועים יומי")
        pd_d = st.date_input("תאריך הדוח")
        metric = st.selectbox("מדד", ["שיחות נכנסות", "זמן המתנה (שניות)", "% מענה"])
        val = st.number_input("ערך")
        if st.button("פרסם ביצועים"):
            c.execute("INSERT INTO daily_perf VALUES (?,?,?)", (str(pd_d), metric, val))
            conn.commit()
            st.success("הדוח פורסם")
        st.markdown('</div>', unsafe_allow_html=True)
        
        perf_data = pd.read_sql("SELECT * FROM daily_perf", conn)
        if not perf_data.empty:
            fig = px.line(perf_data, x='date', y='value', color='metric', title="מגמות ביצועים")
            st.plotly_chart(fig, use_container_width=True)

conn.close()
