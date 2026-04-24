import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- בסיס נתונים משופר ---
conn = sqlite3.connect('mgroup_full_flow.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    # משתמשים פעילים
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, team TEXT, manager TEXT, plain_password TEXT)''')
    # ניהול קליטה/גריעה (Onboarding/Offboarding)
    c.execute('''CREATE TABLE IF NOT EXISTS system_access 
                 (username TEXT PRIMARY KEY, full_name TEXT, status TEXT, 
                  crm INTEGER, telephony INTEGER, email INTEGER, active_directory INTEGER)''')
    # קבצי IT (שמות משתמשים וסיסמאות)
    c.execute('CREATE TABLE IF NOT EXISTS it_files (file_name TEXT, file_data BLOB)')
    
    # תבלאות קיימות (חיזוי, אילוצים וכו')
    c.execute('CREATE TABLE IF NOT EXISTS forecast (date TEXT, hour TEXT, required_agents INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS constraints (username TEXT, date TEXT, shift_start TEXT, shift_end TEXT, note TEXT)')
    
    # משתמש IT דיפולטיבי
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', ("admin", admin_hash, "IT", "System", "None", "admin123"))
    conn.commit()

create_tables()

# --- לוגיקת התחברות ועיצוב (מקוצר לצורך הדוגמה) ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# --- ממשק משתמש ---
if not st.session_state['logged_in']:
    st.title("MGROUP - מערכת ניהול משולבת")
    u = st.text_input("שם משתמש")
    p = st.text_input("סיסמה", type='password')
    if st.button("כניסה"):
        c.execute('SELECT password, role, team FROM users WHERE username = ?', (u,))
        data = c.fetchone()
        if data and make_hashes(p) == data[0]:
            st.session_state.update({"logged_in": True, "user": u, "role": data[1], "team": data[2]})
            st.rerun()
else:
    role = st.session_state['role']
    
    # --- פאנל מש"א: ניהול כוח אדם וחיזוי ---
    if role == "משא":
        st.header("📈 פאנל משאבי אנוש")
        t1, t2 = st.tabs(["קליטת/גריעת עובדים", "הזנת חיזוי"])
        
        with t1:
            st.subheader("בקשת הוספת עובד חדש (קורס שהסתיים)")
            new_name = st.text_input("שם מלא של העובד")
            new_u = st.text_input("שם משתמש מבוקש")
            if st.button("שלח ל-IT לפתיחת מערכות"):
                c.execute("INSERT INTO system_access VALUES (?, ?, 'קליטה', 0, 0, 0, 0)", (new_u, new_name))
                conn.commit()
                st.success(f"הבקשה עבור {new_name} הועברה לטיפול IT")
            
            st.divider()
            st.subheader("בקשת גריעת עובד (סיום העסקה)")
            active_users = pd.read_sql("SELECT username FROM users WHERE role = 'נציג'", conn)
            to_remove = st.selectbox("בחר עובד להסרה", active_users)
            if st.button("בקש חסימת משתמש מה-IT"):
                c.execute("UPDATE system_access SET status = 'גריעה' WHERE username = ?", (to_remove,))
                conn.commit()
                st.warning(f"בקשת חסימה ל-{to_remove} נשלחה")

    # --- פאנל IT: צ'ק-ליסט מערכות והעלאת קבצים ---
    elif role == "IT":
        st.header("⚙️ מרכז שליטה IT")
        t1, t2 = st.tabs(["צ'ק-ליסט מערכות", "העלאת נתוני גישה"])
        
        with t1:
            st.subheader("משימות פתיחה/סגירת מערכות")
            tasks = pd.read_sql("SELECT * FROM system_access", conn)
            for i, row in tasks.iterrows():
                with st.expander(f"עובד: {row['username']} | סטטוס: {row['status']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    crm = col1.checkbox("CRM", value=row['crm'], key=f"crm_{i}")
                    tele = col2.checkbox("טלפוניה", value=row['telephony'], key=f"tele_{i}")
                    mail = col3.checkbox("מייל", value=row['email'], key=f"mail_{i}")
                    ad = col4.checkbox("AD/רשת", value=row['active_directory'], key=f"ad_{i}")
                    
                    if st.button("עדכן סטטוס", key=f"upd_{i}"):
                        c.execute("UPDATE system_access SET crm=?, telephony=?, email=?, active_directory=? WHERE username=?", 
                                 (crm, tele, mail, ad, row['username']))
                        # אם הכל מסומן ובסטטוס קליטה - הוסף למערכת
                        if all([crm, tele, mail, ad]):
                            if row['status'] == 'קליטה':
                                c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", 
                                         (row['username'], make_hashes("123456"), "נציג", "כללי", "None", "123456"))
                                st.success("העובד הוסף למערכת המשמרות!")
                            elif row['status'] == 'גריעה':
                                c.execute("DELETE FROM users WHERE username = ?", (row['username'],))
                                st.error("העובד הוסר ממערכת המשמרות!")
                        conn.commit()

        with t2:
            st.subheader("העלאת קובץ ריכוז משתמשים למנהלים")
            up_file = st.file_uploader("בחר קובץ (CSV/Excel)", type=['csv', 'xlsx'])
            if up_file and st.button("פרסם קובץ למנהלים"):
                c.execute("INSERT INTO it_files VALUES (?, ?)", (up_file.name, up_file.getvalue()))
                conn.commit()
                st.success("הקובץ פורסם בהצלחה")

    # --- פאנל ר"צ ומנהל מוקד: צפייה בנתונים ---
    elif role in ["ר\"צ", "מנהל מוקד"]:
        st.header("📋 פאנל ניהול")
        with st.expander("🔑 רשימת שמות משתמשים וסיסמאות (IT)"):
            it_data = pd.read_sql("SELECT file_name, file_data FROM it_files", conn)
            if not it_data.empty:
                last_file = it_data.iloc[-1]
                st.download_button(f"הורד קובץ: {last_file['file_name']}", last_file['file_data'], file_name=last_file['file_name'])
            else:
                st.info("טרם הועלה קובץ ע\"י ה-IT")
