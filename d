# app.py
import streamlit as st
import os
import pandas as pd
from pathlib import Path

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
                                "RowData": row_dict
                            })
                except Exception:
                    continue
        except Exception:
            continue
    return pd.DataFrame(rows)

def highlight_terms(text, keywords):
    for keyword in keywords:
        if keyword:
            text = text.replace(keyword, f"**:blue[{keyword}]**")
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

# Stats
st.sidebar.header("Search Filters")
file_filter = st.sidebar.text_input("File Name")
sheet_filter = st.sidebar.text_input("Sheet Name")
column_filter = st.sidebar.text_input("Column Name")
value_filter = st.sidebar.text_input("General Keywords (comma separated)")

keywords = [k.strip() for k in value_filter.split(',') if k.strip()]

filtered_df = df.copy()
if file_filter:
    filtered_df = filtered_df[filtered_df["File"].str.contains(file_filter, case=False)]
if sheet_filter:
    filtered_df = filtered_df[filtered_df["Sheet"].str.contains(sheet_filter, case=False)]
if column_filter:
    filtered_df = filtered_df[filtered_df["Column"].str.contains(column_filter, case=False)]
if keywords:
    keyword_mask = filtered_df["Value"].apply(lambda val: any(k.lower() in val.lower() for k in keywords))
    filtered_df = filtered_df[keyword_mask]

st.sidebar.markdown("---")
st.sidebar.metric("Total Files", df["File"].nunique())
st.sidebar.metric("Total Sheets", df["Sheet"].nunique())
st.sidebar.metric("Variables (Columns)", df["Column"].nunique())

st.success(f"✅ {len(filtered_df)} results found.")

# Rearrange columns
display_df = filtered_df[["Value", "Sheet", "File", "Row", "Column"]].copy()
if keywords:
    display_df["Value"] = display_df["Value"].apply(lambda x: highlight_terms(x, keywords))

# Display multiple rows with full preview
st.subheader("📋 Search Results")
for i, row in display_df.iterrows():
    with st.expander(f"🔹 {row['Value']} (Row {row['Row']} in {row['Sheet']}, {row['File']})"):
        st.markdown(f"**Sheet:** {row['Sheet']}  ")
        st.markdown(f"**File:** {row['File']}  ")
        st.markdown(f"**Row:** {row['Row']}  ")
        st.markdown(f"**Column:** {row['Column']}  ")
        full_row = filtered_df.loc[i, "RowData"]
        st.json(full_row)

# Export options
col1, col2 = st.columns(2)
with col1:
    st.download_button("📥 Download results as CSV", data=display_df.to_csv(index=False), file_name="excel_search_results.csv")
with col2:
    try:
        import pdfkit
        pdf_data = display_df.to_string(index=False)
        with open("temp_output.txt", "w") as f:
            f.write(pdf_data)
        os.system("pandoc temp_output.txt -o excel_search_results.pdf")
        with open("excel_search_results.pdf", "rb") as f:
            st.download_button("📄 Download as PDF", f, file_name="excel_search_results.pdf")
    except Exception:
        st.warning("PDF export failed. Make sure Pandoc is installed.")
