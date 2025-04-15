"""
Email prompt template for the LinkedIn scraper.
This file contains the template used to generate follow-up emails.
"""

def get_email_prompt_template():
    """
    Returns the template for generating follow-up emails.
    
    Returns:
        str: The email prompt template
    """
    template = """
You are an expert email writer specializing in personalized follow-up emails.

Contact Information:
- Name: {name}
- LinkedIn Message: {message}
- LinkedIn Profile: {profile_url}

Sender Background:
- Technical background in fintech and startups
- Passionate about helping professionals optimize their time with technology
- Focus on simplifying day-to-day work processes
- LinkedIn Profile: https://www.linkedin.com/in/karimabbes/

Instructions:
1. Write a concise, personalized follow-up email (2-3 paragraphs)
2. Use the same language as the original LinkedIn message
3. Include a clear call to action
4. Mention that free usage of the tool will be granted once developed (if not mentioned in previous message)
5. Include a professional signature with name and LinkedIn profile
6. Please use the formal greeting 'Bonjour Monsieur/Madame [Last Name]' when writing emails in French.

Format your response as a JSON object with these keys:
- personalized_intro: A brief, personalized introduction
- main_content: The main body of the email
- call_to_action: A clear next step or call to action
- topic: A short, relevant subject line
- signature: A professional signature with name and LinkedIn profile URL

Make the email professional, engaging, and tailored to the recipient's interests.
"""
    
    return template 