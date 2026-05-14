import streamlit as st
import pandas as pd
from datetime import date

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

# 1. Data Processing
def load_data():
    try:
        df = pd.read_csv('tasks.csv')
        for col in ["Est Hours", "Act Hours"]:
            if col not in df.columns:
                df[col] = 0
        return df
    except:
        return pd.DataFrame(columns=["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"])

def save_data(dataframe):
    dataframe.to_csv('tasks.csv', index=False)

# Initialize Session State for navigation
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'

df = load_data()
cols = ["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"]
df = df.reindex(columns=cols)

# --- VIEW 1: ADD NEW TASK PAGE ---
if st.session_state.page == 'add_task':
    st.title("Add New Task")
    
    with st.form("new_task_form"):
        # Added a '*' to the label to indicate required field
        f_title = st.text_input("Title *")
        
        col1, col2 = st.columns(2)
        with col1:
            f_est = st.number_input("Est Hours", min_value=0)
            f_start = st.date_input("Start Date", value=date.today())
        with col2:
            f_act = st.number_input("Act Hours", min_value=0)
            f_end = st.date_input("End Date", value=date.today())
            
        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            submit = st.form_submit_button("Save Task")
        with col_btn2:
            cancel = st.form_submit_button("Cancel")

        if submit:
            # Check if title is empty or just whitespace
            if f_title.strip():
                new_id = str(len(df) + 1)
                new_row = pd.DataFrame([{
                    "Task ID": new_id, 
                    "Title": f_title.strip(), 
                    "Status": "To Do",
                    "Est Hours": f_est, 
                    "Act Hours": f_act,
                    "Start Date": f_start, 
                    "End Date": f_end, 
                    "Completion %": 0
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.session_state.page = 'dashboard'
                st.rerun()
            else:
                # Show error if title is missing
                st.error("Title is a required field. Please enter a task title.")
        
        if cancel:
            st.session_state.page = 'dashboard'
            st.rerun()

# --- VIEW 2: DASHBOARD PAGE ---
else:
    st.title("📊 PROJECT 01: WBS & Timeline Tracker")

    st.subheader("Project Summary")
    total_tasks = len(df)
    completed_tasks = len(df[df['Status'] == 'Done'])
    progress_ratio = completed_tasks / total_tasks if total_tasks > 0 else 0
    st.progress(progress_ratio)
    st.write(f"Completed {completed_tasks} out of {total_tasks} tasks ({progress_ratio:.0%})")

    st.markdown("---")

    col_head, col_act = st.columns([5, 1])
    with col_head:
        st.subheader("WBS Task List")
    with col_act:
        if st.button("➕ Add New", use_container_width=True):
            st.session_state.page = 'add_task'
            st.rerun()

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["To Do", "In Progress", "Done", "On Hold"]),
            "Est Hours": st.column_config.NumberColumn("Est Hours", format="%d"),
            "Act Hours": st.column_config.NumberColumn("Act Hours", format="%d"),
            "Completion %": st.column_config.ProgressColumn("Completion %", format="%d%%", min_value=0, max_value=100),
        },
        hide_index=True,
    )