#!/usr/bin/env python3
"""
LinkedIn Scraper - Main Entry Point
This script serves as the main entry point for the LinkedIn scraper application.
It imports and runs the scraper module with appropriate configuration.
"""

import os
import sys
import argparse
from datetime import datetime

# Add the parent directory to the path to import from modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.linkedin_scraper import scrape_linkedin, save_messages_to_csv
from modules.email_generator import EmailGenerator

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LinkedIn Message Scraper')
    
    parser.add_argument('--use-cookies', action='store_true', help='Use existing cookies for authentication')
    
    parser.add_argument('--login', action='store_true', help='Force login with credentials instead of using cookies')
    
    parser.add_argument('--output', type=str, help='Custom output filename for the CSV file')
    
    parser.add_argument('--keywords', type=str, default="real estate,agent",
                        help='Comma-separated keywords to filter messages (default: "real estate,agent")')
    
    parser.add_argument('--max-threads', type=int, default=10,
                        help='Maximum number of message threads to process (default: 10)')
    
    # Email generation arguments
    parser.add_argument('--generate-emails', action='store_true', 
                        help='Generate emails after scraping')
    
    parser.add_argument('--email-template', type=str, default='default',
                        help='Email template to use (default: default)')
    
    parser.add_argument('--gmail', action='store_true',
                        help='Save generated emails as Gmail drafts')
    
    parser.add_argument('--sender-email', type=str,
                        help='Email address to send from (for Gmail drafts)')
    
    parser.add_argument('--api-key', type=str,
                        help='DeepSeek API key (overrides config)')
    
    return parser.parse_args()

def main():
    """Main function to run the LinkedIn scraper."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Determine whether to use cookies based on arguments
    use_cookies = args.use_cookies and not args.login
    
    # Split keywords into a list
    keywords = [k.strip() for k in args.keywords.split(",")]
    
    # Print welcome message
    print("=" * 50)
    print("LinkedIn Message Scraper")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Authentication method: {'Cookies' if use_cookies else 'Credentials'}")
    print(f"Keywords: {', '.join(keywords)}")
    print(f"Max threads: {args.max_threads}")
    print("=" * 50)
    
    csv_path = None
    
    try:
        # Run the scraper with the specified keywords
        messages = scrape_linkedin(use_cookies=use_cookies, keywords=keywords, max_threads=args.max_threads)
        
        # Save messages to CSV if any were found
        if messages:
            output_file = args.output if args.output else None
            csv_path = save_messages_to_csv(messages, filename=output_file)
            print(f"\nScraping completed successfully!")
            print(f"Found {len(messages)} messages matching your criteria.")
            print(f"Results saved to: {csv_path}")
        else:
            print("\nScraping completed, but no messages matching your criteria were found.")
            return 0
        
        # Generate emails if requested
        if args.generate_emails and csv_path:
            print("\n" + "=" * 50)
            print("Email Generation")
            print("=" * 50)
            
            # Initialize the email generator
            generator = EmailGenerator(api_key=args.api_key, use_gmail=args.gmail)
            
            # Generate emails for all contacts in the CSV file
            generator.batch_generate_emails(
                csv_file_path=csv_path,
                template_name=args.email_template,
                save_as_drafts=args.gmail,
                sender_email=args.sender_email
            )
            
            print("\nEmail generation completed!")
    
    except Exception as e:
        print(f"\nError during execution: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
