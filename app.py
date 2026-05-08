import streamlit as st
import pandas as pd

st.set_page_config(page_title="WBS Tracker", layout="wide")
st.title("📊 PROJECT 01: WBS & Timeline Tracker")

# 1. Đọc dữ liệu từ CSV (Yêu cầu bắt buộc)
df = pd.read_csv('tasks.csv')

# 2. Dashboard tóm tắt (Baseline requirement)
st.subheader("Project Summary")
total = len(df)
done = len(df[df['Status'] == 'Done'])
st.progress(done/total)
st.write(f"Hoàn thành {done}/{total} nhiệm vụ")

# 3. Hiển thị bảng WBS
st.subheader("WBS Task List")
st.dataframe(df, use_container_width=True)

# 4. Form cập nhật trạng thái (Inline updates)
st.subheader("Update Progress")
with st.form("update_form"):
    task_id = st.selectbox("Chọn Task ID", df['Task ID'])
    new_status = st.selectbox("Trạng thái", ["To Do", "In Progress", "Done", "On Hold"])
    new_pct = st.slider("Tiến độ (%)", 0, 100, step=5)
    
    if st.form_submit_button("Lưu thay đổi"):
        df.loc[df['Task ID'] == task_id, 'Status'] = new_status
        df.loc[df['Task ID'] == task_id, 'Completion %'] = new_pct
        df.to_csv('tasks.csv', index=False) # Lưu lại CSV
        st.success("Đã lưu!")
        st.rerun()
