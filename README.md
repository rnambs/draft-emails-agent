## This script connects to your Google Account, and uses AI to figure out which of your unread emails need a response and drafts them for you.

# First Run

1. Run the script:

```bash
python agent.py
```

2. On first run, a browser window will open asking you to authorize the application
3. Sign in with your Google account and grant the requested permissions
4. The script will create a `token.json` file to store your credentials

# Usage

The script will:

- Check your Gmail inbox for unread messages
- Process up to 5 unread emails at a time
- For each email:
  - Determine if a reply is needed
  - If needed, create a draft response
  - Mark the email as read

# Troubleshooting

- If you get authentication errors, delete `token.json` and run the script again
- Ensure your Google Cloud project has the Gmail API enabled
- Check that your OpenAI API key is valid and has sufficient credits
