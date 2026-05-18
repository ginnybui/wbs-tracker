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
                    
                    # Compute initial auto-calculated properties
                    calc_completion = 100 if task_status == "Done" else 0
                    calc_health = "🟢 Efficient" if act_hours <= est_hours else "🔴 Overtime"
                    
                    new_row = [new_id, task_title, calc_health, task_status, est_hours, act_hours, str(start_date), str(end_date), calc_completion]
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

# --- 5. PAGE: EDIT TASK ---
if st.session_state.page == 'edit_task' and 'editing_task_data' in st.session_state:
    task_data = st.session_state.editing_task_data
    st.title(f"✏️ Edit Task: {task_data.get('Title', '')}")
    
    with st.form("edit_task_form"):
        edit_title = st.text_input("Task Title (Required)*", value=task_data.get('Title', ''))
        edit_status = st.selectbox(
            "Status", 
            options=["To Do", "In Progress", "Done", "On Hold"],
            index=["To Do", "In Progress", "Done", "On Hold"].index(task_data.get('Status', 'To Do'))
        )
        
        c1, c2 = st.columns(2)
        edit_est = c1.number_input("Estimated Hours", min_value=0.0, step=0.5, value=float(task_data.get('Est Hours', 0.0)))
        edit_act = c2.number_input("Actual Hours", min_value=0.0, step=0.5, value=float(task_data.get('Act Hours', 0.0)))
        
        # Auto-calculating Read-only feedback on form layout
        calc_completion = 100 if edit_status == "Done" else (0 if edit_status == "To Do" else int(task_data.get('Completion %', 0)))
        calc_health = "🟢 Efficient" if edit_act <= edit_est else "🔴 Overtime"
        
        # Display computed preview KPIs to user
        st.markdown(f"**Calculated Metrics Preview:** Status Health: `{calc_health}` | Completion Rate: `{calc_completion}%`")
        
        st.write("##")
        
        ebtn_col1, ebtn_col2, espacer = st.columns([1, 1, 8])
        update_btn = ebtn_col1.form_submit_button("Update", type="primary", width="stretch")
        cancel_btn = ebtn_col2.form_submit_button("Cancel", width="stretch")
        
        if update_btn:
            if edit_title:
                with st.spinner("Updating records..."):
                    # Pull original index references from execution dictionary
                    target_master_idx = st.session_state.editing_task_idx
                    
                    # Mutate copy values directly onto targeted master dataframe row slice
                    st.session_state.df.at[target_master_idx, 'Title'] = edit_title
                    st.session_state.df.at[target_master_idx, 'Status'] = edit_status
                    st.session_state.df.at[target_master_idx, 'Est Hours'] = edit_est
                    st.session_state.df.at[target_master_idx, 'Act Hours'] = edit_act
                    st.session_state.df.at[target_master_idx, 'Health'] = calc_health
                    st.session_state.df.at[target_master_idx, 'Completion %'] = calc_completion
                    
                    # Reverse collection matrix order sequence back to source structure before cloud pushing
                    final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
                    final_values = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
                    
                    worksheet.clear()
                    worksheet.update('A1', final_values)
                    
                    # Cleanup volatile execution states
                    del st.session_state.editing_task_data
                    del st.session_state.editing_task_idx
                    
                    st.toast("🚀 Task updated successfully!")
                    time.sleep(0.5)
                    navigate_to('list')
            else:
                st.error("Title cannot be blank!")
                
        if cancel_btn:
            navigate_to('list')
            
    st.stop()

# --- 6. PAGE: LIST VIEW ---
st.title("📂 WBS Tracker")

# Real-time Data Loading
raw_df = load_data()

# REVERSE DATA: Bring the newest records to the top row
raw_df = raw_df.iloc[::-1].reset_index(drop=True)
st.session_state.df = raw_df

display_df = st.session_state.df.copy()

# Header UI Spacing Optimization
col_search, col_edit, col_bulk_del, col_add = st.columns([2.5, 1, 1, 1])

with col_search:
    search = st.text_input("🔍 Search", placeholder="Search by title...", label_visibility="collapsed")
    if search:
        display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]

# --- PAGINATION LOGIC ---
ROWS_PER_PAGE = 50
total_rows = len(display_df)
total_pages = max(1, math.ceil(total_rows / ROWS_PER_PAGE))

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if st.session_state.current_page > total_pages:
    st.session_state.current_page = total_pages

start_idx = (st.session_state.current_page - 1) * ROWS_PER_PAGE
end_idx = start_idx + ROWS_PER_PAGE
page_df = display_df.iloc[start_idx:end_idx].copy()

if "Select" not in page_df.columns:
    page_df.insert(0, "Select", False)

# --- TRACK SELECTION AND STATE TRIGGERS ---
any_selected = False
selected_row_indices = []

if "main_editor" in st.session_state:
    edits = st.session_state["main_editor"].get("edited_rows", {})
    # Map out list index references that are actively checked "True"
    for local_str_idx, val in edits.items():
        if val.get("Select") is True:
            selected_row_indices.append(int(local_str_idx))
    any_selected = len(selected_row_indices) > 0

# Edit button is enabled ONLY when exactly one row is checked
can_edit = len(selected_row_indices) == 1

with col_edit:
    if st.button("✏️ Edit Task", width="stretch", disabled=not can_edit):
        # Translate local page data index reference to its master index value
        local_page_offset = selected_row_indices[0]
        master_df_index = start_idx + local_page_offset
        
        # Extract target item data record dictionary object
        target_record = st.session_state.df.iloc[master_df_index].to_dict()
        
        # Save payload data references into active application session states
        st.session_state.editing_task_data = target_record
        st.session_state.editing_task_idx = master_df_index
        navigate_to('edit_task')

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
        updated_page_df = edited_df.drop(columns=["Select"])
        st.session_state.df.iloc[start_idx:end_idx] = updated_page_df
        
        # Re-apply automated math metrics across modified row elements inline
        for idx in range(start_idx, min(end_idx, len(st.session_state.df))):
            row = st.session_state.df.iloc[idx]
            est, act, status = row['Est Hours'], row['Act Hours'], row['Status']
            
            st.session_state.df.at[idx, 'Health'] = "🟢 Efficient" if act <= est else "🔴 Overtime"
            if status == "Done":
                st.session_state.df.at[idx, 'Completion %'] = 100
            elif status == "To Do":
                st.session_state.df.at[idx, 'Completion %'] = 0

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
        rows_to_keep_on_page = edited_df[edited_df["Select"] == False].drop(columns=["Select"])
        
        part_before = st.session_state.df.iloc[0:start_idx]
        part_after = st.session_state.df.iloc[end_idx:]
        new_total_df = pd.concat([part_before, rows_to_keep_on_page, part_after]).reset_index(drop=True)
        
        final_df_to_cloud = new_total_df.iloc[::-1].reset_index(drop=True)
        final_data = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
        
        worksheet.clear()
        worksheet.update('A1', final_data)
        st.toast("Deleted successfully!")
        time.sleep(0.2)
        st.rerun()