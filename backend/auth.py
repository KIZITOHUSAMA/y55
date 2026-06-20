import os
import json
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import starlette.status as status

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth 2.0 configuration
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]
REDIRECT_URI = "http://localhost:8000/auth/callback"

# In-memory session storage (In production, use a database or secure cookie)
sessions = {}

@router.get("/login")
async def login():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "client_secrets.json not found. Please provide it to enable YouTube connection."}

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    return {"url": authorization_url}

@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code not found in callback")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Store credentials in session (Simplified for this task)
    session_id = "default_user" # Since it's a local app, we can use a fixed ID or handle multiple
    sessions[session_id] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    # Redirect back to the frontend
    return RedirectResponse(url="http://localhost:5173/?login=success")

@router.get("/status")
async def get_status():
    if "default_user" in sessions:
        return {"logged_in": True}
    return {"logged_in": False}

def get_yt_service():
    if "default_user" not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    creds_data = sessions["default_user"]
    credentials = Credentials(
        token=creds_data["token"],
        refresh_token=creds_data["refresh_token"],
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=creds_data["scopes"]
    )

    return build('youtube', 'v3', credentials=credentials)
