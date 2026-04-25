import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
from datetime import datetime, date, time
import time as python_time
import plotly.express as px
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Master ERP System", layout="wide")

# --- פונקציות עזר (אבטחה, יומן ועיבוד נתונים) ---
def create_ics(summary, start_dt, end_dt):
    return f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{summary}\nDTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\nDTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\nEND:VEVENT\nEND:VCALENDAR"

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- עיצוב CSS פרימיום ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --success-green: #28a745; }
    .stApp { background-color: #F8F9FA; }
    .header-container { background: white; padding: 1.5rem; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 6px solid var(--accent-orange); text-align: center; }
    .custom-card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 1rem; border-right: 5px solid var(--main-blue); }
    [data-testid="stSidebar"] { background-color: var(--main-blue); color: white; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- חיבור וטעינת נתונים (מנגנון מניעת KeyError) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except Exception:
        return pd.DataFrame()

def save_data(df, sheet):
    try:
        if df is not None:
            conn.update(worksheet=sheet, data=df.fillna(""))
            st.cache_data.clear()
            python_time.sleep(1) # השהיה למניעת Quota API Error
    except Exception as e:
        st.error(f"שגיאת API של גוגל. וודא הרשאות עריכה (Editor). שגיאה: {e}")

# --- ניהול התחברות חכם (Smart Login) ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

if not st.session_state.auth["logged_in"]:
    st.markdown('<div class="header-container"><h1>MGROUP 360 | Enterprise ERP</h1></div>', unsafe_allow_html=True)
    with st.columns([1, 1.2, 1])[1]:
        u_in = st.text_input("שם משתמש").strip().lower()
        p_in = st.text_input("סיסמה", type="password")
        if st.button("כניסה למערכת"):
            if u_in == "admin" and p_in == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            u_df = load_data("users")
            if not u_df.empty:
                match = u_df[u_df['username'].str.lower() == u_in]
                if not match.empty:
                    stored = str(match.iloc[0]['password']).strip()
                    if p_in == stored or hash_pwd(p_in) == stored:
                        if p_in == stored: # הצפנה אוטומטית בכניסה ראשונה
                            u_df.loc[match.index, 'password'] = hash_pwd(p_in)
                            save_data(u_df, "users")
                        st.session_state.auth = {"logged_in": True, "user": match.iloc[0]['username'], "role": match.iloc[0]['role'], "team": match.iloc[0]['team']}
                        st.rerun()
            st.error("פרטי כניסה שגויים או משתמש מושבת")
else:
    user = st.session_state.auth
    st.sidebar.title(f"שלום, {user['user']}")
    st.sidebar.write(f"תפקיד: {user['role']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- 1. מנהל מערכת (IT) ---
    if user['role'] == "IT":
        st.title("🛠️ פאנל IT - ניהול תשתית")
        it_t1, it_t2, it_t3 = st.tabs(["👥 משתמשים (כולל אקסל)", "📊 דוחות ביצועים", "✅ צ'ק-ליסט Onboarding"])
        with it_t1:
            st.subheader("ייבוא משתמשים חדשים")
            f = st.file_uploader("העלה קובץ עובדים (XLSX/CSV)", type=['xlsx', 'csv'])
            if f and st.button("ייבא למערכת"):
                new_u = pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)
                save_data(pd.concat([load_data("users"), new_u.astype(str)]), "users")
            st.divider()
            ed_u = st.data_editor(load_data("users"), num_rows="dynamic")
            if st.button("שמור שינויים ביוזרים"): save_data(ed_u, "users")
            if st.button("🔄 איפוס גורף ל-123456"):
                u_df = load_data("users")
                u_df['password'] = hash_pwd("123456")
                save_data(u_df, "users")
        with it_t2:
            pf = st.file_uploader("העלה דוח ביצועים יומי", type=['xlsx', 'csv'], key="perf")
            if pf and st.button("עדכן נתוני ביצועים"):
                save_data(pd.concat([load_data("performance"), (pd.read_excel(pf) if pf.name.endswith('xlsx') else pd.read_csv(pf)).astype(str)]), "performance")
        with it_t3:
            st.data_editor(load_data("onboarding"), num_rows="dynamic", key="it_ob")

    # --- 2. ר"צ (Team Lead) ---
    elif user['role'] == "ר\"צ":
        st.title(f"🚀 ניהול צוות: {user['user']}")
        rt1, rt2 = st.tabs(["📅 אישור אילוצים", "👥 ביצועי הצוות"])
        with rt1:
            cons = load_data("constraints")
            sched = load_data("schedule")
            evs = [{"id": str(i), "title": f"אילוץ: {r['username']}", "start": r['date'], "color": "#FF8C32"} for i, r in cons.iterrows()]
            res_tl = calendar(events=evs, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="tl_cal")
            if res_tl.get("eventClick"):
                idx = int(res_tl["eventClick"]["event"]["id"])
                sel = cons.iloc[idx]
                st.info(f"מנהל אילוץ עבור: {sel['username']} ב-{sel['date']}")
                c1, c2 = st.columns(2)
                if c1.button("✅ אשר כמשמרת"):
                    new_s = pd.DataFrame([{"username": sel['username'], "date": sel['date'], "start_time": sel.get('start_time','08:00'), "end_time": sel.get('end_time','16:00'), "team": user['team']}])
                    save_data(pd.concat([sched, new_s]), "schedule")
                    save_data(cons.drop(idx), "constraints")
                    st.rerun()
                if c2.button("❌ דחה/מחק"):
                    save_data(cons.drop(idx), "constraints")
                    st.rerun()
        with rt2:
            st.subheader("נתוני הצוות")
            st.dataframe(load_data("performance"))

    # --- 3. נציג (Agent) ---
    elif user['role'] == "נציג":
        st.header(f"👤 פורטל נציג: {user['user']}")
        nt1, nt2 = st.tabs(["📝 הגשת אילוץ", "📅 המשמרות שלי"])
        with nt1:
            st.subheader("לחץ על תאריך להגשת אילוץ")
            res_a = calendar(events=[], options={"initialView": "dayGridMonth", "direction": "rtl"}, key="a_con")
            if res_a.get("dateClick"):
                d = res_a["dateClick"]["date"]
                with st.expander(f"הזנת שעות ל-{d}", expanded=True):
                    s = st.time_input("התחלה", time(8,0))
                    e = st.time_input("סיום", time(16,0))
                    if st.button("שלח אילוץ"):
                        save_data(pd.concat([load_data("constraints"), pd.DataFrame([{"username": user['user'], "date": d, "start_time": s.strftime("%H:%M"), "end_time": e.strftime("%H:%M")}])]), "constraints")
                        st.success("נשלח!")
        with nt2:
            st.subheader("משמרות מאושרות")
            df_s = load_data("schedule")
            if not df_s.empty and 'username' in df_s.columns:
                my_s = df_s[df_s['username'].str.lower() == user['user'].lower()]
                ev_s = [{"title": f"{r['start_time']}-{r['end_time']}", "start": r['date'], "color": "#28a745"} for i, r in my_s.iterrows()]
                calendar(events=ev_s, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="sh_cal")
                for i, r in my_s.iterrows():
                    try:
                        s_dt = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                        e_dt = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                        st.download_button(f"📅 סנכרן {r['date']} ליומן", create_ics("MGROUP Shift", s_dt, e_dt), file_name="shift.ics", key=f"dl_{i}")
                    except: pass

    # --- 4. מנהל מוקד (Manager) ---
    elif user['role'] == "מנהל מוקד":
        st.title(f"📊 מוקד: {user['team']}")
        m_tabs = st.tabs(["📅 עריכת סידור", "📈 ביצועי מוקד"])
        with m_tabs[0]:
            sched = load_data("schedule")
            ed_s = st.data_editor(sched[sched['team'] == user['team']], num_rows="dynamic")
            if st.button("פרסם שינויים בסידור"):
                save_data(pd.concat([sched[sched['team'] != user['team']], ed_s]), "schedule")
        with m_tabs[1]:
            p_df = load_data("performance")
            if not p_df.empty:
                p_df['calls'] = pd.to_numeric(p_df['calls'], errors='coerce')
                st.plotly_chart(px.line(p_df[p_df['team'] == user['team']], x='date', y='calls', title="עומס שיחות במוקד"))

    # --- 5. משא"בי אנוש (HR) ---
    elif user['role'] == "משא":
        st.title("📋 פורטל HR")
        hr1, hr2 = st.tabs(["Lifecycle", "דוחות כוח אדם"])
        with hr1:
            nm = st.text_input("שם עובד")
            tp = st.radio("פעולה", ["קליטה", "גריעה"])
            if st.button("שלח בקשה ל-IT"):
                save_data(pd.concat([load_data("onboarding"), pd.DataFrame([{"username": nm, "type": tp, "status": "ממתין", "date": str(date.today())}])]), "onboarding")
        with hr2:
            st.dataframe(load_data("onboarding"))
