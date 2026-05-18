import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import math

# --- 1. SETTINGS & CONNECTION ---
st.set_page_config(page_title="WBS Tracker Pro", layout="wide")

@st.cache_resource
def get_spreadsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1-5j3sNfaF41Yydcw4ozGspvg6Nvv5VqzuESuJILcTK4").worksheet("Data_DEV")

try:
    worksheet = get_spreadsheet()
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

# --- 2. DATA LOADING ---
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

# --- 4. PAGE: ADD NEW TASK ---
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
        
        btn_col1, btn_col2, spacer = st.columns([1, 1, 8])
        save_btn = btn_col1.form_submit_button("Save", type="primary", width="stretch")
        cancel_btn = btn_col2.form_submit_button("Cancel", width="stretch")

        if save_btn:
            if task_title:
                with st.spinner("Saving to Cloud..."):
                    raw_df = load_data()
                    new_id = len(raw_df) + 1
                    new_row = [new_id, task_title, "🟢 Efficient", task_status, est_hours, act_hours, str(start_date), str(end_date), 0]
                    
                    worksheet.append_row(new_row)
                    
                    if 'df' in st.session_state: 
                        del st.session_state.df
                        
                    st.toast("🔥 Added successfully!")
                    time.sleep(0.5)
                    navigate_to('list')
            else:
                st.error("Please enter a Title!")
        
        if cancel_btn:
            navigate_to('list')
            
    st.stop() 

# --- 5. PAGE: LIST VIEW ---
st.title("📂 WBS Tracker")

# Real-time Data Loading
raw_df = load_data()

# REVERSE DATA: Bring the newest records to the top row
raw_df = raw_df.iloc[::-1].reset_index(drop=True)
st.session_state.df = raw_df

display_df = st.session_state.df.copy()

# Header UI
col_search, col_bulk_del, col_add = st.columns([3, 1, 1])

with col_search:
    search = st.text_input("🔍 Search", placeholder="Search by title...", label_visibility="collapsed")
    if search:
        display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]

# --- PAGINATION LOGIC ---
ROWS_PER_PAGE = 50
total_rows = len(display_df)
total_pages = max(1, math.ceil(total_rows / ROWS_PER_PAGE))

# Initialize current page session state if not existing
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Ensure current page doesn't exceed total pages after filtering/searching
if st.session_state.current_page > total_pages:
    st.session_state.current_page = total_pages

# Slice the data for current page view
start_idx = (st.session_state.current_page - 1) * ROWS_PER_PAGE
end_idx = start_idx + ROWS_PER_PAGE
page_df = display_df.iloc[start_idx:end_idx].copy()

# Insert temporary 'Select' checkbox column for pagination row selection
if "Select" not in page_df.columns:
    page_df.insert(0, "Select", False)

# Check if any row is checked for bulk deletion
any_selected = False
if "main_editor" in st.session_state:
    edits = st.session_state["main_editor"].get("edited_rows", {})
    any_selected = any(val.get("Select") for val in edits.values())

with col_bulk_del:
    btn_del = st.button("🗑️ Bulk Delete", width="stretch", disabled=not any_selected)

with col_add:
    if st.button("➕ Add New Task", width="stretch", type="primary"):
        navigate_to('add_new')

# Render main data grid
edited_df = st.data_editor(
    page_df,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", default=False),
        "Progress": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100),
        "Status": st.column_config.SelectboxColumn("Status", options=["To Do", "In Progress", "Done", "On Hold"])
    },
    hide_index=True,
    width="stretch",
    key="main_editor"
)

# --- CLEAN PAGINATION NAVIGATION CONTROLBAR ---
st.markdown("<div style='margin-top: -22px;'></div>", unsafe_allow_html=True)

# FIXED: Changed column layout ratio to [1.2, 1.3, 1.2, 8.3] to prevent word wrap on all screen widths
p_col1, p_col2, p_col3, p_spacer = st.columns([1.2, 1.3, 1.2, 8.3])

with p_col1:
    if st.button("Previous", width="stretch", disabled=st.session_state.current_page == 1):
        st.session_state.current_page -= 1
        st.rerun()

with p_col2:
    st.markdown(
        f"""
        <div style='text-align: center; line-height: 38px; font-weight: bold; font-size: 15px; color: #31333F; white-space: nowrap;'>
            Page {st.session_state.current_page} of {total_pages}
        </div>
        """, 
        unsafe_allow_html=True
    )

with p_col3:
    if st.button("Next", width="stretch", disabled=st.session_state.current_page == total_pages):
        st.session_state.current_page += 1
        st.rerun()


# --- TWO-WAY AUTO-SYNC TRIGGER (CELL INLINE EDITING) ---
changes = st.session_state.main_editor.get("edited_rows", {})
is_real_edit = any(len(v) > 1 or (len(v) == 1 and "Select" not in v) for v in changes.values())

if is_real_edit:
    with st.spinner("Syncing changes to Cloud..."):
        # Map edits back to the master dataframe session state
        updated_page_df = edited_df.drop(columns=["Select"])
        st.session_state.df.iloc[start_idx:end_idx] = updated_page_df
        
        # Reverse back to match original database structure before uploading
        final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
        final_values = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
        
        worksheet.clear()
        worksheet.update('A1', final_values)
        st.toast("Database Updated Automatically!")
        time.sleep(0.2)
        st.rerun()

# --- BULK DELETE SYNC LOGIC ---
if btn_del:
    with st.spinner("Deleting selected rows..."):
        # Filter out checked rows from current page viewport
        rows_to_keep_on_page = edited_df[edited_df["Select"] == False].drop(columns=["Select"])
        
        # Splice and merge untouched slices with filtered slice
        part_before = st.session_state.df.iloc[0:start_idx]
        part_after = st.session_state.df.iloc[end_idx:]
        new_total_df = pd.concat([part_before, rows_to_keep_on_page, part_after]).reset_index(drop=True)
        
        # Reverse to store into Google Sheets correctly
        final_df_to_cloud = new_total_df.iloc[::-1].reset_index(drop=True)
        final_data = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
        
        worksheet.clear()
        worksheet.update('A1', final_data)
        st.toast("Deleted successfully!")
        time.sleep(0.2)
        st.rerun()