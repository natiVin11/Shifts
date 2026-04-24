import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, date, time
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Master ERP", layout="wide")

# --- פונקציות עזר ---
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
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(26, 55, 77, 0.3); color: var(--accent-orange); }
    [data-testid="stSidebar"] { background-color: var(--main-blue); }
    [data-testid="stSidebar"] * { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור וטעינת נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except: return pd.DataFrame()

def save_data(df, sheet):
    if not df.empty:
        conn.update(worksheet=sheet, data=df.fillna(""))
        st.cache_data.clear()

# --- ניהול התחברות חכם (Smart Login) ---
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
                    if p_in == stored_p or hash_pwd(p_in) == stored_p:
                        if p_in == stored_p: # הצפנה אוטומטית בכניסה ראשונה
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
    user_info = st.session_state.auth
    st.sidebar.title(f"שלום, {user_info['user']}")
    st.sidebar.write(f"תפקיד: {user_info['role']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- 1. מנהל מערכת (IT) ---
    if user_info['role'] == "IT":
        st.title("🛠️ ניהול מערכת - IT")
        t_it1, t_it2, t_it3, t_it4 = st.tabs(["👥 משתמשים", "📂 ייבוא/ייצוא", "✅ צ'ק-ליסט מערכות", "📈 דוח ביצועים גלובלי"])
        
        with t_it1:
            u_df = load_data("users")
            edited_u = st.data_editor(u_df, num_rows="dynamic", use_container_width=True, key="it_u_ed")
            if st.button("שמור שינויים ביוזרים"): save_data(edited_u, "users")
            if st.button("🔄 איפוס גורף ל-123456"):
                u_df['password'] = hash_pwd("123456")
                save_data(u_df, "users")
                st.success("כל הסיסמאות אופסו")

        with t_it2:
            up_file = st.file_uploader("העלה קובץ אקסל עובדים חדשים", type=['xlsx'])
            if up_file and st.button("ייבא עובדים"):
                new_data = pd.read_excel(up_file).astype(str)
                save_data(pd.concat([u_df, new_data]), "users")

        with t_it3:
            ob_df = load_data("onboarding")
            st.data_editor(ob_df, num_rows="dynamic", key="ob_ed")
            
        with t_it4:
            perf_df = load_data("performance")
            st.plotly_chart(px.bar(perf_df, x='date', y='calls', color='team', title="ביצועי מוקדים חוצה ארגון"))

    # --- 2. מנהל מוקד (Manager) ---
    elif user_info['role'] == "מנהל מוקד":
        st.title(f"📊 ניהול מוקד: {user_info['team']}")
        m_t1, m_t2, m_t3 = st.tabs(["📅 עריכת סידור", "📝 אילוצי נציגים", "📈 בקרת ביצועים BI"])
        
        with m_t1:
            sched = load_data("schedule")
            edited_sched = st.data_editor(sched[sched['team'] == user_info['team']], num_rows="dynamic")
            if st.button("פרסם סידור"):
                save_data(pd.concat([sched[sched['team'] != user_info['team']], edited_sched]), "schedule")

        with m_t2:
            st.write("אילוצים שהוגשו במוקד שלך:")
            st.dataframe(load_data("constraints"))

        with m_t3:
            p_df = load_data("performance")
            st.plotly_chart(px.line(p_df[p_df['team'] == user_info['team']], x='date', y='calls', title="עומסי שיחות במוקד"))

    # --- 3. ר"צ (Team Lead) ---
    elif user_info['role'] == "ר\"צ":
        st.title(f"🚀 פאנל ר\"צ - צוות {user_info['user']}")
        rt1, rt2, rt3 = st.tabs(["👥 נתוני הצוות", "📅 לוח שנה משמרות", "🔮 אילוצים וחיזוי"])
        
        with rt1:
            st.write("ביצועי נציגים בצוות:")
            st.dataframe(load_data("performance")) # כאן ניתן להוסיף פילטר לפי נציגי הצוות
            
        with rt2:
            sched = load_data("schedule")
            events = [{"title": f"{r['username']}: {r['start_time']}-{r['end_time']}", "start": r['date'], "end": r['date']} for i, r in sched.iterrows()]
            calendar(events=events, options={"initialView": "dayGridMonth", "direction": "rtl"})

        with rt3:
            st.subheader("אילוצים מול לוח חיזוי")
            st.write("לוח זה מאפשר לקבוע משמרות לפי צפי עומסים")
            st.dataframe(load_data("constraints"))

    # --- 4. נציג (Agent) ---
    elif user_info['role'] == "נציג":
        st.header(f"👤 פורטל נציג: {user_info['user']}")
        my_shifts = pd.DataFrame()
        events = []
        sched_df = load_data("schedule")
        if not sched_df.empty:
            my_shifts = sched_df[sched_df['username'].str.lower() == user_info['user'].lower()]
            for i, r in my_shifts.iterrows():
                events.append({"title": f"משמרת: {r['start_time']}-{r['end_time']}", "start": r['date'], "end": r['date'], "color": "#28a745", "allDay": True})

        res = calendar(events=events, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="agent_cal")
        if res.get("callback") == "dateClick":
            st.session_state.selected_date = res["dateClick"]["date"]
            st.info(f"תאריך נבחר לאילוץ: {res['dateClick']['date']}")
            
        with st.expander("הגשת אילוץ חדש"):
            s_t = st.time_input("התחלה", time(8,0))
            e_t = st.time_input("סיום", time(16,0))
            if st.button("שלח אילוץ"):
                c_df = load_data("constraints")
                new_c = pd.DataFrame([{"username": user_info['user'], "date": st.session_state.get('selected_date', str(date.today())), "start_time": s_t.strftime("%H:%M"), "end_time": e_t.strftime("%H:%M")}])
                save_data(pd.concat([c_df, new_c]), "constraints")
                st.success("נשלח!")

        if not my_shifts.empty:
            st.subheader("סנכרון יומן")
            for i, r in my_shifts.iterrows():
                s_dt = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                e_dt = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                st.download_button(f"📅 הורד {r['date']}", create_ics("MGROUP Shift", s_dt, e_dt), file_name="shift.ics", key=f"dl_{i}")

    # --- 5. משא"בי אנוש (HR) ---
    elif user_info['role'] == "משא":
        st.title("📋 פורטל משא\"בי אנוש")
        h1, h2 = st.tabs(["Lifecycle (קליטה/גריעה)", "דוחות כוח אדם"])
        
        with h1:
            u_name = st.text_input("שם עובד")
            action = st.radio("פעולה", ["קליטה", "גריעה"])
            if st.button("שלח בקשה ל-IT"):
                ob = load_data("onboarding")
                save_data(pd.concat([ob, pd.DataFrame([{"username": u_name, "type": action, "status": "ממתין ל-IT", "date": str(date.today())}])]), "onboarding")
                st.success("בקשה נשלחה")
        
        with h2:
            st.write("סטטוס הקמת משתמשים:")
            st.dataframe(load_data("onboarding"))
