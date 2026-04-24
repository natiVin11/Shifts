import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime

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

# --- חיבור מאובטח לענן (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        # ttl=0 מבטיח משיכת נתונים טריים מהענן בכל טעינה
        return conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
    except Exception:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        df_to_save = df.fillna("")
        conn.update(worksheet=sheet_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ הנתונים סונכרנו לגיליון {sheet_name}")
    except Exception as e:
        st.error(f"❌ שגיאת סנכרון: וודא שחשבון השירות מוגדר כ-'Editor' בגיליון. שגיאה: {e}")

def hash_pwd(pwd): return hashlib.sha256(str.encode(str(pwd))).hexdigest()

# --- כותרת לוגו ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-card"><img src="{logo_url}" width="180"><h3>MGROUP 360 | מערכת ניהול מוקד אחודה</h3></div>', unsafe_allow_html=True)

# --- ניהול התחברות ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
                    st.session_state.update({
                        "logged_in": True, "user": u_in, 
                        "role": user_row.iloc[0]['role'], 
                        "team": user_row.iloc[0]['team'],
                        "manager_name": user_row.iloc[0].get('manager', 'None')
                    })
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

    # --- פאנל IT: אוטומציה מלאה ---
    if role == "IT":
        st.header("⚙️ ניהול תשתית IT")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("ייבוא משתמשים מרובי (Excel Sync)")
        up_file = st.file_uploader("העלה אקסל (username, role, team, manager)", type=['xlsx'])
        if up_file and st.button("סנכרן משתמשים לענן"):
            new_df = pd.read_excel(up_file)
            new_df['password'] = new_df.get('password', '123456').apply(hash_pwd)
            old_df = get_data("users")
            save_data(pd.concat([old_df, new_df]).drop_duplicates(subset=['username']), "users")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד: חיזוי וביצועים ---
    elif role == "מנהל מוקד":
        st.header(f'📊 מוקד: {st.session_state["team"]}')
        t1, t2 = st.tabs(['דאשבורד חיזוי', 'ניהול צוותים'])
        with t1:
            st.subheader("מגמות עומס שיחות (מהענן)")
            perf_data = get_data("performance")
            if not perf_data.empty:
                st.plotly_chart(px.line(perf_data, x='date', y='calls'))
            else: st.info("ממתין להעלאת נתונים ראשונית")

    # --- פאנל ר"צ: שיבוץ חכם ---
    elif role == 'ר"צ':
        st.header(f'👥 צוות: {st.session_state["user"]}')
        t1, t2 = st.tabs(['שיבוץ משמרות', 'אילוצי נציגים'])
        with t2:
            cons = get_data("constraints")
            my_agents = cons[cons['manager'] == st.session_state['user']]
            st.write("אילוצים שהוגשו על ידי הנציגים שלך:")
            st.dataframe(my_agents)

    # --- פאנל נציג: פורטל אישי ---
    elif role == "נציג":
        st.header("👤 הפורטל האישי שלי")
        with st.expander("הגשת אילוץ חדש"):
            d_con = st.date_input("תאריך")
            note_con = st.text_input("הערה (בוקר/ערב/סיבה)")
            if st.button("שלח אילוץ"):
                df = get_data("constraints")
                new_row = pd.DataFrame([{"username": st.session_state['user'], "date": str(d_con), "note": note_con, "manager": st.session_state['manager_name']}])
                save_data(pd.concat([df, new_row]), "constraints")

    # --- פאנל משא: גיוס וכוח אדם ---
    elif role == "משא":
        st.header('📋 משא"בי אנוש')
        st.subheader("מצבת עובדים פעילה")
        st.dataframe(get_data("users")[['username', 'role', 'team', 'manager']])
