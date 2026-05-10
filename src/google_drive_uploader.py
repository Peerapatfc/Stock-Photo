import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_REQUIRED_ENV = (
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_OAUTH_REFRESH_TOKEN",
    "GOOGLE_DRIVE_FOLDER_ID",
)


def _creds_available() -> bool:
    return all(os.environ.get(k) for k in _REQUIRED_ENV)


def _get_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def create_run_folder(run_date: str) -> tuple[str, str] | tuple[None, None]:
    """Create a YYYY-MM-DD subfolder under GOOGLE_DRIVE_FOLDER_ID. Returns (folder_id, link) or (None, None)."""
    if not _creds_available():
        log.warning("Google Drive creds not set — skipping Drive upload")
        return None, None
    try:
        service = _get_service()
        parent_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
        meta = {
            "name": run_date,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=meta, fields="id,webViewLink").execute()
        log.info(f"Drive folder created: {folder['webViewLink']}")
        return folder["id"], folder["webViewLink"]
    except Exception as e:
        log.error(f"Drive folder creation failed: {e}")
        return None, None


def upload(ready_path: Path, folder_id: str) -> str | None:
    """Upload a single file to Drive folder. Returns webViewLink or None on error."""
    from googleapiclient.http import MediaFileUpload

    try:
        service = _get_service()
        meta = {"name": ready_path.name, "parents": [folder_id]}
        media = MediaFileUpload(str(ready_path), mimetype="image/png", resumable=False)
        f = service.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
        log.info(f"Uploaded to Drive: {f['webViewLink']}")
        return f["webViewLink"]
    except Exception as e:
        log.error(f"Drive upload failed [{ready_path.name}]: {e}")
        return None
