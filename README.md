# LinkedIn Scraper and Email Generator

A Python-based tool for scraping LinkedIn messages and generating personalized follow-up emails.

## Features

- **LinkedIn Scraping**: Automatically scrapes LinkedIn messages and saves contact information to a CSV file.
- **Email Generation**: Generates personalized follow-up emails based on the scraped data.
- **Gmail Integration**: Option to save generated emails as Gmail drafts.
- **Sent Email Checking**: Option to check if emails have already been sent to contacts to avoid duplicates.

## Prerequisites

- Python 3.8 or higher
- Chrome browser
- ChromeDriver (compatible with your Chrome version)
- Gmail account (for saving drafts)

## Setup

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/linkedin-scraper.git
   cd linkedin-scraper
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:

   - Create a `.env` file in the project root
   - Add your LinkedIn credentials and DeepSeek API key:
     ```
     LINKEDIN_EMAIL=your_email@example.com
     LINKEDIN_PASSWORD=your_password
     DEEPSEEK_API_KEY=your_api_key
     ```

5. Set up Gmail API (for saving emails as drafts):
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials JSON file
   - Place the credentials file in the `config` directory as `credentials.json`

## Usage

### Basic Scraping

```
python main.py
```

### Advanced Scraping

```
python main.py --use-cookies --filter "real estate" --max-threads 4
```

### Integrated Workflow (Scraping + Email Generation)

```
python main.py --generate-emails --gmail --sender-email your_email@gmail.com
```

### Check for Sent Emails

```
python main.py --generate-emails --check-sent-emails
```

This option will check if emails have already been sent to contacts in the past 30 days, helping you avoid sending duplicate emails.

## Command Line Arguments

### LinkedIn Scraping Options

- `--use-cookies`: Use cookies for authentication
- `--force-login`: Force login even if cookies are valid
- `--output`: Output filename for the CSV file
- `--filter`: Filter contacts by keyword in name or message
- `--max-threads`: Maximum number of threads for scraping (default: 4)

### Email Generation Options

- `--generate-emails`: Generate emails after scraping
- `--gmail`: Save generated emails as Gmail drafts
- `--sender-email`: Email address to send from when saving drafts
- `--check-sent-emails`: Check if emails have already been sent to contacts
- `--api-key`: DeepSeek API key (overrides config)

## Troubleshooting

### LinkedIn Verification Requests

If LinkedIn requests verification during login:

1. The script will prompt you to enter the verification code
2. Enter the code when prompted
3. The script will continue automatically after verification

### Browser Issues

If you encounter browser-related issues:

1. Ensure Chrome and ChromeDriver versions match
2. Try clearing browser cache and cookies
3. Check your internet connection

### Gmail API Issues

If you encounter issues with the Gmail API:

1. Ensure your credentials.json file is correctly placed in the config directory
2. Check that you have enabled the Gmail API in your Google Cloud Console
3. Verify that your OAuth consent screen is properly configured

## License

This project is licensed under the MIT License - see the LICENSE file for details.
