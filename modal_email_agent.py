import modal
import os
import json
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import openai

app = modal.App("modal_email_agent")

image = modal.Image.debian_slim().pip_install(
    "google-auth-oauthlib",
    "google-auth-httplib2",
    "google-api-python-client",
    "openai",
    "python-dotenv",
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]


@app.function(image=image, secrets=[modal.Secret.from_name("email-agent-secrets")])
def get_gmail_service():
    try:
        if "GOOGLE_REFRESH_TOKEN" not in os.environ:
            raise Exception("GOOGLE_REFRESH_TOKEN not found in environment")

        token_data = json.loads(os.environ["GOOGLE_REFRESH_TOKEN"])

        print("Token data keys:", list(token_data.keys()))

        creds = Credentials(
            None,
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=SCOPES,
        )

        creds.refresh(Request())

        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"Error in get_gmail_service: {str(e)}")
        print(f"Error type: {type(e)}")
        raise Exception(f"Authentication failed: {str(e)}")


@app.function(image=image, secrets=[modal.Secret.from_name("email-agent-secrets")])
def draft_reply(subject, sender, body, service=None):
    openai.api_key = os.environ["OPENAI_API_KEY"]
    system_prompt = (
        "You are an executive assistant for a professional in their early 20s working in tech. "
        "Your primary responsibilities are as follows:"
        "\n\n1. **Determine if an email requires a response based on these rules:**"
        "   - If the email is from a specific person and sent directly to me, or if the email falls into one of these categories, move to step 2:"
        "       * Direct questions"
        "       * Meeting requests"
        "       * Action items"
        "       * Personal emails"
        "   - If the email falls into one of these categories, do not reply:"
        "       * Newsletters"
        "       * Marketing emails"
        "       * Automated notifications"
        "       * Spam"
        "       * Meeting confirmation emails"
        "       * LinkedIn messages or InMails"
        "       * Emails selling a product or course"
        "   - If the email does not clearly fit into any of the above categories, assume a reply is needed and move to step 2."
        "\n\n2. **Draft a concise, professional reply if a response is needed:**"
        "   - Maintain a friendly but efficient tone."
        "   - Never use emojis or informal language."
        "   - Always sign off with: 'Best,\\nRahul'."
        "\n\n3. **Output the result as a JSON object with exactly these keys:**"
        "   - `needs_reply`: true/false (true if a reply is needed, false otherwise)."
        "   - `reply_draft`: the draft text if `needs_reply` is true, or an empty string if `needs_reply` is false."
        "\n\n4. **IMPORTANT - Calendar Tool Usage:**"
        "   - If the email is about scheduling a meeting or finding a time to meet, you MUST use the get_calendar_events tool."
        "   - Do not make assumptions about availability without checking the calendar."
        "   - When you see words like 'meet', 'schedule', 'calendar', 'availability', or 'time', use the tool."
        "   - The tool will return your schedule for the next 7 days."
        "   - Use this information to suggest specific available times between 11am and 5pm EST."
    )

    user_prompt = (
        f"Here is the email I receive. From: {sender}\nSubject: {subject}\n\n{body}"
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_calendar_events",
                "description": "Get calendar events for the next 7 days to know when is a good time to meet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format",
                        },
                    },
                    "required": ["start_time", "end_time"],
                },
            },
        }
    ]

    print("Making initial API call to check if calendar tool is needed...")
    # if we need calendar
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        tools=tools,
    )

    print("Checking for tool calls in response...")
    if response.choices[0].message.tool_calls and service:
        print("Tool call detected!")
        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "get_calendar_events":
            print("Calendar tool requested, fetching events...")
            current_time = datetime.now(timezone.utc)
            end_time = current_time + timedelta(days=7)
            calendar_events = get_calendar_events.remote(
                service, current_time, end_time
            )

            print(f"Found {len(calendar_events)} calendar events")
            # format calendar events for the prompt
            calendar_context = "My upcoming schedule:\n"
            for event in calendar_events:
                start = datetime.fromisoformat(
                    event["start"].get("dateTime", event["start"].get("date"))
                )
                calendar_context += (
                    f"- {start.strftime('%a, %b %d %I:%M %p')}: {event['summary']}\n"
                )

            print("Making second API call with calendar context...")
            # Second call with calendar context
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": calendar_context,
                    },
                ],
                temperature=0.2,
            )
    else:
        print("No tool calls detected or no service provided")

    try:
        return json.loads(response.choices[0].message.content.strip())
    except:
        return {
            "needs_reply": True,
            "reply_draft": response.choices[0].message.content.strip(),
        }


