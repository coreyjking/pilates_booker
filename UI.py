import os
import sys
import streamlit as st
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

#Setup
#Get selenium URL set in dockerfile - this is an env file on the container, where this script will be running
SELENIUM_WEBDRIVER_URL = f'{os.getenv("SELENIUM_URL")}/wd/hub'
url = "https://www.derrimut247.com.au/pages/reformer-pilates-thomastown"
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--headless")
chrome_path = "/usr/bin/google-chrome"  # Path to Chrome binary
driver_path = "/usr/bin/chromedriver"  # Path to Chromedriver
service = Service(driver_path)
chrome_options.binary_location = chrome_path


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
    available_sessions = []

    for i, date_elem in enumerate(date_elements):
        # Extract the date text
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
            available_sessions.append((the_date, times_for_date))

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


def check_and_book(target_day, target_time):
    """Check for available sessions and attempt booking."""
    try:
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Locate the specific date section
        target_date_class = f"date-{target_day}"
        print(f"Looking for session date: {target_date_class}")

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, target_date_class))
        )
        date_section = driver.find_element(By.CLASS_NAME, target_date_class)

        # Find all session elements under the correct date
        sessions = date_section.find_elements(By.XPATH, "following-sibling::div[contains(@class, 'bw-session')]")
        if not sessions:
            print(f"No sessions found for {target_day}.")
            return False

        print(f"Total sessions found for {target_day}: {len(sessions)}")

        for session in sessions:
            try:
                # Extract session time
                time_element = session.find_element(By.CLASS_NAME, "hc_starttime")
                session_time = time_element.text.strip()
                print(f"Checking session time: {session_time}")

                if session_time == target_time:
                    print(f"Session match found for {target_day} at {session_time}")

                    # Locate the "Book" button
                    book_buttons = session.find_elements(By.CLASS_NAME, "bw-widget__signup-now")
                    
                    if not book_buttons:
                        print("No booking button found for this session")
                        continue
                    
                    if book_buttons[0].text.strip() != "Book":
                        print("Session is not available for booking")
                        continue

                    # Scroll the session into view before clicking
                    print("Scrolling to booking button...")
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", book_buttons[0])
                    time.sleep(1)  # Wait for scroll to complete

                    print("Found 'Book' button. Proceeding to click.")
                    book_buttons[0].click()

                    # Wait for the iframe to load
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "mindbody_branded_web_cart_modal"))
                    )

                    # Switch to iframe
                    driver.switch_to.frame("mindbody_branded_web_cart_modal")
                    print("Switched to iframe.")

                    # Click confirm button
                    confirm_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "cart-cta-disable-me-on-click"))
                    )
                    confirm_button.click()
                    print("Clicked 'Confirm' button.")
                    time.sleep(10)

                    # Switch back to main content
                    driver.switch_to.default_content()
                    print("Switched back to main page context.")

                    return True  # Booking complete

            except Exception as e:
                print(f"Error processing session: {e}")

        print(f"No booking available for {target_day} at {target_time}.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_and_book_loop():
    try:
        print("Starting to monitor the schedule... Press Ctrl+C to stop.", file=sys.stderr, flush=True)
        while True:
            confirm_logged_in()  # Ensure user is logged in
            booked = check_and_book(selected_date, selected_time)  # Attempt booking

            if booked:
                print("Booking successful! Exiting script.", file=sys.stderr, flush=True)
                break  # Stop after booking is complete

            print("Waiting for 30 seconds before rechecking...", file=sys.stderr, flush=True)
            time.sleep(30)  # Retry after delay
    finally:
        driver.quit()


# Connect to Selenium webdriver
if 'driver' not in st.session_state:
    st.session_state['driver'] = None

if not st.session_state['driver']:
    for attempt in range(10):  # Try up to 10 times
        try:
            st.session_state['driver'] = webdriver.Remote(
                command_executor=SELENIUM_WEBDRIVER_URL,
                options=chrome_options
            )
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
st.title("Pilates Class Booking Bot")

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
        print('✅Submit received', file=sys.stderr, flush=True)
        driver.get(url)
        print("✅Arrived at Derrimut Webpage", file=sys.stderr, flush=True)
        with st.spinner("Fetching available sessions..."):
            available_sessions = get_available_sessions(st.session_state['email'], st.session_state['password'])
            if available_sessions:
                st.session_state['available_sessions'] = available_sessions
                st.success("✅Sessions fetched successfully!")
            else:
                st.error("❌Could not fetch sessions. Please try again.")
    else:
        st.error("Please enter email and password")

if 'available_sessions' in st.session_state:
    # Extract unique available dates and sort them
    available_dates = [date for date, _ in st.session_state['available_sessions']]

    # Use a radio button for selecting a date
    selected_date = st.radio("Select a Date:", available_dates)
    
    # Get available times for the selected date
    available_times = next((times for date, times in st.session_state['available_sessions'] if date == selected_date), [])

    if available_times:
        # Show either radio buttons or a select box for time selection
        # selected_time = st.radio("Select a Time:", available_times)  # Use radio buttons
        selected_time = st.selectbox("Select a Time:", available_times)  # Alternative dropdown

        if st.button("Start Monitoring"):
            if st.session_state['email'] and st.session_state['password'] and selected_date and selected_time:
                check_and_book_loop()
            else:
                st.error("Please fill in all fields")
    else:
        st.warning("No sessions available for the selected date.")
