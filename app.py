import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
from datetime import datetime, timedelta

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

# --- DIRECT CONNECTION ENGINE ---
using_cloud_db = False
df_activities = pd.DataFrame(columns=['Timestamp', 'Date', 'Course', 'Type', 'Duration', 'Notes'])
connection_error = None

# Linked directly to your verified public web publication stream
csv_target_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMblRIafhDycZoVlcNeONz3MRqxJLiHonQ12S_9UHgHBIsN76uhlwy9AHpIUNSLdjhbY8GX3WXYpYw/pub?output=csv"

try:
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(csv_target_url, headers=browser_headers, timeout=10)

    if response.status_code == 200:
        df_raw = pd.read_csv(StringIO(response.text))
        if df_raw is not None and not df_raw.empty:
            df_activities = df_raw.copy()
            df_activities.columns = ['Timestamp', 'Date', 'Course', 'Type', 'Duration', 'Notes'][:len(df_activities.columns)]
            using_cloud_db = True
    else:
        connection_error = f"Google Cloud responded with status: {response.status_code}."
except Exception as e:
    connection_error = str(e)

if not using_cloud_db:
    if 'activities' not in st.session_state:
        st.session_state.activities = pd.DataFrame(columns=['Timestamp', 'Date', 'Course', 'Type', 'Duration', 'Notes'])
    df_activities = st.session_state.activities

# --- DATETIME PARSING ENGINE ---
if not df_activities.empty and 'Date' in df_activities.columns:
    try:
        df_activities['Date'] = pd.to_datetime(df_activities['Date'], errors='coerce').dt.date
    except Exception:
        pass

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

# --- REVISED HEADERS & ADVANCED ENHANCED PROGRESS BAR CSS ---
st.markdown("""
    <style>
        .main-header {
            text-align: center; 
            font-family: 'Inter', sans-serif; 
            font-weight: 800; 
            color: white;
            white-space: nowrap; 
            overflow: hidden; 
            padding: 10px 0 5px 0;
            font-size: clamp(1.2rem, 2.2vw, 1.85rem); 
            letter-spacing: -0.5px;
        }
        .metric-box {
            background-color: #1e293b; 
            border-radius: 10px; 
            padding: 20px; 
            text-align: center; 
            border: 1px solid #334155; 
            margin-bottom: 15px;
        }
        .metric-val {
            font-size: 2.8rem !important; 
            font-weight: 800 !important; 
            color: #38bdf8 !important; 
            line-height: 1.1;
        }
        .metric-lbl {
            font-size: 1.0rem !important; 
            color: #94a3b8 !important; 
            font-weight: 600; 
            margin-top: 6px;
            letter-spacing: 0.5px;
        }
        
        /* TARGETING BOTH THE BASE TRACK AND THE INNER BLUE FILLING PROGRESS BAR ELEMENT */
        div[data-testid="stProgress"] {
            height: 32px !important;
            background-color: #1e293b !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin-top: 15px !important;
            margin-bottom: 25px !important;
            border: 1px solid #334155 !important;
        }
        div[data-testid="stProgress"] > div {
            height: 32px !important;
            background-color: #1e293b !important;
        }
        div[data-testid="stProgress"] > div > div {
            height: 32px !important;
            background-color: #0284c7 !important;
            border-radius: 6px 0px 0px 6px !important;
            transition: width 0.6s ease !important;
        }
    </style>
    <div class='main-header'>Archie's Coursework Tracking System - KDI School</div>
    """, unsafe_allow_html=True)
st.write("---")

if using_cloud_db:
    st.success("🔒 Connected safely to your permanent Google Sheet database storage layer.")
else:
    st.warning("⚠️ Running on temporary session fallback logic.")
    if connection_error:
        st.error(f"🔍 Connection Debug Error: {connection_error}")

