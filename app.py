import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime

# --- הגדרות עיצוב MGROUP ---
st.set_page_config(page_title="MGROUP 360 | Enterprise System", layout="wide")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F0F2F6; }
    .stApp { background-color: var(--light-bg); }
    .header-card { background: white; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; border-bottom: 5px solid var(--accent-orange); }
    .card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border-right: 5px solid var(--main-blue); }
    .stButton>button { background: linear-gradient(135deg, var(--accent-orange), #e67e22); color: white; border-radius: 10px; font-weight: bold; width: 100%; border: none; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לענן (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try: return conn.read(worksheet=sheet)
    except: return pd.DataFrame()

def save_data(df, sheet):
    conn.update(worksheet=sheet, data=df)
    st.cache_data.clear()

def hash_p(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- כותרת לוגו ---
st.markdown(f'<div class="header-card"><img src="https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg" width="160"><h3>MGROUP 360 - פורטל ניהול משולב</h3></div>', unsafe_allow_html=True)

# --- לוגיקת כניסה ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type='password')
        if st.button("כניסה למערכת"):
            users = get_data("users")
            if not users.empty:
                user_row = users[users['username'] == u]
                if not user_row.empty and hash_p(p) == user_row.iloc[0]['password']:
                    st.session_state.update({"logged_in": True, "user": u, "role": user_row.iloc[0]['role'], 
                                           "team": user_row.iloc[0]['team'], "manager": user_row.iloc[0]['manager']})
                    st.rerun()
            if u == "admin" and p == "admin123":
                st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול", "manager": "None"})
                st.rerun()
            else: st.error("פרטים שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.markdown(f'**שלום, {st.session_state["user"]}**')
    if st.sidebar.button("🚪 יציאה"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("יצירת משתמשים אוטומטית (אקסל)")
        up = st.file_uploader("העלה קובץ", type=['xlsx'])
        if up and st.button("בצע סנכרון משתמשים לענן"):
            new_u = pd.read_excel(up)
            new_u['password'] = hash_p("123456")
            old_u = get_data("users")
            save_data(pd.concat([old_u, new_u]).drop_duplicates(subset=['username']), "users")
            st.success("המשתמשים סונכרנו בהצלחה!")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד ---
    elif role == "מנהל מוקד":
        st.header(f'📊 ניהול מוקד: {st.session_state["team"]}')
        # תיקון הגרש ב-tabs
        t1, t2, t3 = st.tabs(['דוחות וחיזוי', 'ניהול ר"צים', 'מעקב שעות'])
        
        with t1:
            st.subheader("ניתוח ביצועים")
            perf = get_data("performance")
            if not perf.empty:
                st.plotly_chart(px.line(perf, x='date', y='calls'))

    # --- פאנל ר"צ ---
    elif role == 'ר"צ':
        st.header(f'👥 צוות: {st.session_state["user"]}')
        t1, t2 = st.tabs(['שיבוץ חכם', 'אישור מחלות'])
        
        with t1:
            target_date = st.date_input("תאריך לשיבוץ")
            cons = get_data("constraints")
            st.write("אילוצים מהענן:")
            st.dataframe(cons)

    # --- פאנל נציג ---
    elif role == "נציג":
        st.header("👤 פורטל אישי")
        with st.expander("הגשת אילוץ חדש"):
            d = st.date_input("תאריך")
            if st.button("שלח אילוץ"):
                all_c = get_data("constraints")
                new_c = pd.DataFrame([{"username": st.session_state['user'], "date": str(d), "manager": st.session_state['manager']}])
                save_data(pd.concat([all_c, new_c]), "constraints")
                st.success("האילוץ נשמר בענן")

    # --- פאנל משא ---
    elif role == "משא":
        st.header('📋 משא"בי אנוש')
        users = get_data("users")
        st.metric("עובדים פעילים", len(users))
        st.dataframe(users)
