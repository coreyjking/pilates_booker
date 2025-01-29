import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Load environment variables
load_dotenv()
username = os.getenv('email')
password = os.getenv('password')

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument('--log-level=3')  # Set log level to ERROR only
chrome_options.add_argument('--disable-logging')  # Disable logging
chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Disable logging in console

# Start WebDriver with options
driver = webdriver.Chrome(options=chrome_options)
url = "https://www.derrimut247.com.au/pages/reformer-pilates-thomastown"
driver.get(url)

# Get user input
target_day = input("Enter the target day (YYYY-MM-DD format, e.g., '2025-01-21'): ").strip()
target_time = input("Enter the target time (e.g., '6:30 AM'): ").strip()



def restart_driver():
    """Restart the WebDriver session if needed."""
    global driver
    try:
        driver.quit()
    except:
        pass
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    print("WebDriver restarted.")


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
            print("Opening My Account.")
            # Use JavaScript click as a fallback if regular click is intercepted
            driver.execute_script("arguments[0].click();", account_button)
            time.sleep(5)
            
            # Check if login form appears (indicating logged out)
            if driver.find_elements(By.ID, "username"):
                print("Not logged in. Logging in now...")
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))

                # Fill login details
                username_input = driver.find_element(By.ID, "username")
                password_input = driver.find_element(By.ID, "password")
                submit_button = driver.find_element(By.XPATH, "/html/body/div[1]/span/div/div/div/main/div/div/form/section[2]/button")

                username_input.send_keys(username)
                password_input.send_keys(password)
                submit_button.click()
                time.sleep(4)

                print("Logged in successfully.")
                driver.get(url)
            else:
                print("Already logged in.")
                driver.refresh()
                driver.get(url)
        else:
            print("Login button not found. Trying to refresh and check again.")
            driver.get(url)
    except Exception as e:
        print(f"Login verification error: {e}")
        driver.get(url)


# **Main Loop: Monitor & Book Sessions**
try:
    print("Starting to monitor the schedule... Press Ctrl+C to stop.")

    while True:
        confirm_logged_in()  # Ensure user is logged in
        booked = check_and_book(target_day, target_time)  # Attempt booking

        if booked:
            print("Booking successful! Exiting script.")
            break  # Stop after booking is complete

        print("Waiting for 30 seconds before rechecking...")
        time.sleep(30)  # Retry after delay

finally:
    driver.quit()
