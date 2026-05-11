import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="WBS Tracker", layout="wide")

# Hide Streamlit UI elements for a professional look
st.markdown("""
<style>
    header {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("📊 PROJECT 01: WBS & Timeline Tracker")

# 1. Data Processing
def load_data():
    return pd.read_csv('tasks.csv')

def save_data(dataframe):
    dataframe.to_csv('tasks.csv', index=False)

df = load_data()

# 2. Project Summary Dashboard
st.subheader("Project Summary")
total_tasks = len(df)
completed_tasks = len(df[df['Status'] == 'Done'])
progress_ratio = completed_tasks / total_tasks if total_tasks > 0 else 0

st.progress(progress_ratio)
st.write(f"Completed {completed_tasks} out of {total_tasks} tasks ({progress_ratio:.0%})")

# 3. UI Styling Logic (Text Color Only)
def apply_status_color(status):
    if status == 'Done':
        return 'color: #28a745; font-weight: bold;'
    elif status == 'In Progress':
        return 'color: #fd7e14; font-weight: bold;'
    elif status == 'To Do':
        return 'color: #6c757d;'
    elif status == 'On Hold':
        return 'color: #dc3545; font-weight: bold;'
    return ''

# 4. Task Display
st.subheader("WBS Task List")
styled_df = df.style.applymap(apply_status_color, subset=['Status'])
st.dataframe(styled_df, use_container_width=True)

# 5. Management Form
st.subheader("Update Task Status")
with st.form("update_form"):
    selected_task_id = st.selectbox("Select Task ID", df['Task ID'])
    updated_status = st.selectbox("Status", ["To Do", "In Progress", "Done", "On Hold"])
    updated_progress = st.slider("Completion (%)", 0, 100, step=5)
    
    submit_changes = st.form_submit_button("Save Changes")
    
    if submit_changes:
        df.loc[df['Task ID'] == selected_task_id, 'Status'] = updated_status
        df.loc[df['Task ID'] == selected_task_id, 'Completion %'] = updated_progress
        save_data(df)
        st.success("Changes saved successfully!")
        st.rerun()