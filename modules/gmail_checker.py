import os
import pickle
import datetime
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GmailChecker:
    """
    Class to check if an email has already been sent to a contact in Gmail.
    """
    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_path=None):
        """
        Initialize the Gmail checker.
        
        Args:
            credentials_path (str, optional): Path to the credentials.json file
        """
        self.credentials_path = credentials_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "config", 
            "credentials.json"
        )
        self.token_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "config", 
            "token.pickle"
        )
        self.service = None
    
    def authenticate(self):
        """
        Authenticate with Gmail API.
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            creds = None
            
            # The file token.pickle stores the user's access and refresh tokens
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        print(f"Credentials file not found at {self.credentials_path}")
                        print("Please download your credentials.json file from Google Cloud Console")
                        print("and place it in the config directory.")
                        return False
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, self.SCOPES)
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        print(f"Error during OAuth flow: {e}")
                        print("Please make sure you have the required packages installed:")
                        print("pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
                        return False
                
                # Save the credentials for the next run
                os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def check_if_email_sent(self, email_address, days_back=30):
        """
        Check if an email has been sent to the given address in the last X days.
        
        Args:
            email_address (str): The email address to check
            days_back (int): Number of days to look back in the sent emails
            
        Returns:
            bool: True if an email has been sent to the address, False otherwise
        """
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Create a query to search for sent emails to the given address
            # Adding 'in:sent' to specifically search in the SENT folder
            after_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days_back)).strftime('%Y/%m/%d')

            # Only look in the "Sent" folder
            query = f"to:{email_address} after:{after_date}"
            
            # Search for messages matching the query
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                labelIds=['SENT'],
                maxResults=10
            ).execute()
            
            # Check if any messages were found
            messages = results.get('messages', [])
            
            if not messages:
                return False
            
            # Check the first few messages to confirm they were actually sent by the user
            for message in messages[:3]:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['From']
                ).execute()
                
                # Check if the message was sent by the user
                headers = msg.get('payload', {}).get('headers', [])
                for header in headers:
                    if header['name'].lower() == 'from':
                        # If the from address matches the user's email, it was sent by the user
                        if '@gmail.com' in header['value'].lower():
                            return True
            
            return False
        except Exception as e:
            print(f"Error checking sent emails: {e}")
            return False
    
    def get_last_email_date(self, email_address, days_back=30):
        """
        Get the date of the last email sent to the given email address.
        
        Args:
            email_address (str): The email address to check
            days_back (int): Number of days to look back in the sent emails
            
        Returns:
            str: Date of the last email sent, or None if no email was found
        """
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            # Create a query to search for sent emails to the given address
            # Adding 'in:sent' to specifically search in the SENT folder
            query = f"to:{email_address} in:sent after:{days_back}d"
            
            # Search for messages matching the query
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=1
            ).execute()
            
            # Check if any messages were found
            messages = results.get('messages', [])
            
            if not messages:
                return None
            
            # Get the date of the most recent message
            msg = self.service.users().messages().get(
                userId='me',
                id=messages[0]['id'],
                format='metadata',
                metadataHeaders=['Date']
            ).execute()
            
            # Extract the date from the headers
            headers = msg.get('payload', {}).get('headers', [])
            for header in headers:
                if header['name'].lower() == 'date':
                    return header['value']
            
            return None
        except Exception as e:
            print(f"Error getting last email date: {e}")
            return None 