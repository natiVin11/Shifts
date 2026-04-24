import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Smart ERP", layout="wide")

# --- עיצוב CSS משודרג ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    :root { --main-blue: #1A374D; --accent-orange: #FF8C32; --soft-bg: #F8F9FA; }
    .stApp { background-color: var(--soft-bg); }
    .header-container { background: white; padding: 2rem; border-radius: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 6px solid var(--accent-orange); text-align: center; }
    .custom-card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 1rem; border-right: 5px solid var(--main-blue); }
    .stButton>button { background: linear-gradient(135deg, var(--main-blue), #2c5d81); color: white; border-radius: 10px; border: none; padding: 0.6rem 1rem; font-weight: 600; width: 100%; transition: 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(26, 55, 77, 0.3); }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data(sheet):
    # ttl=0 מבטיח משיכת נתונים טריים בכל פעם כדי למנוע בעיות סנכרון
    return conn.read(worksheet=sheet, ttl=0).dropna(how='all')

def update_sheet(df, sheet):
    conn.update(worksheet=sheet, data=df.fillna(""))
    st.cache_data.clear()

def hash_password(p):
    # המרה ל-string לפני ה-hash כדי למנוע שגיאות עם סיסמאות מספריות
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- לוגיקת התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

def login_ui():
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.image("https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg", width=200)
    st.markdown('<h2>כניסה למערכת MGROUP 360</h2>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.columns([1,1.5,1])[1]:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        # ניקוי רווחים מהקלט של המשתמש
        user_input = st.text_input("שם משתמש").strip().lower()
        pass_input = st.text_input("סיסמה", type="password").strip()
        
        if st.button("התחבר"):
            # כניסת חירום של אדמין
            if user_input == "admin" and pass_input == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            users_df = load_all_data("users")
            if not users_df.empty:
                # הכנת הטבלה להשוואה חכמה (ניקוי רווחים והפיכה לאותיות קטנות)
                users_df['username_clean'] = users_df['username'].astype(str).str.strip().str.lower()
                
                match = users_df[(users_df['username_clean'] == user_input) & (users_df['status'] == 'Active')]
                
                if not match.empty:
                    stored_hash = str(match.iloc[0]['password']).strip()
                    if hash_password(pass_input) == stored_hash:
                        st.session_state.auth = {
                            "logged_in": True, 
                            "user": match.iloc[0]['username'],
                            "role": match.iloc[0]['role'],
                            "team": match.iloc[0]['team'],
                            "manager": match.iloc[0].get('manager', 'None')
                        }
                        st.success("מתחבר...")
                        st.rerun()
                st.error("❌ פרטי כניסה שגויים. וודא שהמשתמש פעיל בגיליון (Active).")
        st.markdown('</div>', unsafe_allow_html=True)

# --- דף הבית ומערכת ניהול ---
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    user_info = st.session_state.auth
    st.sidebar.markdown(f"### שלום, {user_info['user']}")
    st.sidebar.write(f"🎭 תפקיד: {user_info['role']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT ---
    if user_info['role'] == "IT":
        st.title("🛠️ ניהול מערכת - IT")
        t1, t2 = st.tabs(["👥 ניהול משתמשים", "📂 ייבוא/ייצוא"])
        
        with t1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            u_df = load_all_data("users")
            if not u_df.empty:
                sel_user = st.selectbox("בחר משתמש לעריכה", u_df['username'].unique())
                idx = u_df[u_df['username'] == sel_user].index[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    u_df.at[idx, 'role'] = st.selectbox("תפקיד", ["נציג", "ר\"צ", "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"], 
                                                     index=["נציג", "ר\"צ", "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"].index(u_df.at[idx, 'role']))
                with col2:
                    u_df.at[idx, 'status'] = st.selectbox("סטטוס", ["Active", "Inactive"], 
                                                        index=0 if u_df.at[idx, 'status'] == "Active" else 1)
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        u_df.at[idx, 'password'] = hash_password("123456")
                        update_sheet(u_df, "users")
                        st.success("סיסמה אופסה!")
                
                if st.button("💾 שמור שינויים"):
                    update_sheet(u_df, "users")
                    st.success("נשמר בהצלחה!")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            curr_u = load_all_data("users")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                curr_u.to_excel(writer, index=False)
            st.download_button(label="📥 הורד רשימת משתמשים (Excel)", data=output.getvalue(), file_name="Users.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנלים אחרים (נציג/משא) נשארים לפי הלוגיקה הקודמת ---
    else:
        st.info("ברוך הבא למערכת MGROUP. הפאנל שלך בבנייה.")
