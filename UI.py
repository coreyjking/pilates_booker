import os
import sys
import streamlit as st
import time
import requests
import json
import boto3
import pytz
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.core.os_manager import ChromeType
from webdriver_manager.chrome import ChromeDriverManager

API_GATEWAY_URL = "https://0wk32adhz8.execute-api.ap-southeast-2.amazonaws.com/pilatesStage/schedule_booker"
url = "https://www.derrimut247.com.au/pages/reformer-pilates-thomastown"
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
region = st.secrets["aws"]["region_name"]
dynamodb = boto3.resource('dynamodb', region_name=region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
table = dynamodb.Table('pilatesBookings')
    
### INSTALL THE WEBDRIVER
@st.cache_resource
def get_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run without a UI
    chrome_options.add_argument("--no-sandbox")  
    chrome_options.add_argument("--disable-dev-shm-usage")  
    #chrome_options.add_argument("--disable-gpu")  # Optional: Improve performance
    #chrome_options.add_argument("--window-size=1920x1080")  # Ensure consistent rendering

    try:
        service = Service(
        ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        )
        driver = webdriver.Chrome(service=service, options=chrome_options)
        st.session_state['driver'] = driver
        return driver
    except Exception as e:
        st.error(f"Error initializing Selenium WebDriver: {e}")
        return None


def get_available_sessions(email, password):
    """
    Collect all available days (date-YYYY-MM-DD) and their session times
    from the webpage, and return them in a list of tuples.

    Example return value:
    [
        ("2025-01-20", ["5:00 AM", "5:30 AM", ...]),
        ("2025-01-21", [...]),
        ...
    ]
    """

    # Give time for the page to load and scroll down
    time.sleep(5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # Wait for at least one date element to appear
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'bw-widget__date')]"))
    )

    # Find all date elements
    date_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'bw-widget__date')]")
    st.session_state['date_elements'] = date_elements
    available_sessions = []

    for i, date_elem in enumerate(date_elements):
        
        # Extract the date text
        elem_classes = date_elem.get_attribute("class")
        elem_classes_split = elem_classes.split()
        class_date = elem_classes_split[1]
        
        the_date = date_elem.text.strip()

        if not the_date:
            continue  # Skip if no valid date found

        # Identify the XPath for the **current date section**
        date_xpath = f"(//div[contains(@class, 'bw-widget__date')])[{i+1}]"

        # Locate only the sessions **following this specific date**
        session_elements = driver.find_elements(By.XPATH, f"{date_xpath}/following-sibling::div[contains(@class, 'bw-session')]")

        times_for_date = []
        for session in session_elements:
            try:
                # Extract session start time
                time_element = session.find_element(By.CLASS_NAME, "hc_starttime")
                session_time = time_element.text.strip()
                times_for_date.append(session_time)
            except Exception as e:
                print(f"Skipping session due to error: {e}", file=sys.stderr, flush=True)

        # Store only if there are available times
        if times_for_date:
            available_sessions.append((the_date, times_for_date, class_date))

    return available_sessions

    
def confirm_logged_in():
    """Ensure the user is logged in. If not, log in automatically."""
    try:
        # Scroll to top of page and wait for elements to load
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)  # Allow time for any animations to complete
        
        # Wait for account button to be clickable
        account_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "bw-header__account-link"))
        )
        
        if account_button.text.strip() == "My Account":
            print("Opening My Account.", file=sys.stderr, flush=True)
            # Use JavaScript click as a fallback if regular click is intercepted
            driver.execute_script("arguments[0].click();", account_button)
            time.sleep(5)
            
            # Check if login form appears (indicating logged out)
            if driver.find_elements(By.ID, "username"):
                print("Not logged in. Logging in now...", file=sys.stderr, flush=True)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))

                # Fill login details
                username_input = driver.find_element(By.ID, "username")
                password_input = driver.find_element(By.ID, "password")
                submit_button = driver.find_element(By.XPATH, "/html/body/div[1]/span/div/div/div/main/div/div/form/section[2]/button")

                username_input.send_keys(st.session_state['email'])
                password_input.send_keys(st.session_state['password'])
                submit_button.click()
                time.sleep(4)

                print("Logged in successfully.", file=sys.stderr, flush=True)
                driver.get(url)
            else:
                print("Already logged in.", file=sys.stderr, flush=True)
                driver.refresh()
                driver.get(url)
        else:
            print("Login button not found. Trying to refresh and check again.", file=sys.stderr, flush=True)
            driver.get(url)
    except Exception as e:
        print(f"Login verification error: {e}", file=sys.stderr, flush=True)
        driver.get(url)


