import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, date, time
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Management System", layout="wide")

# --- פונקציות עזר ---
def create_ics(summary, start_dt, end_dt):
    return f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{summary}\nDTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\nDTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\nEND:VEVENT\nEND:VCALENDAR"

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- עיצוב CSS ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --soft-bg: #F8F9FA; }
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

def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except: return pd.DataFrame()

def save_data(df, sheet):
    conn.update(worksheet=sheet, data=df.fillna(""))
    st.cache_data.clear()

# --- ניהול התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

if not st.session_state.auth["logged_in"]:
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.image("https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg", width=180)
    st.markdown('<h1>MGROUP 360 | כניסה למערכת</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.columns([1, 1.5, 1])[1]:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        u_in = st.text_input("שם משתמש").strip().lower()
        p_in = st.text_input("סיסמה", type="password").strip()
        
        if st.button("התחבר"):
            if u_in == "admin" and p_in == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            u_df = load_data("users")
            if not u_df.empty:
                u_df['u_clean'] = u_df['username'].str.strip().str.lower()
                match = u_df[(u_df['u_clean'] == u_in) & (u_df['status'] == 'Active')]
                
                if not match.empty:
                    stored_p = str(match.iloc[0]['password']).strip()
                    # מנגנון כניסה חכם: בודק גם סיסמה גלויה וגם מוצפנת
                    if p_in == stored_p or hash_pwd(p_in) == stored_p:
                        # אם נכנס עם סיסמה גלויה, נצפין אותה עכשיו בגיליון
                        if p_in == stored_p:
                            u_df.loc[match.index, 'password'] = hash_pwd(p_in)
                            save_data(u_df.drop(columns=['u_clean']), "users")
                        
                        st.session_state.auth = {
                            "logged_in": True, "user": match.iloc[0]['username'],
                            "role": match.iloc[0]['role'], "team": match.iloc[0]['team']
                        }
                        st.rerun()
                st.error("שם משתמש או סיסמה שגויים")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    role = st.session_state.auth["role"]
    st.sidebar.title(f"שלום, {st.session_state.auth['user']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT: ניהול משתמשים מלא ---
    if role == "IT":
        st.title("🛠️ ניהול מערכת (IT)")
        t1, t2, t3 = st.tabs(["👥 משתמשים", "📈 ביצועים", "📂 גיבויים"])
        with t1:
            u_df = load_data("users")
            st.data_editor(u_df, num_rows="dynamic", key="it_editor", on_change=lambda: save_data(st.session_state.it_editor, "users"))
            if st.button("סנכרן שינויים לגיליון"):
                save_data(u_df, "users")
                st.success("נשמר!")

    # --- פאנל מנהל מוקד: ניהול סידור וביצועים ---
    elif role == "מנהל מוקד":
        st.title(f"📊 ניהול מוקד: {st.session_state.auth['team']}")
        m_t1, m_t2 = st.tabs(["📅 סידור עבודה", "📝 אילוצי נציגים"])
        with m_t1:
            st.subheader("עריכת סידור עבודה")
            sched = load_data("schedule")
            edited_sched = st.data_editor(sched[sched['team'] == st.session_state.auth['team']], num_rows="dynamic")
            if st.button("פרסם סידור"):
                save_data(pd.concat([sched[sched['team'] != st.session_state.auth['team']], edited_sched]), "schedule")
                st.success("הסידור פורסם!")
        with m_t2:
            st.subheader("אילוצים שהוגשו")
            st.write(load_data("constraints"))

    # --- פאנל נציג: לוח שנה ואילוצים ---
    elif role == "נציג":
        st.header("👤 פורטל נציג")
        my_shifts = pd.DataFrame()
        events = []
        sched_df = load_data("schedule")
        if not sched_df.empty:
            my_shifts = sched_df[sched_df['username'].str.lower() == st.session_state.auth['user'].lower()]
            for i, r in my_shifts.iterrows():
                events.append({"title": f"משמרת: {r['start_time']}-{r['end_time']}", "start": r['date'], "end": r['date'], "color": "#28a745", "allDay": True})

        col_cal, col_form = st.columns([2, 1])
        with col_cal:
            res = calendar(events=events, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="agent_cal")
            if res.get("callback") == "dateClick": st.session_state.selected_date = res["dateClick"]["date"]
        with col_form:
            st.subheader("הגשת אילוץ")
            sel_d = st.session_state.get('selected_date', str(date.today()))
            st.write(f"תאריך: {sel_d}")
            s_t = st.time_input("התחלה", time(8,0))
            e_t = st.time_input("סיום", time(16,0))
            if st.button("שמור"):
                c_df = load_data("constraints")
                new_c = pd.DataFrame([{"username": st.session_state.auth['user'], "date": sel_d, "start_time": s_t.strftime("%H:%M"), "end_time": e_t.strftime("%H:%M")}])
                save_data(pd.concat([c_df, new_c]), "constraints")
                st.success("נשלח!")
            
            if not my_shifts.empty:
                st.divider()
                st.subheader("הורד ליומן")
                for i, r in my_shifts.iterrows():
                    s_dt = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                    e_dt = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                    st.download_button(f"📅 {r['date']}", create_ics("MGROUP Shift", s_dt, e_dt), file_name="shift.ics", key=f"dl_{i}")
