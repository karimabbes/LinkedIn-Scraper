import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LinkedIn credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# DeepSeek credentials
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Validate that credentials are available
if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
    raise ValueError("LinkedIn credentials not found in environment variables. Please check your .env file.") 