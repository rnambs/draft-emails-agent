# Email Draft Agent

This script connects to your Google Account, and uses AI to figure out which of your unread emails need a response and drafts them for you.

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

## Security

- Never commit `.env`, `credentials.json`, or `token.json`
- Keep your API keys secure
