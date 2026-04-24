import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, date
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
    .header-container { background: white; padding: 2rem; border-radius: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 6px solid var(--accent-orange); text-align: center; }
    .custom-card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 1rem; border-right: 5px solid var(--main-blue); }
    .shift-card { background: #d4edda; border-radius: 12px; padding: 1.2rem; border-right: 8px solid var(--success-green); margin-bottom: 1rem; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
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
        # ניקוי שמות עמודות למניעת KeyError
        df.columns = df.columns.str.strip().str.lower()
        return df.astype(str)
    except Exception as e:
        return pd.DataFrame()

def save_to_sheet(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df.fillna(""))
    st.cache_data.clear()

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- לוגיקת התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

if not st.session_state.auth["logged_in"]:
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.image("https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg", width=200)
    st.markdown('<h1>MGROUP 360 | פורטל ניהול ארגוני</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.columns([1, 1.5, 1])[1]:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        u_in = st.text_input("שם משתמש").strip().lower()
        p_in = st.text_input("סיסמה", type="password").strip()
        
        if st.button("כניסה"):
            if u_in == "admin" and p_in == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            u_df = load_data("users")
            if not u_df.empty and 'username' in u_df.columns:
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
            else: st.error("שגיאה בטעינת מסד נתונים. וודא שלשונית users קיימת.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    user_info = st.session_state.auth
    st.sidebar.markdown(f"### שלום, {user_info['user']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT ---
    if user_info['role'] == "IT":
        st.title("🛠️ מרכז בקרה IT")
        t1, t2 = st.tabs(["👥 ניהול משתמשים", "📂 ייבוא וייצוא"])
        with t1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            u_df = load_data("users")
            if not u_df.empty:
                sel_u = st.selectbox("בחר משתמש לעריכה", u_df['username'].unique())
                idx = u_df[u_df['username'] == sel_u].index[0]
                c1, c2 = st.columns(2)
                with c1:
                    u_df.at[idx, 'role'] = st.selectbox("תפקיד", ["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"])
                with c2:
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        u_df['password'] = u_df['password'].astype(str)
                        u_df.at[idx, 'password'] = hash_pwd("123456")
                        save_to_sheet(u_df, "users")
                        st.success("הסיסמה אופסה!")
                if st.button("💾 שמור שינויים"):
                    save_to_sheet(u_df, "users")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פורטל נציג ---
    elif user_info['role'] == "נציג":
        st.title(f"👤 פורטל נציג - {user_info['user']}")
        n1, n2 = st.tabs(["📝 הגשת אילוצים", "📅 המשמרות שלי"])
        
        with n1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            init_df = pd.DataFrame([{"תאריך": str(date.today()), "התחלה": "08:00", "סיום": "16:00", "הערה": ""}])
            ed_df = st.data_editor(init_df, num_rows="dynamic", use_container_width=True)
            if st.button("שמור אילוצים"):
                c_df = load_data("constraints")
                ed_df['username'] = user_info['user']
                save_to_sheet(pd.concat([c_df, ed_df]), "constraints")
                st.success("נשמר!")
            st.markdown('</div>', unsafe_allow_html=True)

        with n2:
            st.subheader("המשמרות שפורסמו עבורך")
            sched = load_data("schedule")
            if not sched.empty and 'username' in sched.columns:
                my_shifts = sched[sched['username'].str.strip().str.lower() == user_info['user'].lower()]
                if my_shifts.empty:
                    st.info("אין משמרות כרגע.")
                else:
                    for i, r in my_shifts.iterrows():
                        st.markdown(f"""<div class="shift-card">
                            <b>תאריך:</b> {r.get('date','')} | <b>שעות:</b> {r.get('start_time','')} - {r.get('end_time','')}
                        </div>""", unsafe_allow_html=True)
                        try:
                            s = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                            e = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                            ics = create_ics("משמרת MGROUP", s, e)
                            st.download_button("➕ הוסף ליומן", ics, file_name="shift.ics", key=f"ics_{i}")
                        except: pass
            else: st.warning("גיליון schedule לא תקין או חסר עמודת username.")

    # --- דאשבורד מנהלים ---
    elif user_info['role'] in ["מנהל מוקד", "מנהל פרוייקט"]:
        st.title("📊 דאשבורד ניהולי")
        perf = load_data("performance")
        if not perf.empty:
            st.plotly_chart(px.bar(perf, x='date', y='calls', color='team', barmode='group'), use_container_width=True)
