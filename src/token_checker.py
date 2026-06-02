import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)


def _check_openai() -> tuple[bool, str]:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return False, "OPENAI_API_KEY not set"
    try:
        from openai import AuthenticationError, OpenAI
        client = OpenAI(api_key=key)
        client.models.list()
        return True, "OK"
    except AuthenticationError:
        return False, "OPENAI_API_KEY invalid (401)"
    except Exception as e:
        return False, f"OPENAI_API_KEY check failed: {e}"


def _check_replicate() -> tuple[bool, str]:
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        return False, "REPLICATE_API_TOKEN not set"
    try:
        req = urllib.request.Request(
            "https://api.replicate.com/v1/account",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10):
            return True, "OK"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "REPLICATE_API_TOKEN invalid (401)"
        return False, f"Replicate check returned {e.code}"
    except Exception as e:
        return False, f"REPLICATE_API_TOKEN check failed: {e}"


def _check_google_drive() -> tuple[bool, str]:
    required = ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
                "GOOGLE_OAUTH_REFRESH_TOKEN", "GOOGLE_DRIVE_FOLDER_ID")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        return False, f"not set: {', '.join(missing)}"
    try:
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
        }).encode()
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=data,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        if "access_token" not in body:
            return False, "token refresh returned no access_token"
        return True, "OK"
    except urllib.error.HTTPError as e:
        return False, f"Google OAuth refresh failed ({e.code})"
    except Exception as e:
        return False, f"Google Drive check failed: {e}"


def _check_telegram() -> tuple[bool, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token and not chat_id:
        return False, "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID not set"
    if not token:
        return False, "TELEGRAM_BOT_TOKEN not set"
    if not chat_id:
        return False, "TELEGRAM_CHAT_ID not set"
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        if not body.get("ok"):
            return False, "getMe returned ok=false"
        username = body["result"].get("username", "?")
        return True, f"bot @{username}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "TELEGRAM_BOT_TOKEN invalid (401)"
        return False, f"Telegram getMe returned {e.code}"
    except Exception as e:
        return False, f"Telegram check failed: {e}"


def run_checks() -> bool:
    """Check API tokens. Required tokens failure = abort. Optional = warn only."""
    required = [
        ("OpenAI", _check_openai),
        ("Replicate", _check_replicate),
        ("Google Drive", _check_google_drive),
    ]
    optional = [
        ("Telegram", _check_telegram),
    ]

    all_ok = True
    for name, fn in required:
        ok, msg = fn()
        if ok:
            log.info(f"[token_check] {name}: {msg}")
        else:
            log.error(f"[token_check] {name}: FAILED — {msg}")
            all_ok = False

    for name, fn in optional:
        ok, msg = fn()
        if ok:
            log.info(f"[token_check] {name}: {msg}")
        else:
            log.warning(f"[token_check] {name}: skipped — {msg}")

    return all_ok
