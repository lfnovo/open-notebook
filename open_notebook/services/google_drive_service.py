from __future__ import annotations
from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from open_notebook.config.oauth_providers import OAUTH_PROVIDERS

class GoogleDriveService:
    def __init__(self, credentials: Dict[str, Any]):
        provider_config = OAUTH_PROVIDERS.get("google", {})
        info = credentials.copy()

        info.setdefault("client_id", provider_config.get("client_id"))
        info.setdefault("client_secret", provider_config.get("client_secret"))
        info.setdefault("token_uri", provider_config.get("token_url"))
        info.setdefault("type", "authorized_user")

        if "token" not in info and "access_token" in info:
            info["token"] = info.get("access_token")

        scopes = info.get("scopes") or info.get("scope") or provider_config.get("scopes", [])
        if isinstance(scopes, str):
            scopes = scopes.split()
        info["scopes"] = scopes
        info.pop("scope", None)

        missing = [field for field in ("client_id", "client_secret", "token_uri") if not info.get(field)]
        if missing:
            raise ValueError(
                "Missing required Google OAuth configuration: " + ", ".join(missing)
            )

        self.creds = Credentials.from_authorized_user_info(info=info)

    def list_files(self) -> List[Dict[str, Any]]:
        """Lists the user's files in Google Drive."""
        service = build("drive", "v3", credentials=self.creds)

        results = (
            service.files()
            .list(pageSize=10, fields="nextPageToken, files(id, name)")
            .execute()
        )
        items = results.get("files", [])

        return items
