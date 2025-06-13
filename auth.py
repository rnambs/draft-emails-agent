# auth.py
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]


def get_refresh_token():
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES, redirect_uri="http://localhost:8090"
    )
    flow.oauth2session.auto_refresh_url = flow.client_config["token_uri"]
    flow.oauth2session.auto_refresh_kwargs = {
        "client_id": flow.client_config["client_id"],
        "client_secret": flow.client_config["client_secret"],
    }
    creds = flow.run_local_server(port=8090, prompt="consent")
    print("Credentials:", creds)

    # save refresh token data
    token_data = {
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    # write to refresh_toke.json
    with open("refresh_token.json", "w") as f:
        json.dump(token_data, f)

    print("Refresh token saved to refresh_token.json!")
    print("\nNow run this command to add it to Modal secrets:")
    print(
        f"modal secret create email-agent-secrets GOOGLE_REFRESH_TOKEN='{json.dumps(token_data)}'"
    )


if __name__ == "__main__":
    get_refresh_token()
