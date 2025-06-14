NEW: Branch modal allows you to run this constantly via Modal. Modal's free tier should cover it.
This uses Google Cal events to know when to set meetings for you as well!
Steps are as follows:
1. Clone the 'modal' branch - you only need auth.py and modal_email_agent.py
2. Make sure you create a [modal](www.modal.com) account and app:
3. I am assuming you already have a Google Cloud App with API access to Mail and Calendar
4. After this is done, run `python auth.py`. This will create a `refresh_token.json` file. Create a secret on modal called GOOGLE_REFRESH_TOKEN and paste the contents of that file into it.
5. Set your OPENAI_API_KEY on modal secrets
6. Make sure you `pip install modal` and finally run `modal deploy {whatever_you_set_the_app_name}`

# Email Draft Agent

This script connects to your Google Account, and uses AI to figure out which of your unread emails need a response and drafts them for you.

UPDATE: New feature that unmarks spam emails as spam and moves to important. Useful if you have a forwarding address to your main email inbox that gets caught in spam.

## Prerequisites

1. **Google Cloud Setup**

   - Create a project in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Gmail API
   - Create OAuth credentials with the following scope:
     ```
     https://www.googleapis.com/auth/gmail.modify
     ```
   - Download credentials as `credentials.json`

2. **OpenAI API Key**
   - Get your API key from [OpenAI Platform](https://platform.openai.com/)

## Installation

1. Clone the repository and install dependencies:

```bash
git clone <your-repo-url>
cd email-draft-agent
pip install -r requirements.txt
```

2. Place your files in the project root:
   - `credentials.json` (from Google Cloud Console)
   - Create `.env` file with your OpenAI API key:
     ```
     OPENAI_API_KEY=your_key_here
     ```

## First Run

1. Run the script:

```bash
python agent.py
```

2. A browser window will open for Google OAuth authorization
3. After authorizing, the script will create `token.json` for future use

## Customization

### Response Style

Modify the `system_prompt` in `draft_reply()` function to change the AI's tone and style. For example:

```python
system_prompt = (
    "You are an executive assistant for a early 20s professional managing their personal inbox. Your goal is to decide if an email needs a reply, and if it does, draft the reply message. "
        "You must return JSON with keys: needs_reply (true/false) and reply_draft (string)."
        "Your tone will be friendly, professional, concise and to the point. You will never use emojis."
)
```

### Email Processing

- Change the number of emails processed by modifying the `limit` parameter in `list_unread(limit=5)`
- Add filters to the Gmail query in `list_unread()`. For example, to exclude spam:

```python
q="is:unread -category:promotions -category:social -category:updates"
```
