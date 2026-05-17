import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Set up page configuration
st.set_page_config(page_title="AFG Tracker - KDI School", layout="wide", initial_sidebar_state="expanded")

# --- SEMESTER TIMING CONFIGURATION ---
SEMESTER_START = datetime(2026, 5, 17).date()

def calculate_semester_week(input_date):
    if isinstance(input_date, datetime):
        input_date = input_date.date()
    days_difference = (input_date - SEMESTER_START).days
    if days_difference < 0:
        return "Pre-Semester"
    return f"Week { (days_difference // 7) + 1 }"

def get_date_range_for_week(week_str):
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
    using_cloud_db = True
except Exception:
    using_cloud_db = False
    if 'activities' not in st.session_state:
        st.session_state.activities = pd.DataFrame(columns=['Date', 'Course', 'Type', 'Duration', 'Notes'])
    if 'deadlines' not in st.session_state:
        st.session_state.deadlines = pd.DataFrame(columns=['Task', 'Course', 'Due Date', 'Priority', 'Weight', 'Status'])
    df_activities = st.session_state.activities
    df_deadlines = st.session_state.deadlines

if not df_activities.empty:
    df_activities['Date'] = pd.to_datetime(df_activities['Date']).dt.date

# --- APP SIDEBAR ---
st.sidebar.title("⚙️ Controls & Settings")
target_hours = st.sidebar.slider("Target Study Hours This Week", min_value=10, max_value=80, value=40, step=5)

if 'courses' not in st.session_state:
    st.session_state.courses = [
        "Korean Language & Culture", "Financial Statement Analysis & Valuation",
        "Introduction to Geospatial Analysis", "Managerial Accounting",
        "Entrepreneurship & Innovation", "Programming Fundamentals using Python",
        "Technological Innovation in Finance"
    ]
editable_courses = st.sidebar.data_editor(pd.DataFrame({"Courses": st.session_state.courses}), num_rows="dynamic")
course_list = editable_courses["Courses"].tolist()

# --- PERSONALIZED HEADER (STRICT ONE-LINE FIT) ---
st.markdown("""
    <style>
        .personalized-header {
            text-align: center;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            color: white;
            white-space: nowrap;
            overflow: hidden;
            padding: 10px 0;
            font-size: clamp(0.9rem, 2.2vw, 1.7rem); 
            letter-spacing: -0.5px;
        }
    </style>
    <div class='personalized-header'>
        Archie's Coursework and Progress Tracker - KDI School
    </div>
    """, unsafe_allow_html=True)

st.markdown("<p style='text-align: center; color: #94a3b8; margin-top: -10px; font-size: 0.9rem;'>Official Analytic Dashboard for the 2026 Academic Year</p>", unsafe_allow_html=True)
st.write("---")

# Alert user if they are using temporary or cloud database
if using_cloud_db:
    st.success("🔒 Connected safely to your permanent Google Sheet database storage.")
else:
    st.warning("⚠️ Running on temporary session storage. Setup your Streamlit Secrets to connect Google Sheets permanently.")

# --- WEEK FILTER ---
current_week_num = max(1, ((datetime.now().date() - SEMESTER_START).days // 7) + 1)
available_weeks = [f"Week {i}" for i in range(1, 17)] 

selected_week = st.selectbox("📅 Select Semester Week View:", options=available_weeks, index=min(current_week_num - 1, len(available_weeks) - 1))
w_start, w_end = get_date_range_for_week(selected_week)
st.info(f"📆 Metrics for **{selected_week}** ({w_start.strftime('%B %d')} to {w_end.strftime('%B %d, %Y')})")

if not df_activities.empty:
    df_filtered_activities = df_activities[(df_activities['Date'] >= w_start) & (df_activities['Date'] <= w_end)]
else:
    df_filtered_activities = df_activities

# --- LAYOUT ---
col_input, col_dash = st.columns([1, 2])

with col_input:
    st.subheader("📝 Log Activity")
    with st.form("activity_form", clear_on_submit=True):
        act_date = st.date_input("Date", datetime.now())
        act_course = st.selectbox("Course", course_list)
        act_type = st.selectbox("Type", ["General Overview / Skimming", "Conceptual Deep Dive", "Practice", "Assignment/Project", "Revision", "Others"])
        col_hrs, col_mins = st.columns(2)
        with col_hrs: act_hrs = st.number_input("Hours", 0, 12, 1)
        with col_mins: act_mins = st.number_input("Minutes", 0, 59, 0, 5)
        act_notes = st.text_area("Notes")
        if st.form_submit_button("Log Activity"):
            total_mins = (act_hrs * 60) + act_mins
            if total_mins > 0:
                if using_cloud_db:
                    # Append rows directly to the cloud sheet database
                    new_row = [str(act_date), act_course, act_type, total_mins, act_notes]
                    conn.create(worksheet="Activities", data=[new_row], append=True)
                else:
                    new_act = pd.DataFrame([[act_date, act_course, act_type, total_mins, act_notes]], columns=['Date', 'Course', 'Type', 'Duration', 'Notes'])
                    df_activities = pd.concat([df_activities, new_act], ignore_index=True)
                    st.session_state.activities = df_activities
                st.success(f"Logged {act_hrs}h {act_mins}m to {calculate_semester_week(act_date)}!")
                st.rerun()

with col_dash:
    if not df_filtered_activities.empty:
        df_filtered_activities['Duration'] = pd.to_numeric(df_filtered_activities['Duration'], errors='coerce').fillna(0)
        total_hours = float(df_filtered_activities['Duration'].sum() / 60)
    else: total_hours = 0.0
    
    st.subheader(f"📊 {selected_week} Matrix")
    st.metric("Hours Tracked", f"{total_hours:.1f} hrs", f"{total_hours - target_hours:.1f} vs Target")
    st.progress(min(total_hours / target_hours, 1.0) if target_hours > 0 else 0.0)
    
    st.write("---")
    st.subheader(f"📚 Time Accumulated Per Course")
    if not df_filtered_activities.empty and total_hours > 0:
        df_chart = df_filtered_activities.groupby('Course')['Duration'].sum().reset_index()
        df_chart['Hours'] = df_chart['Duration'] / 60
        fig = px.bar(df_chart, x='Course', y='Hours', color='Course', template="plotly_dark", title=f"Study Velocity: {selected_week}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activities logged in this week view yet.")
