from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import sys
import os
import pickle
import csv
from datetime import datetime
import re

# Add the parent directory to the path to import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.credentials import LINKEDIN_EMAIL, LINKEDIN_PASSWORD

# Set up ChromeDriver path
driver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'drivers', 'chromedriver')
if os.path.exists(driver_path):
    # Use local ChromeDriver if available
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)
else:
    # Fall back to system ChromeDriver
    driver = webdriver.Chrome()

# Function to check if login was successful
def is_login_successful():
    try:
        # Wait for the feed page to load (indicates successful login)
        WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.CLASS_NAME, "global-nav"))
        )
        return True
    except TimeoutException:
        # Check for error messages that indicate login failure
        try:
            error_message = driver.find_element(By.CLASS_NAME, "form__error")
            print(f"Login failed: {error_message.text}")
            return False
        except NoSuchElementException:
            # If we can't find an error message, check if we're still on the login page
            if "login" in driver.current_url:
                print("Login failed: Still on login page after timeout")
                return False
            else:
                # We're not on the login page and no error message, might be successful
                return True

# Function to save cookies to a file
def save_cookies(cookies, filename="linkedin_cookies.pkl"):
    # Create config directory if it doesn't exist
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # Save cookies to the config directory
    filepath = os.path.join(config_dir, filename)
    with open(filepath, "wb") as f:
        pickle.dump(cookies, f)
    print(f"Cookies saved to {filepath}")

# Function to load cookies from a file
def load_cookies(filename="linkedin_cookies.pkl"):
    try:
        # Look for cookies in the config directory
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        filepath = os.path.join(config_dir, filename)
        
        with open(filepath, "rb") as f:
            cookies = pickle.load(f)
        print(f"Cookies loaded from {filepath}")
        return cookies
    except FileNotFoundError:
        print(f"Cookie file {filename} not found")
        return None

# Function to use existing session via cookies
def use_existing_session():
    cookies = load_cookies()
    if not cookies:
        return False
    
    # First navigate to LinkedIn domain (required before adding cookies)
    driver.get("https://www.linkedin.com")
    time.sleep(2)
    
    # Add cookies to the browser
    for cookie in cookies:
        try:
            # Check if cookie is expired
            if 'expiry' in cookie and cookie['expiry'] < time.time():
                continue
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error adding cookie: {e}")
    
    # Refresh the page to apply cookies
    driver.refresh()
    time.sleep(3)
    
    # Check if we're logged in
    return is_login_successful()

# Function to save messages to CSV
def save_messages_to_csv(messages, filename=None):
    if not messages:
        print("No messages to save to CSV.")
        return
    
    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_messages_{timestamp}.csv"
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Full path to the CSV file
    filepath = os.path.join(data_dir, filename)
    
    # Write messages to CSV
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'message', 'profile_url', 'email', 'website']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for message in messages:
            writer.writerow(message)
    
    print(f"Messages saved to {filepath}")
    return filepath

# Function to check if message contains any of the keywords
def message_contains_keywords(message_text, keywords):
    message_text = message_text.lower()
    for keyword in keywords:
        if keyword.strip().lower() in message_text:
            return True
    return False

