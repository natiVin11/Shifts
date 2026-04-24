import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta

# --- הגדרות עיצוב Premium MGROUP ---
st.set_page_config(page_title="MGROUP 360 | Enterprise Portal", layout="wide")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F0F2F6; }
    .stApp { background-color: var(--light-bg); }
    .header-card { background: white; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; border-bottom: 5px solid var(--accent-orange); }
    .card { background: white; padding: 25px; border-radius: 18px; box-shadow: 0 5px 15px rgba(0,0,0,0.04); margin-bottom: 20px; border-right: 6px solid var(--main-blue); }
    .stButton>button { background: linear-gradient(135deg, var(--accent-orange), #e67e22); color: white; border-radius: 12px; font-weight: bold; width: 100%; height: 3.5em; border: none; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור מאובטח לענן ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        df_to_save = df.fillna("")
        conn.update(worksheet=sheet_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ סונכרן לגיליון {sheet_name}")
    except Exception as e:
        st.error(f"❌ שגיאת סנכרון: {e}")

def hash_pwd(pwd): return hashlib.sha256(str.encode(str(pwd))).hexdigest()

# --- כותרת לוגו ---
st.markdown(f'<div class="header-card"><img src="https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg" width="180"><h3>MGROUP 360 | ניהול מוקד אחודה</h3></div>', unsafe_allow_html=True)

# --- ניהול התחברות ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔐 כניסה למערכת")
        u_in = st.text_input("שם משתמש")
        p_in = st.text_input("סיסמה", type='password')
        if st.button("התחבר"):
            users_df = get_data("users")
            if not users_df.empty:
                user_row = users_df[users_df['username'] == u_in]
                if not user_row.empty and hash_pwd(p_in) == user_row.iloc[0]['password']:
                    st.session_state.update({"logged_in": True, "user": u_in, "role": user_row.iloc[0]['role'], 
                                           "team": user_row.iloc[0]['team'], "manager_name": user_row.iloc[0].get('manager', 'None')})
                    st.rerun()
            if u_in == "admin" and p_in == "admin123":
                st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול", "manager_name": "None"})
                st.rerun()
            else: st.error("פרטים שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.markdown(f"👋 שלום, **{st.session_state['user']}**")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        t1, t2 = st.tabs(["ניהול משתמשים", "ייבוא אקסל"])
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            users_df = get_data("users")
            if not users_df.empty:
                selected_user = st.selectbox("בחר משתמש לעריכה", users_df['username'].unique())
                user_data = users_df[users_df['username'] == selected_user].iloc[0]
                new_role = st.selectbox("תפקיד", ['נציג', 'ר"צ', 'מנהל מוקד', 'משא', 'IT'], index=0)
                if st.button("🔄 איפוס סיסמה ל-123456"):
                    users_df.loc[users_df['username'] == selected_user, 'password'] = hash_pwd("123456")
                    save_data(users_df, "users")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד ---
    elif role == "מנהל מוקד":
        st.header(f"""📊 מוקד: {st.session_state["team"]}""")
        t1, t2 = st.tabs(["דוחות וחיזוי", "ניהול צוותים"])
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("""העלאת דוח שיחות""")
            c_file = st.file_uploader("העלה דוח", type=['xlsx'])
            if c_file and st.button("עדכן"):
                new_p = pd.read_excel(c_file)
                old_p = get_data("performance")
                save_data(pd.concat([old_p, new_p]), "performance")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ ---
    elif role == 'ר"צ':
        st.header(f"""👥 ניהול צוות: {st.session_state["user"]}""")
        t1, t2 = st.tabs(["שיבוץ משמרות", "אילוצי נציגים"])
        with t2:
            cons = get_data("constraints")
            st.dataframe(cons[cons['manager'] == st.session_state['user']])

    # --- פאנל נציג ---
    elif role == "נציג":
        st.header("👤 פורטל נציג")
        t1, t2 = st.tabs(["הגשת אילוץ", "המשמרות שלי"])
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            d = st.date_input("תאריך")
            if st.button("שלח אילוץ"):
                df = get_data("constraints")
                new_row = pd.DataFrame([{"username": st.session_state['user'], "date": str(d), "manager": st.session_state['manager_name']}])
                save_data(pd.concat([df, new_row]), "constraints")
            st.markdown('</div>', unsafe_allow_html=True)
        with t2:
            st.subheader("""לו"ז משמרות שפורסם""")
            sched = get_data("schedule")
            st.dataframe(sched[sched['username'] == st.session_state['user']])

    # --- פאנל משא ---
    elif role == "משא":
        st.header("""📋 משא"בי אנוש""")
        st.dataframe(get_data("users"))