@app.function(image=image)
def create_draft(service, to_addr, reply_text, thread_id, original_subject):
    msg = MIMEText(reply_text)
    msg["to"] = to_addr
    msg["subject"] = f"Re: {original_subject}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"message": {"raw": raw, "threadId": thread_id}}

    try:
        draft = service.users().drafts().create(userId="me", body=body).execute()
        return {"success": True, "draft_id": draft["id"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(image=image)
def process_email(email_data, service):
    subject = email_data["subject"]
    sender = email_data["from"]
    body = email_data["body"]
    thread_id = email_data["thread_id"]

    reply_data = draft_reply.remote(subject, sender, body, service=service)

    if reply_data.get("needs_reply"):
        result = create_draft.remote(
            service, sender, reply_data["reply_draft"], thread_id, subject
        )
        return {
            "needs_reply": True,
            "draft_created": result["success"],
            "draft_id": result.get("draft_id"),
            "error": result.get("error"),
        }

    return {"needs_reply": False}


@app.function(image=image, schedule=modal.Period(minutes=10))
def check_emails_periodically():
    service = get_gmail_service.remote()

    # Use UTC time
    current_time = datetime.now(timezone.utc)
    sixty_mins_ago = current_time - timedelta(minutes=60)
    date_str = sixty_mins_ago.strftime("%Y/%m/%d")
    query = f"is:unread after:{date_str} -category:promotions -category:social -category:updates"

    print(f"Searching for emails after {date_str}")
    print(f"Using query: {query}")

    try:
        results = service.users().messages().list(userId="me", q=query).execute()

        messages = results.get("messages", [])
        if not messages:
            print(f"No new emails at {current_time.strftime('%H:%M:%S')} UTC")
            return

        print(f"Found {len(messages)} new emails")

        for msg in messages:
            try:
                email = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )

                headers = {h["name"]: h["value"] for h in email["payload"]["headers"]}
                subject = headers.get("Subject", "")
                sender = headers.get("From", "")

                body = ""
                if "parts" in email["payload"]:
                    for part in email["payload"]["parts"]:
                        if part["mimeType"] == "text/plain":
                            body = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                            break

                email_data = {
                    "subject": subject,
                    "from": sender,
                    "body": body,
                    "thread_id": msg["threadId"],
                }

                print(f"Processing email: {subject}")
                result = process_email.remote(email_data, service)
                print(f"Process result: {result}")

                if result.get("needs_reply"):
                    print(f"Created draft for: {subject}")
                else:
                    print(f"No reply needed for: {subject}")

                service.users().messages().modify(
                    userId="me", id=msg["id"], body={"removeLabelIds": ["UNREAD"]}
                ).execute()

            except Exception as e:
                print(f"Error processing message {msg['id']}:")
                print(f"Error type: {type(e)}")
                print(f"Error message: {str(e)}")
                print(
                    f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}"
                )
                continue

    except Exception as e:
        print(f"Error checking emails:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print(
            f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}"
        )


@app.function(image=image, secrets=[modal.Secret.from_name("email-agent-secrets")])
def get_calendar_events(service, start_time, end_time):
    try:
        calendar = build("calendar", "v3", credentials=service)
        events_result = (
            calendar.events()
            .list(
                calendarId="primary",
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])
    except Exception as e:
        print(f"Error fetching calendar events: {str(e)}")
        return []


if __name__ == "__main__":
    with app.run():
        check_emails_periodically.remote()
        print("Email checker started. Will run every 10 minutes.")
