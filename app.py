import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime, timedelta

# --- הגדרות עיצוב RTL וצבעי MGROUP מותאם לנייד ---
st.set_page_config(page_title="MGROUP - Mobile Ready", layout="wide")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    /* הגדרות כלליות */
    html, body, [class*="css"] { 
        font-family: 'Assistant', sans-serif; 
        direction: RTL; 
        text-align: right; 
    }
    
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F5F5F5; }
    .stApp { background-color: var(--light-bg); }
    
    /* התאמת כותרת הלוגו לנייד */
    .header-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 15px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    .header-container img {
        max-width: 150px; /* לוגו קטן יותר בנייד */
        height: auto;
    }

    /* עיצוב כרטיסיות (Cards) */
    .card { 
        background: white; 
        padding: 15px; 
        border-radius: 12px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); 
        border-right: 5px solid var(--accent-orange); 
        margin-bottom: 15px; 
    }
    
    /* שיפור כפתורים ללחיצה קלה באצבע */
    .stButton>button { 
        background-color: var(--accent-orange); 
        color: white; 
        border-radius: 10px; 
        width: 100%; 
        font-weight: bold; 
        height: 3.5em; /* גבוה יותר לנייד */
        font-size: 16px;
        border: none;
        margin-top: 10px;
    }

    /* התאמת טבלאות למסכים קטנים - גלילה אופקית */
    .stDataFrame {
        width: 100%;
        overflow-x: auto;
    }

    /* הסתרת תפריט הצד בנייד כשלא צריך אותו (אופציונלי) */
    @media (max-width: 768px) {
        .header-container h2 { font-size: 1.2rem; }
        .card { padding: 10px; }
        [data-testid="stSidebar"] { width: 250px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- פונקציות בסיס נתונים ---
conn = sqlite3.connect('mgroup_mobile.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, team TEXT, manager TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS constraints (username TEXT, date TEXT, shift_start TEXT, shift_end TEXT, note TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS forecast (date TEXT, hour TEXT, required_agents INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS schedule (username TEXT, team TEXT, date TEXT, shift_range TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS daily_reports (date TEXT, hour TEXT, call_volume INTEGER, actual_agents INTEGER)')
    
    admin_pwd = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)', ("admin", admin_pwd, "IT", "ניהול", "None"))
    conn.commit()

create_tables()
local_css()

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

# --- תצוגת לוגו ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-container"><img src="{logo_url}"><h2>MGROUP | מערכת ניהול</h2></div>', unsafe_allow_html=True)

# --- לוגיקת התחברות ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    col_login = st.columns([1, 4, 1])[1] if not st.sidebar.checkbox("תצוגת נייד", value=True) else st.container()
    with col_login:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("התחברות")
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
    st.sidebar.markdown(f"**שלום, {st.session_state['user']}**")
    if st.sidebar.button("התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל נציג (הכי חשוב לנייד) ---
    if role == "נציג":
        st.header("📝 הגשת אילוץ")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        d = st.date_input("בחר תאריך")
        # בנייד נשתמש בסידור של עמודה אחת
        s_t = st.time_input("שעת התחלה")
        e_t = st.time_input("שעת סיום")
        note = st.text_area("הערות")
        if st.button("שלח אילוץ"):
            c.execute("INSERT INTO constraints VALUES (?,?,?,?,?)", (st.session_state['user'], str(d), str(s_t), str(e_t), note))
            conn.commit()
            st.success("האילוץ נשמר")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ (מותאם לניהול מהשטח) ---
    elif role == 'ר"צ':
        st.header(f"📋 שיבוץ - צוות {st.session_state['team']}")
        sel_date = st.date_input("תאריך לשיבוץ", datetime.now())
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("אילוצי נציגים")
        q = "SELECT constraints.username, shift_start, shift_end FROM constraints JOIN users ON constraints.username = users.username WHERE date = ? AND users.team = ?"
        cons = pd.read_sql(q, conn, params=(str(sel_date), st.session_state['team']))
        
        if not cons.empty:
            for i, r in cons.iterrows():
                st.write(f"**{r['username']}**: {r['shift_start']}-{r['shift_end']}")
                if st.button(f"שבץ את {r['username']}", key=f"s_{i}"):
                    c.execute("INSERT INTO schedule VALUES (?,?,?,?)", (r['username'], st.session_state['team'], str(sel_date), f"{r['shift_start']}-{r['shift_end']}"))
                    conn.commit()
                    st.rerun()
        else:
            st.info("אין אילוצים להיום")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנלים ניהוליים (IT / מנהל מוקד) ---
    elif role in ["IT", "מנהל מוקד", "משא"]:
        st.header(f"📊 פאנל {role}")
        # שימוש ב-Tabs כדי לחסוך מקום בנייד
        tab_data, tab_charts = st.tabs(["נתונים", "גרפים"])
        
        with tab_data:
            if role == "IT":
                st.subheader("הוספת משתמש")
                nu = st.text_input("שם משתמש")
                nr = st.selectbox("תפקיד", ["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT"])
                if st.button("צור"):
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?)', (nu, make_hashes("1234"), nr, "צוות", "None"))
                    conn.commit()
                    st.success("נוצר (סיסמה: 1234)")
            
            all_s = pd.read_sql("SELECT * FROM schedule LIMIT 20", conn)
            st.dataframe(all_s)

        with tab_charts:
            # גרף פשוט שמתאים לרוחב הנייד
            f_g = pd.read_sql("SELECT date, SUM(required_agents) as req FROM forecast GROUP BY date", conn)
            if not f_g.empty:
                fig = px.bar(f_g, x='date', y='req', title="חיזוי שבועי")
                fig.update_layout(margin=dict(l=10, r=10, t=30, b=10)) # צמצום שוליים לנייד
                st.plotly_chart(fig, use_container_width=True)

conn.close()