import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
from datetime import datetime, date, time
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | ERP System", layout="wide")

# --- פונקציות עזר ---
def create_ics(summary, start_dt, end_dt):
    return f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{summary}\nDTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\nDTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\nEND:VEVENT\nEND:VCALENDAR"

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- עיצוב CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; }
    .stApp { background-color: #F8F9FA; }
    .header-container { background: white; padding: 1.5rem; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 6px solid var(--accent-orange); text-align: center; }
    .custom-card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 1rem; border-right: 5px solid var(--main-blue); }
    [data-testid="stSidebar"] { background-color: var(--main-blue); color: white; }
</style>
""", unsafe_allow_html=True)

# --- חיבור וטעינה ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet, ttl=0).dropna(how='all')
        # תיקון קריטי ל-KeyError: ניקוי שמות עמודות מרווחים והמרתם לאותיות קטנות
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except Exception as e:
        st.error(f"שגיאה בטעינת גיליון {sheet}: {e}")
        return pd.DataFrame()

def save_data(df, sheet):
    if df is not None:
        conn.update(worksheet=sheet, data=df.fillna(""))
        st.cache_data.clear()

# --- ניהול התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

if not st.session_state.auth["logged_in"]:
    st.markdown('<div class="header-container"><h1>MGROUP 360</h1></div>', unsafe_allow_html=True)
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
                        st.session_state.auth = {"logged_in": True, "user": match.iloc[0]['username'], "role": match.iloc[0]['role'], "team": match.iloc[0]['team']}
                        st.rerun()
            st.error("פרטים שגויים")
else:
    u = st.session_state.auth
    st.sidebar.title(f"שלום, {u['user']}")
    if st.sidebar.button("התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT ---
    if u['role'] == "IT":
        st.title("🛠️ ניהול מערכת IT")
        t1, t2 = st.tabs(["ניהול משתמשים (כולל העלאת אקסל)", "דוחות ביצועים"])
        
        with t1:
            st.subheader("ייבוא משתמשים חדשים מאקסל")
            u_file = st.file_uploader("העלה קובץ משתמשים (CSV/XLSX)", type=['csv', 'xlsx'], key="u_up")
            if u_file:
                new_users = pd.read_csv(u_file) if u_file.name.endswith('csv') else pd.read_excel(u_file)
                if st.button("הוסף משתמשים למערכת"):
                    current_u = load_data("users")
                    save_data(pd.concat([current_u, new_users.astype(str)]), "users")
                    st.success("משתמשים נוספו בהצלחה!")
            
            st.divider()
            st.subheader("עריכה ידנית")
            df_u = load_data("users")
            ed_u = st.data_editor(df_u, num_rows="dynamic")
            if st.button("שמור שינויים"): save_data(ed_u, "users")

        with t2:
            st.subheader("העלאת דוח ביצועים תקופתי")
            p_file = st.file_uploader("העלה דוח ביצועים", type=['csv', 'xlsx'], key="p_up")
            if p_file:
                new_perf = pd.read_csv(p_file) if p_file.name.endswith('csv') else pd.read_excel(p_file)
                if st.button("עדכן נתוני ביצועים"):
                    df_perf = load_data("performance")
                    save_data(pd.concat([df_perf, new_perf.astype(str)]), "performance")
                    st.success("נתוני ביצועים עודכנו")

    # --- פאנל ר"צ (אישור אילוצים בלוח שנה) ---
    elif u['role'] == "ר\"צ":
        st.title(f"🚀 ניהול צוות: {u['team']}")
        rt1, rt2 = st.tabs(["ניהול ואישור משמרות", "ביצועי צוות"])
        
        with rt1:
            cons = load_data("constraints")
            sched = load_data("schedule")
            
            st.write("לחץ על אילוץ בלוח כדי להפוך אותו למשמרת מאושרת:")
            evs = [{"id": str(i), "title": f"אילוץ: {r['username']}", "start": r['date'], "color": "#FF8C32"} for i, r in cons.iterrows()]
            
            res_tl = calendar(events=evs, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="tl_mgr")
            
            if res_tl.get("eventClick"):
                idx = int(res_tl["eventClick"]["event"]["id"])
                sel = cons.iloc[idx]
                st.markdown(f'<div class="custom-card">אישור אילוץ עבור {sel["username"]} ב-{sel["date"]}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✅ אשר כמשמרת"):
                    new_s = pd.DataFrame([{"username": sel['username'], "date": sel['date'], "start_time": sel['start_time'], "end_time": sel['end_time'], "team": u['team']}])
                    save_data(pd.concat([sched, new_s]), "schedule")
                    save_data(cons.drop(idx), "constraints")
                    st.rerun()
                if c2.button("❌ מחק אילוץ"):
                    save_data(cons.drop(idx), "constraints")
                    st.rerun()

    # --- פאנל נציג (2 מסכים) ---
    elif u['role'] == "נציג":
        st.title(f"👤 פורטל נציג: {u['user']}")
        nt1, nt2 = st.tabs(["📝 הגשת אילוץ", "📅 המשמרות שלי"])
        
        with nt1:
            st.subheader("בחר תאריך להגשת אילוץ")
            res_a = calendar(events=[], options={"initialView": "dayGridMonth", "direction": "rtl"}, key="a_con")
            if res_a.get("dateClick"):
                d = res_a["dateClick"]["date"]
                with st.expander(f"הגש אילוץ ל-{d}", expanded=True):
                    s = st.time_input("התחלה", time(8,0))
                    e = st.time_input("סיום", time(16,0))
                    if st.button("שלח אילוץ"):
                        df_c = load_data("constraints")
                        new_r = pd.DataFrame([{"username": u['user'], "date": d, "start_time": s.strftime("%H:%M"), "end_time": e.strftime("%H:%M")}])
                        save_data(pd.concat([df_c, new_r]), "constraints")
                        st.success("האילוץ נשלח לר"צ")

        with nt2:
            st.subheader("משמרות שנקבעו לך")
            df_s = load_data("schedule")
            # וידוא עמודה לפני סינון למניעת KeyError
            if not df_s.empty and 'username' in df_s.columns:
                my_s = df_s[df_s['username'].str.lower() == u['user'].lower()]
                ev_s = [{"title": f"{r['start_time']}-{r['end_time']}", "start": r['date'], "color": "#28a745"} for _, r in my_s.iterrows()]
                calendar(events=ev_s, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="a_sh")
            else:
                st.info("עדיין לא נקבעו משמרות")

    # --- פאנל משא"ב ---
    elif u['role'] == "משא":
        st.title("📋 ניהול HR")
        ob = load_data("onboarding")
        ed_ob = st.data_editor(ob, num_rows="dynamic")
        if st.button("עדכן"): save_data(ed_ob, "onboarding")
