import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
from datetime import datetime, date, time
import time as python_time # השהיה למניעת Quota Error

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Master ERP", layout="wide")

# --- פונקציות עזר (אבטחה ויומן) ---
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

# --- חיבור וטעינת נתונים ---
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
            python_time.sleep(1) # השהיה קלה למניעת שגיאות API
    except Exception as e:
        st.error(f"שגיאת תקשורת עם גוגל (API Error). וודא שיש לך הרשאות עריכה. פירוט: {e}")

# --- ניהול התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

if not st.session_state.auth["logged_in"]:
    st.markdown('<div class="header-container"><h1>MGROUP 360 | Master ERP</h1></div>', unsafe_allow_html=True)
    with st.columns([1, 1.2, 1])[1]:
        u_in = st.text_input("שם משתמש").strip().lower()
        p_in = st.text_input("סיסמה", type="password")
        if st.button("כניסה"):
            if u_in == "admin" and p_in == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            u_df = load_data("users")
            if not u_df.empty:
                match = u_df[u_df['username'].str.lower() == u_in]
                if not match.empty:
                    stored = str(match.iloc[0]['password'])
                    if p_in == stored or hash_pwd(p_in) == stored:
                        if p_in == stored:
                            u_df.loc[match.index, 'password'] = hash_pwd(p_in)
                            save_data(u_df, "users")
                        st.session_state.auth = {"logged_in": True, "user": match.iloc[0]['username'], "role": match.iloc[0]['role'], "team": match.iloc[0]['team']}
                        st.rerun()
            st.error("פרטי כניסה שגויים")
else:
    u = st.session_state.auth
    st.sidebar.title(f"שלום, {u['user']}")
    if st.sidebar.button("התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT ---
    if u['role'] == "IT":
        st.title("🛠️ פאנל IT")
        it1, it2 = st.tabs(["👥 ניהול משתמשים", "📈 דוח ביצועים"])
        with it1:
            f = st.file_uploader("ייבוא משתמשים (Excel/CSV)", type=['xlsx', 'csv'])
            if f and st.button("ייבא עובדים"):
                new_u = pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)
                save_data(pd.concat([load_data("users"), new_u.astype(str)]), "users")
            ed_u = st.data_editor(load_data("users"), num_rows="dynamic")
            if st.button("שמור שינויים"): save_data(ed_u, "users")
        with it2:
            pf = st.file_uploader("העלה דוח ביצועים", type=['xlsx', 'csv'], key="perf")
            if pf and st.button("עדכן דוח"):
                new_p = pd.read_excel(pf) if pf.name.endswith('xlsx') else pd.read_csv(pf)
                save_data(pd.concat([load_data("performance"), new_p.astype(str)]), "performance")

    # --- פאנל ר"צ (ניהול אילוצים) ---
    elif u['role'] == "ר\"צ":
        st.title(f"🚀 ניהול צוות: {u['user']}")
        rt1, rt2 = st.tabs(["📅 אישור אילוצים", "👥 ביצועי נציגים"])
        with rt1:
            cons = load_data("constraints")
            sched = load_data("schedule")
            evs = [{"id": str(i), "title": f"אילוץ: {r['username']}", "start": r['date'], "color": "#FF8C32"} for i, r in cons.iterrows()]
            res_tl = calendar(events=evs, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="tl_cal")
            if res_tl.get("eventClick"):
                idx = int(res_tl["eventClick"]["event"]["id"])
                sel = cons.iloc[idx]
                st.info(f"מנהל אילוץ עבור {sel['username']}")
                c1, c2 = st.columns(2)
                if c1.button("✅ אשר כמשמרת"):
                    new_s = pd.DataFrame([{"username": sel['username'], "date": sel['date'], "start_time": sel.get('start_time','08:00'), "end_time": sel.get('end_time','16:00'), "team": u['team']}])
                    # פעולה כפולה: הוספה לסידור ומחיקה מהאילוצים
                    combined_sched = pd.concat([sched, new_s])
                    save_data(combined_sched, "schedule")
                    new_cons = cons.drop(idx)
                    save_data(new_cons, "constraints")
                    st.rerun()
                if c2.button("❌ דחה"):
                    save_data(cons.drop(idx), "constraints")
                    st.rerun()

    # --- פאנל נציג ---
    elif u['role'] == "נציג":
        st.header(f"👤 פורטל נציג: {u['user']}")
        nt1, nt2 = st.tabs(["📝 הגשת אילוץ", "📅 המשמרות שלי"])
        with nt1:
            res_a = calendar(events=[], options={"initialView": "dayGridMonth", "direction": "rtl"}, key="a_cal")
            if res_a.get("dateClick"):
                d = res_a["dateClick"]["date"]
                with st.expander(f"אילוץ ל-{d}", expanded=True):
                    s_t = st.time_input("התחלה", time(8,0))
                    e_t = st.time_input("סיום", time(16,0))
                    if st.button("שלח"):
                        c_df = load_data("constraints")
                        save_data(pd.concat([c_df, pd.DataFrame([{"username": u['user'], "date": d, "start_time": s_t.strftime("%H:%M"), "end_time": e_t.strftime("%H:%M")}])]), "constraints")
        with nt2:
            sh = load_data("schedule")
            if not sh.empty and 'username' in sh.columns:
                my_s = sh[sh['username'].str.lower() == u['user'].lower()]
                ev_s = [{"title": f"{r['start_time']}-{r['end_time']}", "start": r['date'], "color": "#28a745"} for i, r in my_s.iterrows()]
                calendar(events=ev_s, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="sh_cal")

    # --- פאנל משא"ב ---
    elif u['role'] == "משא":
        st.title("📋 פורטל HR")
        ob = load_data("onboarding")
        ed_ob = st.data_editor(ob, num_rows="dynamic", key="hr_ed")
        if st.button("עדכן"): save_data(ed_ob, "onboarding")
