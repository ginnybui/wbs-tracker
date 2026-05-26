import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import math
import os
import re
import base64
from datetime import datetime

# --- 1. SETTINGS & CONNECTION ---
st.set_page_config(page_title="WBS Tracker Pro", layout="wide")

# UI CLEANING COOKBOOK (Hiding default elements & injecting custom pagination styling)
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    .main .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    .stDataFrame [data-testid="stElementToolbarvanishing"],
    .stDataFrame [data-testid="stElementToolbar"],
    [data-testid="stDataFrameToolbar"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; pointer-events: none !important; }
    .custom-pagination-bar { margin-top: 14px !important; display: flex !important; justify-content: space-between !important; align-items: center !important; padding: 10px 4px !important; width: 100% !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .custom-pagination-bar .total-records { font-size: 14px !important; color: var(--text-color, #31333F) !important; opacity: 0.8; font-weight: 500 !important; user-select: none; }
    .custom-pagination-bar .button-group { display: flex !important; align-items: center !important; gap: 6px !important; }
    .custom-pagination-bar .pag-btn { height: 32px !important; min-width: 36px !important; padding: 0 10px !important; border-radius: 6px !important; font-size: 14px !important; font-weight: 500 !important; background-color: transparent !important; border: 1px solid var(--text-color, #31333F) !important; color: var(--text-color, #31333F) !important; text-decoration: none !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; opacity: 0.7; transition: all 0.15s ease-in-out; }
    .custom-pagination-bar .pag-btn:hover { opacity: 1 !important; background-color: rgba(128, 128, 128, 0.08) !important; border-color: var(--primary-color, #FF4B4B) !important; color: var(--primary-color, #FF4B4B) !important; }
    .custom-pagination-bar .pag-btn.disabled { opacity: 0.15 !important; pointer-events: none !important; cursor: not-allowed !important; }
    .custom-pagination-bar .page-indicator { height: 32px !important; padding: 0 14px !important; font-size: 13px !important; font-weight: 600 !important; color: var(--text-color, #31333F) !important; border: 1px solid var(--text-color, #31333F) !important; border-radius: 6px !important; opacity: 0.5; display: inline-flex !important; align-items: center !important; justify-content: center !important; user-select: none; }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_resource
def get_google_spreadsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 🌟 AUTO-PADDING BASE64 ENGINE: Auto-calculate and pad base64 string if trimmed in Streamlit Secrets
    gcp_config = dict(st.secrets["gcp"])
    if "private_key" in gcp_config:
        try:
            b64_str = gcp_config["private_key"].strip()
            
            # Resolve padding issue (e.g. 1621 characters instead of 1624) using modulo % 4
            missing_padding = len(b64_str) % 4
            if missing_padding:
                b64_str += '=' * (4 - missing_padding)
                
            # Safely decode Base64
            decoded_bytes = base64.b64decode(b64_str)
            raw_private_key = decoded_bytes.decode("utf-8")
            
            if "BEGIN PRIVATE KEY" not in raw_private_key:
                raw_private_key = f"-----BEGIN PRIVATE KEY-----\n{raw_private_key}\n-----END PRIVATE KEY-----"
                
            gcp_config["private_key"] = raw_private_key
        except Exception as encode_error:
            raise ValueError(f"Failed to parse base64 private key: {encode_error}")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_config, scope)
    client = gspread.authorize(creds)
    
    target_url = st.secrets["gsheets"]["spreadsheet_url"]
    spreadsheet_key_match = re.search(r"/d/([a-zA-Z0-9-_]+)", target_url)
    if not spreadsheet_key_match:
        raise ValueError("Invalid Google Sheets URL format detected in configuration secrets.")
    
    spreadsheet_key = spreadsheet_key_match.group(1)
    opened_spreadsheet = client.open_by_key(spreadsheet_key)
    return opened_spreadsheet, target_url

def get_projects_worksheet():
    opened_spreadsheet, _ = get_google_spreadsheet_client()
    try:
        return opened_spreadsheet.worksheet("Projects_Metadata")
    except gspread.exceptions.WorksheetNotFound:
        # Initialize Projects_Metadata worksheet with correct headers
        new_sheet = opened_spreadsheet.add_worksheet(title="Projects_Metadata", rows=100, cols=20)
        headers = ["Project ID", "Project Name", "Platform", "Description", "Start Date", "Target End Date", "Status"]
        new_sheet.append_row(headers)
        return new_sheet

@st.cache_resource
def get_spreadsheet():
    opened_spreadsheet, target_url = get_google_spreadsheet_client()
    
    # 🌟 DYNAMIC WORKSHEET SWITCHING ENGINE
    tasks_sheet = None
    # 1. First, attempt to locate the worksheet by the 'gid' query parameter in the spreadsheet URL (best for branch isolation).
    gid_match = re.search(r"gid=(\d+)", target_url)
    if gid_match:
        target_gid = gid_match.group(1)
        for sheet in opened_spreadsheet.worksheets():
            if str(sheet.id) == target_gid:
                tasks_sheet = sheet
                break
                
    if not tasks_sheet:
        # 2. Next, check if a specific worksheet name is explicitly defined in Streamlit secrets.
        custom_worksheet = st.secrets["gsheets"].get("worksheet_name")
        if custom_worksheet:
            try:
                tasks_sheet = opened_spreadsheet.worksheet(custom_worksheet)
            except gspread.exceptions.WorksheetNotFound:
                pass
                
    if not tasks_sheet:
        # 3. Fallback: Search for commonly used default worksheet names.
        for fallback_name in ["Data_Dev", "Data_UAT"]:
            try:
                tasks_sheet = opened_spreadsheet.worksheet(fallback_name)
                break
            except gspread.exceptions.WorksheetNotFound:
                continue
                
    if not tasks_sheet:
        # 4. Final Fallback: Return the first available worksheet in the spreadsheet.
        tasks_sheet = opened_spreadsheet.get_worksheet(0)

    # 🌟 AUTO-SETUP PROJECT ID COLUMN (Ensures legacy sheets are automatically updated)
    try:
        first_row = tasks_sheet.row_values(1)
        if first_row and "Project ID" not in first_row:
            # Insert "Project ID" at the very first column (position 1)
            tasks_sheet.insert_cols([["Project ID"]], col=1)
    except Exception:
        # Silent pass if initialization row check fails
        pass

    return tasks_sheet

try:
    worksheet = get_spreadsheet()
    projects_worksheet = get_projects_worksheet()
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

# --- 2. DATA LOADING ---
@st.cache_data
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str).str.strip()
    return df

@st.cache_data
def load_projects_data():
    data = projects_worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str).str.strip()
    return df

# --- 3. URL QUERY ROUTING & STATE MANAGEMENT ---
query_params = st.query_params

if 'page' not in st.session_state:
    st.session_state.page = query_params.get("page", "list")

if 'current_page' not in st.session_state:
    try: st.session_state.current_page = int(query_params.get("p", 1))
    except: st.session_state.current_page = 1

def navigate_to(page_name, target_page_idx=1):
    st.session_state.page = page_name
    st.session_state.current_page = target_page_idx
    st.query_params.update(page=page_name, p=target_page_idx)
    st.rerun()

if query_params.get("page") != st.session_state.page or query_params.get("p") != str(st.session_state.current_page):
    try: url_p = int(query_params.get("p", 1))
    except: url_p = 1
    st.session_state.page = query_params.get("page", "list")
    st.session_state.current_page = url_p

# --- 4. PAGE: ADD NEW PROJECT ---
if st.session_state.page == 'add_project':
    st.title("➕ Add New Project")
    with st.form("new_project_form", clear_on_submit=True):
        proj_name = st.text_input("Project Name (Required)*")
        platforms = st.multiselect("Platforms", options=["iOS", "Android", "Web", "CMS"], default=["Web"])
        proj_desc = st.text_area("Description")
        c1, c2 = st.columns(2)
        start_date = c1.date_input("Start Date", value=datetime.today().date())
        end_date = c2.date_input("Target End Date", value=datetime.today().date())
        proj_status = st.selectbox("Status", options=["Active", "On Hold", "Completed"])
        st.write("##")
        btn_col1, btn_col2, btn_col_empty = st.columns([1.2, 1, 7])
        with btn_col1: save_btn = st.form_submit_button("Save Project", type="primary", use_container_width=True)
        with btn_col2: cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

        if save_btn:
            if proj_name:
                with st.spinner("Saving Project..."):
                    raw_projects = load_projects_data()
                    new_id_num = len(raw_projects) + 1
                    proj_id = f"PRJ-{new_id_num:03d}"
                    platforms_str = ", ".join(platforms) if platforms else ""
                    new_row = [proj_id, proj_name, platforms_str, proj_desc, str(start_date), str(end_date), proj_status]
                    projects_worksheet.append_row(new_row)
                    load_projects_data.clear()
                    st.toast("🔥 Project created successfully!")
                    time.sleep(0.5)
                    st.session_state.current_project_id = proj_id
                    navigate_to('list')
            else:
                st.error("Please enter a Project Name!")
        if cancel_btn:
            navigate_to('list')

# --- 4.1. PAGE: EDIT PROJECT ---
elif st.session_state.page == 'edit_project':
    if 'editing_project_data' not in st.session_state:
        st.warning("No project selected for editing.")
        if st.button("Back to List"): navigate_to('list')
    else:
        proj_data = st.session_state.editing_project_data
        st.title(f"✏️ Edit Project: {proj_data.get('Project Name', '')}")
        
        @st.dialog("📦 Archive Project")
        def confirm_project_archive(target_idx, name):
            st.write(f"Are you sure you want to archive the project: **{name}**?")
            st.write("This will hide it from the active workspace list by default but keep all of its tasks intact.")
            m1, m2 = st.columns(2)
            with m1:
                if st.button("Yes, Archive", type="primary", use_container_width=True):
                    with st.spinner("Archiving project..."):
                        proj_df = load_projects_data()
                        proj_df.at[target_idx, 'Status'] = 'Archived'
                        proj_values = [proj_df.columns.values.tolist()] + proj_df.values.tolist()
                        projects_worksheet.clear()
                        projects_worksheet.update('A1', proj_values)
                        load_projects_data.clear()
                        
                        st.toast("Project archived successfully!")
                        time.sleep(0.5)
                        if 'current_project_id' in st.session_state:
                            del st.session_state.current_project_id
                        if 'editing_project_data' in st.session_state:
                            del st.session_state.editing_project_data
                        if 'editing_project_idx' in st.session_state:
                            del st.session_state.editing_project_idx
                        navigate_to('list', 1)
            with m2:
                if st.button("Cancel", use_container_width=True): st.rerun()

        edit_name = st.text_input("Project Name (Required)*", value=str(proj_data.get('Project Name', '')))
        
        platforms_options = ["iOS", "Android", "Web", "CMS"]
        raw_platforms = str(proj_data.get('Platform', ''))
        default_platforms = [p.strip() for p in raw_platforms.split(",") if p.strip() in platforms_options]
        edit_platforms = st.multiselect("Platforms", options=platforms_options, default=default_platforms)
        
        edit_desc = st.text_area("Description", value=str(proj_data.get('Description', '')))
        
        try: default_start = datetime.strptime(str(proj_data.get('Start Date', '')).strip(), "%Y-%m-%d").date()
        except: default_start = datetime.today().date()
        try: default_end = datetime.strptime(str(proj_data.get('Target End Date', '')).strip(), "%Y-%m-%d").date()
        except: default_end = datetime.today().date()
        
        c1, c2 = st.columns(2)
        edit_start = c1.date_input("Start Date", value=default_start)
        edit_end = c2.date_input("Target End Date", value=default_end)
        
        status_options = ["Active", "On Hold", "Completed", "Archived"]
        current_status = proj_data.get('Status', 'Active')
        default_index = status_options.index(current_status) if current_status in status_options else 0
        edit_status = st.selectbox("Status", options=status_options, index=default_index)
        
        with st.form("edit_project_details_form"):
            st.write("##")
            ebtn_col1, ebtn_col2, ebtn_col_space, ebtn_col_archive = st.columns([1.3, 1, 4.7, 1.3])
            with ebtn_col1: update_btn = st.form_submit_button("Update Project", type="primary", use_container_width=True)
            with ebtn_col2: cancel_btn = st.form_submit_button("Cancel", use_container_width=True)
            with ebtn_col_archive: archive_btn = st.form_submit_button("📦 Archive", use_container_width=True)
            
            if update_btn:
                if edit_name:
                    with st.spinner("Updating project..."):
                        target_idx = st.session_state.editing_project_idx
                        proj_df = load_projects_data()
                        
                        platforms_str = ", ".join(edit_platforms) if edit_platforms else ""
                        proj_df.at[target_idx, 'Project Name'] = edit_name
                        proj_df.at[target_idx, 'Platform'] = platforms_str
                        proj_df.at[target_idx, 'Description'] = edit_desc
                        proj_df.at[target_idx, 'Start Date'] = str(edit_start)
                        proj_df.at[target_idx, 'Target End Date'] = str(edit_end)
                        proj_df.at[target_idx, 'Status'] = edit_status
                        
                        proj_values = [proj_df.columns.values.tolist()] + proj_df.values.tolist()
                        projects_worksheet.clear()
                        projects_worksheet.update('A1', proj_values)
                        load_projects_data.clear()
                        
                        if 'editing_project_data' in st.session_state: del st.session_state.editing_project_data
                        if 'editing_project_idx' in st.session_state: del st.session_state.editing_project_idx
                        st.toast("🚀 Project updated successfully!")
                        time.sleep(0.5)
                        navigate_to('list')
                else:
                    st.error("Project Name cannot be blank!")
            if cancel_btn:
                if 'editing_project_data' in st.session_state: del st.session_state.editing_project_data
                if 'editing_project_idx' in st.session_state: del st.session_state.editing_project_idx
                navigate_to('list')
            if archive_btn:
                confirm_project_archive(st.session_state.editing_project_idx, edit_name)

# --- 5. PAGE: ADD NEW TASK ---
elif st.session_state.page == 'add_new':
    st.title("📝 Add New Task")
    with st.form("new_task_form", clear_on_submit=True):
        task_title = st.text_input("Task Title (Required)*")
        task_status = st.selectbox("Status", options=["To Do", "In Progress", "On Hold"])
        c1, c2 = st.columns(2)
        est_hours = c1.number_input("Estimated Hours", min_value=0.0, step=0.5, value=0.0)
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Start Date", value=datetime.today().date())
        end_date = c4.date_input("End Date", value=datetime.today().date())
        st.write("##") 
        btn_col1, btn_col2, btn_col_empty = st.columns([1.2, 1, 7])
        with btn_col1: save_btn = st.form_submit_button("Save Task", type="primary", use_container_width=True)
        with btn_col2: cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

        if save_btn:
            if task_title:
                with st.spinner("Saving to Cloud..."):
                    raw_df = load_data()
                    new_id = len(raw_df) + 1
                    calc_completion = 100 if task_status == "Done" else 0
                    calc_health = "🟢 Efficient" 
                    proj_id = st.session_state.get("current_project_id", "PRJ-001")
                    new_row = [proj_id, new_id, task_title, calc_health, task_status, est_hours, 0.0, str(start_date), str(end_date), calc_completion]
                    worksheet.append_row(new_row)
                    load_data.clear()
                    if 'df' in st.session_state: del st.session_state.df
                    st.toast("🔥 Task added successfully!")
                    time.sleep(0.5)
                    navigate_to('list')
            else: st.error("Please enter a Title!")
        if cancel_btn: navigate_to('list')

# --- 5. PAGE: EDIT TASK ---
elif st.session_state.page == 'edit_task':
    if 'editing_task_data' not in st.session_state:
        st.warning("No task selected for editing.")
        if st.button("Back to List"): navigate_to('list')
    else:
        task_data = st.session_state.editing_task_data
        st.title(f"✏️ Edit Task: {task_data.get('Title', '')}")
        
        @st.dialog("⚠️ Confirm Task Deletion")
        def confirm_single_delete(target_idx, title_name):
            st.write(f"Are you sure you want to permanently delete the task: **{title_name}**?")
            m1, m2 = st.columns(2)
            with m1:
                if st.button("Yes, Delete", type="primary", use_container_width=True):
                    with st.spinner("Deleting record..."):
                        st.session_state.df = st.session_state.df.drop(index=target_idx).reset_index(drop=True)
                        final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
                        final_data = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
                        worksheet.clear()
                        worksheet.update('A1', final_data)
                        load_data.clear()
                        st.toast("Task deleted successfully!")
                        time.sleep(0.5)
                        navigate_to('list', 1)
            with m2:
                if st.button("Cancel", use_container_width=True): st.rerun()

        edit_title = st.text_input("Task Title (Required)*", value=str(task_data.get('Title', '')))
        status_options = ["To Do", "In Progress", "Done", "On Hold"]
        current_status = task_data.get('Status', 'To Do')
        default_index = status_options.index(current_status) if current_status in status_options else 0
        edit_status = st.selectbox("Status", options=status_options, index=default_index)
        
        try: current_completion_val = int(task_data.get('Completion %', 0))
        except: current_completion_val = 0
        
        if edit_status == "Done": edit_completion = st.slider("Completion %", min_value=0, max_value=100, value=100, disabled=True)
        elif edit_status == "To Do": edit_completion = st.slider("Completion %", min_value=0, max_value=100, value=0, disabled=True)
        else: edit_completion = st.slider("Completion %", min_value=0, max_value=100, value=max(0, min(current_completion_val, 100)))

        with st.form("edit_task_details_form"):
            c1, c2 = st.columns(2)
            try: d_est = float(task_data.get('Est Hours', 0.0))
            except: d_est = 0.0
            try: d_act = float(task_data.get('Act Hours', 0.0))
            except: d_act = 0.0
            edit_est = c1.number_input("Estimated Hours", min_value=0.0, step=0.5, value=d_est)
            edit_act = c2.number_input("Actual Hours", min_value=0.0, step=0.5, value=d_act)
            
            c3, c4 = st.columns(2)
            try: default_start = datetime.strptime(str(task_data.get('Start Date', '')).strip(), "%Y-%m-%d").date()
            except: default_start = datetime.today().date()
            try: default_end = datetime.strptime(str(task_data.get('End Date', '')).strip(), "%Y-%m-%d").date()
            except: default_end = datetime.today().date()
            edit_start = c3.date_input("Start Date", value=default_start)
            edit_end = c4.date_input("End Date", value=default_end)
            
            calc_health = "🟢 Efficient" if edit_act <= edit_est else "🔴 Overtime"
            st.markdown(f"**Calculated Metrics:** Status Health: `{calc_health}`")
            st.write("##")
            ebtn_col1, ebtn_col2, ebtn_col_space, ebtn_col_del = st.columns([1.3, 1, 4.7, 1.3])
            with ebtn_col1: update_btn = st.form_submit_button("Update Task", type="primary", use_container_width=True)
            with ebtn_col2: cancel_btn = st.form_submit_button("Cancel", use_container_width=True)
            with ebtn_col_del: delete_btn = st.form_submit_button("🗑️ Delete", use_container_width=True)
            
            if update_btn:
                if edit_title:
                    with st.spinner("Updating records..."):
                        target_master_idx = st.session_state.editing_task_idx
                        final_completion = 100 if edit_status == "Done" else (0 if edit_status == "To Do" else edit_completion)
                        st.session_state.df.at[target_master_idx, 'Title'] = edit_title
                        st.session_state.df.at[target_master_idx, 'Status'] = edit_status
                        st.session_state.df.at[target_master_idx, 'Est Hours'] = edit_est
                        st.session_state.df.at[target_master_idx, 'Act Hours'] = edit_act
                        st.session_state.df.at[target_master_idx, 'Start Date'] = str(edit_start)
                        st.session_state.df.at[target_master_idx, 'End Date'] = str(edit_end)
                        st.session_state.df.at[target_master_idx, 'Health'] = calc_health
                        st.session_state.df.at[target_master_idx, 'Completion %'] = final_completion
                        
                        final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
                        final_values = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
                        worksheet.clear()
                        worksheet.update('A1', final_values)
                        load_data.clear()
                        if 'editing_task_data' in st.session_state: del st.session_state.editing_task_data
                        if 'editing_task_idx' in st.session_state: del st.session_state.editing_task_idx
                        st.toast("🚀 Task updated successfully!")
                        time.sleep(0.5)
                        navigate_to('list')
                else: st.error("Title cannot be blank!")
            if cancel_btn:
                if 'editing_task_data' in st.session_state: del st.session_state.editing_task_data
                if 'editing_task_idx' in st.session_state: del st.session_state.editing_task_idx
                navigate_to('list')
            if delete_btn: confirm_single_delete(st.session_state.editing_task_idx, edit_title)

# --- 6. PAGE: LIST VIEW (MAIN DASHBOARD) ---
elif st.session_state.page == 'list':
    st.title("📂 WBS Tracker Dashboard")
    
    # 💼 PROJECT WORKSPACE SELECTOR
    projects_df = load_projects_data()
    
    # Auto-initialize a default project if Projects_Metadata is empty
    if projects_df.empty:
        with st.spinner("Initializing default project..."):
            default_row = ["PRJ-001", "Default Project", "Web", "Initial WBS Project Workspace", str(datetime.today().date()), str(datetime.today().date()), "Active"]
            projects_worksheet.append_row(default_row)
            load_projects_data.clear()
            projects_df = load_projects_data()
            
    # Track the active project in session state
    if "current_project_id" not in st.session_state:
        st.session_state.current_project_id = projects_df["Project ID"].iloc[0] if not projects_df.empty else "PRJ-001"
        
    # Check if active project is archived
    curr_proj_row = projects_df[projects_df["Project ID"] == st.session_state.current_project_id]
    curr_proj_is_archived = False
    if not curr_proj_row.empty:
        curr_proj_is_archived = (curr_proj_row.iloc[0].get("Status") == "Archived")
        
    show_archived = st.checkbox("📂 Show Archived Projects", value=curr_proj_is_archived)
    
    if not show_archived:
        filtered_projects_df = projects_df[projects_df["Status"] != "Archived"]
    else:
        filtered_projects_df = projects_df
        
    if filtered_projects_df.empty:
        filtered_projects_df = projects_df
        
    project_list = filtered_projects_df["Project Name"].tolist()
    project_ids = filtered_projects_df["Project ID"].tolist()
    project_options = [f"{pid} - {pname}" for pid, pname in zip(project_ids, project_list)]
    
    try:
        default_sel_idx = project_ids.index(st.session_state.current_project_id)
    except ValueError:
        default_sel_idx = 0
        st.session_state.current_project_id = project_ids[0]
        
    col_proj_sel, col_proj_edit, col_proj_add = st.columns([6, 2, 2], gap="small")
    with col_proj_sel:
        selected_proj_option = st.selectbox(
            "💼 Active Project Workspace",
            options=project_options,
            index=default_sel_idx
        )
    st.session_state.current_project_id = selected_proj_option.split(" - ")[0]
    
    with col_proj_edit:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("✏️ Edit Project", use_container_width=True):
            curr_proj_id = st.session_state.current_project_id
            proj_idx = projects_df[projects_df["Project ID"] == curr_proj_id].index[0]
            st.session_state.editing_project_data = projects_df.iloc[proj_idx].to_dict()
            st.session_state.editing_project_idx = proj_idx
            navigate_to('edit_project')
            
    with col_proj_add:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Add Project", use_container_width=True):
            navigate_to('add_project')
            
    st.write("##")

    # Load and reverse task list
    raw_df = load_data()
    raw_df = raw_df.iloc[::-1].reset_index(drop=True)
    st.session_state.df = raw_df
    
    # 🌟 LEGACY DATA AUTO-MIGRATION: Auto-fill empty Project IDs with default "PRJ-001" and sync to Google Sheets
    has_legacy_empty_rows = False
    if "Project ID" in st.session_state.df.columns:
        empty_mask = (st.session_state.df["Project ID"].fillna("").astype(str).str.strip() == "")
        if empty_mask.any():
            st.session_state.df.loc[empty_mask, "Project ID"] = "PRJ-001"
            has_legacy_empty_rows = True
    else:
        st.session_state.df.insert(0, "Project ID", "PRJ-001")
        has_legacy_empty_rows = True

    if has_legacy_empty_rows:
        with st.spinner("Migrating legacy tasks to default project workspace..."):
            final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
            final_values = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
            worksheet.clear()
            worksheet.update('A1', final_values)
            load_data.clear()
            
    display_df = st.session_state.df.copy()
    
    # Apply dynamic filtering by active Project ID
    display_df = display_df[display_df["Project ID"] == st.session_state.current_project_id]

    # Column configuration with spacer and action buttons
    col_search, col_spacer, col_edit, col_bulk_del, col_add = st.columns([3.2, 4.4, 1.3, 1.4, 1.7], gap="small")

    with col_search:
        search = st.text_input("🔍 Search", placeholder="Search by title...", label_visibility="collapsed")
        if search: 
            display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]

    ROWS_PER_PAGE = 50
    total_rows = len(display_df)
    total_pages = max(1, math.ceil(total_rows / ROWS_PER_PAGE))
    if st.session_state.current_page > total_pages: 
        st.session_state.current_page = total_pages

    start_idx = (st.session_state.current_page - 1) * ROWS_PER_PAGE
    end_idx = min(start_idx + ROWS_PER_PAGE, total_rows)
    page_df = display_df.iloc[start_idx:end_idx].copy()

    if "Select" not in page_df.columns: 
        page_df.insert(0, "Select", False)
    any_selected = False
    selected_row_indices = []

    if "main_editor" in st.session_state:
        edits = st.session_state["main_editor"].get("edited_rows", {})
        for local_str_idx, val in edits.items():
            if val.get("Select") is True: 
                selected_row_indices.append(int(local_str_idx))
        any_selected = len(selected_row_indices) > 0



    # ✏️ EDIT TASK BUTTON (Secure mapping using Task ID)
    can_edit = len(selected_row_indices) == 1
    with col_edit:
        if st.button("✏️ Edit Task", disabled=not can_edit, use_container_width=True):
            selected_task_id = page_df.iloc[selected_row_indices[0]]["Task ID"]
            master_df_index = st.session_state.df[st.session_state.df["Task ID"] == selected_task_id].index[0]
            st.session_state.editing_task_data = st.session_state.df.iloc[master_df_index].to_dict()
            st.session_state.editing_task_idx = master_df_index
            navigate_to('edit_task')

    # 🗑️ CONFIRM BULK DELETION DIALOG (Safe, index-independent drop by Task ID)
    @st.dialog("⚠️ Warning: Confirm Bulk Deletion")
    def show_delete_confirmation_modal(rows_to_delete_count, target_task_ids):
        st.write(f"Are you sure you want to permanently delete **{rows_to_delete_count}** selected task(s)?")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            if st.button("Yes, Delete", type="primary"):
                with st.spinner("Deleting selected rows..."):
                    # Drop selected Task IDs from the master dataframe
                    new_total_df = st.session_state.df[~st.session_state.df["Task ID"].isin(target_task_ids)].reset_index(drop=True)
                    final_df_to_cloud = new_total_df.iloc[::-1].reset_index(drop=True)
                    final_data = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
                    worksheet.clear()
                    worksheet.update('A1', final_data)
                    load_data.clear()
                    st.toast("Selected tasks deleted successfully!")
                    time.sleep(0.5)
                    st.query_params.update(page="list", p=1)
                    st.rerun()
        with m_col2:
            if st.button("Cancel"): 
                st.rerun()

    with col_bulk_del:
        if st.button("🗑️ Bulk Delete", disabled=not any_selected, use_container_width=True):
            selected_task_ids = [page_df.iloc[i]["Task ID"] for i in selected_row_indices]
            show_delete_confirmation_modal(len(selected_row_indices), selected_task_ids)

    with col_add:
        if st.button("➕ Add New Task", type="primary", use_container_width=True): 
            navigate_to('add_new')

    edited_df = st.data_editor(
        page_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "Completion %": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100),
            "Status": st.column_config.SelectboxColumn("Status", options=["To Do", "In Progress", "Done", "On Hold"])
        },
        hide_index=True,
        key="main_editor"
    )
    st.session_state.current_edited_data = edited_df

    cp = st.session_state.current_page
    first_state = "disabled" if cp == 1 else ""
    prev_state = "disabled" if cp == 1 else ""
    next_state = "disabled" if cp == total_pages else ""
    last_state = "disabled" if cp == total_pages else ""
    
    pagination_html = f"""
    <div class="custom-pagination-bar">
        <div class="total-records">Total records found: {total_rows}</div>
        <div class="button-group">
            <a class="pag-btn {first_state}" href="?page=list&p=1" target="_self">«</a>
            <a class="pag-btn {prev_state}" href="?page=list&p={max(1, cp - 1)}" target="_self">‹</a>
            <div class="page-indicator">{cp} / {total_pages}</div>
            <a class="pag-btn {next_state}" href="?page=list&p={min(total_pages, cp + 1)}" target="_self">›</a>
            <a class="pag-btn {last_state}" href="?page=list&p={total_pages}" target="_self">»</a>
        </div>
    </div>
    """
    st.markdown(pagination_html, unsafe_allow_html=True)

    # 🔄 INLINE EDITING DYNAMIC SYNC ENGINE (Safe row update mapped by unique Task ID)
    changes = st.session_state.main_editor.get("edited_rows", {})
    is_real_edit = any(len(v) > 1 or (len(v) == 1 and "Select" not in v) for v in changes.values())

    if is_real_edit:
        with st.spinner("Syncing changes to Cloud..."):
            for local_idx_str, row_changes in changes.items():
                local_idx = int(local_idx_str)
                task_id = page_df.iloc[local_idx]["Task ID"]
                master_idx = st.session_state.df[st.session_state.df["Task ID"] == task_id].index[0]
                
                # Apply changes to the exact row in master df
                for col_name, new_val in row_changes.items():
                    if col_name != "Select":
                        st.session_state.df.at[master_idx, col_name] = new_val
                
                # Recalculate metrics for the edited row
                row = st.session_state.df.iloc[master_idx]
                try: est_h = float(row.get('Est Hours', 0.0))
                except: est_h = 0.0
                try: act_h = float(row.get('Act Hours', 0.0))
                except: act_h = 0.0
                st.session_state.df.at[master_idx, 'Health'] = "🟢 Efficient" if act_h <= est_h else "🔴 Overtime"
                
                if row['Status'] == "Done": 
                    st.session_state.df.at[master_idx, 'Completion %'] = 100
                elif row['Status'] == "To Do": 
                    st.session_state.df.at[master_idx, 'Completion %'] = 0

            final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
            final_values = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
            worksheet.clear()
            worksheet.update('A1', final_values)
            load_data.clear()
            st.toast("Database Updated Automatically!")
            time.sleep(0.2)
            st.rerun()