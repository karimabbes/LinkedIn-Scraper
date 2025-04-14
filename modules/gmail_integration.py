import os
import pickle
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GmailIntegration:
    """
    Class to handle Gmail API integration for saving emails as drafts.
    """
    
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    
    def __init__(self, credentials_path=None):
        """
        Initialize the Gmail integration.
        
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
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build the Gmail service
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def create_draft(self, to, subject, body, from_email=None):
        """
        Create a draft email in Gmail.
        
        Args:
            to (str): Recipient email address
            subject (str): Email subject
            body (str): Email body
            from_email (str, optional): Sender email address
            
        Returns:
            dict: Draft object if successful, None otherwise
        """
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if from_email:
                message['from'] = from_email
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Create the draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return draft
        except Exception as e:
            print(f"Error creating draft: {e}")
            return None
    
    def batch_create_drafts(self, emails_data):
        """
        Create multiple draft emails in Gmail.
        
        Args:
            emails_data (list): List of dictionaries containing email data
                Each dictionary should have 'to', 'subject', and 'body' keys
        
        Returns:
            list: List of created draft objects
        """
        if not self.service:
            if not self.authenticate():
                return []
        
        drafts = []
        for email_data in emails_data:
            draft = self.create_draft(
                to=email_data.get('to'),
                subject=email_data.get('subject'),
                body=email_data.get('body'),
                from_email=email_data.get('from')
            )
            if draft:
                drafts.append(draft)
        
        return drafts 