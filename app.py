import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import io

# --- הגדרות עיצוב MGROUP 360 ---
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
        st.toast(f"✅ סונכרן לגיליון {sheet_name}")
    except Exception as e:
        st.error(f"❌ שגיאת סנכרון: {e}")

def hash_pwd(pwd): return hashlib.sha256(str.encode(str(pwd))).hexdigest()

# --- פונקציית ייצוא לאקסל (מתוקנת) ---
def to_excel(df):
    output = io.BytesIO()
    # שימוש ב-openpyxl כברירת מחדל שהיא נפוצה יותר
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Users_List')
    return output.getvalue()

# --- כותרת לוגו ---
st.markdown(f'''<div class="header-card">
    <img src="https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg" width="180">
    <h3>MGROUP 360 | מערכת ניהול מוקדים אחודה</h3>
</div>''', unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# --- לוגיקת כניסה ---
if not st.session_state['logged_in']:
    with st.columns([1,1.2,1])[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_in = st.text_input("שם משתמש")
        p_in = st.text_input("סיסמה", type='password')
        if st.button("כניסה למערכת"):
            u_df = get_data("users")
            if not u_df.empty:
                # סינון משתמש פעיל בלבד
                user_row = u_df[(u_df['username'] == u_in) & (u_df['status'] == 'Active')]
                if not user_row.empty and hash_pwd(p_in) == user_row.iloc[0]['password']:
                    st.session_state.update({
                        "logged_in": True, "user": u_in, 
                        "role": user_row.iloc[0]['role'], 
                        "team": user_row.iloc[0]['team'], 
                        "manager_name": user_row.iloc[0].get('manager', 'None')
                    })
                    st.rerun()
            if u_in == "admin" and p_in == "admin123":
                st.session_state.update({"logged_in": True, "user": "admin", "role": "IT", "team": "ניהול", "manager_name": "None"})
                st.rerun()
            else: st.error("פרטים שגויים או משתמש מושבת")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    role = st.session_state['role']
    st.sidebar.markdown(f"👋 שלום, **{st.session_state['user']}**")
    if st.sidebar.button("🚪 יציאה"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- פאנל IT ---
    if role == "IT":
        st.header("⚙️ מרכז בקרה IT")
        t = st.tabs(["ניהול ועריכה", "ייבוא וייצוא", "צ'ק-ליסט מערכות", "דוחות"])
        
        with t[0]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            u_df = get_data("users")
            if not u_df.empty:
                sel_u = st.selectbox("בחר משתמש לעריכה", u_df['username'].unique())
                idx = u_df[u_df['username'] == sel_u].index[0]
                c1, c2 = st.columns(2)
                with c1:
                    u_df.loc[idx, 'role'] = st.selectbox("תפקיד", ["נציג", 'ר"צ', "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"])
                    u_df.loc[idx, 'team'] = st.text_input("צוות", u_df.loc[idx, 'team'])
                with c2:
                    u_df.loc[idx, 'status'] = st.selectbox("סטטוס", ["Active", "Inactive"], index=0 if u_df.loc[idx, 'status'] == "Active" else 1)
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        u_df.loc[idx, 'password'] = hash_pwd("123456")
                        save_data(u_df, "users")
                if st.button("💾 שמור שינויים"):
                    save_data(u_df, "users")
            st.markdown('</div>', unsafe_allow_html=True)

        with t[1]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("ייבוא משתמשים")
            up = st.file_uploader("העלה אקסל לייבוא", type=['xlsx'])
            if up and st.button("בצע ייבוא המוני"):
                new_u = pd.read_excel(up)
                new_u['password'] = new_u['password'].apply(lambda x: hash_pwd(str(x)))
                new_u['status'] = 'Active'
                save_data(pd.concat([get_data("users"), new_u]).drop_duplicates(subset=['username']), "users")
            
            st.divider()
            st.subheader("ייצוא משתמשים")
            curr_u = get_data("users")
            if not curr_u.empty:
                try:
                    excel_out = to_excel(curr_u)
                    st.download_button(
                        label="📥 הורד רשימת משתמשים וסיסמאות (Excel)",
                        data=excel_out,
                        file_name=f"mgroup_users_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"שגיאה בהכנת הקובץ: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

        with t[2]:
            st.subheader("בקשות הקמה (מול מש\"א)")
            ob = get_data("onboarding")
            st.data_editor(ob, key="it_ob_editor", on_change=lambda: save_data(st.session_state.it_ob_editor, "onboarding"))

    # --- פאנל משא ---
    elif role == "משא":
        st.header('📋 פאנל משא"בי אנוש')
        t = st.tabs(["גיוס והסרה", "מעקב צ'ק-ליסט"])
        with t[0]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            u_name = st.text_input("שם העובד")
            action = st.radio("פעולה", ["קליטה", "גריעה"])
            if st.button("שלח בקשה ל-IT"):
                df = get_data("onboarding")
                new_r = pd.DataFrame([{"username": u_name, "type": action, "status": "בטיפול IT", "crm": False, "phone": False, "mail": False}])
                save_data(pd.concat([df, new_r]), "onboarding")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל נציג ---
    elif role == "נציג":
        st.header("👤 הפורטל האישי שלי")
        t = st.tabs(["אילוצים וחופשים", "דיווח מחלה"])
        with t[0]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            d = st.date_input("תאריך")
            tp = st.selectbox("סוג", ["אילוץ משמרת", "בקשת חופש"])
            note = st.text_area("הערה")
            if st.button("שלח אילוץ"):
                df = get_data("constraints")
                new_c = pd.DataFrame([{"username": st.session_state['user'], "date": str(d), "type": tp, "note": note, "manager": st.session_state['manager_name']}])
                save_data(pd.concat([df, new_c]), "constraints")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל ר"צ ---
    elif role == 'ר"צ':
        st.header(f'👥 ניהול צוות: {st.session_state["user"]}')
        t = st.tabs(["לוח שיבוץ", "אילוצי הצוות"])
        with t[1]:
            all_c = get_data("constraints")
            st.dataframe(all_c[all_c['manager'] == st.session_state['user']])

    # --- פאנל מנהל מוקד ---
    elif role == "מנהל מוקד":
        st.header(f'📊 מוקד: {st.session_state["team"]}')
        perf = get_data("performance")
        if not perf.empty:
            st.plotly_chart(px.line(perf[perf['team'] == st.session_state['team']], x='date', y='calls', title="חיזוי מול ביצוע"))

    # --- פאנל מנהל פרוייקט ---
    elif role == "מנהל פרוייקט":
        st.header("🌐 ניהול פרוייקט - MGROUP Global")
        perf = get_data("performance")
        if not perf.empty:
            col1, col2 = st.columns(2)
            with col1: st.plotly_chart(px.pie(perf, values='calls', names='team', title="חלוקת עומס"))
            with col2: st.plotly_chart(px.bar(perf, x='date', y='calls', color='team', title="ניתוח חוצה ארגון"))
