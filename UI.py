import streamlit as st
#from backend import get_available_sessions, start_monitoring
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
import time

SELENIUM_URL = "http://127.0.0.1:4444/wd/hub"

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--headless")


os.system("pkill -f chrome")
os.system("pkill -f chromedriver")
chrome_path = "/usr/bin/google-chrome"  # Path to Chrome binary
driver_path = "/usr/bin/chromedriver"  # Path to Chromedriver

service = Service(driver_path)
chrome_options.binary_location = chrome_path

driver = webdriver.Chrome(service=service, options=chrome_options)

# Retry connection to Selenium
for attempt in range(10):  # Try up to 10 times
    try:
        driver = webdriver.Remote(
            command_executor=SELENIUM_URL,
            options=chrome_options
        )
        print("✅ Selenium WebDriver connected successfully!")
        break
    except WebDriverException:
        print(f"❌ Selenium not ready. Retrying ({attempt+1}/10)...")
        time.sleep(5)
else:
    raise RuntimeError("❌ Selenium did not start in time.")

# Rest of your Streamlit code...
st.title("Pilates Class Booking Bot")

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

'''if submit:
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

if 'available_sessions' in st.session_state:
    available_dates = sorted(list({session['date'] for session in st.session_state['available_sessions']}))
    date_options = [datetime.strptime(date, "%Y-%m-%d").date() for date in available_dates]
    selected_date = st.date_input("Select Date", min_value=date_options[0], max_value=date_options[-1], value=date_options[0])
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    available_times = [session['time'] for session in st.session_state['available_sessions'] if session['date'] == selected_date_str]
    selected_time = st.selectbox("Select Time", available_times)
    if st.button("Start Monitoring"):
        if email and password and selected_date and selected_time:
            start_monitoring(email, password, selected_date_str, selected_time)
        else:
            st.error("Please fill in all fields")'''