# Function to extract the email from the profile
def extract_data_from_profile(messages):
    print("\nExtracting email addresses from profiles...")
    
    for i, message in enumerate(messages):
        print(f"Processing profile {i+1}/{len(messages)}: {message['name']}")
        
        # Check if profile_url is valid
        if not message.get('profile_url') or not isinstance(message['profile_url'], str):
            print(f"Invalid profile URL for {message['name']}, skipping email extraction")
            message['email'] = None
            message['website'] = None
            continue
        
        # Clean the profile URL if needed
        profile_url = message['profile_url']
        if not profile_url.startswith('http'):
            profile_url = f"https://www.linkedin.com{profile_url}"
        
        try:
            # Check if browser is still open
            if not is_browser_window_open():
                if not restart_browser_if_needed():
                    print("Failed to restart browser. Aborting email extraction.")
                    return messages
            
            # Navigate to the profile page
            driver.get(profile_url)
            time.sleep(3)
            
            # Check for Microsoft authentication error
            if handle_microsoft_auth_error():
                print("Handled Microsoft authentication error, continuing with profile extraction...")
            
            # Extract the full name from the profile
            try:
                # Look for the name in the profile header using a simpler h1 selector
                name_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
                full_name = name_element.text.strip()
                if full_name:
                    message['name'] = full_name
                    print(f"Found full name: {full_name}")
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Could not extract full name: {str(e)}")
            
            # Try to find the contact info button
            try:
                # Look for the contact info button with a more reliable selector
                contact_info_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='overlay/contact-info']"))
                )
                contact_info_button.click()
                time.sleep(2)
                
                contact_info = {}

                # Try to find the contact info section
                try:
                    # Look for the contact info container
                    contact_info_sections = driver.find_elements(By.CLASS_NAME, "pv-contact-info__contact-type")
                    
                    if not contact_info_sections:
                        print(f"No contact info sections found for {message['name']}")
                        # Try alternative selectors
                        contact_info_sections = driver.find_elements(By.CSS_SELECTOR, ".pv-contact-info__contact-type, .pv-contact-info__ci-container")
                    
                    # Process each contact info section
                    for section in contact_info_sections:
                        # First try to find <a> tags (links)
                        links = section.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            try:
                                href = link.get_attribute("href")
                                if href:
                                    if "mailto:" in href:  # Extract email
                                        email = href.replace("mailto:", "").strip()
                                        if re.match(r"[^@]+@[^@]+\.[^@]+", email):  # Validate email format
                                            contact_info["email"] = email
                                            print(f"Found email for {message['name']}: {email}")
                                    elif "http" in href:  # Extract website or social media link
                                        if "linkedin.com" not in href:  # Exclude LinkedIn URLs
                                            contact_info["website"] = href
                                            print(f"Found website for {message['name']}: {href}")
                            except Exception as e:
                                print(f"Error processing link: {str(e)}")
                        
                        # Then try to find <span> tags (text content)
                        spans = section.find_elements(By.TAG_NAME, "span")
                        for span in spans:
                            try:
                                text = span.text.strip()
                                if text:
                                    # Check if it looks like an email
                                    if re.match(r"[^@]+@[^@]+\.[^@]+", text):
                                        contact_info["email"] = text
                                        print(f"Found email in span for {message['name']}: {text}")
                                    # Check if it looks like a website
                                    elif text.startswith(("http://", "https://", "www.")):
                                        if "linkedin.com" not in text:  # Exclude LinkedIn URLs
                                            contact_info["website"] = text
                                            print(f"Found website in span for {message['name']}: {text}")
                            except Exception as e:
                                print(f"Error processing span: {str(e)}")
                    
                    # If no email found in links or spans, try the old method as fallback
                    if "email" not in contact_info:
                        try:
                            email_element = WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".ci-email .pv-contact-info__ci-container"))
                            )
                            email = email_element.text.strip()
                            
                            # Validate email format
                            if re.match(r"[^@]+@[^@]+\.[^@]+", email):
                                contact_info["email"] = email
                                print(f"Found email using fallback method for {message['name']}: {email}")
                        except (TimeoutException, NoSuchElementException):
                            pass
                    
                except Exception as e:
                    print(f"Error extracting contact info for {message['name']}: {str(e)}")
                
                # Update message with contact info
                message['email'] = contact_info.get("email")
                message['website'] = contact_info.get("website")
                
                # Close the contact info overlay if it's open
                try:
                    close_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                    close_button.click()
                    time.sleep(1)
                except:
                    pass
                
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                print(f"Could not access contact info for {message['name']}")
                message['email'] = None
                message['website'] = None
        
        except Exception as e:
            print(f"Error extracting email for {message['name']}: {str(e)}")
            message['email'] = None
            message['website'] = None
    
    return messages

