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
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, team TEXT, manager TEXT, plain_pwd TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS system_access (username TEXT PRIMARY KEY, full_name TEXT, status TEXT, crm INTEGER, telephony INTEGER, mail INTEGER, network INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS forecast (date TEXT, hour TEXT, required_agents INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS constraints (username TEXT, date TEXT, shift_start TEXT, shift_end TEXT, note TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS schedule (username TEXT, team TEXT, date TEXT, shift_range TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS sick_leaves (username TEXT, date TEXT, status TEXT, file_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS daily_perf (date TEXT, metric TEXT, value REAL)')
    
    admin_h = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', ("admin", admin_h, "IT", "ניהול", "None", "admin123"))
    conn.commit()

create_tables()
local_css()

def make_hashes(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

# --- כותרת ---
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

    # --- פאנל IT ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        t1, t2 = st.tabs(["👥 ניהול משתמשים", '🚦 צ"ק-ליסט מערכות'])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            up_xlsx = st.file_uploader("העלה אקסל ליצירת משתמשים", type=['xlsx'])
            if up_xlsx and st.button("בצע ייבוא"):
                df_u = pd.read_excel(up_xlsx)
                for _, r in df_u.iterrows():
                    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', 
                             (str(r['username']), make_hashes(str(r['password'])), r['role'], r['team'], "None", str(r['password'])))
                conn.commit()
                st.success("המשתמשים נוספו!")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            # שימוש בגרש בודד למניעת שגיאה
            st.subheader('בקשות פתיחה/סגירה של מש"א')
            reqs = pd.read_sql("SELECT * FROM system_access", conn)
            for i, r in reqs.iterrows():
                with st.expander(f"עובד: {r['full_name']}"):
                    col1, col2 = st.columns(2)
                    crm = col1.checkbox("CRM", value=r['crm'], key=f"it_crm_{i}")
                    tel = col2.checkbox("טלפוניה", value=r['telephony'], key=f"it_tel_{i}")
                    if st.button("עדכן", key=f"it_btn_{i}"):
                        c.execute("UPDATE system_access SET crm=?, telephony=? WHERE username=?", (crm, tel, r['username']))
                        conn.commit()
                        st.rerun()

    # --- פאנל מש"א ---
    elif role == "משא":
        st.header('📈 פאנל משא"בי אנוש')
        t1, t2 = st.tabs(["גיוס/גריעה", "חיזוי"])
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            fn = st.text_input("שם מלא")
            un = st.text_input("שם משתמש")
            if st.button("שלח ל-IT"):
                c.execute("INSERT INTO system_access VALUES (?, ?, 'קליטה', 0, 0, 0, 0)", (un, fn))
                conn.commit()
                st.success("הבקשה הועברה")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ ---
    elif role == 'ר"צ':
        st.header(f"👥 ניהול צוות: {st.session_state['team']}")
        t1, t2 = st.tabs(["שיבוץ", "מחלות"])
        with t1:
            sel_d = st.date_input("תאריך")
            ds = str(sel_d)
            cons = pd.read_sql("SELECT * FROM constraints WHERE date=?", conn, params=(ds,))
            st.write("אילוצים ליום זה:")
            st.table(cons)

    # --- פאנל נציג ---
    elif role == "נציג":
        st.header("👤 פורטל נציג")
        t1, t2 = st.tabs(["אילוצים", "מחלה"])
        with t1:
            d = st.date_input("תאריך")
            st_t = st.time_input("התחלה")
            en_t = st.time_input("סיום")
            if st.button("שלח אילוץ"):
                c.execute("INSERT INTO constraints VALUES (?,?,?,?,?)", (st.session_state['user'], str(d), str(st_t), str(en_t), ""))
                conn.commit()
                st.success("נשלח")

    # --- פאנל מנהל מוקד ---
    elif role == "מנהל מוקד":
        st.header("📊 דאשבורד מנהל")
        perf_data = pd.read_sql("SELECT * FROM daily_perf", conn)
        if not perf_data.empty:
            fig = px.line(perf_data, x='date', y='value', color='metric')
            st.plotly_chart(fig, use_container_width=True)

conn.close()
