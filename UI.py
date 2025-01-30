import streamlit as st
from backend import get_available_sessions, start_monitoring
from datetime import datetime

st.title("Pilates Class Booking Bot")

# Single form with inputs
with st.form("login_form"):
    email = st.text_input(
        "Email",
        type="default",
        key="email_form",
        autocomplete="username email"
    )
    password = st.text_input(
        "Password",
        type="password",
        key="password_form",
        autocomplete="current-password"
    )
    submit = st.form_submit_button("Check Available Sessions")

if submit:
    if email and password:
        with st.spinner("Fetching available sessions..."):
            available_sessions = get_available_sessions(email, password)
            if available_sessions:
                st.session_state['available_sessions'] = available_sessions
                st.success("Sessions fetched successfully!")
            else:
                st.error("Could not fetch sessions. Please try again.")
    else:
        st.error("Please enter email and password")

# Only show date/time selection if we have fetched available sessions
if 'available_sessions' in st.session_state:
    # Get unique dates from available sessions
    available_dates = sorted(list({session['date'] for session in st.session_state['available_sessions']}))
    
    # Convert string dates to datetime for date_input
    date_options = [datetime.strptime(date, "%Y-%m-%d").date() for date in available_dates]
    selected_date = st.date_input("Select Date", 
                                 min_value=date_options[0],
                                 max_value=date_options[-1],
                                 value=date_options[0])
    
    # Convert selected date back to string format
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    
    # Get available times for selected date
    available_times = [
        session['time'] for session in st.session_state['available_sessions'] 
        if session['date'] == selected_date_str
    ]
    
    selected_time = st.selectbox("Select Time", available_times)

    if st.button("Start Monitoring"):
        if email and password and selected_date and selected_time:
            start_monitoring(email, password, selected_date_str, selected_time)
        else:
            st.error("Please fill in all fields")
