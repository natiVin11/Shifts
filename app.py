import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP | Enterprise Cloud", layout="wide")

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

# --- חיבור לענן (Google Sheets) ---
# וודא שהגדרת ב-Secrets את ה-URL תחת [connections.gsheets]
conn = st.connection("gsheets", type=GSheetsConnection)

def get_table(sheet_name):
    try:
        return conn.read(worksheet=sheet_name)
    except:
        # יצירת טבלה ריקה עם עמודות נכונות אם הגיליון לא קיים
        return pd.DataFrame()

def save_table(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- עזרי אבטחה ---
def hash_pwd(pwd): return hashlib.sha256(str.encode(pwd)).hexdigest()

# --- לוגו וכותרת ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-card"><img src="{logo_url}" width="180"><h3>MGROUP | פורטל ארגוני מבוסס ענן</h3></div>', unsafe_allow_html=True)

# --- ניהול התחברות ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_in = st.text_input("שם משתמש")
        p_in = st.text_input("סיסמה", type='password')
        if st.button("כניסה למערכת"):
            users_df = get_table("users")
            if not users_df.empty:
                user_match = users_df[users_df['username'] == u_in]
                if not user_match.empty and hash_pwd(p_in) == user_match.iloc[0]['password']:
                    st.session_state.update({"logged_in": True, "user": u_in, "role": user_match.iloc[0]['role'], "team": user_match.iloc[0]['team']})
                    st.rerun()
                else: st.error("פרטים שגויים")
            else:
                # כניסת חירום למנהל ראשון אם הגיליון ריק
                if u_in == "admin" and p_in == "admin123":
                    st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול"})
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.image(logo_url, width=120)
    st.sidebar.markdown(f"**שלום, {st.session_state['user']}**")
    if st.sidebar.button("יציאה"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT: ניהול משתמשים וסנכרון ענן ---
    if role == "IT":
        st.header("⚙️ ניהול IT (Google Sheets Sync)")
        t1, t2 = st.tabs(["ניהול משתמשים באקסל", 'צ"ק-ליסט מערכות'])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            up_xlsx = st.file_uploader("העלה אקסל ליצירת משתמשים", type=['xlsx'])
            if up_xlsx and st.button("סנכרן נתונים לענן"):
                df_new = pd.read_excel(up_xlsx)
                df_new['password'] = df_new['password'].apply(lambda x: hash_pwd(str(x)))
                save_table(df_new, "users")
                st.success("המשתמשים עודכנו בגיליון הענן!")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל משא: חיזוי וגיוס ---
    elif role == "משא":
        st.header('📈 פאנל משא"בי אנוש')
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("בקשת גיוס חדשה")
        fn = st.text_input("שם מלא")
        un = st.text_input("שם משתמש מבוקש")
        if st.button("שלח ל-IT"):
            onboard_df = get_table("onboarding")
            new_row = pd.DataFrame([{"username": un, "full_name": fn, "status": "קליטה"}])
            save_table(pd.concat([onboard_df, new_row]), "onboarding")
            st.success("הבקשה נרשמה בענן")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ: שיבוץ חכם ---
    elif role == 'ר"צ':
        st.header(f"👥 ניהול צוות: {st.session_state['team']}")
        sel_date = st.date_input("תאריך לשיבוץ")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # קריאת אילוצים מהענן
        cons = get_table("constraints")
        day_cons = cons[cons['date'] == str(sel_date)]
        st.write("אילוצים מהענן ליום זה:")
        st.dataframe(day_cons)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל נציג: הגשת אילוץ לענן ---
    elif role == "נציג":
        st.header("👤 פורטל נציג")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        d = st.date_input("בחר תאריך")
        note = st.text_area("הערות")
        if st.button("שלח אילוץ לענן"):
            all_cons = get_table("constraints")
            new_con = pd.DataFrame([{"username": st.session_state['user'], "date": str(d), "note": note}])
            save_table(pd.concat([all_cons, new_con]), "constraints")
            st.success("האילוץ נשמר ב-Google Sheets")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד: דוחות ביצועים ---
    elif role == "מנהל מוקד":
        st.header("📊 דאשבורד מנהל מוקד")
        perf_data = get_table("performance")
        if not perf_data.empty:
            fig = px.line(perf_data, x='date', y='value', color='metric', title="מגמות עומס במוקד")
            st.plotly_chart(fig, use_container_width=True)
