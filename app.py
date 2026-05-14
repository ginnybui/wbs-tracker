import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="WBS Tracker", layout="wide")

# CUSTOM CSS: Background color and UI cleanup
st.markdown("""
<style>
    /* Change background color of the entire app */
    .stApp {
        background-color: #f0f2f6; 
    }
    
    /* Clean up headers and menus */
    header {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* REMOVE TABLE ICONS (Toolbar at top-right) */
    [data-testid="stElementToolbar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 PROJECT 01: WBS & Timeline Tracker")

# 1. Data Processing
def load_data():
    try:
        df = pd.read_csv('tasks.csv')
        # Ensure hours columns exist for display
        if "Est Hours" not in df.columns:
            df["Est Hours"] = 0
        if "Act Hours" not in df.columns:
            df["Act Hours"] = 0
        return df
    except:
        return pd.DataFrame(columns=["Task ID", "Title", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %"])

df = load_data()

# Enforce column order: Status followed by Est Hours and Act Hours
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