from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.responses import RedirectResponse
from open_notebook.services.oauth2_service import OAuth2Service
from open_notebook.domain.credentials import OAuth2Credentials
from open_notebook.services.session_service import SessionService
import secrets

router = APIRouter()

def get_session_service(request: Request) -> SessionService:
    return SessionService(request)

@router.get("/oauth2/{provider}/login")
async def oauth2_login(provider: str, session: SessionService = Depends(get_session_service)):
    """
    Redirects the user to the provider's authorization URL.
    """
    try:
        oauth_service = OAuth2Service(provider)
        state = secrets.token_urlsafe(32)
        session.set("oauth_state", state)
        authorization_url = await oauth_service.get_authorization_url(state)
        return RedirectResponse(authorization_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/oauth2/{provider}/callback")
async def oauth2_callback(provider: str, code: str, state: str, session: SessionService = Depends(get_session_service)):
    """
    Handles the callback from the provider.
    """
    # Verify state to prevent CSRF attacks
    if state != session.pop("oauth_state", None):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        oauth_service = OAuth2Service(provider)
        token = await oauth_service.exchange_code_for_token(code)
        authorized_credentials = oauth_service.build_authorized_user_info(token)

        # Store the credentials in the database
        # We are storing credentials globally for now.
        # In a multi-user setup, this should be associated with the current user.
        
        from open_notebook.database.repository import repo_query
        
        existing_credentials_data = await repo_query(
            "SELECT * FROM oauth2_credentials WHERE provider = $provider",
            {"provider": provider},
        )
        
        if existing_credentials_data:
            credentials = OAuth2Credentials(**existing_credentials_data[0])
            credentials.credentials = authorized_credentials
            await credentials.save()
        else:
            credentials = OAuth2Credentials(provider=provider, credentials=authorized_credentials)
            await credentials.save()

        # Redirect the user to the frontend settings page, or a success page
        return RedirectResponse(url="/settings/integrations?success=true")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
