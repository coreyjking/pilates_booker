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

# --------------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------------

API_GATEWAY_URL = "https://0wk32adhz8.execute-api.ap-southeast-2.amazonaws.com/pilatesStage/schedule_booker"
url = "https://www.derrimut247.com.au/pages/reformer-pilates-thomastown"

# Load secrets for AWS from Streamlit secrets
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
region = st.secrets["aws"]["region_name"]

# DynamoDB table
dynamodb = boto3.resource(
    'dynamodb',
    region_name=region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)
table = dynamodb.Table('pilatesBookings')

# --------------------------------------------------------------------------------
# SELENIUM SETUP
# --------------------------------------------------------------------------------

@st.cache_resource
def get_webdriver():
    """Initialize the Chrome WebDriver with headless options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        service = Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        )
        driver = webdriver.Chrome(service=service, options=chrome_options)
        st.session_state['driver'] = driver
    except Exception as e:
        st.error(f"Error initializing Selenium WebDriver: {e}")
        return None

# --------------------------------------------------------------------------------
# SCRAPE: GET AVAILABLE SESSIONS
# --------------------------------------------------------------------------------

def get_available_sessions(email, password):
    """
    Collects available days and times from the webpage.
    
    Returns a list of tuples: 
      [
        ( "2025-02-15", ["5:00 AM","5:30 AM"], "Saturday, February 15" ),
        ...
      ]
    """
    driver = st.session_state['driver']
    
    # Let the page load
    time.sleep(5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # Wait for date elements
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'bw-widget__date')]"))
    )
    
    date_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'bw-widget__date')]")
    st.session_state['date_elements'] = date_elements
    
    available_sessions = []
    
    for i, date_elem in enumerate(date_elements):
        # Example of class: "bw-widget__date date-2025-02-15"
        elem_classes = date_elem.get_attribute("class")
        class_parts = elem_classes.split()
        if len(class_parts) < 2:
            continue
        
        # e.g. "date-2025-02-15"
        class_date = class_parts[1]
        # Raw date: "2025-02-15"
        raw_date = class_date.replace("date-", "").strip()
        
        # User-friendly text: e.g. "Saturday, February 15"
        user_facing_text = date_elem.text.strip()
        
        if not raw_date:
            continue
        
        # Get sessions
        date_xpath = f"(//div[contains(@class, 'bw-widget__date')])[{i+1}]"
        session_elements = driver.find_elements(
            By.XPATH, f"{date_xpath}/following-sibling::div[contains(@class, 'bw-session')]"
        )
        
        times_for_date = []
        for session in session_elements:
            try:
                time_elem = session.find_element(By.CLASS_NAME, "hc_starttime")
                times_for_date.append(time_elem.text.strip())
            except Exception as ex:
                print(f"Skipping session due to error: {ex}", file=sys.stderr, flush=True)
        
        if times_for_date:
            # store (raw_date, times_for_date, user_facing_text)
            available_sessions.append((raw_date, times_for_date, user_facing_text))
    
    return available_sessions

# --------------------------------------------------------------------------------
# LOGIN CHECK
# --------------------------------------------------------------------------------

def confirm_logged_in():
    """
    Checks if user is logged in, if not logs them in.
    """
    driver = st.session_state['driver']
    try:
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        account_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "bw-header__account-link"))
        )
        
        if account_button.text.strip() == "My Account":
            print("Opening My Account.", file=sys.stderr, flush=True)
            driver.execute_script("arguments[0].click();", account_button)
            time.sleep(5)
            
            if driver.find_elements(By.ID, "username"):
                print("Not logged in. Logging in now...", file=sys.stderr, flush=True)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                username_input = driver.find_element(By.ID, "username")
                password_input = driver.find_element(By.ID, "password")
                submit_button = driver.find_element(
                    By.XPATH, "/html/body/div[1]/span/div/div/div/main/div/div/form/section[2]/button"
                )
                
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
            print("Login button not found. Refreshing...", file=sys.stderr, flush=True)
            driver.get(url)
    except Exception as e:
        print(f"Login verification error: {e}", file=sys.stderr, flush=True)
        driver.get(url)

# --------------------------------------------------------------------------------
# OPTIONAL: GET UPCOMING DATES FROM DYNAMO (not mandatory for the question)
# --------------------------------------------------------------------------------

def get_upcoming_dates():
    """
    Example: Queries future bookings from DynamoDB by email & date range
    """
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    current_time = datetime.now(melbourne_tz)
    
    start_date = current_time.strftime('%Y-%m-%d')
    end_date   = (current_time + timedelta(days=30)).strftime('%Y-%m-%d')
    
    if 'email' not in st.session_state:
        return []
    
    email = st.session_state['email']
    
    print(f"Querying bookings for {email} between {start_date} and {end_date}")
    
    response = table.query(
        KeyConditionExpression=Key('email').eq(email) & 
                               Key('scheduled_date').between(start_date, end_date)
    )
    
    dates = [item['booking_timestamp'] for item in response.get('Items', [])]
    return dates

# --------------------------------------------------------------------------------
# MAIN STREAMLIT APP
# --------------------------------------------------------------------------------

if 'driver' not in st.session_state:
    st.session_state['driver'] = None

if not st.session_state['driver']:
    for attempt in range(10):
        try:
            get_webdriver()
            print("✅ Selenium started successfully!", file=sys.stderr, flush=True)
            break
        except WebDriverException:
            print(f"❌ Selenium cannot connect. Retrying {attempt+1}/10...", file=sys.stderr, flush=True)
            time.sleep(5)
    else:
        raise RuntimeError("❌ Selenium did not start in time.")

driver = st.session_state['driver']
st.title("Pilates Booking Assistant")

with st.form("login_form"):
    st.session_state['email'] = st.text_input("Email", key="email_form")
    st.session_state['password'] = st.text_input("Password", type="password", key="password_form")
    submit = st.form_submit_button("Check Available Sessions")

if submit:
    if st.session_state['email'] and st.session_state['password']:
        print("✅ Request for available sessions received", file=sys.stderr, flush=True)
        driver.get(url)
        print("✅ Arrived at Derrimut Webpage", file=sys.stderr, flush=True)
        
        # (Optional) Confirm login
        confirm_logged_in()
        
        # (Optional) Get upcoming bookings from Dynamo
        upcoming_dates = get_upcoming_dates()
        st.session_state['upcoming_dates'] = upcoming_dates
        st.write("### Upcoming Booking Dates (Dynamo)")
        for d in upcoming_dates:
            st.write(f"- {d}")
        
        # Now get sessions from the website
        with st.spinner("Fetching available sessions..."):
            sessions = get_available_sessions(st.session_state['email'], st.session_state['password'])
            if sessions:
                st.session_state['available_sessions'] = sessions
            else:
                st.error("❌ Could not fetch sessions. Please try again.")
    else:
        st.error("Please enter email and password")

# After we have available_sessions
if 'available_sessions' in st.session_state:
    # Build a date_map: user_facing_label -> raw_date
    sessions = st.session_state['available_sessions']
    # e.g. sessions = [("2025-02-15", ["5:00 AM","5:30 AM"], "Saturday, February 15"), ...]
    
    # We want to display user_facing_text but store the raw date
    date_map = {}
    for (raw_date, times, user_text) in sessions:
        date_map[user_text] = raw_date
    
    if date_map:
        selected_label = st.radio("Select a Date:", list(date_map.keys()))
        selected_raw_date = date_map[selected_label]  # "2025-02-15"
        
        # Find the times for this raw date
        available_times = next(
            (t_list for (rd, t_list, utxt) in sessions if rd == selected_raw_date),
            []
        )
        
        if available_times:
            selected_time = st.selectbox("Select a Time:", available_times)
            st.session_state['selected_time'] = selected_time
            
            if st.button("Schedule Booking"):
                if st.session_state['email'] and st.session_state['password'] and selected_raw_date and selected_time:
                    payload = {
                        "email": st.session_state['email'],
                        "password": st.session_state['password'],
                        # Use the raw date internally
                        "scheduled_date_str": selected_raw_date,
                        "scheduled_time_str": selected_time
                    }
                    
                    response = requests.post(API_GATEWAY_URL, json=payload)
                    print(response.json())
                    st.success("Booking scheduled successfully!")
                else:
                    st.error("Please fill in all fields")
        else:
            st.warning("No sessions available for that date.")
    else:
        st.info("No dates found to display.")
