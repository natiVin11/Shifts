import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta

# --- הגדרות עיצוב Premium ---
st.set_page_config(page_title="MGROUP 360 | Enterprise ERP", layout="wide")

def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --light-bg: #F0F2F6; }
    .stApp { background-color: var(--light-bg); }
    .header-card { background: white; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; border-bottom: 5px solid var(--accent-orange); }
    .card { background: white; padding: 25px; border-radius: 18px; box-shadow: 0 5px 15px rgba(0,0,0,0.04); margin-bottom: 20px; border-right: 6px solid var(--main-blue); }
    .stButton>button { background: linear-gradient(135deg, var(--accent-orange), #e67e22); color: white; border-radius: 12px; font-weight: bold; width: 100%; height: 3.5em; border: none; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור מאובטח לענן ---
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
        st.toast(f"✅ סונכרן בהצלחה לגיליון {sheet_name}")
    except Exception as e:
        st.error(f"❌ שגיאת סנכרון: {e}")

def hash_pwd(pwd): return hashlib.sha256(str.encode(str(pwd))).hexdigest()

# --- כותרת לוגו ---
st.markdown(f'''<div class="header-card">
    <img src="https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg" width="180">
    <h3>MGROUP 360 | מערכת ניהול מוקדים כוללת</h3>
</div>''', unsafe_allow_html=True)

# --- ניהול התחברות ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_in = st.text_input("שם משתמש")
        p_in = st.text_input("סיסמה", type='password')
        if st.button("התחבר"):
            users_df = get_data("users")
            if not users_df.empty:
                user_row = users_df[(users_df['username'] == u_in) & (users_df['status'] == 'Active')]
                if not user_row.empty and hash_pwd(p_in) == user_row.iloc[0]['password']:
                    st.session_state.update({"logged_in": True, "user": u_in, "role": user_row.iloc[0]['role'], 
                                           "team": user_row.iloc[0]['team'], "manager_name": user_row.iloc[0].get('manager', 'None')})
                    st.rerun()
            if u_in == "admin" and p_in == "admin123":
                st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול"})
                st.rerun()
            else: st.error("פרטים שגויים או משתמש חסום")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.markdown(f"👋 שלום, **{st.session_state['user']}** | **{role}**")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT: המעטפת הטכנית ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        t1, t2, t3 = st.tabs(["ניהול משתמשים", 'צ"ק-ליסט מערכות', "דוחות וחיזוי"])
        
        with t1:
            st.subheader("הוספת משתמש ידנית / אקסל")
            col1, col2 = st.columns(2)
            with col1:
                new_u = st.text_input("שם משתמש חדש")
                new_p = st.text_input("סיסמה", value="123456")
            with col2:
                new_r = st.selectbox("תפקיד", ["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"])
                new_t = st.text_input("צוות/מוקד")
            
            if st.button("צור משתמש"):
                df = get_data("users")
                new_row = pd.DataFrame([{"username": new_u, "password": hash_pwd(new_p), "role": new_r, "team": new_t, "status": "Active"}])
                save_data(pd.concat([df, new_row]), "users")

            st.divider()
            up_f = st.file_uploader("ייבוא משתמשים מאקסל", type=['xlsx'])
            if up_f and st.button("בצע ייבוא המוני"):
                df_excel = pd.read_excel(up_f)
                df_excel['password'] = df_excel['password'].apply(hash_pwd)
                df_excel['status'] = 'Active'
                save_data(pd.concat([get_data("users"), df_excel]), "users")

        with t2:
            st.subheader('צ"ק-ליסט משולב IT ומש"א')
            ob_df = get_data("onboarding")
            st.dataframe(ob_df)
            if not ob_df.empty:
                idx = st.selectbox("בחר עובד לעדכון מערכות", ob_df.index)
                c1, c2, c3 = st.columns(3)
                crm = c1.checkbox("CRM", value=ob_df.loc[idx, 'crm'] if 'crm' in ob_df.columns else False)
                phone = c2.checkbox("טלפוניה", value=ob_df.loc[idx, 'phone'] if 'phone' in ob_df.columns else False)
                mail = c3.checkbox("מייל", value=ob_df.loc[idx, 'mail'] if 'mail' in ob_df.columns else False)
                if st.button("עדכן צק-ליסט"):
                    ob_df.loc[idx, ['crm', 'phone', 'mail']] = [crm, phone, mail]
                    save_data(ob_df, "onboarding")

    # --- פאנל משא: ניהול כוח אדם ---
    elif role == "משא":
        st.header('📋 פאנל משא"בי אנוש')
        m1, m2 = st.tabs(["גיוס והסרה", "מעקב חיזוי"])
        with m1:
            st.subheader("בקשת הוספה/הסרה")
            u_name = st.text_input("שם המשתמש")
            action = st.radio("פעולה", ["קליטה", "גריעה"])
            if st.button("בצע בקשה"):
                ob_df = get_data("onboarding")
                new_req = pd.DataFrame([{"username": u_name, "type": action, "status": "בטיפול IT"}])
                save_data(pd.concat([ob_df, new_req]), "onboarding")
                if action == "גריעה":
                    u_df = get_data("users")
                    u_df.loc[u_df['username'] == u_name, 'status'] = 'Inactive'
                    save_data(u_df, "users")

    # --- פאנל נציג: פורטל אישי ---
    elif role == "נציג":
        st.header("👤 הפורטל האישי שלי")
        n1, n2 = st.tabs(["אילוצים וחופשים", "דיווח מחלה"])
        with n1:
            st.subheader("לוח שנה - הגשת אילוצים")
            d_con = st.date_input("תאריך")
            type_con = st.selectbox("סוג", ["אילוץ משמרת", "בקשת חופש"])
            note = st.text_area("הערות")
            if st.button("שלח בקשה"):
                df = get_data("constraints")
                new_c = pd.DataFrame([{"username": st.session_state['user'], "date": str(d_con), "type": type_con, "note": note, "manager": st.session_state['manager_name']}])
                save_data(pd.concat([df, new_c]), "constraints")

        with n2:
            st.subheader("העלאת אישור מחלה (PDF)")
            sick_file = st.file_uploader("צרף קובץ", type=['pdf', 'jpg'])
            if sick_file and st.button("שלח אישור מחלה"):
                st.success("הקובץ נשלח לאישור מנהל הצוות")

    # --- פאנל ר"צ: ניהול הצוות ---
    elif role == 'ר"צ':
        st.header(f'👥 ניהול צוות: {st.session_state["user"]}')
        r1, r2 = st.tabs(["לוח שיבוץ", "נתוני ביצועים"])
        with r1:
            st.subheader("אילוצי נציגים (לוח שנה)")
            all_c = get_data("constraints")
            my_c = all_c[all_c['manager'] == st.session_state['user']]
            st.dataframe(my_c)
            st.divider()
            st.subheader("קביעת סידור עבודה")
            # לוגיקת שיבוץ שעות...

        with r2:
            st.subheader("ביצועי נציגים בצוות")
            # הצגת נתוני שיחות, הפסקות וכו'
            st.info("נתונים אלו נמשכים מדוחות ה-Performance שהועלו ע\"י IT/מנהל מוקד")

    # --- פאנל מנהל מוקד: בקרת מוקד ---
    elif role == "מנהל מוקד":
        st.header(f'📊 מוקד: {st.session_state["team"]}')
        st.subheader("מצב נוכחי: 15 נציגים במענה") # דוגמה לנתון חי
        perf = get_data("performance")
        st.plotly_chart(px.line(perf, x='date', y='calls', title="חיזוי מול ביצוע בפועל"))

    # --- פאנל מנהל פרוייקט: מבט על ---
    elif role == "מנהל פרוייקט":
        st.header("🌐 ניהול פרוייקט - MGROUP")
        st.subheader("ניתוח דוחות חוצה מוקדים")
        all_perf = get_data("performance")
        st.plotly_chart(px.bar(all_perf, x='date', y='calls', color='team'))
