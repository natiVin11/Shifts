import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
import io

# --- הגדרות דף ---
st.set_page_config(page_title="MGROUP 360 | Smart ERP", layout="wide", initial_sidebar_state="expanded")

# --- עיצוב CSS מתקדם ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: RTL; text-align: right; }
    
    :root {
        --main-blue: #1A374D;
        --accent-orange: #FF8C32;
        --soft-bg: #F8F9FA;
        --card-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }

    .stApp { background-color: var(--soft-bg); }

    /* Header & Branding */
    .header-container {
        background: white;
        padding: 2rem;
        border-radius: 25px;
        box-shadow: var(--card-shadow);
        margin-bottom: 2rem;
        border-bottom: 6px solid var(--accent-orange);
        text-align: center;
    }

    /* Cards */
    .custom-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: var(--card-shadow);
        margin-bottom: 1rem;
        border-right: 5px solid var(--main-blue);
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

    /* Input Fields */
    .stTextInput>div>div>input {
        border-radius: 10px;
    }

    /* Sidebar Customization */
    [data-testid="stSidebar"] {
        background-color: var(--main-blue);
        color: white;
    }
    [data-testid="stSidebar"] * { color: white !important; }

    </style>
    """, unsafe_allow_html=True)

local_css()

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data(sheet):
    return conn.read(worksheet=sheet, ttl="5m").dropna(how='all')

def update_sheet(df, sheet):
    conn.update(worksheet=sheet, data=df.fillna(""))
    st.cache_data.clear()

def hash_password(p):
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
        user_input = st.text_input("שם משתמש").strip().lower()
        pass_input = st.text_input("סיסמה", type="password")
        
        if st.button("התחבר"):
            if user_input == "admin" and pass_input == "admin123":
                st.session_state.auth = {"logged_in": True, "user": "Admin", "role": "IT", "team": "ניהול"}
                st.rerun()
            
            users_df = load_all_data("users")
            if not users_df.empty:
                # חיפוש חכם: מתעלם מרווחים ואותיות רישיות
                users_df['username_clean'] = users_df['username'].str.strip().str.lower()
                match = users_df[(users_df['username_clean'] == user_input) & (users_df['status'] == 'Active')]
                
                if not match.empty:
                    stored_hash = match.iloc[0]['password']
                    if hash_password(pass_input) == stored_hash:
                        st.session_state.auth = {
                            "logged_in": True, 
                            "user": match.iloc[0]['username'],
                            "role": match.iloc[0]['role'],
                            "team": match.iloc[0]['team'],
                            "manager": match.iloc[0].get('manager', 'None')
                        }
                        st.rerun()
                st.error("❌ שם משתמש או סיסמה שגויים, או שהחשבון מושבת.")
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

    # --- פאנל IT (ניהול מערכת) ---
    if user_info['role'] == "IT":
        st.title("🛠️ ניהול מערכת - IT")
        t1, t2, t3 = st.tabs(["👥 ניהול משתמשים", "📂 ייבוא/ייצוא", "📋 בקשות Onboarding"])
        
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
                    u_df.at[idx, 'team'] = st.text_input("מוקד", u_df.at[idx, 'team'])
                with col2:
                    u_df.at[idx, 'status'] = st.selectbox("סטטוס", ["Active", "Inactive"], 
                                                        index=0 if u_df.at[idx, 'status'] == "Active" else 1)
                    if st.button("🔄 איפוס סיסמה ל-123456"):
                        u_df.at[idx, 'password'] = hash_password("123456")
                        update_sheet(u_df, "users")
                        st.success("הסיסמה אופסה בהצלחה!")
                
                if st.button("💾 שמור שינויי משתמש"):
                    update_sheet(u_df, "users")
                    st.success("הנתונים נשמרו!")
            st.markdown('</div>', unsafe_allow_html=True)

        with t2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("הורדת נתוני מערכת")
            curr_u = load_all_data("users")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                curr_u.to_excel(writer, index=False, sheet_name='Users')
            
            st.download_button(label="📥 הורד רשימת משתמשים (Excel)", 
                             data=output.getvalue(), 
                             file_name=f"MGROUP_Users_{datetime.now().date()}.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מש"א ---
    elif user_info['role'] == "משא":
        st.title("👥 ניהול הון אנושי")
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        new_name = st.text_input("שם עובד חדש")
        new_role = st.selectbox("תפקיד מיועד", ["נציג", "ר\"צ", "מנהל מוקד"])
        if st.button("שלח בקשת הקמה ל-IT"):
            ob_df = load_all_data("onboarding")
            new_row = pd.DataFrame([{"username": new_name, "type": "קליטה", "status": "בטיפול IT", "date": str(datetime.now().date())}])
            update_sheet(pd.concat([ob_df, new_row]), "onboarding")
            st.success("הבקשה הועברה")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל נציג ---
    elif user_info['role'] == "נציג":
        st.title(f"👋 שלום {user_info['user']}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("📅 הגשת אילוץ")
            d = st.date_input("תאריך האילוץ")
            note = st.text_area("הערה למנהל")
            if st.button("שלח אילוץ"):
                c_df = load_all_data("constraints")
                new_c = pd.DataFrame([{"username": user_info['user'], "date": str(d), "note": note, "manager": user_info.get('manager', 'None')}])
                update_sheet(pd.concat([c_df, new_c]), "constraints")
                st.balloons()
            st.markdown('</div>', unsafe_allow_html=True)

    # --- פאנל מנהלים ---
    elif user_info['role'] in ["מנהל מוקד", "מנהל פרוייקט"]:
        st.title(f"📈 דאשבורד מנהלים - {user_info['team']}")
        perf_df = load_all_data("performance")
        if not perf_df.empty:
            if user_info['role'] == "מנהל מוקד":
                perf_df = perf_df[perf_df['team'] == user_info['team']]
            
            fig = px.bar(perf_df, x='date', y='calls', color='team', title="עומס שיחות יומי", barmode='group')
            st.plotly_chart(fig, use_container_width=True)
