# app.py
import streamlit as st
import os
import pandas as pd
from pathlib import Path
from difflib import get_close_matches

st.set_page_config(page_title="Excel Research Assistant", layout="wide")

@st.cache_data
def load_all_excel_cells(folder_path):
    rows = []
    row_data_map = []  # store full rows for preview
    for file_path in Path(folder_path).glob("*.xlsx"):
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                try:
                    df = xls.parse(sheet_name, dtype=str).fillna("")
                    for row_idx, row in df.iterrows():
                        row_dict = row.to_dict()
                        for col in df.columns:
                            value = str(row[col])
                            rows.append({
                                "Value": value,
                                "Sheet": sheet_name,
                                "File": file_path.name,
                                "Row": row_idx + 2,
                                "Column": col,
                                "RowData": row_dict  # for preview
                            })
                except Exception:
                    continue
        except Exception:
            continue
    return pd.DataFrame(rows)

def highlight_term(text, keyword):
    if keyword:
        return text.replace(keyword, f"**:blue[{keyword}]**")
    return text

# Load Excel content
st.title("📊 Excel Research Assistant")
current_folder = os.getcwd()
st.caption(f"Searching Excel files in: `{current_folder}`")

with st.spinner("Loading..."):
    df = load_all_excel_cells(current_folder)

if df.empty:
    st.error("No Excel data found.")
    st.stop()

# Filters
st.sidebar.header("Search Filters")
file_filter = st.sidebar.text_input("File Name")
sheet_filter = st.sidebar.text_input("Sheet Name")
column_filter = st.sidebar.text_input("Column Name")
value_filter = st.sidebar.text_input("General Keyword")

use_fuzzy = st.sidebar.checkbox("🔍 Use fuzzy search", value=True)

filtered_df = df.copy()

def fuzzy_filter(series, keyword):
    matches = series.dropna().unique().tolist()
    close = get_close_matches(keyword, matches, n=10, cutoff=0.6)
    return series.isin(close)

if file_filter:
    filtered_df = filtered_df[
        fuzzy_filter(filtered_df["File"], file_filter) if use_fuzzy
        else filtered_df["File"].str.contains(file_filter, case=False)]
if sheet_filter:
    filtered_df = filtered_df[
        fuzzy_filter(filtered_df["Sheet"], sheet_filter) if use_fuzzy
        else filtered_df["Sheet"].str.contains(sheet_filter, case=False)]
if column_filter:
    filtered_df = filtered_df[
        fuzzy_filter(filtered_df["Column"], column_filter) if use_fuzzy
        else filtered_df["Column"].str.contains(column_filter, case=False)]
if value_filter:
    if use_fuzzy:
        filtered_df = filtered_df[
            fuzzy_filter(filtered_df["Value"], value_filter)]
    else:
        filtered_df = filtered_df[
            filtered_df["Value"].str.contains(value_filter, case=False)]

st.success(f"✅ {len(filtered_df)} results found.")

# Rearrange columns
display_df = filtered_df[["Value", "Sheet", "File", "Row", "Column"]].copy()
if value_filter:
    display_df["Value"] = display_df["Value"].apply(lambda x: highlight_term(x, value_filter))

st.dataframe(display_df, use_container_width=True, height=400)

# Row preview section
if st.checkbox("🔎 Show full row data for selected result"):
    selected_row_index = st.number_input("Select row index (0 to N)", min_value=0, max_value=len(filtered_df) - 1, step=1)
    selected_data = filtered_df.iloc[selected_row_index]["RowData"]
    st.subheader(f"📄 Full Row (Sheet: {filtered_df.iloc[selected_row_index]['Sheet']})")
    st.json(selected_data)

# Export
st.download_button("📥 Download results as CSV", data=display_df.to_csv(index=False), file_name="excel_search_results.csv")
