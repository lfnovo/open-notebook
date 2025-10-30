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
