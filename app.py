import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Using direct CSV link to bypass HTTP 400 errors from streamlit-gsheets
SHEET_ID = "1-5j3sNfaF41Yydcw4ozGspvg6Nvv5VqzuESuJILcTK4"
SHEET_NAME = "Data_DEV"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

st.set_page_config(page_title="WBS Tracker Pro", layout="wide")

# --- DATA LOADING ---
def load_data():
    try:
        # Direct read from Google Sheets public CSV export
        df = pd.read_csv(CSV_URL)
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Ensure essential columns exist
        required_cols = ["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Completion %"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0 if "Hours" in col else "N/A"
        
        return df
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return pd.DataFrame()

# --- UI HEADER ---
st.title("📊 Project WBS Dashboard")
st.markdown("---")

# --- MAIN APP ---
df = load_data()

if not df.empty:
    # 1. METRICS SECTION
    col1, col2, col3, col4 = st.columns(4)
    total_tasks = len(df)
    completed_tasks = len(df[df['Status'] == 'Done'])
    total_est = df['Est Hours'].sum()
    total_act = df['Act Hours'].sum()

    col1.metric("Total Tasks", total_tasks)
    col2.metric("Done", f"{completed_tasks} / {total_tasks}")
    col3.metric("Total Est. Hours", f"{total_est}h")
    col4.metric("Total Act. Hours", f"{total_act}h", delta=f"{total_act - total_est}h", delta_color="inverse")

    st.write("")

    # 2. DATA TABLE
    st.subheader("Task Inventory")
    
    # Simple search bar
    search = st.text_input("🔍 Search tasks by title...", "")
    if search:
        df = df[df['Title'].str.contains(search, case=False, na=False)]

    # Display the table with progress bar
    st.data_editor(
        df,
        column_config={
            "Completion %": st.column_config.ProgressColumn(
                "Progress",
                help="Task completion percentage",
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["To Do", "In Progress", "Done", "On Hold"],
                required=True,
            )
        },
        hide_index=True,
        use_container_width=True,
        disabled=["Task ID"] # Only let them edit status/details
    )

    # 3. SIDEBAR ACTIONS
    with st.sidebar:
        st.header("Actions")
        if st.button("➕ Create New Task", use_container_width=True):
            st.info("Form feature coming soon! Currently in Read-Only mode to fix Connection 400.")
        
        st.divider()
        st.success("✅ Connected to Google Sheets")
        st.caption(f"Last synced: {datetime.now().strftime('%H:%M:%S')}")

else:
    st.warning("No data found. Please check if your Google Sheet is shared as 'Anyone with the link'.")