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
        return df
    except:
        return pd.DataFrame(columns=["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"])

def save_data(dataframe):
    dataframe.to_csv('tasks.csv', index=False)

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
        d_comp = int(task_to_edit['Completion %'])
    else:
        d_title, d_status, d_est, d_act = "", "To Do", 0, 0
        d_start, d_end, d_comp = datetime.now().date(), datetime.now().date(), 0

    with st.form("task_form"):
        f_title = st.text_input("Title", value=d_title)
        col1, col2 = st.columns(2)
        with col1:
            f_status = st.selectbox("Status", ["To Do", "In Progress", "Done", "On Hold"], 
                                    index=["To Do", "In Progress", "Done", "On Hold"].index(d_status))
            f_est = st.number_input("Est Hours", min_value=0, value=d_est)
            f_start = st.date_input("Start Date", value=d_start)
        with col2:
            f_comp = st.slider("Completion %", 0, 100, value=d_comp)
            f_act = st.number_input("Act Hours", min_value=0, value=d_act)
            f_end = st.date_input("End Date", value=d_end)
            
        c_btn1, c_btn2 = st.columns([1, 8])
        if c_btn1.form_submit_button("Save"):
            if is_update:
                idx = df[df['Task ID'].astype(str) == str(st.session_state.edit_task_id)].index[0]
                df.at[idx, 'Title'], df.at[idx, 'Status'] = f_title, f_status
                df.at[idx, 'Est Hours'], df.at[idx, 'Act Hours'] = f_est, f_act
                df.at[idx, 'Start Date'], df.at[idx, 'End Date'] = f_start, f_end
                df.at[idx, 'Completion %'] = f_comp
            else:
                new_id = str(len(df) + 1)
                new_row = pd.DataFrame([{"Task ID": new_id, "Title": f_title, "Status": f_status, 
                                         "Est Hours": f_est, "Act Hours": f_act, "Start Date": f_start, 
                                         "End Date": f_end, "Completion %": f_comp}])
                df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.session_state.page = 'dashboard'
            st.rerun()
        if c_btn2.form_submit_button("Cancel"):
            st.session_state.page = 'dashboard'
            st.rerun()

# --- VIEW: DASHBOARD PAGE ---
else:
    st.title("📊 PROJECT 01: WBS & Timeline Tracker")
    
    total_tasks = len(df)
    completed_tasks = len(df[df['Status'] == 'Done'])
    progress_ratio = completed_tasks / total_tasks if total_tasks > 0 else 0
    st.subheader("Project Summary")
    st.progress(progress_ratio)
    st.write(f"Overall Progress: {progress_ratio:.0%}")

    st.markdown("---")

    col_head, col_act = st.columns([5, 1])
    with col_head:
        st.subheader("WBS Task List")
    with col_act:
        if st.button("➕ Add New", use_container_width=True):
            st.session_state.page = 'add_task'
            st.rerun()

    # Create an 'Action' column with a button value for each row
    df['Action'] = False 

    # Display data with the checkbox moved to the last column (Action column)
    # We use column_config to turn the 'Action' column into a button-like checkbox
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Action": st.column_config.CheckboxColumn(
                "Edit",
                help="Select to update this task",
                default=False,
            ),
            "Completion %": st.column_config.ProgressColumn("Completion %", format="%d%%", min_value=0, max_value=100),
            "Est Hours": st.column_config.NumberColumn("Est Hours", format="%d"),
            "Act Hours": st.column_config.NumberColumn("Act Hours", format="%d"),
        },
        disabled=[col for col in df.columns if col != "Action"] # Only Action is clickable
    )

    # Check if any "Action" checkbox was clicked
    if edited_df['Action'].any():
        selected_id = edited_df[edited_df['Action'] == True].iloc[0]['Task ID']
        st.session_state.edit_task_id = selected_id
        st.session_state.page = 'update_task'
        st.rerun()