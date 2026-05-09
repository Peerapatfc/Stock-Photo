import logging
import os
import shutil
from datetime import date
from pathlib import Path

import yaml

from src import (
    adobe_stock_uploader,
    image_generator,
    metadata_writer,
    prompt_generator,
    qc_checker,
    report,
    upscaler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def _load_settings() -> dict:
    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline() -> None:
    settings = _load_settings()
    today = date.today()
    today_str = today.isoformat()

    quota = settings.get("daily_quota", 3)
    contributor_name = settings.get("contributor_name", "Contributor")

    sftp_user = os.environ.get("ADOBE_STOCK_SFTP_USER", "")
    sftp_pass = os.environ.get("ADOBE_STOCK_SFTP_PASS", "")
    skip_upload = not (sftp_user and sftp_pass)
    if skip_upload:
        log.warning("ADOBE_STOCK_SFTP_USER/PASS not set — skipping upload")

    niches_path = PROJECT_ROOT / "config" / "niches.yaml"
    log_path = PROJECT_ROOT / "data" / "niche_usage_log.json"
    output_root = PROJECT_ROOT / "output" / today_str
    pipeline_log = PROJECT_ROOT / "logs" / "pipeline.log"

    generated_dir = output_root / "generated"
    ready_dir = output_root / "ready"
    rejected_dir = output_root / "rejected"

    log.info(f"Pipeline start | date={today_str} quota={quota}")

    prompts = prompt_generator.generate_prompts(niches_path, log_path, quota, today)

    results: dict[str, list] = {"ok": [], "failed": []}
    used_niches: list[str] = []

    for prompt_text, niche_name in prompts:
        log.info(f"--- [{niche_name}] ---")
        try:
            img_bytes = image_generator.generate_image(prompt_text)
            raw_path = image_generator.save_generated(img_bytes, prompt_text, niche_name, generated_dir)

            if not qc_checker.check(raw_path, rejected_dir):
                results["failed"].append({"niche": niche_name, "error": "QC failed"})
                continue

            ready_path = ready_dir / (raw_path.stem + ".png")
            upscaler.upscale(raw_path, ready_path)

            metadata_writer.write(ready_path, prompt_text, niche_name, contributor_name)

            if not skip_upload:
                adobe_stock_uploader.upload(ready_path, sftp_user, sftp_pass)

            results["ok"].append(str(ready_path))
            used_niches.append(niche_name)

        except Exception as e:
            log.error(f"Failed [{niche_name}]: {e}", exc_info=True)
            results["failed"].append({"niche": niche_name, "error": str(e)})

    prompt_generator.update_usage_log(log_path, used_niches, today)
    report.write(results, pipeline_log)
