from typing import Dict, Any
from authlib.integrations.httpx_client import AsyncOAuth2Client
from open_notebook.config.oauth_providers import OAUTH_PROVIDERS

class OAuth2Service:
    def __init__(self, provider: str):
        if provider not in OAUTH_PROVIDERS:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        self.provider_config = OAUTH_PROVIDERS[provider]
        self.client = AsyncOAuth2Client(
            client_id=self.provider_config["client_id"],
            client_secret=self.provider_config["client_secret"],
            redirect_uri=self.provider_config["redirect_uri"],
            scope=" ".join(self.provider_config["scopes"]),
        )

    async def get_authorization_url(self, state: str) -> str:
        authorization_url, _ = self.client.create_authorization_url(
            self.provider_config["authorization_url"], state=state
        )
        return authorization_url

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        token = await self.client.fetch_token(
            self.provider_config["token_url"],
            grant_type="authorization_code",
            code=code,
        )
        return token

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        token = await self.client.fetch_token(
            self.provider_config["token_url"],
            grant_type="refresh_token",
            refresh_token=refresh_token,
        )
        return token

    def build_authorized_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Augment the fetched token with provider fields required by Google auth."""
        info: Dict[str, Any] = token.copy()

        # The google client expects a top-level "token" field.
        if "token" not in info and "access_token" in info:
            info["token"] = info.get("access_token")

        # Normalize scopes to a list so google-auth accepts them.
        scopes: Any = info.get("scopes") or info.get("scope")
        if isinstance(scopes, str):
            scopes = scopes.split()
        if scopes is None:
            scopes = self.provider_config.get("scopes", [])
        info["scopes"] = scopes
        info.pop("scope", None)

        info.setdefault("client_id", self.provider_config["client_id"])
        info.setdefault("client_secret", self.provider_config["client_secret"])
        info.setdefault("token_uri", self.provider_config.get("token_url"))
        info.setdefault("type", "authorized_user")

        return info
