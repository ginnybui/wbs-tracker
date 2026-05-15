import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
SHEET_ID = "1-5j3sNfaF41Yydcw4ozGspvg6Nvv5VqzuESuJILcTK4"
SHEET_NAME = "Data_DEV"

def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    return gspread.authorize(creds).open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="WBS Tracker Pro", layout="wide")

# --- HIDE STREAMLIT STYLE ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA FUNCTIONS ---
try:
    worksheet = init_gspread()
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    return df

# --- INITIALIZE SESSION STATE ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()

if 'page' not in st.session_state:
    st.session_state.page = 'list'

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- 2. HEADER & SYNC BUTTON ---
col_title, col_controls = st.columns([4, 1])
with col_title:
    st.title("📂 WBS Tracker")

with col_controls:
    st.write("##") 
    if st.button("🔄 Sync", use_container_width=True):
        st.cache_data.clear()
        st.session_state.df = load_data()
        st.rerun()
    st.markdown("<p style='color: #28a745; font-size: 10px; font-weight: bold; text-align: center; margin-top: -5px;'>● LIVE SYNC ACTIVE</p>", unsafe_allow_html=True)

st.divider()

# --- 3. PREPARE DATA ---
display_df = st.session_state.df.copy()
if "Select" not in display_df.columns:
    display_df.insert(0, "Select", False)

any_selected = False
if "main_editor" in st.session_state:
    edited_rows = st.session_state["main_editor"].get("edited_rows", {})
    any_selected = any(val.get("Select") for val in edited_rows.values())

# --- 4. PAGE: ADD NEW TASK ---
if st.session_state.page == 'add_new':
    st.subheader("📝 Add New Task")
    with st.form("new_task_form", clear_on_submit=True):
        task_title = st.text_input("Task Title (Required)*")
        task_status = st.selectbox("Status", options=["To Do", "In Progress", "Done", "On Hold"])
        
        c1, c2 = st.columns(2)
        est_hours = c1.number_input("Estimated Hours", min_value=0.0, step=0.5)
        act_hours = c2.number_input("Actual Hours", min_value=0.0, step=0.5)
        
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Start Date")
        end_date = c4.date_input("End Date")
        
        st.write("##") 
        f_col1, f_col2 = st.columns([1, 4])
        save_btn = f_col1.form_submit_button("Save", type="primary")
        cancel_btn = f_col2.form_submit_button("Cancel")

        if save_btn:
            if task_title:
                try:
                    # Generate a new ID based on current row count
                    new_id = len(st.session_state.df) + 1
                    
                    # Correct Sequence for your Google Sheet:
                    # ID | Title | Health | Status | Est | Act | Start | End | Progress
                    new_row = [
                        new_id,           # Task ID
                        task_title,       # Title
                        "🟢 Efficient",    # Health (Auto)
                        task_status,      # Status
                        est_hours,        # Est Hours
                        act_hours,        # Act Hours
                        str(start_date),  # Start Date
                        str(end_date),    # End Date
                        0                 # Progress (Auto 0%)
                    ] 
                    
                    worksheet.append_row(new_row)
                    st.toast("Task saved successfully!", icon="✅")
                    st.session_state.df = load_data()
                    navigate_to('list')
                except Exception as e:
                    st.error(f"Failed to save: {e}")
            else:
                st.error("Please enter a Task Title!")
        
        if cancel_btn:
            navigate_to('list')
    st.stop()

# --- 5. PAGE: LIST VIEW ---
if st.session_state.page == 'list':
    col_search, col_bulk_del, col_add = st.columns([3, 1, 1])
    
    with col_search:
        search = st.text_input("🔍 Search", placeholder="Filter by title...", label_visibility="collapsed")
        if search:
            display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]

    with col_bulk_del:
        btn_del = st.button("🗑️ Bulk Delete", use_container_width=True, disabled=not any_selected)

    with col_add:
        if st.button("➕ Add New Task", use_container_width=True, type="primary"):
            navigate_to('add_new')

    edited_df = st.data_editor(
        display_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "Progress": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100),
            "Status": st.column_config.SelectboxColumn("Status", options=["To Do", "In Progress", "Done", "On Hold"])
        },
        hide_index=True,
        use_container_width=True,
        key="main_editor"
    )

    if st.session_state.main_editor.get("edited_rows"):
        changes = st.session_state.main_editor["edited_rows"]
        is_real_edit = any(len(v) > 1 or "Select" not in v for v in changes.values())
        
        if is_real_edit:
            try:
                data_to_save = edited_df.drop(columns=["Select"])
                final_values = [data_to_save.columns.values.tolist()] + data_to_save.values.tolist()
                worksheet.clear()
                worksheet.update('A1', final_values)
                st.session_state.df = data_to_save
                st.toast("☁️ Cloud Updated!")
            except Exception as e:
                st.error(f"Auto-sync failed: {e}")

    if btn_del:
        rows_to_keep = edited_df[edited_df["Select"] == False].drop(columns=["Select"])
        final_data = [rows_to_keep.columns.values.tolist()] + rows_to_keep.values.tolist()
        worksheet.clear()
        worksheet.update('A1', final_data)
        st.session_state.df = rows_to_keep
        st.success("Tasks deleted!")
        st.rerun()