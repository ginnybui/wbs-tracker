import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# --- 1. SETTINGS & CONNECTION ---
st.set_page_config(page_title="WBS Tracker Pro", layout="wide")

# Persistent connection to prevent handshake delays
@st.cache_resource
def get_spreadsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Ensure your service_account.json is in the same folder
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1-5j3sNfaF41Yydcw4ozGspvg6Nvv5VqzuESuJILcTK4").worksheet("Data_DEV")

try:
    worksheet = get_spreadsheet()
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

# --- 2. FAST DATA LOADING ---
@st.cache_data(ttl=600) # 10-minute cache for instant UI response
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    return df

# --- 3. NAVIGATION LOGIC ---
if 'page' not in st.session_state:
    st.session_state.page = 'list'

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- 4. PAGE: ADD NEW TASK (LIGHTWEIGHT & INSTANT) ---
if st.session_state.page == 'add_new':
    st.title("📝 Add New Task")
    
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
        
        # FIXED: Buttons close together using [1, 1, 8] ratio
        btn_col1, btn_col2, spacer = st.columns([1, 1, 8])
        
        save_btn = btn_col1.form_submit_button("Save", type="primary", use_container_width=True)
        cancel_btn = btn_col2.form_submit_button("Cancel", use_container_width=True)

        if save_btn:
            if task_title:
                with st.spinner("Saving..."):
                    new_id = int(time.time())
                    new_row = [new_id, task_title, "🟢 Efficient", task_status, est_hours, act_hours, str(start_date), str(end_date), 0]
                    worksheet.append_row(new_row)
                    st.cache_data.clear() # Reset cache to fetch new row
                    if 'df' in st.session_state: del st.session_state.df
                    navigate_to('list')
            else:
                st.error("Please enter a Title!")
        
        if cancel_btn:
            navigate_to('list')
            
    st.stop() # Prevents the heavy List View code from running while adding a task

# --- 5. PAGE: LIST VIEW ---
st.title("📂 WBS Tracker")

# Ensure data is loaded into session state
if 'df' not in st.session_state:
    st.session_state.df = load_data()

display_df = st.session_state.df.copy()
if "Select" not in display_df.columns:
    display_df.insert(0, "Select", False)

# Header UI
col_search, col_bulk_del, col_add = st.columns([3, 1, 1])

with col_search:
    search = st.text_input("🔍 Search", placeholder="Search by title...", label_visibility="collapsed")
    if search:
        display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]

# Check if any row is selected for deletion
any_selected = False
if "main_editor" in st.session_state:
    edits = st.session_state["main_editor"].get("edited_rows", {})
    any_selected = any(val.get("Select") for val in edits.values())

with col_bulk_del:
    btn_del = st.button("🗑️ Bulk Delete", use_container_width=True, disabled=not any_selected)

with col_add:
    if st.button("➕ Add New Task", use_container_width=True, type="primary"):
        navigate_to('add_new')

# Main Data Table
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

# Manual Save Trigger
changes = st.session_state.main_editor.get("edited_rows", {})
is_real_edit = any(len(v) > 1 or (len(v) == 1 and "Select" not in v) for v in changes.values())

if is_real_edit:
    st.warning("⚠️ You have unsaved local changes.")
    if st.button("💾 SAVE ALL TO CLOUD", type="primary", use_container_width=True):
        with st.spinner("Syncing..."):
            data_to_save = edited_df.drop(columns=["Select"])
            final_values = [data_to_save.columns.values.tolist()] + data_to_save.values.tolist()
            worksheet.clear()
            worksheet.update('A1', final_values)
            st.session_state.df = data_to_save
            st.cache_data.clear()
            st.toast("Database Updated!")
            st.rerun()

# Delete Logic
if btn_del:
    with st.spinner("Deleting..."):
        rows_to_keep = edited_df[edited_df["Select"] == False].drop(columns=["Select"])
        final_data = [rows_to_keep.columns.values.tolist()] + rows_to_keep.values.tolist()
        worksheet.clear()
        worksheet.update('A1', final_data)
        st.session_state.df = rows_to_keep
        st.cache_data.clear()
        st.rerun()