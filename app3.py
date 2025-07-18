import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import shutil
import os
import time
import hashlib
import win32com.client as win32

EXCEL_FILE = 'leave_tracker.xlsx'
LOCK_FILE = EXCEL_FILE + ".lock"
COLUMNS = ['Name of employee', 'Leave Type', 'start Date', 'end Date', 'Workday approved']

EMAIL_LOOKUP = {
    "Alice": "alice@example.com",
    "Bob": "bob@example.com",
    "Charlie": "charlie@example.com"
}

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

def format_date(date):
    return date.strftime("%b %d, %Y")

def send_outlook_email(to_address, subject, body):
    try:
        outlook = win32.Dispatch('outlook.application')
        mail = outlook.CreateItem(0)
        mail.To = to_address
        mail.Subject = subject
        mail.Body = body
        mail.Send()
        st.success(f"Email sent to {to_address}")
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")

def download_filtered_df(filtered_df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        filtered_df.to_excel(tmp.name, index=False)
        with open(tmp.name, 'rb') as f:
            st.download_button("📤 Download Filtered Data as Excel", f, file_name="leave_data_filtered.xlsx")
        os.remove(tmp.name)

# ---------------- Streamlit App ----------------

st.set_page_config(page_title="Team Leave Tracker", layout="wide")
st.title("📅 Team Leave Tracker")

df = load_data()

# ---------------- Filter Section ----------------
with st.sidebar:
    st.header("🔍 Filters")
    employee_filter = st.selectbox("Filter by Employee", ["All"] + sorted(df["Name of employee"].unique().tolist()))
    type_filter = st.selectbox("Filter by Leave Type", ["All"] + sorted(df["Leave Type"].unique().tolist()))

def apply_filters(df):
    if employee_filter != "All":
        df = df[df["Name of employee"] == employee_filter]
    if type_filter != "All":
        df = df[df["Leave Type"] == type_filter]
    return df

df_filtered = apply_filters(df)

# ---------------- Tabs ----------------
tab_today, tab_pending, tab_history = st.tabs(["📍 Today", "🕒 Pending", "📜 History"])

# ---------------- TODAY TAB ----------------
with tab_today:
    st.subheader("Today's Leaves")
    today = pd.to_datetime(datetime.today().date())
    today_df = df_filtered[(df_filtered['start Date'] <= today) & (df_filtered['end Date'] >= today)]

    pending_today = today_df[today_df['Workday approved'] == False]
    approved_today = today_df[today_df['Workday approved'] == True]

    st.markdown("### 🔴 Pending Approvals for Today")
    for i, row in pending_today.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(row["Name of employee"])
        cols[1].write(row["Leave Type"])
        cols[2].write(format_date(row["start Date"]))
        cols[3].write(format_date(row["end Date"]))
        toggle_key = get_unique_key(row, "today_pending")
        approved = cols[4].toggle("✔️", value=False, key=toggle_key)
        if approved:
            df.at[i, 'Workday approved'] = True
            save_data(df)
            st.rerun()

    st.markdown("### ✅ Approved Leaves for Today")
    for i, row in approved_today.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(row["Name of employee"])
        cols[1].write(row["Leave Type"])
        cols[2].write(format_date(row["start Date"]))
        cols[3].write(format_date(row["end Date"]))
        toggle_key = get_unique_key(row, "today_approved")
        approved = cols[4].toggle("✔️", value=True, key=toggle_key)
        if not approved:
            df.at[i, 'Workday approved'] = False
            save_data(df)
            st.rerun()

# ---------------- PENDING TAB ----------------
with tab_pending:
    st.subheader("Pending Leaves (Not Approved in Workday)")

    # --- Add New Entry ---
    with st.expander("➕ Add New Leave Request"):
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

    pending_df = df_filtered[df_filtered['Workday approved'] == False]
    updated = False

    for i, row in pending_df.iterrows():
        cols = st.columns([2, 2, 2, 2, 2])
        cols[0].write(row["Name of employee"])
        cols[1].write(row["Leave Type"])
        cols[2].write(format_date(row["start Date"]))
        cols[3].write(format_date(row["end Date"]))
        toggle_key = get_unique_key(row, "pending")
        approved = cols[4].toggle("✔️", value=False, key=toggle_key)
        if approved:
            df.at[i, 'Workday approved'] = True
            updated = True

        # Email reminder
        if row["Name of employee"] in EMAIL_LOOKUP:
            if cols[4].button("📧 Notify", key=f"email_{i}"):
                to = EMAIL_LOOKUP[row["Name of employee"]]
                body = f"Hi {row['Name of employee']},\n\nPlease update your Workday leave request for: {row['Leave Type']} leave from {format_date(row['start Date'])} to {format_date(row['end Date'])}.\n\nThanks!"
                send_outlook_email(to, "Pending Workday Leave Update", body)

    if updated:
        save_data(df)
        st.rerun()

# ---------------- HISTORY TAB ----------------
with tab_history:
    st.subheader("Leave History (All Entries)")

    for i, row in df_filtered.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(row["Name of employee"])
        cols[1].write(row["Leave Type"])
        cols[2].write(format_date(row["start Date"]))
        cols[3].write(format_date(row["end Date"]))
        toggle_key = get_unique_key(row, "history")
        approved = cols[4].toggle("✔️", value=bool(row["Workday approved"]), key=toggle_key)
        if approved != row["Workday approved"]:
            df.at[i, 'Workday approved'] = approved
            save_data(df)
            st.rerun()

    # --- Summary Table ---
    st.markdown("### 📊 Summary: Leave Count Per Employee")
    summary_df = df.groupby("Name of employee").size().reset_index(name="Total Leaves")
    st.dataframe(summary_df)

    download_filtered_df(df_filtered)
