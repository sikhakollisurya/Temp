import streamlit as st
import pandas as pd
from datetime import datetime
import os

EXCEL_FILE = 'leave_tracker.xlsx'
COLUMNS = ['Name of employee', 'Leave Type', 'start Date', 'end Date', 'Workday approved']

# ---------- Helper Functions ----------
def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df['start Date'] = pd.to_datetime(df['start Date'])
        df['end Date'] = pd.to_datetime(df['end Date'])
        return df
    else:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

def add_entry(df, name, leave_type, start_date, end_date):
    new_row = {
        'Name of employee': name,
        'Leave Type': leave_type,
        'start Date': pd.to_datetime(start_date),
        'end Date': pd.to_datetime(end_date),
        'Workday approved': False
    }
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

# ---------- Streamlit App ----------
st.set_page_config(page_title="Team Leave Tracker", layout="wide")
st.title("📅 Team Leave Tracker")

# Load initial data
df = load_data()
tab1, tab2, tab3 = st.tabs(["📜 History", "🕒 Pending", "📍 Today"])

# ---------- History Tab ----------
with tab1:
    st.subheader("Leave History")
    for i in df.index:
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(df.loc[i, col_name])
        # Toggle
        approved = cols[-1].toggle("✔️", value=bool(df.loc[i, 'Workday approved']), key=f"hist_toggle_{i}")
        if approved != df.loc[i, 'Workday approved']:
            df.loc[i, 'Workday approved'] = approved
            save_data(df)

# ---------- Pending Tab ----------
with tab2:
    st.subheader("Pending Leaves (Not Approved in Workday)")
    
    # --- Add New Entry ---
    with st.expander("➕ Add New Leave Request"):
        emp_names = sorted(df['Name of employee'].unique().tolist() + ['Alice', 'Bob', 'Charlie'])  # editable as needed
        emp_names = list(set(emp_names))
        name = st.selectbox("Employee Name", emp_names, index=0)
        leave_type = st.selectbox("Leave Type", ["Personal", "Medical", "Work"])
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", datetime.today())
        end_date = col2.date_input("End Date", datetime.today())

        if start_date > end_date:
            st.warning("End date must be on or after start date.")
        else:
            if st.button("Add", key="add_new"):
                df = add_entry(df, name, leave_type, start_date, end_date)
                save_data(df)
                st.success("Leave request added!")

    # --- Display Pending Rows ---
    pending_df = df[df['Workday approved'] == False]
    updated = False

    for i in pending_df.index:
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(pending_df.loc[i, col_name])
        # Toggle
        approved = cols[-1].toggle("✔️", value=False, key=f"pend_toggle_{i}")
        if approved:
            df.loc[i, 'Workday approved'] = True
            updated = True
    
    if updated:
        save_data(df)
        st.experimental_rerun()

# ---------- Today Tab ----------
with tab3:
    st.subheader("Today's Leaves")
    today = pd.to_datetime(datetime.today().date())

    today_df = df[
        (df['start Date'] <= today) & (df['end Date'] >= today)
    ]

    pending_today = today_df[today_df['Workday approved'] == False]
    approved_today = today_df[today_df['Workday approved'] == True]

    st.markdown("### 🔴 Pending Approvals for Today")
    for i in pending_today.index:
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(pending_today.loc[i, col_name])
        approved = cols[-1].toggle("✔️", value=False, key=f"today_pending_toggle_{i}")
        if approved:
            df.loc[i, 'Workday approved'] = True
            save_data(df)
            st.experimental_rerun()

    st.markdown("### ✅ Approved Leaves for Today")
    for i in approved_today.index:
        cols = st.columns([2, 2, 2, 2, 1])
        for j, col_name in enumerate(COLUMNS[:-1]):
            cols[j].write(approved_today.loc[i, col_name])
        approved = cols[-1].toggle("✔️", value=True, key=f"today_approved_toggle_{i}")
        if not approved:
            df.loc[i, 'Workday approved'] = False
            save_data(df)
            st.experimental_rerun()
