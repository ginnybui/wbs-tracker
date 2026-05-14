import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="WBS Tracker", layout="wide")

# CUSTOM CSS: Background color and UI cleanup
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    header {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stForm"] {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 PROJECT 01: WBS & Timeline Tracker")

# 1. Data Processing
def load_data():
    df = pd.read_csv('tasks.csv')
    # Add columns if they don't exist yet
    if "Est Hours" not in df.columns:
        df["Est Hours"] = 0
    if "Act Hours" not in df.columns:
        df["Act Hours"] = 0
    return df

def save_data(dataframe):
    dataframe.to_csv('tasks.csv', index=False)

df = load_data()

# Reorder columns to place Hours after Status
# Current order: Task ID, Title, Status, Est Hours, Act Hours, Start Date, End Date, Completion %
cols = ["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"]
df = df.reindex(columns=cols)

# 2. Project Summary Dashboard
st.subheader("Project Summary")
total_tasks = len(df)
completed_tasks = len(df[df['Status'] == 'Done'])
progress_ratio = completed_tasks / total_tasks if total_tasks > 0 else 0

st.progress(progress_ratio)
st.write(f"Completed {completed_tasks} out of {total_tasks} tasks ({progress_ratio:.0%})")

# 3. Task Display using Column Config
st.subheader("WBS Task List")
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=["To Do", "In Progress", "Done", "On Hold"],
            required=True,
        ),
        "Est Hours": st.column_config.NumberColumn("Est Hours", format="%d"),
        "Act Hours": st.column_config.NumberColumn("Act Hours", format="%d"),
        "Completion %": st.column_config.ProgressColumn(
            "Completion %",
            format="%d%%",
            min_value=0,
            max_value=100,
        ),
    },
    hide_index=True,
)

# 4. Management Form
st.subheader("Update Task Status")
with st.form("update_form"):
    selected_task_id = st.selectbox("Select Task ID", df['Task ID'])
    
    col1, col2 = st.columns(2)
    with col1:
        updated_status = st.selectbox("Status", ["To Do", "In Progress", "Done", "On Hold"])
        updated_est = st.number_input("Estimated Hours", min_value=0)
    with col2:
        updated_progress = st.slider("Completion (%)", 0, 100, step=5)
        updated_act = st.number_input("Actual Hours", min_value=0)
    
    submit_changes = st.form_submit_button("Save Changes")
    
    if submit_changes:
        df.loc[df['Task ID'] == selected_task_id, 'Status'] = updated_status
        df.loc[df['Task ID'] == selected_task_id, 'Completion %'] = updated_progress
        df.loc[df['Task ID'] == selected_task_id, 'Est Hours'] = updated_est
        df.loc[df['Task ID'] == selected_task_id, 'Act Hours'] = updated_act
        save_data(df)
        st.success("Changes saved successfully!")
        st.rerun()