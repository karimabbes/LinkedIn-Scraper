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

class LinkedInScraper:
    def __init__(self):
        # Set up ChromeDriver path
        driver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'drivers', 'chromedriver')
        if os.path.exists(driver_path):
            # Use local ChromeDriver if available
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service)
        else:
            # Fall back to system ChromeDriver
            self.driver = webdriver.Chrome()
        
        # Create config directory if it doesn't exist
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
    
    # Function to check if login was successful
    def is_login_successful(self):
        try:
            # Wait for the feed page to load (indicates successful login)
            WebDriverWait(self.driver, 100).until(
                EC.presence_of_element_located((By.CLASS_NAME, "global-nav"))
            )
            return True
        except TimeoutException:
            # Check for error messages that indicate login failure
            try:
                error_message = self.driver.find_element(By.CLASS_NAME, "form__error")
                print(f"Login failed: {error_message.text}")
                return False
            except NoSuchElementException:
                # If we can't find an error message, check if we're still on the login page
                if "login" in self.driver.current_url:
                    print("Login failed: Still on login page after timeout")
                    return False
                else:
                    # We're not on the login page and no error message, might be successful
                    return True
    
    def save_cookies(self, cookies, filename="linkedin_cookies.pkl"):
        # Create config directory if it doesn't exist
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Save cookies to file
        cookie_path = os.path.join(config_dir, filename)
        with open(cookie_path, 'wb') as f:
            pickle.dump(cookies, f)
        print(f"Cookies saved to {cookie_path}")
    
    def load_cookies(self, filename="linkedin_cookies.pkl"):
        # Check if cookies file exists
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        cookie_path = os.path.join(config_dir, filename)
        
        if not os.path.exists(cookie_path):
            print(f"No cookies file found at {cookie_path}")
            return None
        
        # Check if cookies are expired (older than 24 hours)
        if os.path.getmtime(cookie_path) < time.time() - 86400:  # 86400 seconds = 24 hours
            print("Cookies are expired (older than 24 hours)")
            return None
        
        # Load cookies from file
        try:
            with open(cookie_path, 'rb') as f:
                cookies = pickle.load(f)
            print(f"Cookies loaded from {cookie_path}")
            return cookies
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return None
    
    def use_existing_session(self):
        # Load cookies
        cookies = self.load_cookies()
        if not cookies:
            return False
        
        # Navigate to LinkedIn
        self.driver.get("https://www.linkedin.com/")
        
        # Add cookies to browser
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie: {e}")
        
        # Refresh page to apply cookies
        self.driver.refresh()
        
        # Check if login was successful
        return self.is_login_successful()
    
    def save_messages_to_csv(self, messages, filename=None):
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Generate filename with timestamp if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_contacts_{timestamp}.csv"
        
        # Save messages to CSV
        filepath = os.path.join(data_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'profile url', 'message', 'email', 'company', 'title'])
            for message in messages:
                writer.writerow([
                    message.get('name', ''),
                    message.get('profile_url', ''),
                    message.get('message', ''),
                    message.get('email', ''),
                    message.get('company', ''),
                    message.get('title', '')
                ])
        
        print(f"Saved {len(messages)} contacts to {filepath}")
        return filepath
    
    def message_contains_keywords(self, message_text, keywords):
        if not keywords:
            return True
        
        # Convert keywords to lowercase for case-insensitive matching
        keywords = [k.lower() for k in keywords]
        message_text = message_text.lower()
        
        # Check if any keyword is in the message
        return any(keyword in message_text for keyword in keywords)
    
    def extract_data_from_profile(self, messages):
        print("\nExtracting email addresses from profiles...")
        
        for i, message in enumerate(messages):
            print(f"Processing profile {i+1}/{len(messages)}: {message['profile_url']}")
            
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
                if not self.is_browser_window_open():
                    if not self.restart_browser_if_needed():
                        print("Failed to restart browser. Aborting email extraction.")
                        return messages
                
                # Navigate to the profile page
                self.driver.get(profile_url)
                time.sleep(3)
                
                # Check for Microsoft authentication error
                if self.handle_microsoft_auth_error():
                    print("Handled Microsoft authentication error, continuing with profile extraction...")
                
                # Extract the full name from the profile
                try:
                    # Look for the name in the profile header using a simpler h1 selector
                    name_element = WebDriverWait(self.driver, 5).until(
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
                    contact_info_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='overlay/contact-info']"))
                    )
                    contact_info_button.click()
                    time.sleep(2)
                    
                    contact_info = {}

                    # Try to find the contact info section
                    try:
                        # Look for the contact info container
                        contact_info_sections = self.driver.find_elements(By.CLASS_NAME, "pv-contact-info__contact-type")
                        
                        if not contact_info_sections:
                            print(f"No contact info sections found for {message['name']}")
                            # Try alternative selectors
                            contact_info_sections = self.driver.find_elements(By.CSS_SELECTOR, ".pv-contact-info__contact-type, .pv-contact-info__ci-container")
                        
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
                                email_element = WebDriverWait(self.driver, 3).until(
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
                        close_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
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
    
    def handle_microsoft_auth_error(self):
        try:
            # Check if there's an error message related to Microsoft authentication
            error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Microsoft') or contains(text(), 'authentication')]")
            if error_elements:
                print("Detected Microsoft authentication error. Attempting to work around...")
                
                # Try to refresh the page
                self.driver.refresh()
                time.sleep(5)
                
                # Try to click any "Skip" or "Continue" buttons that might appear
                try:
                    skip_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Skip') or contains(text(), 'Continue')]")
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
    
    def is_browser_window_open(self):
        try:
            # Try to get the current URL, which will raise an exception if the browser is closed
            self.driver.current_url
            return True
        except:
            return False
    
    def restart_browser_if_needed(self):
        if not self.is_browser_window_open():
            print("Browser window is closed. Restarting...")
            # Set up ChromeDriver path
            driver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'drivers', 'chromedriver')
            if os.path.exists(driver_path):
                # Use local ChromeDriver if available
                service = Service(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service)
            else:
                # Fall back to system ChromeDriver
                self.driver = webdriver.Chrome()
            return True
        return False
    
    def scrape_linkedin(self, use_cookies=True, keywords=None, max_threads=10):
        global driver
        
        # Default keywords if none provided
        if keywords is None:
            keywords = ["real estate", "agent", "immobilier"]
        elif isinstance(keywords, str):
            # Split comma-separated string into list
            keywords = [k.strip() for k in keywords.split(",")]
        
        print(f"Filtering messages for keywords: {', '.join(keywords)}")
        print(f"Maximum number of threads to process: {max_threads}")
        
        # Check if browser is open, restart if needed
        if not self.is_browser_window_open():
            self.restart_browser_if_needed()
        
        # Try to use cookies first (more reliable and less likely to trigger verification)
        if use_cookies:
            print("Attempting to use existing session via cookies...")
            if self.use_existing_session():
                print("Successfully loaded existing session!")
            else:
                print("Failed to use existing session. Falling back to login with credentials...")
                self.login_with_credentials()
        else:
            self.login_with_credentials()
        
        # Navigate to the Messaging section
        print("Navigating to LinkedIn Messaging...")
        try:
            self.driver.get("https://www.linkedin.com/messaging/")
            time.sleep(5)
            
            # Check for verification request after navigation
            self.handle_verification_request()
        except Exception as e:
            print(f"Error navigating to messaging page: {str(e)}")
            if "no such window" in str(e):
                self.restart_browser_if_needed()
                self.driver.get("https://www.linkedin.com/messaging/")
                time.sleep(5)
                self.handle_verification_request()
        
        # Scrape messages related to real estate professionals
        messages = []
        print("Looking for message threads...")
        
        try:
            # Find the message list container element
            message_list = self.driver.find_element(By.CLASS_NAME, "msg-conversations-container__conversations-list")

            chat_threads = self.driver.find_elements(By.CLASS_NAME, "msg-conversation-listitem__link")
            
            # Scroll to load more threads if necessary
            while len(chat_threads) < max_threads:
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", message_list)
                time.sleep(2)
                chat_threads = self.driver.find_elements(By.CLASS_NAME, "msg-conversation-listitem__link")
            
            
            if not chat_threads:
                print("No message threads found. The page structure might have changed or you might not have any messages.")
            else:
                print(f"Found {len(chat_threads)} message threads. Processing up to {max_threads}...")
                
                
                # Determine how many threads to process
                threads_to_process = min(len(chat_threads), max_threads)
                
                for i, thread in enumerate(chat_threads[:threads_to_process]):
                    print(f"Processing thread {i+1}/{threads_to_process}...")
                    
                    # Check if browser is still open before each thread
                    if not self.is_browser_window_open():
                        if not self.restart_browser_if_needed():
                            print("Failed to restart browser. Aborting scraping.")
                            return messages
                    
                    try:
                        thread.click()
                        time.sleep(3)
                        
                        try:
                            message_content = self.driver.find_element(By.CLASS_NAME, "msg-s-event-listitem__body").text  # Extract message content
                            
                            # Get the profile URL
                            try:
                                profile_link = self.driver.find_element(By.CLASS_NAME, "msg-thread__link-to-profile")
                                profile_url = profile_link.get_attribute("href")
                                
                                # Clean the profile URL if needed
                                if profile_url and not profile_url.startswith('http'):
                                    profile_url = f"https://www.linkedin.com{profile_url}"
                            except:
                                profile_url = None
                            
                            # Filter messages based on keywords
                            if self.message_contains_keywords(message_content, keywords):
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
                            if not self.restart_browser_if_needed():
                                print("Failed to restart browser. Aborting scraping.")
                                return messages
                        continue
        except Exception as e:
            print(f"Error finding message threads: {str(e)}")
            if "no such window" in str(e):
                if not self.restart_browser_if_needed():
                    print("Failed to restart browser. Aborting scraping.")
                    return messages
        
        # Print results
        if messages:
            # Extract emails from profiles
            messages = self.extract_data_from_profile(messages)
            
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
    
    def login_with_credentials(self):
        print("Attempting to log in to LinkedIn...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        username = self.driver.find_element(By.ID, "username")
        password = self.driver.find_element(By.ID, "password")
        username.send_keys(LINKEDIN_EMAIL)  # Using credentials from .env file
        password.send_keys(LINKEDIN_PASSWORD)  # Using credentials from .env file
        password.send_keys(Keys.RETURN)
        time.sleep(5)
        
        # Check if login was successful
        if self.is_login_successful():
            print("Authentication successful!")
            # Save cookies for future use
            self.save_cookies(self.driver.get_cookies())
            
            # Try to handle any verification requests
            self.handle_verification_request()
        else:
            print("Authentication failed. Please check your credentials and try again.")
            return False
        
        return True
    
    def handle_verification_request(self):
        try:
            # Check if there's a verification code input field
            verification_elements = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'pin') or contains(@id, 'verification') or contains(@id, 'code')]")
            if verification_elements:
                print("LinkedIn is requesting verification. Please enter the verification code manually.")
                print("After entering the code, the script will continue automatically.")
                
                # Wait for the user to enter the verification code
                # We'll wait for the verification input to disappear or for the feed page to load
                try:
                    WebDriverWait(self.driver, 300).until(
                        lambda d: (
                            len(d.find_elements(By.XPATH, "//input[contains(@id, 'pin') or contains(@id, 'verification') or contains(@id, 'code')]")) == 0 or
                            "feed" in d.current_url
                        )
                    )
                    print("Verification completed or timed out. Continuing...")
                    
                    # Save the updated cookies after verification
                    self.save_cookies(self.driver.get_cookies())
                    return True
                except TimeoutException:
                    print("Verification timed out. Please try again later.")
                    return False
        except Exception as e:
            print(f"Error handling verification request: {e}")
        
        return True

# For backward compatibility, create a global instance
driver = None

# Main execution
if __name__ == "__main__":
    # Set to True to use existing session via cookies, False to login with credentials
    USE_COOKIES = True
    
    try:
        scraper = LinkedInScraper()
        messages = scraper.scrape_linkedin(use_cookies=USE_COOKIES)
    finally:
        scraper.driver.quit()


