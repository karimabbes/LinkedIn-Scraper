# LinkedIn Scraper

A Python application that scrapes LinkedIn messages related to real estate professionals using Selenium.

## Features

- Automated LinkedIn login using credentials from environment variables
- Option to use existing session via cookies for faster and more reliable access
- Scrapes messages from LinkedIn's messaging section
- Filters messages based on customizable keywords
- Extracts contact information for real estate professionals
- Saves results to CSV files for easy analysis
- Generates personalized emails using AI
- Option to save generated emails as Gmail drafts
- Integrated workflow from scraping to email generation

## Prerequisites

- Python 3.7 or higher
- Chrome browser installed
- ChromeDriver compatible with your Chrome version
- Gmail account (for saving emails as drafts)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LinkedIn-Scraper
```

### 2. Create and Activate a Virtual Environment

#### On macOS/Linux:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

#### On Windows:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 5. Set Up Gmail API (for saving emails as drafts)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API for your project
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Place the credentials file in the `config` directory as `credentials.json`

### 6. Install ChromeDriver

#### Option 1: Include ChromeDriver in the project directory (Recommended)

1. Download ChromeDriver from [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
2. Place the ChromeDriver executable in the `drivers` directory

#### Option 2: Use system ChromeDriver

Make sure ChromeDriver is installed and available in your system PATH.

## Usage

### Basic Scraping

```bash
python main.py
```

This will:

1. Log in to LinkedIn (using cookies if available, otherwise with credentials)
2. Scrape messages from your LinkedIn inbox
3. Filter messages based on keywords (default: "real estate,agent")
4. Extract contact information from profiles
5. Save results to a CSV file in the `data` directory

### Advanced Scraping Options

```bash
python main.py --keywords "real estate,agent,broker" --max-threads 10 --output custom_filename.csv
```

### Integrated Workflow: Scraping + Email Generation

To scrape LinkedIn profiles and immediately generate personalized emails:

```bash
python main.py --generate-emails
```

This will:

1. Scrape LinkedIn messages and extract contact information
2. Save the results to a CSV file
3. Generate personalized emails for each contact
4. Save the emails to the `data/generated_emails` directory

### Saving Emails as Gmail Drafts

To save generated emails as Gmail drafts:

```bash
python main.py --generate-emails --gmail --sender-email your.email@gmail.com
```

This will:

1. Scrape LinkedIn messages and extract contact information
2. Save the results to a CSV file
3. Generate personalized emails for each contact
4. Save the emails as drafts in your Gmail account
5. Also save the emails to the local filesystem

### Using Different Email Templates

```bash
python main.py --generate-emails --email-template follow_up
```

### Complete Example

```bash
python main.py --use-cookies --keywords "real estate,agent" --max-threads 10 --generate-emails --gmail --sender-email your.email@gmail.com --email-template follow_up
```

## Email Generation

The application can generate personalized emails for contacts scraped from LinkedIn using the DeepSeek API.

### Basic Usage

```bash
python generate_emails.py
```

This will:

1. Find the most recent CSV file in the `data` directory
2. Generate personalized emails for each contact
3. Save the emails to the `data/generated_emails` directory

### Advanced Options

```bash
python generate_emails.py --csv path/to/contacts.csv --output path/to/output --template default
```

#### Saving Emails as Gmail Drafts

To save generated emails as Gmail drafts:

```bash
python generate_emails.py --gmail --sender-email your.email@gmail.com
```

This will:

1. Authenticate with your Gmail account (first time only)
2. Generate personalized emails for each contact
3. Save the emails as drafts in your Gmail account
4. Also save the emails to the local filesystem

Note: The first time you use the Gmail integration, a browser window will open asking you to authorize the application to access your Gmail account.

## Troubleshooting

### LinkedIn Verification Requests

The application now includes improved cookie management to reduce verification requests. If you still encounter verification requests:

1. Enter the verification code when prompted
2. The application will automatically save the updated cookies for future use
3. Future runs should require fewer verification requests

### Browser Issues

If you encounter browser-related issues:

1. Make sure ChromeDriver is compatible with your Chrome version
2. Try restarting the application
3. Check that your LinkedIn credentials are correct

## License

[Your License Information]
