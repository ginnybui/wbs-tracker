import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
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
def get_spreadsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 🌟 DYNAMIC PRIVATE KEY PARSER: Tự động nhận diện và xử lý cả khóa PEM thô (Raw PEM) lẫn khóa mã hóa Base64
    gcp_config = dict(st.secrets["gcp"])
    if "private_key" in gcp_config:
        try:
            private_key_val = gcp_config["private_key"].strip()
            
            # Nếu khóa đã ở dạng PEM thô (bắt đầu bằng -----BEGIN)
            if private_key_val.startswith("-----BEGIN"):
                # Thay thế các ký tự xuống dòng bị double-escape nếu có
                gcp_config["private_key"] = private_key_val.replace("\\n", "\n")
            else:
                # Nếu ở dạng Base64, tiến hành tự động bù padding và giải mã
                b64_str = private_key_val
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                    
                decoded_bytes = base64.b64decode(b64_str)
                raw_private_key = decoded_bytes.decode("utf-8")
                
                if "BEGIN PRIVATE KEY" not in raw_private_key:
                    raw_private_key = f"-----BEGIN PRIVATE KEY-----\n{raw_private_key}\n-----END PRIVATE KEY-----"
                gcp_config["private_key"] = raw_private_key
        except Exception as encode_error:
            raise ValueError(f"Failed to parse private key: {encode_error}")
    
    creds = service_account.Credentials.from_service_account_info(gcp_config, scopes=scope)
    client = gspread.authorize(creds)
    
    target_url = st.secrets["gsheets"]["spreadsheet_url"]
    spreadsheet_key_match = re.search(r"/d/([a-zA-Z0-9-_]+)", target_url)
    if not spreadsheet_key_match:
        raise ValueError("Invalid Google Sheets URL format detected in configuration secrets.")
    
    spreadsheet_key = spreadsheet_key_match.group(1)
    opened_spreadsheet = client.open_by_key(spreadsheet_key)
    
    # 🛠️ CHỈ CHỈNH SỬA TẠI ĐÂY: Trỏ trực tiếp và cố định vào tab Data_UAT cho môi trường UAT hoàn chỉnh
    try:
        return opened_spreadsheet.worksheet("Data_UAT")
    except gspread.exceptions.WorksheetNotFound:
        # Cơ chế fallback phòng hờ nếu tên tab có sự cố, hệ thống sẽ quét theo GID hoặc tab đầu tiên như cũ
        gid_match = re.search(r"gid=(\d+)", target_url)
        if gid_match:
            target_gid = gid_match.group(1)
            for sheet in opened_spreadsheet.worksheets():
                if str(sheet.id) == target_gid:
                    return sheet
        return opened_spreadsheet.get_worksheet(0)

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

# --- 4. PAGE: ADD NEW TASK ---
if st.session_state.page == 'add_new':
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
                    new_row = [new_id, task_title, calc_health, task_status, est_hours, 0.0, str(start_date), str(end_date), calc_completion]
                    worksheet.append_row(new_row)
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
    raw_df = load_data()
    raw_df = raw_df.iloc[::-1].reset_index(drop=True)
    st.session_state.df = raw_df
    display_df = st.session_state.df.copy()
    col_search, col_edit, col_bulk_del, col_add = st.columns([2.5, 1, 1, 1])

    with col_search:
        search = st.text_input("🔍 Search", placeholder="Search by title...", label_visibility="collapsed")
        if search: display_df = display_df[display_df['Title'].str.contains(search, case=False, na=False)]

    ROWS_PER_PAGE = 50
    total_rows = len(display_df)
    total_pages = max(1, math.ceil(total_rows / ROWS_PER_PAGE))
    if st.session_state.current_page > total_pages: st.session_state.current_page = total_pages

    start_idx = (st.session_state.current_page - 1) * ROWS_PER_PAGE
    end_idx = min(start_idx + ROWS_PER_PAGE, total_rows)
    page_df = display_df.iloc[start_idx:end_idx].copy()

    if "Select" not in page_df.columns: page_df.insert(0, "Select", False)
    any_selected = False
    selected_row_indices = []

    if "main_editor" in st.session_state:
        edits = st.session_state["main_editor"].get("edited_rows", {})
        for local_str_idx, val in edits.items():
            if val.get("Select") is True: selected_row_indices.append(int(local_str_idx))
        any_selected = len(selected_row_indices) > 0

    can_edit = len(selected_row_indices) == 1
    with col_edit:
        if st.button("✏️ Edit Task", disabled=not can_edit):
            master_df_index = start_idx + selected_row_indices[0]
            st.session_state.editing_task_data = st.session_state.df.iloc[master_df_index].to_dict()
            st.session_state.editing_task_idx = master_df_index
            navigate_to('edit_task')

    @st.dialog("⚠️ Warning: Confirm Bulk Deletion")
    def show_delete_confirmation_modal(rows_to_delete_count, current_edited_df, start_index, end_index):
        st.write(f"Are you sure you want to permanently delete **{rows_to_delete_count}** selected task(s)?")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            if st.button("Yes, Delete", type="primary"):
                with st.spinner("Deleting selected rows..."):
                    rows_to_keep_on_page = current_edited_df[current_edited_df["Select"] == False].drop(columns=["Select"])
                    part_before = st.session_state.df.iloc[0:start_index]
                    part_after = st.session_state.df.iloc[end_index:]
                    new_total_df = pd.concat([part_before, rows_to_keep_on_page, part_after]).reset_index(drop=True)
                    final_df_to_cloud = new_total_df.iloc[::-1].reset_index(drop=True)
                    final_data = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
                    worksheet.clear()
                    worksheet.update('A1', final_data)
                    st.toast("Selected tasks deleted successfully!")
                    time.sleep(0.5)
                    st.query_params.update(page="list", p=1)
                    st.rerun()
        with m_col2:
            if st.button("Cancel"): st.rerun()

    with col_bulk_del:
        if st.button("🗑️ Bulk Delete", disabled=not any_selected):
            show_delete_confirmation_modal(len(selected_row_indices), st.session_state.current_edited_data, start_idx, end_idx)

    with col_add:
        if st.button("➕ Add New Task", type="primary"): navigate_to('add_new')

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

    changes = st.session_state.main_editor.get("edited_rows", {})
    is_real_edit = any(len(v) > 1 or (len(v) == 1 and "Select" not in v) for v in changes.values())

    if is_real_edit:
        with st.spinner("Syncing changes to Cloud..."):
            updated_page_df = edited_df.drop(columns=["Select"])
            st.session_state.df.iloc[start_idx:end_idx] = updated_page_df
            for idx in range(start_idx, min(end_idx, len(st.session_state.df))):
                row = st.session_state.df.iloc[idx]
                st.session_state.df.at[idx, 'Health'] = "🟢 Efficient" if row['Act Hours'] <= row['Est Hours'] else "🔴 Overtime"
                if row['Status'] == "Done": st.session_state.df.at[idx, 'Completion %'] = 100
                elif row['Status'] == "To Do": st.session_state.df.at[idx, 'Completion %'] = 0

            final_df_to_cloud = st.session_state.df.iloc[::-1].reset_index(drop=True)
            final_values = [final_df_to_cloud.columns.values.tolist()] + final_df_to_cloud.values.tolist()
            worksheet.clear()
            worksheet.update('A1', final_values)
            st.toast("Database Updated Automatically!")
            time.sleep(0.2)
            st.rerun()