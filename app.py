import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime, timedelta
import io

# --- הגדרות עיצוב RTL וצבעי MGROUP ---
st.set_page_config(page_title="MGROUP - IT Advanced Panel", layout="wide")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F5F5F5; }
    .stApp { background-color: var(--light-bg); }
    .header-container { display: flex; flex-direction: column; align-items: center; padding: 15px; background: white; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .header-container img { max-width: 150px; height: auto; }
    .card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-right: 5px solid var(--accent-orange); margin-bottom: 15px; }
    .stButton>button { background-color: var(--accent-orange); color: white; border-radius: 10px; width: 100%; font-weight: bold; height: 3em; font-size: 16px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- בסיס נתונים ---
conn = sqlite3.connect('mgroup_it_pro.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    # הוספת עמודה plain_password כדי שה-IT יוכל לייצא רשימה
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, team TEXT, manager TEXT, plain_password TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS constraints (username TEXT, date TEXT, shift_start TEXT, shift_end TEXT, note TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS forecast (date TEXT, hour TEXT, required_agents INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS schedule (username TEXT, team TEXT, date TEXT, shift_range TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS daily_reports (date TEXT, hour TEXT, call_volume INTEGER, actual_agents INTEGER)')
    
    admin_pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)', ("admin", admin_pwd_hash, "IT", "ניהול", "None", "admin123"))
    conn.commit()

create_tables()
local_css()

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

# --- לוגו ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-container"><img src="{logo_url}"><h2>ניהול משתמשים ותשתיות</h2></div>', unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type='password')
        if st.button("כניסה"):
            c.execute('SELECT password, role, team FROM users WHERE username = ?', (u,))
            data = c.fetchone()
            if data and make_hashes(p) == data[0]:
                st.session_state.update({"logged_in": True, "user": u, "role": data[1], "team": data[2]})
                st.rerun()
            else: st.error("פרטים שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.image(logo_url, width=120)
    if st.sidebar.button("התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    if role == "IT":
        st.header("⚙️ מרכז שליטה IT")
        t1, t2, t3 = st.tabs(["👥 ניהול משתמשים", "📤 יבוא/יצוא באקסל", "📊 דוחות יום קודם"])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("הוספת משתמש בודד")
            c1, c2 = st.columns(2)
            nu = c1.text_input("שם משתמש")
            np = c2.text_input("קבע סיסמה")
            nr = c1.selectbox("תפקיד", ["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT"])
            nt = c2.text_input("צוות")
            if st.button("צור משתמש"):
                try:
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', (nu, make_hashes(np), nr, nt, "None", np))
                    conn.commit()
                    st.success(f"המשתמש {nu} נוצר")
                except: st.error("שם המשתמש כבר קיים")
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("רשימת משתמשים קיימת")
            users_df = pd.read_sql("SELECT username, role, team, plain_password FROM users", conn)
            st.dataframe(users_df, use_container_width=True)
            
            # כפתור הורדה לרשימה עם סיסמאות
            csv = users_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 הורד רשימת משתמשים וסיסמאות (CSV)", csv, "mgroup_users.csv", "text/csv")

        with t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("יצירת משתמשים מרובים מאקסל")
            st.info("העלה קובץ Excel עם העמודות: username, password, role, team")
            uploaded_file = st.file_uploader("בחר קובץ אקסל", type=['xlsx', 'csv'])
            
            if uploaded_file:
                if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
                else: df = pd.read_excel(uploaded_file)
                
                st.write("תצוגה מקדימה של הנתונים:")
                st.dataframe(df.head())
                
                if st.button("אשר ייבוא ויצירת משתמשים"):
                    count = 0
                    for _, row in df.iterrows():
                        try:
                            c.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', 
                                     (str(row['username']), make_hashes(str(row['password'])), 
                                      row['role'], row['team'], "None", str(row['password'])))
                            count += 1
                        except: continue
                    conn.commit()
                    st.success(f"סיימתי! {count} משתמשים חדשים נוספו למערכת.")
            st.markdown('</div>', unsafe_allow_html=True)

        with t3:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("הזנת ביצועי יום קודם")
            # (ממשק הזנת דוחות שהיה קודם...)
            rep_date = st.date_input("תאריך", datetime.now() - timedelta(1))
            rh = st.selectbox("שעה", [f"{i:02d}:00" for i in range(24)])
            rv = st.number_input("שיחות נכנסו", min_value=0)
            ra = st.number_input("נציגים בפועל", min_value=0)
            if st.button("שמור נתוני ביצוע"):
                c.execute("INSERT INTO daily_reports VALUES (?,?,?,?)", (str(rep_date), rh, rv, ra))
                conn.commit()
                st.success("הנתונים הוזנו")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנלים אחרים (ללא שינוי, מוצגים לפי תפקיד) ---
    elif role == 'ר"צ':
        st.header(f"📅 פאנל שיבוץ - צוות {st.session_state['team']}")
        # (קוד הר"צ מהגרסה הקודמת)
    
    elif role in ["מנהל מוקד", "משא"]:
        st.header("📊 דאשבורד מנהלים")
        # (קוד הדאשבורד עם הגרפים מהגרסה הקודמת)

    elif role == "נציג":
        st.header("📝 הגשת אילוץ")
        # (קוד הנציג מהגרסה הקודמת)

conn.close()
