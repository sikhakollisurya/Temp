# app.py
import streamlit as st
import os
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Excel Data Search", layout="wide")

@st.cache_data
def load_all_excel_cells(folder_path):
    rows = []
    for file_path in Path(folder_path).glob("*.xlsx"):
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                try:
                    df = xls.parse(sheet_name, dtype=str).fillna("")
                    for row_idx, row in df.iterrows():
                        for col in df.columns:
                            rows.append({
                                "File": file_path.name,
                                "Sheet": sheet_name,
                                "Row": row_idx + 2,  # +2 for human-readable index (headers + 1-based)
                                "Column": col,
                                "Value": str(row[col])
                            })
                except Exception:
                    continue
        except Exception:
            continue
    return pd.DataFrame(rows)

# Load all data
st.title("Excel Research Assistant 🔍")
st.caption("Searching across all sheets in the current folder...")

current_folder = os.getcwd()
with st.spinner("Reading Excel files..."):
    df = load_all_excel_cells(current_folder)

if df.empty:
    st.error("No Excel content could be loaded. Please check your files.")
    st.stop()

# Filters
st.sidebar.header("Search Filters")
file_filter = st.sidebar.text_input("File Name Contains")
sheet_filter = st.sidebar.text_input("Sheet Name Contains")
column_filter = st.sidebar.text_input("Column Name Contains")
value_filter = st.sidebar.text_input("General Search in Cell Value")

filtered_df = df.copy()

if file_filter:
    filtered_df = filtered_df[filtered_df["File"].str.contains(file_filter, case=False)]
if sheet_filter:
    filtered_df = filtered_df[filtered_df["Sheet"].str.contains(sheet_filter, case=False)]
if column_filter:
    filtered_df = filtered_df[filtered_df["Column"].str.contains(column_filter, case=False)]
if value_filter:
    filtered_df = filtered_df[filtered_df["Value"].str.contains(value_filter, case=False)]

st.success(f"{len(filtered_df)} results found.")
st.dataframe(filtered_df, use_container_width=True)

# Download
st.download_button("Download Results as CSV", data=filtered_df.to_csv(index=False), file_name="search_results.csv")