# Function to handle Microsoft authentication error
def handle_microsoft_auth_error():
    try:
        # Check if there's an error message related to Microsoft authentication
        error_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Microsoft') or contains(text(), 'authentication')]")
        if error_elements:
            print("Detected Microsoft authentication error. Attempting to work around...")
            
            # Try to refresh the page
            driver.refresh()
            time.sleep(5)
            
            # Try to click any "Skip" or "Continue" buttons that might appear
            try:
                skip_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Skip') or contains(text(), 'Continue')]")
                for button in skip_buttons:
                    if button.is_displayed():
                        button.click()
                        time.sleep(2)
            except:
                pass
            
            return True
    except:
        pass
    return False

# Function to check if the browser window is still open
def is_browser_window_open():
    try:
        # Try to get the current URL - this will fail if the window is closed
        driver.current_url
        return True
    except Exception:
        return False

# Function to restart the browser if needed
def restart_browser_if_needed():
    global driver
    if not is_browser_window_open():
        print("Browser window is closed. Restarting browser...")
        try:
            driver.quit()
        except:
            pass
        
        # Reinitialize the driver
        if os.path.exists(driver_path):
            # Use local ChromeDriver if available
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service)
        else:
            # Fall back to system ChromeDriver
            driver = webdriver.Chrome()
        
        print("Browser restarted successfully.")
        return True
    return False

# Main function to scrape LinkedIn
def scrape_linkedin(use_cookies=True, keywords=None, max_threads=10):
    global driver
    
    # Default keywords if none provided
    if keywords is None:
        keywords = ["real estate", "agent"]
    elif isinstance(keywords, str):
        # Split comma-separated string into list
        keywords = [k.strip() for k in keywords.split(",")]
    
    print(f"Filtering messages for keywords: {', '.join(keywords)}")
    print(f"Maximum number of threads to process: {max_threads}")
    
    # Check if browser is open, restart if needed
    if not is_browser_window_open():
        restart_browser_if_needed()
    
    # Try to use cookies first (more reliable and less likely to trigger verification)
    if use_cookies:
        print("Attempting to use existing session via cookies...")
        if use_existing_session():
            print("Successfully loaded existing session!")
        else:
            print("Failed to use existing session. Falling back to login with credentials...")
            login_with_credentials()
    else:
        login_with_credentials()
    
    # Navigate to the Messaging section
    print("Navigating to LinkedIn Messaging...")
    try:
        driver.get("https://www.linkedin.com/messaging/")
        time.sleep(5)
        
        # Check for verification request after navigation
        handle_verification_request()
    except Exception as e:
        print(f"Error navigating to messaging page: {str(e)}")
        if "no such window" in str(e):
            restart_browser_if_needed()
            driver.get("https://www.linkedin.com/messaging/")
            time.sleep(5)
            handle_verification_request()
    
    # Scrape messages related to real estate professionals
    messages = []
    print("Looking for message threads...")
    
    try:
        chat_threads = driver.find_elements(By.CLASS_NAME, "msg-conversation-listitem__link")
        
        if not chat_threads:
            print("No message threads found. The page structure might have changed or you might not have any messages.")
        else:
            print(f"Found {len(chat_threads)} message threads. Processing up to {max_threads}...")
            
            # Determine how many threads to process
            threads_to_process = min(len(chat_threads), max_threads)
            
            for i, thread in enumerate(chat_threads[:threads_to_process]):
                print(f"Processing thread {i+1}/{threads_to_process}...")
                
                # Check if browser is still open before each thread
                if not is_browser_window_open():
                    if not restart_browser_if_needed():
                        print("Failed to restart browser. Aborting scraping.")
                        return messages
                
                try:
                    thread.click()
                    time.sleep(3)
                    
                    try:
                        message_content = driver.find_element(By.CLASS_NAME, "msg-s-event-listitem__body").text  # Extract message content
                        
                        # Get the profile URL
                        try:
                            profile_link = driver.find_element(By.CLASS_NAME, "msg-thread__link-to-profile")
                            profile_url = profile_link.get_attribute("href")
                            
                            # Clean the profile URL if needed
                            if profile_url and not profile_url.startswith('http'):
                                profile_url = f"https://www.linkedin.com{profile_url}"
                        except:
                            profile_url = None
                        
                        # Filter messages based on keywords
                        if message_contains_keywords(message_content, keywords):
                            messages.append({
                                "message": message_content, 
                                "profile_url": profile_url,
                                "name": None, 
                                "email": None,  # Initialize email field
                                "website": None  # Initialize website field
                            })
                            print(f"Found message matching keywords from: {profile_url}")
                    except NoSuchElementException as e:
                        print(f"Error extracting message data: {e}")
                        continue
                except Exception as e:
                    print(f"Error processing thread: {str(e)}")
                    if "no such window" in str(e):
                        if not restart_browser_if_needed():
                            print("Failed to restart browser. Aborting scraping.")
                            return messages
                    continue
    except Exception as e:
        print(f"Error finding message threads: {str(e)}")
        if "no such window" in str(e):
            if not restart_browser_if_needed():
                print("Failed to restart browser. Aborting scraping.")
                return messages
    
    # Print results
    if messages:
        # Extract emails from profiles
        messages = extract_data_from_profile(messages)
        
        print(f"\nFound {len(messages)} messages matching your keywords:")
        for msg in messages:
            print(f"- From: {msg['name']}")
            print(f"  Message: {msg['message'][:100]}...")  # Print first 100 chars
            print(f"  Profile: {msg['profile_url']}")
            print(f"  Email: {msg['email'] or 'Not found'}")
            print(f"  Website: {msg['website'] or 'Not found'}")
            print()
    else:
        print("\nNo messages matching your keywords were found.")
    
    return messages

