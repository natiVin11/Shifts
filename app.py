import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
from datetime import datetime, date, time
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Master ERP System", layout="wide")

# --- פונקציות עזר (אבטחה ויומן) ---
def create_ics(summary, start_dt, end_dt):
    return f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{summary}\nDTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\nDTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\nEND:VEVENT\nEND:VCALENDAR"

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

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
    [data-testid="stSidebar"] { background-color: var(--main-blue); color: white; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור וניהול נתונים (CRUD) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except: return pd.DataFrame()

def save_data(df, sheet):
    if df is not None and not df.empty:
        conn.update(worksheet=sheet, data=df.fillna(""))
        st.cache_data.clear()
        st.toast(f"הנתונים בגיליון {sheet} עודכנו בהצלחה!")

# --- מנגנון התחברות חכם (Smart Login) ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

if not st.session_state.auth["logged_in"]:
    st.markdown('<div class="header-container"><img src="https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg" width="150"><h1>MGROUP 360 | כניסה</h1></div>', unsafe_allow_html=True)
    with st.columns([1, 1.5, 1])[1]:
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
                    if p_in == stored_p or hash_pwd(p_in) == stored_p:
                        if p_in == stored_p: # הצפנה אוטומטית בכניסה ראשונה
                            u_df.loc[match.index, 'password'] = hash_pwd(p_in)
                            save_data(u_df.drop(columns=['u_clean']), "users")
                        st.session_state.auth = {"logged_in": True, "user": match.iloc[0]['username'], "role": match.iloc[0]['role'], "team": match.iloc[0]['team']}
                        st.rerun()
                st.error("פרטי כניסה שגויים או משתמש מושבת")

else:
    u_info = st.session_state.auth
    st.sidebar.title(f"שלום, {u_info['user']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- 1. מנהל מערכת (IT) ---
    if u_info['role'] == "IT":
        st.title("🛠️ פאנל IT")
        it_tabs = st.tabs(["👥 משתמשים", "📈 ביצועים", "📂 ייבוא/ייצוא", "✅ Onboarding"])
        with it_tabs[0]:
            users = load_data("users")
            ed_u = st.data_editor(users, num_rows="dynamic", use_container_width=True, key="it_users")
            if st.button("שמור שינויים"): save_data(ed_u, "users")
            if st.button("🔄 איפוס גורף ל-123456"):
                users['password'] = hash_pwd("123456")
                save_data(users, "users")
        with it_tabs[1]:
            perf = load_data("performance")
            if not perf.empty:
                perf['calls'] = pd.to_numeric(perf['calls'], errors='coerce')
                import plotly.express as px
                st.plotly_chart(px.bar(perf, x='date', y='calls', color='team', title="ביצועים חוצה ארגון"))
        with it_tabs[3]:
            onb = load_data("onboarding")
            st.data_editor(onb, num_rows="dynamic", key="it_onb")

    # --- 2. מנהל מוקד (Manager) ---
    elif u_info['role'] == "מנהל מוקד":
        st.title(f"📊 מנהל מוקד: {u_info['team']}")
        m_tabs = st.tabs(["📅 עריכת סידור", "📝 אילוצי נציגים", "📈 בקרת ביצועים BI"])
        with m_tabs[0]:
            sc = load_data("schedule")
            my_team_sc = sc[sc['team'] == u_info['team']]
            ed_sc = st.data_editor(my_team_sc, num_rows="dynamic", key="mgr_sc")
            if st.button("פרסם סידור"):
                save_data(pd.concat([sc[sc['team'] != u_info['team']], ed_sc]), "schedule")
        with m_tabs[1]:
            st.write("אילוצים שהוגשו:")
            st.dataframe(load_data("constraints"))
        with m_tabs[2]:
            perf = load_data("performance")
            if not perf.empty:
                st.plotly_chart(px.line(perf[perf['team'] == u_info['team']], x='date', y='calls'))

    # --- 3. ר"צ (Team Lead) ---
    elif u_info['role'] == "ר\"צ":
        st.title(f"🚀 פאנל ר\"צ - {u_info['user']}")
        r_tabs = st.tabs(["👥 נתוני צוות", "📅 לוח שנה", "🔮 אילוצים וחיזוי"])
        with r_tabs[0]:
            st.write("ביצועי נציגים:")
            st.dataframe(load_data("performance"))
        with r_tabs[1]:
            sc = load_data("schedule")
            evs = [{"title": f"{r['username']}", "start": r['date'], "end": r['date']} for i, r in sc.iterrows()]
            calendar(events=evs, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="tl_cal")
        with r_tabs[2]:
            st.subheader("אילוצים מול חיזוי עומסים")
            st.dataframe(load_data("constraints"))

    # --- 4. נציג (Agent) ---
    elif u_info['role'] == "נציג":
        st.header(f"👤 פורטל נציג: {u_info['user']}")
        a_tabs = st.tabs(["📝 הגשת אילוצים", "📅 המשמרות שלי"])
        
        with a_tabs[0]:
            st.subheader("בחירת תאריך לאילוץ")
            col_c, col_f = st.columns([2,1])
            with col_c:
                res = calendar(events=[], options={"initialView": "dayGridMonth", "direction": "rtl"}, key="a_cal")
                if res.get("callback") == "dateClick": st.session_state.sel_d = res["dateClick"]["date"]
            with col_f:
                d = st.session_state.get('sel_d', str(date.today()))
                st.write(f"תאריך: **{d}**")
                s_t = st.time_input("התחלה", time(8,0))
                e_t = st.time_input("סיום", time(16,0))
                if st.button("שמור אילוץ"):
                    c_df = load_data("constraints")
                    new_c = pd.DataFrame([{"username": u_info['user'], "date": d, "start_time": s_t.strftime("%H:%M"), "end_time": e_t.strftime("%H:%M")}])
                    save_data(pd.concat([c_df, new_c]), "constraints")
        
        with a_tabs[1]:
            sh = load_data("schedule")
            if not sh.empty and 'username' in sh.columns:
                my_sh = sh[sh['username'].str.lower() == u_info['user'].lower()]
                ev_sh = [{"title": f"{r['start_time']}-{r['end_time']}", "start": r['date'], "end": r['date'], "color": "#28a745"} for i, r in my_sh.iterrows()]
                calendar(events=ev_sh, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="s_cal")
                for i, r in my_sh.iterrows():
                    try:
                        s_dt = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                        e_dt = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                        st.download_button(f"📅 {r['date']} - הורד ליומן", create_ics("MGROUP Shift", s_dt, e_dt), file_name="shift.ics", key=f"dl_{i}")
                    except: pass

    # --- 5. משא"בי אנוש (HR) ---
    elif u_info['role'] == "משא":
        st.title("📋 פורטל משא\"בי אנוש")
        h_tabs = st.tabs(["Lifecycle (קליטה/גריעה)", "דוחות כוח אדם"])
        with h_tabs[0]:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            nm = st.text_input("שם עובד")
            tp = st.radio("סוג פעולה", ["קליטה", "גריעה"])
            if st.button("שלח בקשה ל-IT"):
                onb = load_data("onboarding")
                save_data(pd.concat([onb, pd.DataFrame([{"username": nm, "type": tp, "status": "ממתין ל-IT", "date": str(date.today())}])]), "onboarding")
        with h_tabs[1]:
            st.dataframe(load_data("onboarding"))
