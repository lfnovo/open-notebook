from __future__ import annotations
from typing import Optional, ClassVar, Dict, Any
from open_notebook.domain.base import ObjectModel

class OAuth2Credentials(ObjectModel):
    """
    Stores OAuth 2.0 credentials for a specific provider.
    Note: In the current implementation, credentials are stored globally.
    For a multi-user setup, a user_id field should be added to associate
    credentials with individual users.
    """
    table_name: ClassVar[str] = "oauth2_credentials"
    provider: str
    credentials: Dict[str, Any] # To store the access token, refresh token, etc.
