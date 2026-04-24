import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, date, time
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Enterprise ERP", layout="wide")

# --- פונקציית עזר לייצוא ליומן (ICS) ---
def create_ics(summary, start_dt, end_dt):
    ics_format = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MGROUP//360//HE
BEGIN:VEVENT
SUMMARY:{summary}
DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}
DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}
END:VEVENT
END:VCALENDAR"""
    return ics_format

# --- עיצוב CSS פרימיום ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --soft-bg: #F8F9FA; --success-green: #28a745; }
    .stApp { background-color: var(--soft-bg); }
    .header-container { background: white; padding: 1.5rem; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 6px solid var(--accent-orange); text-align: center; }
    .custom-card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 1rem; border-right: 5px solid var(--main-blue); }
    .stButton>button { background: linear-gradient(135deg, var(--main-blue), #2c5d81); color: white; border-radius: 10px; border: none; padding: 0.6rem 1rem; font-weight: 600; width: 100%; transition: 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(26, 55, 77, 0.3); color: var(--accent-orange); }
    [data-testid="stSidebar"] { background-color: var(--main-blue); }
    [data-testid="stSidebar"] * { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except: return pd.DataFrame()

def save_to_sheet(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df.fillna(""))
    st.cache_data.clear()

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- ניהול התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

def login_screen():
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.image("https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg", width=180)
    st.markdown('<h1>MGROUP 360 | פורטל ניהול ארגוני</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.columns([1, 1.5, 1])[1]:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        u_in = st.text_input("שם משתמש").strip().lower()
        p_in = st.text_input("סיסמה", type="password").strip()
        
        if st.button("כניסה למערכת"):
            if u_in == "admin" and p_in == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            u_df = load_data("users")
            if not u_df.empty:
                u_df['u_clean'] = u_df['username'].str.strip().str.lower()
                match = u_df[(u_df['u_clean'] == u_in) & (u_df['status'] == 'Active')]
                if not match.empty:
                    if hash_pwd(p_in) == str(match.iloc[0]['password']).strip():
                        st.session_state.auth = {
                            "logged_in": True, "user": match.iloc[0]['username'],
                            "role": match.iloc[0]['role'], "team": match.iloc[0]['team'],
                            "manager": match.iloc[0].get('manager', 'None')
                        }
                        st.rerun()
                st.error("פרטי כניסה שגויים או משתמש מושבת")
        st.markdown('</div>', unsafe_allow_html=True)

# --- גוף המערכת ---
if not st.session_state.auth["logged_in"]:
    login_screen()
else:
    user_info = st.session_state.auth
    st.sidebar.markdown(f"### שלום, {user_info['user']}")
    if st.sidebar.button("🚪 יציאה"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT ---
    if user_info['role'] == "IT":
        st.header("🛠️ פאנל ניהול IT")
        t1, t2 = st.tabs(["ניהול משתמשים", "ייצוא נתונים"])
        with t1:
            u_df = load_data("users")
            if not u_df.empty:
                sel_u = st.selectbox("בחר משתמש", u_df['username'].unique())
                idx = u_df[u_df['username'] == sel_u].index[0]
                if st.button("🔄 איפוס סיסמה ל-123456"):
                    u_df.at[idx, 'password'] = hash_pwd("123456")
                    save_to_sheet(u_df, "users")
                    st.success("בוצע!")

    # --- פאנל נציג (עם לוח שנה ויזואלי) ---
    elif user_info['role'] == "נציג":
        st.header(f"👋 שלום {user_info['user']}")
        
        # טעינת משמרות ללוח השנה
        sched_df = load_data("schedule")
        events = []
        if not sched_df.empty and 'username' in sched_df.columns:
            my_shifts = sched_df[sched_df['username'].str.strip() == user_info['user']]
            for i, r in my_shifts.iterrows():
                events.append({
                    "title": f"משמרת: {r.get('start_time')} - {r.get('end_time')}",
                    "start": r.get('date'),
                    "end": r.get('date'),
                    "color": "#28a745",
                    "allDay": True,
                    "id": i
                })

        cal_options = {
            "editable": True, "selectable": True, "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,timeGridWeek"},
            "initialView": "dayGridMonth", "direction": "rtl",
        }

        col_cal, col_form = st.columns([2, 1])
        
        with col_cal:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            res = calendar(events=events, options=cal_options, key="agent_cal")
            if res.get("callback") == "dateClick":
                st.session_state.selected_date = res["dateClick"]["date"]
            st.markdown('</div>', unsafe_allow_html=True)

        with col_form:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("הגשת אילוץ")
            sel_date = st.session_state.get('selected_date', str(date.today()))
            st.info(f"תאריך נבחר: **{sel_date}**")
            
            st1 = st.time_input("התחלה", time(8, 0))
            et1 = st.time_input("סיום", time(16, 0))
            note = st.text_area("הערה")
            
            if st.button("שמור אילוץ"):
                c_df = load_data("constraints")
                new_row = pd.DataFrame([{"username": user_info['user'], "date": sel_date, "start_time": st1.strftime("%H:%M"), "end_time": et1.strftime("%H:%M"), "note": note}])
                save_to_sheet(pd.concat([c_df, new_row]), "constraints")
                st.success("נשמר!")
            st.markdown('</div>', unsafe_allow_html=True)

            # כפתור הורדת משמרת ליומן (ICS) במידה ויש משמרת היום
            if not my_shifts.empty:
                st.subheader("הורדת משמרות")
                for i, r in my_shifts.iterrows():
                    try:
                        s_dt = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                        e_dt = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                        ics = create_ics("MGROUP Shift", s_dt, e_dt)
                        st.download_button(f"📅 הורד ליומן ({r['date']})", ics, file_name="shift.ics", key=f"dl_{i}")
                    except: pass

    # --- פאנלים אחרים (משא/מנהלים) ---
    elif user_info['role'] in ["מנהל מוקד", "מנהל פרוייקט"]:
        st.title("📊 דאשבורד BI")
        perf = load_data("performance")
        if not perf.empty:
            st.plotly_chart(px.bar(perf, x='date', y='calls', color='team', barmode='group'))
