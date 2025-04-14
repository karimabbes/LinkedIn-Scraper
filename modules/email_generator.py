import os
import sys
import csv
import json
import time
import random
import requests
from datetime import datetime

# Add the parent directory to the path to import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.credentials import DEEPSEEK_API_KEY
from modules.gmail_integration import GmailIntegration

class EmailGenerator:
    def __init__(self, api_key=None, use_gmail=False):
        """Initialize the EmailGenerator with DeepSeek API key."""
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.use_gmail = use_gmail
        self.gmail_integration = GmailIntegration() if use_gmail else None
        
        # Default email templates
        self.templates = {
            "default": """
            Subject: Connecting with {name} regarding {topic}
            
            Hi {name},
            
            {personalized_intro}
            
            {main_content}
            
            {call_to_action}
            
            Best regards,
            {sender_name}
            """,
            
            "follow_up": """
            Subject: Following up - {topic}
            
            Hi {name},
            
            {personalized_intro}
            
            {main_content}
            
            {call_to_action}
            
            Best regards,
            {sender_name}
            """
        }
    
    def generate_email(self, contact_data, template_name="default", custom_prompt=None):
        """
        Generate a personalized email for a contact using DeepSeek.
        
        Args:
            contact_data (dict): Dictionary containing contact information
            template_name (str): Name of the template to use
            custom_prompt (str, optional): Custom prompt to use instead of the default
            
        Returns:
            dict: Dictionary containing the generated email and metadata
        """
        # Get the template
        template = self.templates.get(template_name, self.templates["default"])
        
        # Prepare the prompt for DeepSeek
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._create_default_prompt(contact_data, template_name)
        
        # Call DeepSeek API
        try:
            response = self._call_deepseek_api(prompt)
            
            # Extract the email content from the response
            email_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # If the response doesn't look like an email, try to extract it
            if not email_content.strip().startswith("Subject:"):
                # Try to find the email in the response
                email_parts = email_content.split("\n\n")
                for part in email_parts:
                    if part.strip().startswith("Subject:"):
                        email_content = part
                        break
            
            # Create the result
            result = {
                "contact": contact_data,
                "email_content": email_content,
                "template_used": template_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model": response.get("model", "deepseek-chat")
            }
            
            return result
        
        except Exception as e:
            print(f"Error generating email for {contact_data.get('name', 'Unknown')}: {str(e)}")
            return {
                "contact": contact_data,
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def _create_default_prompt(self, contact_data, template_name):
        """Create a default prompt for DeepSeek based on contact data."""
        name = contact_data.get("name", "the contact")
        message = contact_data.get("message", "")
        profile_url = contact_data.get("profile_url", "")
        email = contact_data.get("email", "")
        website = contact_data.get("website", "")
        
        # Extract potential topics from the message
        topics = self._extract_topics(message)
        
        prompt = f"""
        You are an expert email writer. Please write a personalized email to {name}.
        
        Contact Information:
        - Name: {name}
        - Previous Message: {message}
        - Profile URL: {profile_url}
        - Email: {email}
        - Website: {website}
        
        Potential Topics: {', '.join(topics) if topics else 'Not specified'}
        
        Requirements:
        1. The email should be personalized based on the contact's information
        2. Include a subject line starting with "Subject:"
        3. The email should be professional but conversational
        4. If there's a previous message, reference it subtly
        5. Include a clear call to action
        6. Keep the email concise (3-5 paragraphs)
        7. If this is a follow-up email, acknowledge the previous contact
        
        Format the email as follows:
        Subject: [Your subject line]
        
        [Email body]
        
        Best regards,
        [Your name]
        
        Please generate a complete email that I can use directly.
        """
        
        return prompt
    
    def _extract_topics(self, message):
        """Extract potential topics from a message."""
        if not message:
            return []
        
        # Simple topic extraction - look for common business topics
        topics = []
        common_topics = [
            "real estate", "property", "housing", "investment", "business", 
            "partnership", "collaboration", "opportunity", "project", "service",
            "consulting", "marketing", "sales", "development", "technology"
        ]
        
        message_lower = message.lower()
        for topic in common_topics:
            if topic in message_lower:
                topics.append(topic)
        
        return topics
    
    def _call_deepseek_api(self, prompt):
        """Call the DeepSeek API with the given prompt."""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an expert email writer who creates personalized, professional emails."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
        
        return response.json()
    
    def batch_generate_emails(self, csv_file_path, output_dir=None, template_name="default", save_as_drafts=False, sender_email=None):
        """
        Generate emails for all contacts in a CSV file.
        
        Args:
            csv_file_path (str): Path to the CSV file
            output_dir (str, optional): Directory to save the generated emails
            template_name (str): Name of the template to use
            save_as_drafts (bool): Whether to save emails as Gmail drafts
            sender_email (str, optional): Email address to send from
            
        Returns:
            list: List of dictionaries containing the generated emails and metadata
        """
        # Create output directory if not provided
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "generated_emails")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Read contacts from CSV
        contacts = []
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                contacts.append(row)
        
        # Generate emails for each contact
        results = []
        gmail_drafts = []
        
        for i, contact in enumerate(contacts):
            print(f"Generating email for {contact.get('name', f'Contact {i+1}')} ({i+1}/{len(contacts)})...")
            
            # Generate the email
            result = self.generate_email(contact, template_name)
            
            # Save the email to a file
            if "error" not in result:
                email_filename = f"email_{contact.get('name', f'contact_{i+1}').replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                email_filepath = os.path.join(output_dir, email_filename)
                
                with open(email_filepath, 'w', encoding='utf-8') as f:
                    f.write(result["email_content"])
                
                result["saved_to"] = email_filepath
                
                # Save as Gmail draft if requested
                if save_as_drafts and self.gmail_integration:
                    # Extract subject and body from the email content
                    email_content = result["email_content"]
                    subject_line = email_content.split('\n')[0]
                    subject = subject_line.replace('Subject: ', '')
                    body = '\n'.join(email_content.split('\n')[1:]).strip()
                    
                    # Get recipient email from contact data
                    to_email = contact.get('email')
                    if not to_email:
                        print(f"Warning: No email address found for {contact.get('name', f'Contact {i+1}')}")
                        continue
                    
                    # Create draft in Gmail
                    draft = self.gmail_integration.create_draft(
                        to=to_email,
                        subject=subject,
                        body=body,
                        from_email=sender_email
                    )
                    
                    if draft:
                        result["gmail_draft_id"] = draft.get('id')
                        gmail_drafts.append(draft)
                        print(f"Created Gmail draft for {contact.get('name', f'Contact {i+1}')}")
                    else:
                        print(f"Failed to create Gmail draft for {contact.get('name', f'Contact {i+1}')}")
            
            results.append(result)
            
            # Add a small delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
        
        # Save all results to a JSON file
        results_filename = f"email_generation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_filepath = os.path.join(output_dir, results_filename)
        
        with open(results_filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print(f"\nEmail generation complete!")
        print(f"Generated {len(results)} emails")
        if save_as_drafts and self.gmail_integration:
            print(f"Created {len(gmail_drafts)} Gmail drafts")
        
        return results

# Example usage
if __name__ == "__main__":
    # Get the CSV file path from command line arguments or use a default
    if len(sys.argv) > 1:
        csv_file_path = sys.argv[1]
    else:
        # Find the most recent CSV file in the data directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        
        if not csv_files:
            print("No CSV files found in the data directory.")
            sys.exit(1)
        
        # Sort by modification time (most recent first)
        csv_files.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)), reverse=True)
        csv_file_path = os.path.join(data_dir, csv_files[0])
    
    print(f"Using CSV file: {csv_file_path}")
    
    # Initialize the email generator
    generator = EmailGenerator()
    
    # Generate emails for all contacts in the CSV file
    generator.batch_generate_emails(csv_file_path) 