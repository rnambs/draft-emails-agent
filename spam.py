import os, json, base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
load_dotenv()
personal_email = os.getenv("PERSONAL_EMAIL")

creds = None
if os.path.exists("token.json"):
    with open("token.json", "r") as f:
        creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)

if not creds or not creds.valid:
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=8090)
    with open("token.json", "w") as f:
        f.write(creds.to_json())

service = build("gmail", "v1", credentials=creds)


def get_spam_emails():
    # you can change this to look at more recent or older spam
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y/%m/%d")

    # similarly here
    query = f"in:spam after:{thirty_days_ago}"
    results = service.users().messages().list(userId="me", q=query).execute()

    return results.get("messages", [])


def process_email(msg_id):
    msg = (
        service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    )

    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    to_address = headers.get("To", "")

    if personal_email in to_address.lower():
        print(f"Found important email: {headers.get('Subject', 'No Subject')}")

        # Remove from spam and add important label
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"removeLabelIds": ["SPAM"], "addLabelIds": ["IMPORTANT"]},
        ).execute()
        print("✅ Moved to inbox and marked as important")
        return True

    return False


def main():
    print(f"\n🔄 Checking spam folder at {datetime.now().strftime('%H:%M:%S')}")
    spam_emails = get_spam_emails()

    if not spam_emails:
        print("📭 No spam emails found in the last 30 days.")
        return

    print(f"Found {len(spam_emails)} spam emails to process...")
    processed_count = 0

    for msg in spam_emails:
        if process_email(msg["id"]):
            processed_count += 1

    print(f"\n✅ Processed {processed_count} important emails from spam folder.")


if __name__ == "__main__":
    main()