def get_upcoming_dates():
    # Set timezone to Australia/Melbourne
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    current_time = datetime.now(melbourne_tz)
    
    # Format scheduled_date (sort key) as YYYY-MM-DD
    start_date = current_time.strftime('%Y-%m-%d')
    end_date = (current_time + timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"Querying bookings for: {st.session_state["email"]} between {start_date} and {end_date}")

    # Query using partition key (email) and sort key (scheduled_date)
    response = table.query(
        KeyConditionExpression=Key('email').eq(st.session_state["email"]) & Key('scheduled_date').between(start_date, end_date)
    )
    
    # Extract booking timestamps from the response
    dates = [item['booking_timestamp'] for item in response.get('Items', [])]
    
    return dates

    
#Information for AI:
#<div class="bw-widget__date date-2025-02-15">Saturday, February 15</div>
#<time class="hc_starttime" datetime="2025-02-14T20:30">8:30 PM</time>
#<time class="hc_endtime" datetime="2025-02-14T21:15">9:15 PM</time>
#<div class="bw-session__staff" style>Harriet G</div>


# Connect to Selenium webdriver
if 'driver' not in st.session_state:
    st.session_state['driver'] = None

if not st.session_state['driver']:
    for attempt in range(10):  # Try up to 10 times
        try:
            st.session_state['driver'] = get_webdriver()
            print("✅ Python connected to Selenium WebDriver successfully!", file=sys.stderr, flush=True)
            print(st.session_state['driver'], file=sys.stderr, flush=True)
            break
        except WebDriverException:
            print(f"❌ Python cannot connect to Selenium WebDriver. Retrying ({attempt+1}/10)...", file=sys.stderr, flush=True)
            time.sleep(5)
    else:
        raise RuntimeError("❌ Selenium did not start in time.", file=sys.stderr, flush=True)
driver = st.session_state['driver']

# Rest of your Streamlit code...
st.title("Pilates Booking Assistant")

with st.form("login_form"):
    st.session_state['email'] = st.text_input(
        "Email",
        type="default",
        key="email_form",
        autocomplete="username email"
    )
    st.session_state['password'] = st.text_input(
        "Password",
        type="password",
        key="password_form",
        autocomplete="current-password"
    )
    submit = st.form_submit_button("Check Available Sessions")

if submit:
    if st.session_state['email'] and st.session_state['password']:
        print('✅Request for available sessions received', file=sys.stderr, flush=True)
        driver.get(url)
        print("✅Arrived at Derrimut Webpage", file=sys.stderr, flush=True)
        
        # Get upcoming booking dates from DynamoDB
        upcoming_dates = get_upcoming_dates()
        st.session_state['upcoming_dates'] = upcoming_dates
        st.write("### Upcoming Booking Dates")
        for date in st.session_state['upcoming_dates']:
            st.write(f"- {date}")
            
        # Get available sessions
        with st.spinner("Fetching available sessions..."):
            available_sessions = get_available_sessions(st.session_state['email'], st.session_state['password'])
            if available_sessions:
                st.session_state['available_sessions'] = available_sessions
            else:
                st.error("❌Could not fetch sessions. Please try again.")
    else:
        st.error("Please enter email and password")

if 'available_sessions' in st.session_state:
    # Extract unique available dates and sort them
    available_dates = [date for date, _, _ in st.session_state['available_sessions']]

    # Use a radio button for selecting a date
    selected_date_string = st.radio("Select a Date:", available_dates)
    st.session_state['selected_date_string'] = selected_date_string
    
    # Get available times for the selected date
    available_times = next(
        (times for date, times, _ in st.session_state['available_sessions'] if date == selected_date_string), 
        []
    )

    if available_times:
        # Show either radio buttons or a select box for time selection
        # selected_time = st.radio("Select a Time:", available_times)  # Use radio buttons
        selected_time = st.selectbox("Select a Time:", available_times)  # Alternative dropdown
        st.session_state['selected_time'] = selected_time

        if st.button("Schedule Booking"):
            if st.session_state['email'] and st.session_state['password'] and selected_date_string and selected_time:
                payload = {
                    "email": "mae.anuc@gmail.com",
                    "password": "Mind2907",
                    "scheduled_date_str": selected_date_string,
                    "scheduled_time_str": selected_time
                }

                response = requests.post(
                    API_GATEWAY_URL,
                    json=payload  
                )
                print(response.json())
                st.success("Booking scheduled successfully")
            else:
                st.error("Please fill in all fields")
    else:
        st.warning("No sessions available for the selected date.")