# --- WEEK FILTER ---
current_week_num = max(1, ((datetime.now().date() - SEMESTER_START).days // 7) + 1)
available_weeks = [f"Week {i}" for i in range(1, 17)] 
selected_week = st.selectbox("📅 Select Semester Week View:", options=available_weeks, index=min(current_week_num - 1, len(available_weeks) - 1))
w_start, w_end = get_date_range_for_week(selected_week)
st.info(f"📆 Metrics for **{selected_week}** ({w_start.strftime('%B %d')} to {w_end.strftime('%B %d, %Y')})")

if not df_activities.empty and 'Date' in df_activities.columns:
    try:
        df_valid_dates = df_activities.dropna(subset=['Date'])
        df_filtered_activities = df_valid_dates[(df_valid_dates['Date'] >= w_start) & (df_valid_dates['Date'] <= w_end)]
    except Exception:
        df_filtered_activities = pd.DataFrame(columns=['Timestamp', 'Date', 'Course', 'Type', 'Duration', 'Notes'])
else:
    df_filtered_activities = pd.DataFrame(columns=['Timestamp', 'Date', 'Course', 'Type', 'Duration', 'Notes'])

# --- LAYOUT INTERFACE ---
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
                f_secrets = st.secrets.get("form_entries", {})
                form_url = f_secrets.get("form_url")
                
                if form_url:
                    form_data = {
                        f_secrets.get("date_entry"): str(act_date),
                        f_secrets.get("course_entry"): act_course,
                        f_secrets.get("type_entry"): act_type,
                        f_secrets.get("duration_entry"): int(total_mins),
                        f_secrets.get("notes_entry"): act_notes
                    }
                    try:
                        response = requests.post(form_url, data=form_data)
                        st.success(f"Logged {act_hrs}h {act_mins}m safely to database backend!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Form delivery issue: {str(e)}")
                else:
                    new_act_df = pd.DataFrame([{"Timestamp": str(datetime.now()), "Date": act_date, "Course": act_course, "Type": act_type, "Duration": total_mins, "Notes": act_notes}])
                    st.session_state.activities = pd.concat([df_activities, new_act_df], ignore_index=True)
                    st.success("Logged locally to temporary session state.")
                    st.rerun()

with col_dash:
    if not df_filtered_activities.empty:
        df_filtered_activities['Duration'] = pd.to_numeric(df_filtered_activities['Duration'], errors='coerce').fillna(0)
        total_hours = float(df_filtered_activities['Duration'].sum() / 60)
    else:
        total_hours = 0.0
    
    st.subheader(f"📊 {selected_week} Performance Engine")
    
    # Large High-Visibility Metric Card Block
    variance_hours = total_hours - target_hours
    variance_color = "#4ade80" if variance_hours >= 0 else "#f87171"
    variance_sign = "+" if variance_hours >= 0 else ""
    
    st.markdown(f"""
        <div class='metric-box'>
            <div class='metric-val'>{total_hours:.1f} / {target_hours} <span style='font-size: 1.6rem; color: {variance_color}; font-weight:700;'>({variance_sign}{variance_hours:.1f} hrs)</span></div>
            <div class='metric-lbl'>TOTAL HOURS COMMITTED VS. RUNNING WEEKLY TARGET</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Thicker Progress Bar Interface
    completion_rate = min(total_hours / target_hours, 1.0) if target_hours > 0 else 0.0
    st.progress(completion_rate)
    
    st.write("---")
    st.subheader(f"📚 Time Accumulated Per Course & Activity Type")
    if not df_filtered_activities.empty and total_hours > 0:
        df_chart = df_filtered_activities.groupby(['Course', 'Type'])['Duration'].sum().reset_index()
        df_chart['Hours'] = df_chart['Duration'] / 60
        
        fig = px.bar(
            df_chart, 
            x='Course', 
            y='Hours', 
            color='Type', 
            template="plotly_dark", 
            labels={"Hours": "Total Study Hours", "Type": "Activity Allocation"}
        )
        
        # FIXED: Converted layout keywords into direct function parameters to eliminate Plotly multi-line dictionary crash
        fig.update_layout(
            barmode='stack',
            xaxis_tickangle=-15,
            font=dict(size=14),
            xaxis=dict(tickfont=dict(size=14, family='Inter', color='white'), titlefont=dict(size=15, bold=True)),
            yaxis=dict(tickfont=dict(size=14, color='white'), titlefont=dict(size=15, bold=True)),
            legend=dict(font=dict(size=13), title=dict(font=dict(size=14, bold=True))),
            margin_l=20,
            margin_r=20,
            margin_t=20,
            margin_b=60
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activities logged in this week view yet.")
