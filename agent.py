import os, json, base64, time
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
import openai

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# configuration of gmail scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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


def list_unread(limit=5): # you can change the limit to get more or less emails
    # find unread messages
    res = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=limit)
        .execute()
    )
    return [m["id"] for m in res.get("messages", [])]


def fetch_message(msg_id):
    msg = (
        service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    )
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("Subject", "")
    sender = headers.get("From", "")
    body = ""
    for part in msg["payload"].get("parts", []):
        if part["mimeType"] == "text/plain":
            body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                "utf-8", errors="ignore"
            )
            break
    return subject, sender, body


def draft_reply(subject, sender, body):
    system_prompt = (os.getenv("SYSTEM_PROMPT"))
    user_prompt = f"Here is the email I receive. You will sign off on all emails that need a reply with Best, Rahul. From: {sender}\nSubject: {subject}\n\n{body}"
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    try:
        return json.loads(response.choices[0].message.content.strip())
    except:
        return {
            "needs_reply": True,
            "reply_draft": response.choices[0].message.content.strip(),
        }


def create_draft(to_addr, reply_text, thread_id):
    msg = MIMEText(reply_text)
    msg["to"] = to_addr
    msg["subject"] = "Re: (auto) " + datetime.now().strftime("%b %d")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"message": {"raw": raw, "threadId": thread_id}}
    service.users().drafts().create(userId="me", body=body).execute()
    print(body)


def mark_read(msg_id):
    service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def agent_loop():
    print(f"\n🔄 Checking inbox at {datetime.now().strftime('%H:%M:%S')}")
    unread_ids = list_unread(limit=5)
    if not unread_ids:
        print("📭 No unread emails.")
    for msg_id in unread_ids:
        subj, frm, body = fetch_message(msg_id)
        print(f"📨 {subj}")
        reply_data = draft_reply(subj, frm, body)
        if reply_data.get("needs_reply"):
            create_draft(frm, reply_data["reply_draft"], msg_id)
            print("💾 Draft created.")
        else:
            print("⏭️ No reply needed.")
        mark_read(msg_id)  # optionally marks as read - can remove if not needed
    print(f"Done with last {len(unread_ids)} unread emails. Exiting.")


if __name__ == "__main__":
    agent_loop()
