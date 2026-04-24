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
    
    :root {
        --main-blue: #1A374D;
        --accent-orange: #FF8C32;
        --soft-bg: #F8F9FA;
    }

    .stApp { background-color: var(--soft-bg); }

    /* Header */
    .header-container {
        background: white;
        padding: 2rem;
        border-radius: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
        border-bottom: 6px solid var(--accent-orange);
        text-align: center;
    }

    /* Cards */
    .custom-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border-right: 6px solid var(--main-blue);
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, var(--main-blue), #2c5d81);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.6rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(26, 55, 77, 0.3);
        color: var(--accent-orange);
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: var(--main-blue); }
    [data-testid="stSidebar"] * { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    # ttl=0 מבטיח משיכת נתונים טריים מהגיליון בכל פעם
    return conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')

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
            # כניסת חירום למנהל מערכת
            if u_input == "admin" and p_input == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            users_df = load_data("users")
            if not users_df.empty:
                # השוואה חכמה (מתעלמת מרווחים ואותיות רישיות בגיליון)
                users_df['u_clean'] = users_df['username'].astype(str).str.strip().str.lower()
                user_match = users_df[(users_df['u_clean'] == u_input) & (users_df['status'] == 'Active')]
                
                if not user_match.empty:
                    stored_password = str(user_match.iloc[0]['password']).strip()
                    # בדיקה אם הסיסמה בגיליון מוצפנת או גלויה (לצורך הגנה)
                    if hash_pwd(p_input) == stored_password:
                        st.session_state.auth = {
                            "logged_in": True, 
                            "user": user_match.iloc[0]['username'],
                            "role": user_match.iloc[0]['role'],
                            "team": user_match.iloc[0]['team'],
                            "manager": user_match.iloc[0].get('manager', 'None')
                        }
                        st.rerun()
                    elif p_input == stored_password:
                        st.error("⚠️ אבטחה: הסיסמה בגיליון אינה מוצפנת. היכנס כאדמין ובצע איפוס סיסמה.")
                        st.stop()
                
                st.error("❌ פרטי כניסה שגויים או משתמש שאינו פעיל.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- ניהול דפים ---
if not st.session_state.auth["logged_in"]:
    login_screen()
else:
    current_user = st.session_state.auth
    st.sidebar.markdown(f"### שלום, {current_user['user']}")
    st.sidebar.write(f"תפקיד: {current_user['role']}")
    if st.sidebar.button("🚪 התנתק מהמערכת"):
        st.session_state.auth = {"logged_in": False}
        st.rerun()

    # --- פאנל IT (ניהול משתמשים והגדרות) ---
    if current_user['role'] == "IT":
        st.title("🛠️ מרכז בקרה IT")
        t1, t2, t3 = st.tabs(["👥 ניהול משתמשים", "📂 ייבוא וייצוא", "📊 מעקב ביצועים"])
        
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
                    u_df.at[idx, 'team'] = st.text_input("שיוך למוקד/צוות", u_df.at[idx, 'team'])
                with c2:
                    u_df.at[idx, 'status'] = st.selectbox("סטטוס חשבון", ["Active", "Inactive"], 
                                                        index=0 if u_df.at[idx, 'status'] == "Active" else 1)
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        u_df.at[idx, 'password'] = hash_pwd("123456")
                        save_to_sheet(u_df, "users")
                        st.success(f"הסיסמה של {selected_user} אופסה בהצלחה!")
                
                if st.button("💾 שמור שינויים"):
                    save_to_sheet(u_df, "users")
                    st.success("הנתונים עודכנו ב-Google Sheets")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("ייצוא נתונים")
            all_users = load_data("users")
            
            # הכנת קובץ אקסל להורדה
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                all_users.to_excel(writer, index=False, sheet_name='Users_List')
            
            st.download_button(
                label="📥 הורד רשימת משתמשים מלאה (Excel)",
                data=buffer.getvalue(),
                file_name=f"MGROUP_Users_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל נציג (אילוצים) ---
    elif current_user['role'] == "נציג":
        st.title(f"👤 פורטל נציג - {current_user['user']}")
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("📅 הגשת אילוץ חדש")
        date_sel = st.date_input("תאריך")
        reason = st.text_area("פירוט האילוץ")
        if st.button("שלח לאישור מנהל"):
            c_df = load_data("constraints")
            new_entry = pd.DataFrame([{"username": current_user['user'], "date": str(date_sel), "note": reason, "manager": current_user.get('manager', 'None')}])
            save_to_sheet(pd.concat([c_df, new_entry]), "constraints")
            st.balloons()
            st.success("האילוץ נשלח בהצלחה")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהלים (BI) ---
    elif current_user['role'] in ["מנהל מוקד", "מנהל פרוייקט"]:
        st.title(f"📊 דאשבורד מנהלים - {current_user['team']}")
        perf = load_data("performance")
        if not perf.empty:
            if current_user['role'] == "מנהל מוקד":
                perf = perf[perf['team'] == current_user['team']]
            
            fig = px.line(perf, x='date', y='calls', color='team', title="מגמת שיחות יומית", markers=True)
            st.plotly_chart(fig, use_container_width=True)
