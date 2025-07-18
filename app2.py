import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import shutil
import os
import time
import hashlib

EXCEL_FILE = 'leave_tracker.xlsx'
LOCK_FILE = EXCEL_FILE + ".lock"
COLUMNS = ['Name of employee', 'Leave Type', 'start Date', 'end Date', 'Workday approved']

# ---------------- Helper Functions ----------------

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df['start Date'] = pd.to_datetime(df['start Date'])
        df['end Date'] = pd.to_datetime(df['end Date'])
        return df
    else:
        return pd.DataFrame(columns=COLUMNS)

def acquire_lock(timeout=5):
    start = time.time()
    while os.path.exists(LOCK_FILE):
        if time.time() - start > timeout:
            return False
        time.sleep(0.2)
    with open(LOCK_FILE, "w") as f:
        f.write("locked")
    return True

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def save_data(df):
    if not acquire_lock():
        st.error("Another user is currently saving. Please wait and try again.")
        return

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            df.to_excel(tmp.name, index=False)
            shutil.copy(tmp.name, EXCEL_FILE)
        os.remove(tmp.name)
    finally:
        release_lock()

def add_entry(df, name, leave_type, start_date, end_date):
    new_row = {
        'Name of employee': name,
        'Leave Type': leave_type,
        'start Date': pd.to_datetime(start_date),
        'end Date': pd.to_datetime(end_date),
        'Workday approved': False
    }
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

def get_unique_key(row, prefix):
    row_str = str(row.to_dict())
    return f"{prefix}_{hashlib.md5(row_str.encode()).hexdigest()}"

# ---------------- Streamlit App ----------------

st.set_page_config(page_title="Team Leave Tracker", layout="wide")
st.title("📅 Team Leave Tracker")

df = load_data()
tab_today, tab_pending, tab_history = st.tabs(["📍 Today", "🕒 Pending", "📜 History"])

# ---------------- TODAY TAB ----------------

with tab_today:
    st.subheader("Today's Leaves")
    today = pd.to_datetime(datetime.today().date())
    today_df = df[(df['start Date'] <= today) & (df['end Date'] >= today)]

    pending_today = today_df[today_df['Workday approved'] == False]
    approved_today = today_df[today_df['Workday approved'] == True]

    st.markdown("### 🔴 Pending Approvals for Today")
    for i, row in pending_today.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(row[col_name])
        toggle_key = get_unique_key(row, "today_pending")
        approved = cols[-1].toggle("✔️", value=False, key=toggle_key)
        if approved:
            df.at[i, 'Workday approved'] = True
            save_data(df)
            st.rerun()

    st.markdown("### ✅ Approved Leaves for Today")
    for i, row in approved_today.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(row[col_name])
        toggle_key = get_unique_key(row, "today_approved")
        approved = cols[-1].toggle("✔️", value=True, key=toggle_key)
        if not approved:
            df.at[i, 'Workday approved'] = False
            save_data(df)
            st.rerun()

# ---------------- PENDING TAB ----------------

with tab_pending:
    st.subheader("Pending Leaves (Not Approved in Workday)")

    # --- Add New Entry ---
    with st.expander("➕ Add New Leave Request"):
        # Build name dropdown from existing names or fallback list
        known_names = sorted(set(df['Name of employee'].dropna().tolist() + ['Alice', 'Bob', 'Charlie']))
        name = st.selectbox("Employee Name", known_names)
        leave_type = st.selectbox("Leave Type", ["Personal", "Medical", "Work"])
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", datetime.today())
        end_date = col2.date_input("End Date", datetime.today())

        if start_date > end_date:
            st.warning("End date must be on or after start date.")
        else:
            if st.button("Add"):
                df = add_entry(df, name, leave_type, start_date, end_date)
                save_data(df)
                st.success("Leave request added!")
                st.rerun()

    # --- Show Pending Rows ---
    pending_df = df[df['Workday approved'] == False]
    updated = False

    for i, row in pending_df.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(row[col_name])
        toggle_key = get_unique_key(row, "pending")
        approved = cols[-1].toggle("✔️", value=False, key=toggle_key)
        if approved:
            df.at[i, 'Workday approved'] = True
            updated = True

    if updated:
        save_data(df)
        st.rerun()

# ---------------- HISTORY TAB ----------------

with tab_history:
    st.subheader("Leave History (All Entries)")

    for i, row in df.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(row[col_name])
        toggle_key = get_unique_key(row, "history")
        approved = cols[-1].toggle("✔️", value=bool(row['Workday approved']), key=toggle_key)
        if approved != row['Workday approved']:
            df.at[i, 'Workday approved'] = approved
            save_data(df)
            st.rerun()
