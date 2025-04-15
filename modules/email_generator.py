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
from modules.email_prompt_template import get_email_prompt_template
from modules.gmail_checker import GmailChecker

class EmailGenerator:
    def __init__(self, api_key=None, use_gmail=False, check_sent_emails=False):
        """Initialize the EmailGenerator with DeepSeek API key."""
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.use_gmail = use_gmail
        self.gmail_integration = GmailIntegration() if use_gmail else None
        self.check_sent_emails = check_sent_emails
        self.gmail_checker = GmailChecker() if check_sent_emails else None
        
        # Follow-up email template
        self.template = """
Subject: {topic}
        
{personalized_intro}

{main_content}

{call_to_action}

{signature}
"""
    
    def generate_email(self, contact_data, custom_prompt=None):
        """
        Generate a personalized email for a contact using the DeepSeek API.
        
        Args:
            contact_data (dict): Dictionary containing contact information
            custom_prompt (str, optional): Custom prompt to use instead of the default
            
        Returns:
            dict: Dictionary containing the generated email and metadata
        """
        try:
            # Check if we've already sent an email to this contact
            if self.check_sent_emails and self.gmail_checker:
                email = contact_data.get('email')
                if email:
                    if self.gmail_checker.check_if_email_sent(email):
                        print(f"Email already sent to {email} in the past 30 days. Skipping.")
                        last_email_date = self.gmail_checker.get_last_email_date(email)
                        return {
                            "skipped": True,
                            "reason": "Email already sent",
                            "last_email_date": last_email_date,
                            "contact": contact_data
                        }
            
            # Create the prompt for the AI
            prompt = custom_prompt or self._create_default_prompt(contact_data)
            
            # Call the DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            if "error" in response:
                return {"error": response["error"]}
            
            # Extract the generated email content
            email_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Extract topics from the email content
            topics = self._extract_topics(email_content)
            
            # Format the email with the template
            formatted_email = self.template.format(
                name=contact_data.get("name", "there"),
                topic=topics.get("topic", "our conversation"),
                personalized_intro=topics.get("personalized_intro", ""),
                main_content=topics.get("main_content", ""),
                call_to_action=topics.get("call_to_action", ""),
                signature=topics.get("signature", "Best regards,\nKarim Abbes\nhttps://www.linkedin.com/in/karimabbes/"),
            )
            
            return {
                "email_content": formatted_email,
                "topics": topics,
                "contact": contact_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model": response.get("model", "deepseek-chat")
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _create_default_prompt(self, contact_data):
        """
        Create a default prompt for the AI based on contact data.
        
        Args:
            contact_data (dict): Dictionary containing contact information
            
        Returns:
            str: Prompt for the AI
        """
        name = contact_data.get("name", "the contact")
        message = contact_data.get("message", "")
        profile_url = contact_data.get("profile_url", "")
        
        # Get the prompt template from the separate file
        template = get_email_prompt_template()
        
        # Format the template with the contact data
        prompt = template.format(
            name=name,
            message=message,
            profile_url=profile_url
        )
        
        return prompt
    
    def _extract_topics(self, message):
        """
        Extract topics and email sections from the AI response.
        
        Args:
            message (str): The AI response message
            
        Returns:
            dict: Dictionary containing extracted topics and email sections
        """
        if not message:
            return {}
        
        # Initialize the topics dictionary
        topics = {}
        
        # Try to parse the JSON response from the AI
        try:
            # Find JSON content in the message (it might be surrounded by markdown code blocks)
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', message, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like content
                json_match = re.search(r'\{.*\}', message, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = message
            
            # Parse the JSON
            import json
            parsed = json.loads(json_str)
            
            # Extract the email sections
            topics["personalized_intro"] = parsed.get("personalized_intro", "")
            topics["main_content"] = parsed.get("main_content", "")
            topics["call_to_action"] = parsed.get("call_to_action", "")
            topics["topic"] = parsed.get("topic", "our conversation")
            topics["signature"] = parsed.get("signature", "")

        except Exception as e:
            print(f"Error parsing AI response: {e}")
            # Fallback to simple topic extraction
            common_topics = [
                "real estate", "property", "housing", "investment", "business", 
                "partnership", "collaboration", "opportunity", "project", "service",
                "consulting", "marketing", "sales", "development", "technology"
            ]
            
            message_lower = message.lower()
            for topic in common_topics:
                if topic in message_lower:
                    topics["topic"] = topic
                    break
            
            # Set default values for email sections
            topics["personalized_intro"] = ""
            topics["main_content"] = ""
            topics["call_to_action"] = ""
            topics["signature"] = ""
        
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
    
    def batch_generate_emails(self, csv_file_path, output_dir=None, save_as_drafts=False, sender_email=None):
        """
        Generate emails for all contacts in a CSV file.
        
        Args:
            csv_file_path (str): Path to the CSV file
            output_dir (str, optional): Directory to save the generated emails
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
        skipped_contacts = []
        
        for i, contact in enumerate(contacts):
            print(f"Processing {contact.get('name', f'Contact {i+1}')} ({i+1}/{len(contacts)})...")
            
            # Generate the email
            result = self.generate_email(contact)
            
            # Check if the email was skipped
            if result.get("skipped", False):
                print(f"Skipped {contact.get('name', f'Contact {i+1}')}: {result.get('reason', 'Unknown reason')}")
                if result.get("last_email_date"):
                    print(f"Last email sent on: {result.get('last_email_date')}")
                skipped_contacts.append(result)
                continue

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
                    
                    # Find the subject line by looking for "Subject: " at the beginning of a line
                    subject = ""
                    body = email_content
                    
                    # Split the email content into lines
                    lines = email_content.split('\n')
                    
                    # Look for the subject line
                    for i, line in enumerate(lines):
                        if line.strip().startswith("Subject:"):
                            subject = line.replace("Subject:", "").strip()
                            # Join the remaining lines as the body
                            body = '\n'.join(lines[i+1:]).strip()
                            break
                    
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
            json.dump({
                "generated_emails": results,
                "skipped_contacts": skipped_contacts
            }, f, indent=2)
        
        # Print summary
        print(f"\nEmail generation complete!")
        print(f"Generated {len(results)} emails")
        print(f"Skipped {len(skipped_contacts)} contacts (already sent emails)")
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