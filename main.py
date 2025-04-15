#!/usr/bin/env python3
"""
LinkedIn Scraper - Main Entry Point
This script serves as the main entry point for the LinkedIn scraper application.
It imports and runs the scraper module with appropriate configuration.
"""

import os
import sys
import argparse
import time
from datetime import datetime

# Add the parent directory to the path to import from modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.linkedin_scraper import LinkedInScraper
from modules.email_generator import EmailGenerator

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LinkedIn Scraper and Email Generator')
    
    # LinkedIn scraping options
    parser.add_argument('--use-cookies', action='store_true', help='Use cookies for authentication')
    parser.add_argument('--force-login', action='store_true', help='Force login even if cookies are valid')
    parser.add_argument('--output', type=str, help='Output filename for the CSV file')
    parser.add_argument('--filter', type=str, help='Filter contacts by keyword in name or message')
    parser.add_argument('--max-threads', type=int, default=4, help='Maximum number of threads for scraping')
    
    # Email generation options
    parser.add_argument('--generate-emails', action='store_true', help='Generate emails after scraping')
    parser.add_argument('--gmail', action='store_true', help='Save generated emails as Gmail drafts')
    parser.add_argument('--sender-email', type=str, help='Email address to send from when saving drafts')
    parser.add_argument('--check-sent-emails', action='store_true', help='Check if emails have already been sent to contacts')
    parser.add_argument('--api-key', type=str, help='DeepSeek API key (overrides config)')
    
    return parser.parse_args()

def main():
    """Main function to run the LinkedIn scraper and email generator."""
    args = parse_arguments()
    
    # Initialize the LinkedIn scraper
    scraper = LinkedInScraper()
    
    # Scrape LinkedIn messages
    print("Starting LinkedIn scraping...")
    messages = scraper.scrape_linkedin(
        use_cookies=args.use_cookies,
        keywords=args.filter.split(',') if args.filter else None,
        max_threads=args.max_threads
    )
    
    # Save messages to CSV
    if messages:
        output_file = args.output if args.output else None
        csv_file = scraper.save_messages_to_csv(messages, filename=output_file)
        print(f"Scraped data saved to {csv_file}")
        
        # Generate emails if requested
        if args.generate_emails:
            print("\nGenerating emails...")
            generator = EmailGenerator(
                api_key=args.api_key,
                use_gmail=args.gmail,
                check_sent_emails=args.check_sent_emails
            )
     
            if args.gmail:
                if not args.sender_email:
                    print("Error: --sender-email is required when using --gmail")
                    return
                
                print("\nGenerating emails...")

            # Generate emails for all contacts
            generator.batch_generate_emails(csv_file_path=csv_file, output_dir=args.output, save_as_drafts=args.gmail, sender_email=args.sender_email)
           
    else:
        print("No messages found matching the criteria.")
    
    # Close the browser
    scraper.driver.quit()

if __name__ == "__main__":
    main()
