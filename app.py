import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Set up page configuration
st.set_page_config(page_title="Grad Student Tracker", layout="wide", initial_sidebar_state="expanded")

# --- SEMESTER TIMING CONFIGURATION ---
# Your semester baseline starts tracking on Sunday, May 17, 2026
SEMESTER_START = datetime(2026, 5, 17).date()

def calculate_semester_week(input_date):
    """Calculates the semester week number (1, 2, 3...) based on a given date."""
    if isinstance(input_date, datetime):
        input_date = input_date.date()
    days_difference = (input_date - SEMESTER_START).days
    if days_difference < 0:
        return "Pre-Semester"
    # Integer division by 7 plus 1 gives the running week number
    return f"Week { (days_difference // 7) + 1 }"

def get_date_range_for_week(week_str):
    """Returns the start and end dates for a given Week string."""
    if "Week" not in week_str:
        return None, None
    week_num = int(week_str.split()[1]) - 1
    start_date = SEMESTER_START + timedelta(weeks=week_num)
    end_date = start_date + timedelta(days=6)
    return start_date, end_date

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

# Ensure correct data types for dates
if not df_activities.empty:
    df_activities['Date'] = pd.to_datetime(df_activities['Date']).dt.date

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

# --- NEW: TIME MACHINE WEEK FILTER ---
# Calculate current week dynamically to auto-select it
current_week_num = max(1, ((datetime.now().date() - SEMESTER_START).days // 7) + 1)
available_weeks = [f"Week {i}" for i in range(1, 17)] # Generates Weeks 1 to 16

selected_week = st.selectbox(
    "📅 Select Semester Week View:", 
    options=available_weeks, 
    index=min(current_week_num - 1, len(available_weeks) - 1)
)

# Filter bounds
w_start, w_end = get_date_range_for_week(selected_week)
st.info(f"📆 Showing metrics for **{selected_week}** ({w_start.strftime('%B %d')} to {w_end.strftime('%B %d, %Y')})")

# Filter activities dataset based on selection
if not df_activities.empty:
    df_filtered_activities = df_activities[(df_activities['Date'] >= w_start) & (df_activities['Date'] <= w_end)]
else:
    df_filtered_activities = df_activities

# Layout Split: Left side for inputs, Right side for Dashboard Metrics
col_input, col_dash = st.columns([1, 2])

with col_input:
    st.subheader("📝 Log New Activity")
    with st.form("activity_form", clear_on_submit=True):
        act_date = st.date_input("Date", datetime.now())
        act_course = st.selectbox("Course/Project", course_list)
        act_type = st.selectbox("Activity Type", ["Lecture", "Deep Study", "Assignment", "Revision", "Thesis Writing", "Other"])
        
        st.write("**Duration**")
        col_hrs, col_mins = st.columns(2)
        with col_hrs:
            act_hrs = st.number_input("Hours", min_value=0, max_value=12, value=1, step=1)
        with col_mins:
            act_mins = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=5)
            
        act_notes = st.text_area("Notes / Focus Area")
        
        submit_act = st.form_submit_button("Log Activity")
        if submit_act:
            total_logged_minutes = (act_hrs * 60) + act_mins
            if total_logged_minutes == 0:
                st.error("Duration cannot be 0 minutes!")
            else:
                new_act = pd.DataFrame([[act_date, act_course, act_type, total_logged_minutes, act_notes]], columns=['Date', 'Course', 'Type', 'Duration', 'Notes'])
                df_activities = pd.concat([df_activities, new_act], ignore_index=True)
                if 'activities' in st.session_state: st.session_state.activities = df_activities
                st.success(f"Successfully logged {act_hrs}h {act_mins}m! Saved to {calculate_semester_week(act_date)}.")
                st.rerun()

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
    # Metric Calculations based on Filtered Data
    if not df_filtered_activities.empty:
        df_filtered_activities['Duration'] = pd.to_numeric(df_filtered_activities['Duration'], errors='coerce').fillna(0)
        total_hours = float(df_filtered_activities['Duration'].sum() / 60)
    else:
        total_hours = 0.0
        
    progress_percent = min(total_hours / target_hours, 1.0) if target_hours > 0 else 0.0
    
    # Visual Progress Bar
    st.subheader(f"📊 {selected_week} Progress Matrix")
    st.metric(label="Hours Tracked This Week", value=f"{total_hours:.1f} hrs", delta=f"{total_hours - target_hours:.1f} hrs vs Target")
    st.progress(progress_percent)
    st.caption(f"Achieved {progress_percent*100:.1f}% of your weekly {target_hours}-hour goal for {selected_week}.")
    
    # Course Breakdown Chart
    st.write("---")
    st.subheader(f"📚 Time Matrix Per Course ({selected_week})")
    if not df_filtered_activities.empty and total_hours > 0:
        df_chart = df_filtered_activities.groupby('Course')['Duration'].sum().reset_index()
        df_chart['Hours'] = df_chart['Duration'] / 60
        fig = px.bar(df_chart, x='Course', y='Hours', title=f"Hours Spent per Course ({selected_week})", labels={'Hours':'Total Hours Spent'}, color='Course', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No activities logged inside {selected_week} yet. Change the dropdown view at the top or log items on the left to see your matrix update!")

    # Smart Sorting Deadlines Table (Deadlines stay global so you don't miss them!)
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
