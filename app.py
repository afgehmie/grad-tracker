import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Set up page configuration
st.set_page_config(page_title="Grad Student Tracker", layout="wide", initial_sidebar_state="expanded")

# --- GOOGLE SHEETS CONNECTION ---
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_activities = conn.read(worksheet="Activities", ttl="0m")
    df_deadlines = conn.read(worksheet="Deadlines", ttl="0m")
except Exception:
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

# 2. YOUR PERMANENT COURSE LIST
if 'courses' not in st.session_state:
    st.session_state.courses = [
        "Korean Language & Culture",
        "Financial Statement Analysis & Valuation",
        "Introduction to Geospatial Analysis",
        "Managerial Accounting",
        "Entrepreneurship & Innovation",
        "Programming Fundamentals using Python",
        "Technological Innovation in Finance"
    ]
    
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
        
        # --- NEW: Hours & Minutes Split Fields ---
        st.write("**Duration**")
        col_hrs, col_mins = st.columns(2)
        with col_hrs:
            act_hrs = st.number_input("Hours", min_value=0, max_value=12, value=1, step=1)
        with col_mins:
            act_mins = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=5)
            
        act_notes = st.text_area("Notes / Focus Area")
        
        submit_act = st.form_submit_button("Log Activity")
        if submit_act:
            # Convert the split hours and minutes back to total minutes for the database
            total_logged_minutes = (act_hrs * 60) + act_mins
            
            if total_logged_minutes == 0:
                st.error("Duration cannot be 0 minutes!")
            else:
                new_act = pd.DataFrame([[act_date, act_course, act_type, total_logged_minutes, act_notes]], columns=['Date', 'Course', 'Type', 'Duration', 'Notes'])
                df_activities = pd.concat([df_activities, new_act], ignore_index=True)
                if 'activities' in st.session_state: st.session_state.activities = df_activities
                st.success(f"Successfully logged {act_hrs}h {act_mins}m!")

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
        fig = px.bar(df_chart, x='Course', y='Hours', title="Hours Spent per Course/Project", labels={'Hours':'Total Hours Spent'}, color='Course', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activities logged yet. Log something on the left to see chart updates!")

    # Smart Sorting Deadlines Table
    st.write("---")
    st.subheader("🚨 Priority-Weighted Deadlines")
    if not df_deadlines.empty:
        priority_map = {"High": 3, "Medium": 2, "Low": 1}
        df_deadlines['Priority_Weight'] = df_deadlines['Priority'].map(priority_map)
        df_deadlines['Due Date'] = pd.to_datetime(df_deadlines['Due Date'])
        
        df_sorted = df_deadlines.sort_values(by=['Status', 'Priority_Weight', 'Due Date'], ascending=[False, False, True])
        df_display = df_sorted.drop(columns=['Priority_Weight'])
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No deadlines tracked yet! Rest easy, or add one on the left.")
