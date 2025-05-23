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
    errors = []
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
                except Exception as e:
                    errors.append(f"❌ Skipped sheet '{sheet_name}' in {file_path.name}: {e}")
        except Exception as e:
            errors.append(f"❌ Failed to open {file_path.name}: {e}")

    if errors:
        st.sidebar.warning("Some files/sheets could not be loaded.")
        with st.sidebar.expander("📋 Load Errors", expanded=False):
            for e in errors:
                st.markdown(f"- {e}")

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

# Single Search Bar
search_term = st.text_input("🔎 Enter a keyword to search (exact match only)")

if search_term:
    mask = (
        df["File"].str.contains(search_term, case=False) |
        df["Sheet"].str.contains(search_term, case=False) |
        df["Column"].str.contains(search_term, case=False) |
        df["Value"].str.contains(search_term, case=False)
    )
    filtered_df = df[mask].copy()

    # Highlight in the display table
    filtered_df["Value"] = filtered_df["Value"].apply(lambda x: highlight_term(x, search_term))

    # Rearrange and show
    display_df = filtered_df[["Value", "Sheet", "File", "Row", "Column"]]
    st.success(f"✅ {len(display_df)} results found.")
    st.dataframe(display_df, use_container_width=True, height=400)

    # Expandable Comparison Table
    if st.checkbox("📄 Expand and Compare Selected Rows"):
        selected_indices = st.multiselect("Select rows by index", options=display_df.index.tolist())
        if selected_indices:
            st.subheader("🧾 Comparison View")
            for idx in selected_indices:
                row_data = df.loc[idx, "RowData"]
                with st.expander(f"{df.loc[idx, 'File']} → {df.loc[idx, 'Sheet']} → Row {df.loc[idx, 'Row']}"):
                    st.json(row_data)

    # Export
    st.download_button("📥 Download results as CSV", data=display_df.to_csv(index=False), file_name="excel_search_results.csv")
else:
    st.info("Enter a keyword to begin your search.")