# Function to login with credentials
def login_with_credentials():
    print("Attempting to log in to LinkedIn...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")
    username.send_keys(LINKEDIN_EMAIL)  # Using credentials from .env file
    password.send_keys(LINKEDIN_PASSWORD)  # Using credentials from .env file
    password.send_keys(Keys.RETURN)
    time.sleep(5)
    
    # Check if login was successful
    if is_login_successful():
        print("Authentication successful!")
        # Save cookies for future use
        save_cookies(driver.get_cookies())
        
        # Try to handle any verification requests
        handle_verification_request()
    else:
        print("Authentication failed. Please check your credentials and try again.")
        return False
    
    return True

# Function to handle verification requests
def handle_verification_request():
    try:
        # Check if there's a verification code input field
        verification_elements = driver.find_elements(By.XPATH, "//input[contains(@id, 'pin') or contains(@id, 'verification') or contains(@id, 'code')]")
        if verification_elements:
            print("LinkedIn is requesting verification. Please enter the verification code manually.")
            print("After entering the code, the script will continue automatically.")
            
            # Wait for the user to enter the verification code
            # We'll wait for the verification input to disappear or for the feed page to load
            try:
                WebDriverWait(driver, 300).until(
                    lambda d: (
                        len(d.find_elements(By.XPATH, "//input[contains(@id, 'pin') or contains(@id, 'verification') or contains(@id, 'code')]")) == 0 or
                        "feed" in d.current_url
                    )
                )
                print("Verification completed or timed out. Continuing...")
                
                # Save the updated cookies after verification
                save_cookies(driver.get_cookies())
                return True
            except TimeoutException:
                print("Verification timed out. Please try again later.")
                return False
    except Exception as e:
        print(f"Error handling verification request: {e}")
    
    return True

# Main execution
if __name__ == "__main__":
    # Set to True to use existing session via cookies, False to login with credentials
    USE_COOKIES = True
    
    try:
        messages = scrape_linkedin(use_cookies=USE_COOKIES)
    finally:
        driver.quit()


