import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

COST_PER_IMAGE = 0.041
COST_PER_UPSCALE = 0.003
COST_GPT4O_FIXED = 0.002

_API = "https://api.telegram.org/bot{token}/{method}"


def _creds_available() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN")) and bool(os.environ.get("TELEGRAM_CHAT_ID"))


def _api_url(method: str) -> str:
    return _API.format(token=os.environ["TELEGRAM_BOT_TOKEN"], method=method)


def _build_caption(results: dict, today_str: str, drive_link: str | None) -> str:
    ok = results.get("ok", [])
    failed = results.get("failed", [])
    cost = len(ok) * (COST_PER_IMAGE + COST_PER_UPSCALE) + COST_GPT4O_FIXED

    lines = [
        f"<b>📸 Stock Photo Pipeline — {today_str}</b>",
        "",
        f"✅ Generated: {len(ok)}",
        f"💰 Est. cost: ${cost:.3f}",
    ]

    if failed:
        lines.append(f"❌ Failed: {len(failed)}")
        for f in failed:
            lines.append(f"  • {f['niche']}: {f['error']}")

    if drive_link:
        lines.append("")
        lines.append(f'📁 <a href="{drive_link}">Open in Drive</a>')

    return "\n".join(lines)


def _send_photo(chat_id: str, image_path: Path, caption: str) -> None:
    import httpx

    with open(image_path, "rb") as f:
        r = httpx.post(
            _api_url("sendPhoto"),
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"photo": (image_path.name, f, "image/png")},
            timeout=60,
        )
    r.raise_for_status()


def _send_message(chat_id: str, text: str) -> None:
    import httpx

    r = httpx.post(
        _api_url("sendMessage"),
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    r.raise_for_status()


def send_report(results: dict, today_str: str, drive_link: str | None = None) -> None:
    """Send pipeline summary to Telegram. Skip gracefully if creds not set."""
    if not _creds_available():
        log.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set — skipping Telegram notification")
        return

    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    caption = _build_caption(results, today_str, drive_link)

    ok_paths = results.get("ok", [])
    sample = Path(ok_paths[0]) if ok_paths else None

    try:
        if sample and sample.exists():
            _send_photo(chat_id, sample, caption)
        else:
            _send_message(chat_id, caption)
        log.info("Telegram notification sent")
    except Exception as e:
        log.error(f"Telegram notification failed: {e}")
