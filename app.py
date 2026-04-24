import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta
import io

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
    .stButton>button { background: linear-gradient(135deg, var(--accent-orange), #e67e22); color: white; border-radius: 12px; font-weight: bold; width: 100%; height: 3.5em; border: none; transition: 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,140,50,0.3); }
    /* Mobile Adjustments */
    @media (max-width: 768px) { .header-card img { width: 120px; } .card { padding: 15px; } }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לענן (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

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
                        "manager_name": user_row.iloc[0]['manager']
                    })
                    st.rerun()
            # כניסת Admin ראשונית
            if u_in == "admin" and p_in == "admin123":
                st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול", "manager_name": "None"})
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.image(logo_url, width=120)
    st.sidebar.markdown(f"👋 שלום, **{st.session_state['user']}**")
    st.sidebar.info(f"תפקיד: {role}")
    if st.sidebar.button("🚪 התנתק מהמערכת"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT: אוטומציה ותשתית ---
    if role == "IT":
        st.header("⚙️ ניהול תשתית IT")
        t1, t2 = st.tabs(['👥 יצירת משתמשים באקסל', '🚦 בקרת מערכות (Onboarding)'])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("ייבוא משתמשים מרובי (Cloud Sync)")
            up_file = st.file_uploader("העלה קובץ (username, role, team, manager)", type=['xlsx'])
            if up_file and st.button("סנכרן משתמשים לענן (סיסמה: 123456)"):
                new_df = pd.read_excel(up_file)
                new_df['password'] = new_df.get('password', '123456').apply(hash_pwd)
                old_df = get_data("users")
                save_data(pd.concat([old_df, new_df]).drop_duplicates(subset=['username']), "users")
                st.success("הנתונים סונכרנו בהצלחה ל-Google Sheets!")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.subheader('צ"ק-ליסט מערכות פתוחות')
            onboard = get_data("onboarding")
            st.dataframe(onboard, use_container_width=True)

    # --- פאנל משא: חיזוי וכוח אדם ---
    elif role == "משא":
        st.header('📈 משא"בי אנוש וחיזוי')
        t1, t2 = st.tabs(['גיוס וגריעה', 'ניהול חיזוי משמרות'])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("בקשת קליטה לעובד שסיים קורס")
            f_name = st.text_input("שם מלא")
            u_name = st.text_input("שם משתמש מבוקש")
            if st.button("שלח ל-IT לפתיחת מערכות"):
                on_df = get_data("onboarding")
                new_row = pd.DataFrame([{"username": u_name, "full_name": f_name, "status": "קליטה"}])
                save_data(pd.concat([on_df, new_row]), "onboarding")
                st.success("הבקשה הועברה")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד: ניהול 360 ---
    elif role == "מנהל מוקד":
        st.header(f'📊 ניהול מוקד: {st.session_state["team"]}')
        t1, t2 = st.tabs(['דאשבורד ביצועים וחיזוי', 'ניהול ר"צים וצוותים'])
        
        with t1:
            st.subheader("העלאת דוח שיחות יומי")
            c_file = st.file_uploader("דוח אקסל (תאריך, שיחות, זמן_מענה)", type=['xlsx'])
            if c_file and st.button("פרסם דוח ביצועים"):
                perf_df = pd.read_excel(c_file)
                old_perf = get_data("performance")
                save_data(pd.concat([old_perf, perf_df]), "performance")
                st.success("הדוח פורסם בפורטל")
            
            p_data = get_data("performance")
            if not p_data.empty:
                st.plotly_chart(px.line(p_data, x='date', y='calls', title="מגמת עומס שיחות"))

    # --- פאנל ר"צ: שיבוץ וניהול שוטף ---
    elif role == 'ר"צ':
        st.header(f'👥 ניהול צוות: {st.session_state["user"]}')
        t1, t2, t3 = st.tabs(['שיבוץ משמרות', 'אישור מחלות', 'דוחות שעות'])
        
        with t1:
            target_d = st.date_input("יום לשיבוץ")
            st.subheader(f"אילוצים ליום {target_d}")
            all_cons = get_data("constraints")
            # סינון אוטומטי לנציגים של הר"צ הזה בלבד
            my_agents = all_cons[all_cons['manager'] == st.session_state['user']]
            st.dataframe(my_agents[my_agents['date'] == str(target_d)])
            
            agent_to_fix = st.selectbox("בחר נציג לשיבוץ", my_agents['username'].unique() if not my_agents.empty else [])
            shift_time = st.text_input("שעות (למשל 08:00-16:00)")
            if st.button("אשר שיבוץ"):
                sched_df = get_data("schedule")
                new_s = pd.DataFrame([{"username": agent_to_fix, "date": str(target_d), "shift": shift_time, "team": st.session_state['team']}])
                save_data(pd.concat([sched_df, new_s]), "schedule")
                st.success(f"הנציג {agent_to_fix} שובץ!")

    # --- פאנל נציג: הפורטל האישי ---
    elif role == "נציג":
        st.header("👤 הפורטל האישי שלי")
        t1, t2, t3 = st.tabs(['הגשת אילוצים', 'דיווח מחלה', 'אישור שעות עבודה'])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            d_con = st.date_input("תאריך האילוץ")
            note_con = st.text_area("הערות (למשל: בוקר בלבד)")
            if st.button("שלח אילוץ לר\"צ"):
                cons_df = get_data("constraints")
                new_row = pd.DataFrame([{"username": st.session_state['user'], "date": str(d_con), "note": note_con, "manager": st.session_state['manager_name']}])
                save_data(pd.concat([cons_df, new_row]), "constraints")
                st.success("האילוץ נשמר בהצלחה")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("דיווח על יום מחלה")
            sick_d = st.date_input("יום המחלה", key="sick")
            if st.button("דווח מחלה למנהל הצוות"):
                sick_df = get_data("sick_leaves")
                new_sick = pd.DataFrame([{"username": st.session_state['user'], "date": str(sick_d), "status": "ממתין לאישור"}])
                save_data(pd.concat([sick_df, new_sick]), "sick_leaves")
                st.success("הדיווח התקבל במערכת")
            st.markdown('</div>', unsafe_allow_html=True)
