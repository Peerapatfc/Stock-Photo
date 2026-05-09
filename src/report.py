import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

COST_PER_IMAGE = 0.041   # gpt-image-2 medium 1536x1024
COST_PER_UPSCALE = 0.003  # Replicate Real-ESRGAN
COST_GPT4O_FIXED = 0.02   # prompt expand + keyword gen per run


def write(results: dict, log_path: Path) -> None:
    today = date.today().isoformat()
    ok = results.get("ok", [])
    failed = results.get("failed", [])

    cost = len(ok) * (COST_PER_IMAGE + COST_PER_UPSCALE) + COST_GPT4O_FIXED

    lines = [
        f"\n[{today}] Pipeline complete",
        f"  Succeeded : {len(ok)}",
        f"  Failed    : {len(failed)}",
        f"  Est. cost : ${cost:.3f}",
    ]

    for f in failed:
        lines.append(f"  FAIL [{f['niche']}]: {f['error']}")

    text = "\n".join(lines)
    print(text)
    log.info(text)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")
