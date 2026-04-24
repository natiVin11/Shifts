import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Smart ERP", layout="wide")

# --- עיצוב CSS פרימיום ---
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
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(26, 55, 77, 0.3); color: var(--accent-orange); }
    [data-testid="stSidebar"] { background-color: var(--main-blue); }
    [data-testid="stSidebar"] * { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
    # המרה לטקסט למניעת שגיאות סוג נתונים (Dtype Error)
    return df.astype(str)

def save_to_sheet(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df.fillna(""))
    st.cache_data.clear()

def hash_pwd(p):
    return hashlib.sha256(str.encode(str(p))).hexdigest()

# --- לוגיקת התחברות ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None, "team": None}

def login_screen():
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.image("https://www.mgrp.co.il/wp-content/uploads/2022/04/Logo-color@1x.svg", width=200)
    st.markdown('<h1>MGROUP 360 | מערכת ניהול חכמה</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.columns([1, 1.5, 1])[1]:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        u_input = st.text_input("שם משתמש").strip().lower()
        p_input = st.text_input("סיסמה", type="password").strip()
        
        if st.button("כניסה"):
            # כניסת חירום
            if u_input == "admin" and p_input == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            users_df = load_data("users")
            if not users_df.empty:
                users_df['u_clean'] = users_df['username'].str.strip().str.lower()
                user_match = users_df[(users_df['u_clean'] == u_input) & (users_df['status'] == 'Active')]
                
                if not user_match.empty:
                    stored_password = str(user_match.iloc[0]['password']).strip()
                    if hash_pwd(p_input) == stored_password:
                        st.session_state.auth = {
                            "logged_in": True, 
                            "user": user_match.iloc[0]['username'],
                            "role": user_match.iloc[0]['role'],
                            "team": user_match.iloc[0]['team'],
                            "manager": user_match.iloc[0].get('manager', 'None')
                        }
                        st.rerun()
                st.error("❌ פרטי כניסה שגויים או משתמש שאינו פעיל.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- ניהול דפים ---
if not st.session_state.auth["logged_in"]:
    login_screen()
else:
    current_user = st.session_state.auth
    st.sidebar.markdown(f"### שלום, {current_user['user']}")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # פאנל IT
    if current_user['role'] == "IT":
        st.title("🛠️ מרכז בקרה IT")
        t1, t2, t3 = st.tabs(["👥 ניהול משתמשים", "📂 ייבוא וייצוא", "📊 ביצועים"])
        
        with t1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            u_df = load_data("users")
            if not u_df.empty:
                selected_user = st.selectbox("בחר משתמש לניהול", u_df['username'].unique())
                idx = u_df[u_df['username'] == selected_user].index[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    u_df.at[idx, 'role'] = st.selectbox("תפקיד", ["נציג", "ר\"צ", "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"], 
                                                     index=["נציג", "ר\"צ", "מנהל מוקד", "משא", "IT", "מנהל פרוייקט"].index(u_df.at[idx, 'role']))
                    u_df.at[idx, 'team'] = st.text_input("שיוך למוקד", u_df.at[idx, 'team'])
                with c2:
                    u_df.at[idx, 'status'] = st.selectbox("סטטוס", ["Active", "Inactive"], index=0 if u_df.at[idx, 'status'] == "Active" else 1)
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        # המרה כפויה למניעת שגיאת Dtype
                        u_df['password'] = u_df['password'].astype(str)
                        u_df.at[idx, 'password'] = hash_pwd("123456")
                        save_to_sheet(u_df, "users")
                        st.success(f"הסיסמה של {selected_user} אופסה!")
                
                if st.button("💾 שמור שינויים"):
                    save_to_sheet(u_df, "users")
                    st.success("הנתונים עודכנו!")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("ייצוא משתמשים")
            all_u = load_data("users")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                all_u.to_excel(writer, index=False)
            st.download_button(label="📥 הורד רשימת משתמשים (Excel)", data=buffer.getvalue(), file_name="Users.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # פאנל נציג
    elif current_user['role'] == "נציג":
        st.title(f"👤 פורטל נציג - {current_user['user']}")
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("📅 הגשת אילוץ")
        date_in = st.date_input("תאריך")
        note_in = st.text_area("פירוט")
        if st.button("שלח אילוץ"):
            c_df = load_data("constraints")
            new_c = pd.DataFrame([{"username": current_user['user'], "date": str(date_in), "note": note_in, "manager": current_user.get('manager', 'None')}])
            save_to_sheet(pd.concat([c_df, new_c]), "constraints")
            st.success("נשלח בהצלחה")
        st.markdown('</div>', unsafe_allow_html=True)

    # פאנל מנהלים
    elif current_user['role'] in ["מנהל מוקד", "מנהל פרוייקט"]:
        st.title("📊 דאשבורד ניהולי")
        perf = load_data("performance")
        if not perf.empty:
            if current_user['role'] == "מנהל מוקד":
                perf = perf[perf['team'] == current_user['team']]
            st.plotly_chart(px.line(perf, x='date', y='calls', color='team', title="מגמת שיחות"), use_container_width=True)
