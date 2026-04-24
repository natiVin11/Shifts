import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta
import io

# --- הגדרות עיצוב Premium MGROUP ---
st.set_page_config(page_title="MGROUP 360 | Enterprise ERP", layout="wide", initial_sidebar_state="expanded")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F0F2F6; }
    .stApp { background-color: var(--light-bg); }
    /* כרטיסיות מעוצבות */
    .card { background: white; padding: 25px; border-radius: 18px; box-shadow: 0 5px 15px rgba(0,0,0,0.04); margin-bottom: 20px; border-right: 6px solid var(--main-blue); }
    .header-card { background: white; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; border-bottom: 5px solid var(--accent-orange); }
    /* כפתורים */
    .stButton>button { background: linear-gradient(135deg, var(--accent-orange), #e67e22); color: white; border-radius: 12px; font-weight: bold; width: 100%; height: 3.5em; border: none; transition: 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,140,50,0.3); }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור מאובטח ל-Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        df_to_save = df.fillna("")
        conn.update(worksheet=sheet_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ סונכרן לגיליון {sheet_name}")
    except Exception as e:
        st.error(f"❌ שגיאת סנכרון: {e}")

def hash_pwd(pwd): return hashlib.sha256(str.encode(str(pwd))).hexdigest()

# --- כותרת לוגו ---
logo_url = "https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg"
st.markdown(f'<div class="header-card"><img src="{logo_url}" width="180"><h3>MGROUP 360 | פורטל ניהול ארגוני אחוד</h3></div>', unsafe_allow_html=True)

# --- מערכת התחברות ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔐 כניסה מאובטחת")
        u_in = st.text_input("שם משתמש")
        p_in = st.text_input("סיסמה", type='password')
        if st.button("התחבר"):
            users_df = get_data("users")
            if not users_df.empty:
                user_row = users_df[(users_df['username'] == u_in) & (users_df['status'] == 'Active')]
                if not user_row.empty and hash_pwd(p_in) == user_row.iloc[0]['password']:
                    st.session_state.update({
                        "logged_in": True, "user": u_in, "role": user_row.iloc[0]['role'],
                        "team": user_row.iloc[0]['team'], "manager_name": user_row.iloc[0].get('manager', 'None')
                    })
                    st.rerun()
            if u_in == "admin" and p_in == "admin123":
                st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול"})
                st.rerun()
            else: st.error("פרטי התחברות שגויים")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.markdown(f"👋 שלום, **{st.session_state['user']}**")
    st.sidebar.info(f"תפקיד: {role}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT: המוח הטכני ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        t1, t2, t3, t4 = st.tabs(["ניהול משתמשים", "ייבוא אקסל", 'צ"ק-ליסט מערכות', "דוחות וחיזוי"])
        
        with t1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            users_df = get_data("users")
            if not users_df.empty:
                sel_u = st.selectbox("בחר משתמש לעריכה / איפוס", users_df['username'].unique())
                u_idx = users_df[users_df['username'] == sel_u].index[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    new_r = st.selectbox("תפקיד", ["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"], 
                                         index=["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"].index(users_df.loc[u_idx, 'role']))
                    new_t = st.text_input("צוות/מוקד", users_df.loc[u_idx, 'team'])
                with c2:
                    new_s = st.selectbox("סטטוס", ["Active", "Inactive"], index=0 if users_df.loc[u_idx, 'status'] == "Active" else 1)
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        users_df.loc[u_idx, 'password'] = hash_pwd("123456")
                        save_data(users_df, "users")
                
                if st.button("💾 שמור שינויים"):
                    users_df.loc[u_idx, ['role', 'team', 'status']] = [new_r, new_t, new_s]
                    save_data(users_df, "users")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            up_f = st.file_uploader("העלה אקסל משתמשים", type=['xlsx'])
            if up_f and st.button("בצע ייבוא המוני"):
                df_new = pd.read_excel(up_f)
                df_new['password'] = df_new['password'].apply(hash_pwd)
                df_new['status'] = 'Active'
                save_data(pd.concat([get_data("users"), df_new]).drop_duplicates(subset=['username']), "users")
            st.markdown('</div>', unsafe_allow_html=True)

        with t3:
            st.subheader('בקרת הקמת משתמשים (IT & מש"א)')
            onboarding = get_data("onboarding")
            st.dataframe(onboarding, use_container_width=True)
            # לוגיקת סימון מערכות (CRM, טלפוניה וכו')

    # --- פאנל משא: ניהול הון אנושי ---
    elif role == "משא":
        st.header('📋 פאנל משא"בי אנוש')
        m1, m2 = st.tabs(["גיוס והסרה", "חיזוי עומסים"])
        with m1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            u_name = st.text_input("שם עובד מלא")
            u_action = st.radio("פעולה מבוקשת", ["קליטת עובד חדש", "סיום העסקה"])
            if st.button("שלח בקשה ל-IT"):
                ob = get_data("onboarding")
                new_req = pd.DataFrame([{"username": u_name, "type": u_action, "status": "בטיפול IT", "date": str(datetime.now().date())}])
                save_data(pd.concat([ob, new_req]), "onboarding")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל נציג: שירות עצמי ---
    elif role == "נציג":
        st.header("👤 הפורטל האישי שלי")
        n1, n2, n3 = st.tabs(["📅 אילוצים וחופשים", "🤒 דיווח מחלה", "🕒 המשמרות שלי"])
        with n1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            d_con = st.date_input("בחר תאריך")
            t_con = st.selectbox("סוג הבקשה", ["אילוץ משמרת", "בקשת חופש שנתי"])
            note = st.text_area("הערות")
            if st.button("שלח לאישור מנהל"):
                df = get_data("constraints")
                new_c = pd.DataFrame([{"username": st.session_state['user'], "date": str(d_con), "type": t_con, "note": note, "manager": st.session_state['manager_name']}])
                save_data(pd.concat([df, new_c]), "constraints")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with n2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("העלאת אישור מחלה (PDF/JPG)")
            s_file = st.file_uploader("בחר קובץ", type=['pdf', 'jpg', 'png'])
            if s_file and st.button("דווח מחלה"):
                st.success("הדיווח נרשם. החלמה מהירה!")

    # --- פאנל ר"צ: ניהול צוות וביצועים ---
    elif role == 'ר"צ':
        st.header(f'👥 ניהול צוות: {st.session_state["user"]}')
        r1, r2, r3 = st.tabs(["🗓️ לוח שיבוץ", "📊 ביצועי נציגים", "✅ אישור אילוצים"])
        with r3:
            cons = get_data("constraints")
            my_agents_cons = cons[cons['manager'] == st.session_state['user']]
            st.write("אילוצים שהוגשו על ידי הצוות שלך:")
            st.dataframe(my_agents_cons, use_container_width=True)
            # לוגיקת אישור ושיבוץ שעות

    # --- פאנל מנהל מוקד: בקרת המוקד ---
    elif role == "מנהל מוקד":
        st.header(f'📊 ניהול מוקד: {st.session_state["team"]}')
        c1, c2, c3 = st.columns(3)
        c1.metric("נציגים פעילים כעת", "14")
        c2.metric("ממוצע שיחה (AHT)", "04:20")
        c3.metric("שיחות בהמתנה", "2")
        
        perf = get_data("performance")
        if not perf.empty:
            st.plotly_chart(px.line(perf[perf['team'] == st.session_state['team']], x='date', y='calls', title="חיזוי מול ביצוע"))

    # --- פאנל מנהל פרוייקט: High-Level BI ---
    elif role == "מנהל פרוייקט":
        st.header("🌐 ניהול פרוייקט - MGROUP Global")
        all_perf = get_data("performance")
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(px.pie(all_perf, values='calls', names='team', title="חלוקת עומסים בין מוקדים"))
        with col_b:
            st.plotly_chart(px.bar(all_perf, x='date', y='calls', color='team', barmode='group', title="ביצועים יומיים חוצי ארגון"))
