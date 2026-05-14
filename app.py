import streamlit as st
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="WBS Tracker", layout="wide")

# CUSTOM CSS
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    header {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stElementToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# 1. DATA PROCESSING
def load_data():
    try:
        df = pd.read_csv('tasks.csv')
        df['Start Date'] = pd.to_datetime(df['Start Date']).dt.date
        df['End Date'] = pd.to_datetime(df['End Date']).dt.date
        df['Completion %'] = pd.to_numeric(df['Completion %']).fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame(columns=["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"])

def save_data(dataframe):
    # Only drop UI-specific columns, KEEP 'Health' to sync with Git CSV
    temp_cols = ['Select', 'Action']
    save_df = dataframe.drop(columns=[c for c in temp_cols if c in dataframe.columns])
    save_df.to_csv('tasks.csv', index=False)

if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'edit_task_id' not in st.session_state:
    st.session_state.edit_task_id = None

# --- DIALOG FOR DELETE CONFIRMATION ---
@st.dialog("Confirm Deletion")
def confirm_delete_dialog(selected_ids):
    st.warning(f"Are you sure you want to delete {len(selected_ids)} record(s)?")
    st.info("This action will update the CSV and cannot be undone.")
    
    col_d1, col_d2 = st.columns(2)
    if col_d1.button("Cancel", use_container_width=True):
        st.rerun()
    
    if col_d2.button("Yes, Delete", type="primary", use_container_width=True):
        df_full = load_data()
        # Remove selected IDs
        df_full = df_full[~df_full['Task ID'].astype(str).isin([str(x) for x in selected_ids])]
        save_data(df_full)
        st.success("Records deleted successfully!")
        st.rerun()

df = load_data()

# --- VIEW: ADD / UPDATE TASK PAGE ---
if st.session_state.page in ['add_task', 'update_task']:
    is_update = st.session_state.page == 'update_task'
    st.title("Update Task Details" if is_update else "Add New Task")
    
    if is_update:
        task_to_edit = df[df['Task ID'].astype(str) == str(st.session_state.edit_task_id)].iloc[0]
        d_title, d_status = task_to_edit['Title'], task_to_edit['Status']
        d_est, d_act = int(task_to_edit['Est Hours']), int(task_to_edit['Act Hours'])
        d_start, d_end = task_to_edit['Start Date'], task_to_edit['End Date']
    else:
        d_title, d_status, d_est, d_act = "", "To Do", 1, 0
        d_start, d_end = datetime.now().date(), datetime.now().date()

    with st.form("task_form"):
        f_title = st.text_input("Title", value=d_title)
        col1, col2 = st.columns(2)
        with col1:
            f_status = st.selectbox("Status", ["To Do", "In Progress", "Done", "On Hold"], 
                                    index=["To Do", "In Progress", "Done", "On Hold"].index(d_status))
            f_est = st.number_input("Estimated Hours", min_value=1, value=max(1, d_est))
            f_start = st.date_input("Start Date", value=d_start)
        with col2:
            f_act = st.number_input("Actual Hours", min_value=0, value=d_act)
            f_end = st.date_input("End Date", value=d_end)
            
        c1, c2, c3 = st.columns([1, 1, 7])
        
        if c1.form_submit_button("Save", type="primary"):
            calc_comp = int(min((f_act / f_est) * 100, 100)) if f_est > 0 else 0
            # Define health for the new/updated record
            new_health = ""
            if f_act > f_est: new_health = "🔴 Over"
            elif f_act < f_est and f_act > 0: new_health = "🟢 Efficient"
            elif f_status == 'Done': new_health = "⚪ On Track"

            if is_update:
                idx = df[df['Task ID'].astype(str) == str(st.session_state.edit_task_id)].index[0]
                df.loc[idx, ['Title', 'Status', 'Est Hours', 'Act Hours', 'Start Date', 'End Date', 'Completion %', 'Health']] = \
                    [f_title, f_status, f_est, f_act, f_start, f_end, calc_comp, new_health]
            else:
                new_id = str(int(df['Task ID'].max()) + 1 if not df.empty else 1)
                new_row = pd.DataFrame([{"Task ID": new_id, "Title": f_title, "Status": f_status, 
                                         "Est Hours": f_est, "Act Hours": f_act, "Start Date": f_start, 
                                         "End Date": f_end, "Completion %": calc_comp, "Health": new_health}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            save_data(df)
            st.session_state.page = 'dashboard'
            st.rerun()

        if c2.form_submit_button("🗑️ Delete"):
            if is_update:
                confirm_delete_dialog([st.session_state.edit_task_id])
            else:
                st.error("Cannot delete a new record.")

        if c3.form_submit_button("Cancel"):
            st.session_state.page = 'dashboard'
            st.rerun()

# --- VIEW: DASHBOARD PAGE ---
else:
    st.title("📊 PROJECT 01: WBS & Tracker")
    
    # Progress Summary
    total_tasks = len(df)
    completed_tasks = len(df[df['Status'] == 'Done'])
    progress_ratio = completed_tasks / total_tasks if total_tasks > 0 else 0
    st.subheader("Project Summary")
    st.progress(progress_ratio)
    st.write(f"Overall Progress: {progress_ratio:.0%}")
    st.markdown("---")

    # Ensure Health column exists and is calculated
    def calculate_health(row):
        if row['Act Hours'] > row['Est Hours']: return "🔴 Over"
        elif row['Act Hours'] < row['Est Hours'] and row['Act Hours'] > 0: return "🟢 Efficient"
        elif row['Status'] == 'Done': return "⚪ On Track"
        return ""

    df['Health'] = df.apply(calculate_health, axis=1)
    df['Select'] = False 

    # Header with Dynamic Buttons
    col_h, col_edit, col_bulk, col_add = st.columns([3.5, 1.2, 1.2, 1.1])
    col_h.subheader("WBS Task List")
    
    if col_add.button("➕ Add New", use_container_width=True, type="primary"):
        st.session_state.page = 'add_task'
        st.rerun()

    # Data Display
    display_cols = ["Select", "Task ID", "Title", "Health", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"]
    
    edited_df = st.data_editor(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "Completion %": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100),
        },
        disabled=[col for col in display_cols if col != "Select"]
    )

    # Action Logic
    selected_rows = edited_df[edited_df['Select'] == True]

    if len(selected_rows) == 1:
        if col_edit.button("✏️ Update Task", use_container_width=True):
            st.session_state.edit_task_id = selected_rows.iloc[0]['Task ID']
            st.session_state.page = 'update_task'
            st.rerun()

    if len(selected_rows) > 0:
        if col_bulk.button(f"🗑️ Delete ({len(selected_rows)})", use_container_width=True):
            confirm_delete_dialog(selected_rows['Task ID'].tolist())