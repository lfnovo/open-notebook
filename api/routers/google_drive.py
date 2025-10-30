from fastapi import APIRouter, HTTPException
from open_notebook.services.google_drive_service import GoogleDriveService
from open_notebook.domain.credentials import OAuth2Credentials

router = APIRouter()

@router.get("/google-drive/files")
async def list_google_drive_files():
    """
    Lists files from the user's Google Drive.
    """
    try:
        # For now, we assume global credentials for a single user.
        from open_notebook.database.repository import repo_query
        
        existing_credentials_data = await repo_query(
            "SELECT * FROM oauth2_credentials WHERE provider = 'google'",
        )

        if not existing_credentials_data:
            raise HTTPException(status_code=401, detail="Google Drive not authenticated.")

        credentials = OAuth2Credentials(**existing_credentials_data[0])
        
        service = GoogleDriveService(credentials.credentials)
        files = service.list_files()
        return {"files": files}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
