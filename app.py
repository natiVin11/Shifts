import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar
import pandas as pd
import hashlib
from datetime import datetime, date, time
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Enterprise System", layout="wide")

# --- פונקציות עזר (ICS, Hash, ניהול נתונים) ---
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
    # שומר רק אם ה-DataFrame אינו ריק כדי למנוע דריסה בטעות
    if not df.empty:
        conn.update(worksheet=sheet, data=df.fillna(""))
        st.cache_data.clear()

# --- ניהול התחברות חכם ---
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
                    # מנגנון: מאפשר כניסה גם עם טקסט גלוי וגם עם מוצפן
                    if p_in == stored_p or hash_pwd(p_in) == stored_p:
                        # הצפנה אוטומטית אם המשתמש נכנס עם סיסמה גלויה
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
    user_info = st.session_state.auth
    st.sidebar.title(f"שלום, {user_info['user']}")
    st.sidebar.write(f"תפקיד: {user_info['role']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT: ניהול משתמשים מלא ---
    if user_info['role'] == "IT":
        st.title("🛠️ ניהול מערכת (IT)")
        t1, t2, t3 = st.tabs(["👥 ניהול משתמשים", "📂 ייצוא/ייבוא", "📉 ביצועים"])
        with t1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            u_df = load_data("users")
            # עורך טבלה שמאפשר לשנות הכל (כולל הוספת שורות)
            edited_users = st.data_editor(u_df, num_rows="dynamic", use_container_width=True)
            if st.button("שמור שינויים ביוזרים"):
                save_data(edited_users, "users")
                st.success("השינויים נשמרו ב-Google Sheets!")
            st.markdown('</div>', unsafe_allow_html=True)
        with t2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                u_df.to_excel(writer, index=False)
            st.download_button("📥 הורד רשימת משתמשים (Excel)", buffer.getvalue(), file_name="mgroup_users.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהל מוקד: ניהול סידור ---
    elif user_info['role'] == "מנהל מוקד":
        st.title(f"📊 מנהל מוקד: {user_info['team']}")
        m1, m2 = st.tabs(["📅 ניהול סידור", "📝 אילוצי נציגים"])
        with m1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            sched = load_data("schedule")
            # מציג רק את המשמרות של המוקד שלו
            my_team_sched = sched[sched['team'] == user_info['team']]
            edited_sched = st.data_editor(my_team_sched, num_rows="dynamic", use_container_width=True)
            if st.button("פרסם סידור מעודכן"):
                # שילוב הסידור הערוך עם שאר המוקדים
                final_sched = pd.concat([sched[sched['team'] != user_info['team']], edited_sched])
                save_data(final_sched, "schedule")
                st.success("הסידור פורסם!")
            st.markdown('</div>', unsafe_allow_html=True)
        with m2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.write("אילוצים שהוגשו על ידי נציגי המוקד:")
            st.dataframe(load_data("constraints"))
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל נציג: לוח שנה ואילוצים ---
    elif user_info['role'] == "נציג":
        st.header(f"👤 פורטל נציג: {user_info['user']}")
        
        my_shifts = pd.DataFrame()
        events = []
        sched_df = load_data("schedule")
        
        if not sched_df.empty and 'username' in sched_df.columns:
            my_shifts = sched_df[sched_df['username'].str.lower() == user_info['user'].lower()]
            for i, r in my_shifts.iterrows():
                events.append({
                    "title": f"משמרת: {r.get('start_time')}-{r.get('end_time')}",
                    "start": r.get('date'),
                    "end": r.get('date'),
                    "color": "#28a745",
                    "allDay": True
                })

        col_cal, col_form = st.columns([2, 1])
        
        with col_cal:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            res = calendar(events=events, options={"initialView": "dayGridMonth", "direction": "rtl"}, key="agent_cal")
            if res.get("callback") == "dateClick":
                st.session_state.selected_date = res["dateClick"]["date"]
            st.markdown('</div>', unsafe_allow_html=True)

        with col_form:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("הגשת אילוץ")
            sel_d = st.session_state.get('selected_date', str(date.today()))
            st.info(f"תאריך נבחר: **{sel_d}**")
            s_t = st.time_input("שעת התחלה", time(8, 0))
            e_t = st.time_input("שעת סיום", time(16, 0))
            note = st.text_input("הערה (חופש/אירוע)")
            
            if st.button("שמור אילוץ"):
                c_df = load_data("constraints")
                new_c = pd.DataFrame([{"username": user_info['user'], "date": sel_d, "start_time": s_t.strftime("%H:%M"), "end_time": e_t.strftime("%H:%M"), "note": note}])
                save_data(pd.concat([c_df, new_c]), "constraints")
                st.success("האילוץ נשמר!")
            
            if not my_shifts.empty:
                st.divider()
                st.subheader("הורד ליומן (ICS)")
                for i, r in my_shifts.iterrows():
                    try:
                        s_dt = datetime.strptime(f"{r['date']} {r['start_time']}", "%Y-%m-%d %H:%M")
                        e_dt = datetime.strptime(f"{r['date']} {r['end_time']}", "%Y-%m-%d %H:%M")
                        ics = create_ics("משמרת MGROUP", s_dt, e_dt)
                        st.download_button(f"📅 {r['date']}", ics, file_name=f"shift_{r['date']}.ics", key=f"dl_{i}")
                    except: pass
            st.markdown('</div>', unsafe_allow_html=True)
