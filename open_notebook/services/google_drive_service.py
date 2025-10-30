from __future__ import annotations
from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from open_notebook.domain.credentials import OAuth2Credentials

class GoogleDriveService:
    def __init__(self, credentials: Dict[str, Any]):
        self.creds = Credentials.from_authorized_user_info(info=credentials)

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
