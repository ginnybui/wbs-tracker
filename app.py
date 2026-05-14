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
    # Cleanup temporary columns before saving to CSV
    temp_cols = ['Health', 'Action']
    save_df = dataframe.drop(columns=[c for c in temp_cols if c in dataframe.columns])
    save_df.to_csv('tasks.csv', index=False)

if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'edit_task_id' not in st.session_state:
    st.session_state.edit_task_id = None

df = load_data()

# --- VIEW: ADD / UPDATE TASK PAGE ---
if st.session_state.page in ['add_task', 'update_task']:
    is_update = st.session_state.page == 'update_task'
    st.title("Update Task" if is_update else "Add New Task")
    
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
            # Removed st.info alert text as requested
            f_act = st.number_input("Actual Hours", min_value=0, value=d_act)
            f_end = st.date_input("End Date", value=d_end)
            
        c1, c2 = st.columns([1, 8])
        if c1.form_submit_button("Save"):
            # Auto-calculate completion capped at 100%
            calc_comp = int(min((f_act / f_est) * 100, 100)) if f_est > 0 else 0
            
            if is_update:
                idx = df[df['Task ID'].astype(str) == str(st.session_state.edit_task_id)].index[0]
                df.at[idx, 'Title'], df.at[idx, 'Status'] = f_title, f_status
                df.at[idx, 'Est Hours'], df.at[idx, 'Act Hours'] = f_est, f_act
                df.at[idx, 'Start Date'], df.at[idx, 'End Date'] = f_start, f_end
                df.at[idx, 'Completion %'] = calc_comp
            else:
                new_id = str(len(df) + 1)
                new_row = pd.DataFrame([{"Task ID": new_id, "Title": f_title, "Status": f_status, 
                                         "Est Hours": f_est, "Act Hours": f_act, "Start Date": f_start, 
                                         "End Date": f_end, "Completion %": calc_comp}])
                df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.session_state.page = 'dashboard'
            st.rerun()
        if c2.form_submit_button("Cancel"):
            st.session_state.page = 'dashboard'
            st.rerun()

# --- VIEW: DASHBOARD PAGE ---
else:
    st.title("📊 PROJECT 01: WBS & Tracker")
    
    # Summary calculations
    total_tasks = len(df)
    completed_tasks = len(df[df['Status'] == 'Done'])
    progress_ratio = completed_tasks / total_tasks if total_tasks > 0 else 0
    st.subheader("Project Summary")
    st.progress(progress_ratio)
    st.write(f"Overall Progress: {progress_ratio:.0%}")
    st.markdown("---")

    # HEALTH LOGIC for the Alert column
    def get_health(row):
        if row['Act Hours'] > row['Est Hours']:
            return "🔴 Over"
        elif row['Act Hours'] < row['Est Hours'] and row['Act Hours'] > 0:
            return "🟢 Efficient"
        elif row['Status'] == 'Done' and row['Act Hours'] == row['Est Hours']:
            return "⚪ On Track"
        return ""

    df['Health'] = df.apply(get_health, axis=1)
    df['Action'] = False

    # Header
    col_h, col_a = st.columns([5, 1])
    col_h.subheader("WBS Task List")
    if col_a.button("➕ Add New", use_container_width=True):
        st.session_state.page = 'add_task'
        st.rerun()

    # Reorder columns for display
    display_cols = ["Task ID", "Title", "Health", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %", "Action"]
    
    edited_df = st.data_editor(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Health": st.column_config.TextColumn("Health", help="🔴 > Est, 🟢 < Est, ⚪ On Time"),
            "Action": st.column_config.CheckboxColumn("Edit", default=False),
            "Completion %": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100),
        },
        disabled=[col for col in display_cols if col != "Action"]
    )

    # Click handling for Edit button
    if edited_df['Action'].any():
        selected_id = edited_df[edited_df['Action'] == True].iloc[0]['Task ID']
        st.session_state.edit_task_id = selected_id
        st.session_state.page = 'update_task'
        st.rerun()