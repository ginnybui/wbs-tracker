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

st.set_page_config(page_title="WBS Tracker Pro", layout="wide")

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

# --- MAIN APP ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.title("📊 Project WBS Inventory")

# --- TOP BAR: SEARCH AND ACTION BUTTONS ---
col_search, col_bulk_del, col_add = st.columns([3, 1, 1])

with col_search:
    search = st.text_input("🔍 Search tasks...", placeholder="Filter by title...", label_visibility="collapsed")

# Pre-process data for the editor
display_df = st.session_state.df.copy()
if search:
    display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]
display_df.insert(0, "Select", False)

# Check if any row is selected to enable Bulk Delete
# Note: Since st.data_editor returns state AFTER interaction, 
# we check the state from the previous run to toggle the button.
any_selected = False
if "main_editor" in st.session_state:
    edited_rows = st.session_state["main_editor"].get("edited_rows", {})
    any_selected = any(val.get("Select") for val in edited_rows.values())

with col_bulk_del:
    btn_del = st.button("🗑️ Bulk Delete", use_container_width=True, disabled=not any_selected)

with col_add:
    if st.button("➕ Add New Task", use_container_width=True):
        st.session_state.show_form = True

# --- ADD NEW TASK MODAL/FORM ---
if st.session_state.get('show_form'):
    with st.expander("📝 Enter New Task Details", expanded=True):
        with st.form("new_task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            new_id = c1.number_input("Task ID", min_value=1, step=1)
            new_title = c2.text_input("Task Title")
            new_status = c3.selectbox("Status", ["To Do", "In Progress", "Done", "On Hold"])
            
            c4, c5 = st.columns(2)
            new_est = c4.number_input("Est Hours", min_value=0)
            new_health = c5.selectbox("Health Check", ["🟢 Efficient", "🟡 At Risk", "🔴 Delayed"])
            
            f_col1, f_col2 = st.columns(2)
            if f_col1.form_submit_button("Submit Task"):
                if new_title:
                    new_row = [new_id, new_title, new_health, new_status, new_est, 0, "", "", 0]
                    worksheet.append_row(new_row)
                    st.session_state.df = load_data()
                    st.session_state.show_form = False
                    st.rerun()
            if f_col2.form_submit_button("Close"):
                st.session_state.show_form = False
                st.rerun()

st.markdown("---")

# --- DATA TABLE (AUTO-SAVE ENABLED) ---
edited_df = st.data_editor(
    display_df,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", default=False),
        "Completion %": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100),
        "Status": st.column_config.SelectboxColumn("Status", options=["To Do", "In Progress", "Done", "On Hold"])
    },
    hide_index=True,
    use_container_width=True,
    key="main_editor"
)

# --- AUTO-SYNC LOGIC (REPLACES THE SAVE BUTTON) ---
# This block runs automatically every time the table is edited
if st.session_state.main_editor["edited_rows"]:
    changes = st.session_state.main_editor["edited_rows"]
    
    # Check if the user edited actual data (Title, Status, etc.) and not just the 'Select' box
    is_real_edit = any(len(v) > 1 or "Select" not in v for v in changes.values())
    
    if is_real_edit:
        try:
            # Prepare data to save (remove the UI 'Select' column)
            data_to_save = edited_df.drop(columns=["Select"])
            final_values = [data_to_save.columns.values.tolist()] + data_to_save.values.tolist()
            
            # Direct update to Cloud
            worksheet.clear()
            worksheet.update('A1', final_values)
            
            # Update local session state
            st.session_state.df = data_to_save
            st.toast("☁️ Cloud Updated Automatically!")
        except Exception as e:
            st.error(f"Auto-sync failed: {e}")

# --- DELETE LOGIC ---
if btn_del:
    rows_to_keep = edited_df[edited_df["Select"] == False].drop(columns=["Select"])
    final_data = [rows_to_keep.columns.values.tolist()] + rows_to_keep.values.tolist()
    worksheet.clear()
    worksheet.update('A1', final_data)
    st.session_state.df = rows_to_keep
    st.success("Selected tasks deleted!")
    st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    if st.button("🔄 Force Refresh Data", use_container_width=True):
        st.session_state.df = load_data()
        st.rerun()
    st.divider()
    st.success("2-Way Auto-Sync: Active")