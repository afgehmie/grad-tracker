import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Set up page configuration
st.set_page_config(page_title="Grad Student Tracker", layout="wide", initial_sidebar_state="expanded")

# --- GOOGLE SHEETS CONNECTION ---
# This connects your app to a Google Sheet so your data never disappears
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Read existing data or create empty dataframes if sheet is empty
    df_activities = conn.read(worksheet="Activities", ttl="0m")
    df_deadlines = conn.read(worksheet="Deadlines", ttl="0m")
except Exception:
    # Fallback to local session storage if Google Sheets isn't linked yet
    if 'activities' not in st.session_state:
        st.session_state.activities = pd.DataFrame(columns=['Date', 'Course', 'Type', 'Duration', 'Notes'])
    if 'deadlines' not in st.session_state:
        st.session_state.deadlines = pd.DataFrame(columns=['Task', 'Course', 'Due Date', 'Priority', 'Weight', 'Status'])
    df_activities = st.session_state.activities
    df_deadlines = st.session_state.deadlines

# --- APP SIDEBAR (ADAPTIVE CONTROLS) ---
st.sidebar.title("⚙️ Controls & Settings")

# 1. Dynamic Weekly Target
target_hours = st.sidebar.slider("Target Study Hours This Week", min_value=10, max_value=80, value=40, step=5)

# 2. Dynamic Course Management (Editable)
st.sidebar.subheader("Your Courses")
if 'courses' not in st.session_state:
    st.session_state.courses = ["Course A", "Course B", "Thesis Research", "Seminar"]
    
editable_courses = st.sidebar.data_editor(pd.DataFrame({"Courses": st.session_state.courses}), num_rows="dynamic")
course_list = editable_courses["Courses"].tolist()

# --- MAIN DASHBOARD ---
st.title("🎓 Graduate Student Activity & Progress Tracker")
st.markdown("Track your academic velocity, manage shifting priorities, and stay on top of deadlines.")
st.write("---")

# Layout Split: Left side for inputs, Right side for Dashboard Metrics
col_input, col_dash = st.columns([1, 2])

with col_input:
    st.subheader("📝 Log New Activity")
    with st.form("activity_form", clear_on_submit=True):
        act_date = st.date_input("Date", datetime.now())
        act_course = st.selectbox("Course/Project", course_list)
        act_type = st.selectbox("Activity Type", ["Lecture", "Deep Study", "Assignment", "Revision", "Thesis Writing", "Other"])
        act_duration = st.number_input("Duration (minutes)", min_value=5, max_value=480, value=60, step=15)
        act_notes = st.text_area("Notes / Focus Area")
        
        submit_act = st.form_submit_button("Log Activity")
        if submit_act:
            new_act = pd.DataFrame([[act_date, act_course, act_type, act_duration, act_notes]], columns=['Date', 'Course', 'Type', 'Duration', 'Notes'])
            df_activities = pd.concat([df_activities, new_act], ignore_index=True)
            if 'activities' in st.session_state: st.session_state.activities = df_activities
            st.success("Activity logged successfully!")

    st.write("---")
    st.subheader("⏳ Add Upcoming Deadline")
    with st.form("deadline_form", clear_on_submit=True):
        dl_task = st.text_input("Task/Assignment Name")
        dl_course = st.selectbox("Associated Course", course_list, key="dl_course")
        dl_date = st.date_input("Due Date", datetime.now() + timedelta(days=7))
        dl_priority = st.selectbox("Priority Level", ["High", "Medium", "Low"])
        dl_weight = st.slider("Grade Weight (%)", 0, 100, 10)
        
        submit_dl = st.form_submit_button("Add Deadline")
        if submit_dl:
            new_dl = pd.DataFrame([[dl_task, dl_course, dl_date, dl_priority, dl_weight, "Pending"]], columns=['Task', 'Course', 'Due Date', 'Priority', 'Weight', 'Status'])
            df_deadlines = pd.concat([df_deadlines, new_dl], ignore_index=True)
            if 'deadlines' in st.session_state: st.session_state.deadlines = df_deadlines
            st.success("Deadline tracked!")

with col_dash:
    # Metric Calculations
    df_activities['Duration'] = pd.to_numeric(df_activities['Duration'], errors='coerce').fillna(0)
    total_hours = float(df_activities['Duration'].sum() / 60)
    progress_percent = min(total_hours / target_hours, 1.0)
    
    # Visual Progress Bar
    st.subheader("📊 This Week's Progress")
    st.metric(label="Total Hours Tracked", value=f"{total_hours:.1f} hrs", delta=f"{total_hours - target_hours:.1f} hrs vs Target")
    st.progress(progress_percent)
    st.caption(f"Achieved {progress_percent*100:.1f}% of your weekly {target_hours}-hour goal.")
    
    # Course Breakdown Chart
    st.write("---")
    st.subheader("📚 Time Accumulated Per Course")
    if not df_activities.empty:
        df_chart = df_activities.groupby('Course')['Duration'].sum().reset_index()
        df_chart['Hours'] = df_chart['Duration'] / 60
        fig = px.bar(df_chart, x='Course', y='Hours', title="Hours Spent per Course/Project", labels={'Hours':'Total HoursSpent'}, color='Course', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activities logged yet. Log something on the left to see chart updates!")

    # Smart Sorting Deadlines Table
    st.write("---")
    st.subheader("🚨 Priority-Weighted Deadlines")
    if not df_deadlines.empty:
        # Simple sorting weight algorithm: High priority and closer dates go up
        priority_map = {"High": 3, "Medium": 2, "Low": 1}
        df_deadlines['Priority_Weight'] = df_deadlines['Priority'].map(priority_map)
        df_deadlines['Due Date'] = pd.to_datetime(df_deadlines['Due Date'])
        
        # Sort by status (Pending first), Priority (Highest first), and Due Date (Closest first)
        df_sorted = df_deadlines.sort_values(by=['Status', 'Priority_Weight', 'Due Date'], ascending=[False, False, True])
        
        # Drop the helper column for clean UI display
        df_display = df_sorted.drop(columns=['Priority_Weight'])
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No deadlines tracked yet! Rest easy, or add one on the left.")
