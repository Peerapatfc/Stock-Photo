import logging
import shutil
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

MIN_WIDTH = 1024
MIN_HEIGHT = 1024
MIN_FILE_BYTES = 200 * 1024  # 200KB


def check(image_path: Path, rejected_dir: Path) -> bool:
    try:
        if image_path.stat().st_size < MIN_FILE_BYTES:
            _reject(image_path, rejected_dir, f"file too small ({image_path.stat().st_size} bytes)")
            return False

        with Image.open(image_path) as img:
            w, h = img.size
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                _reject(image_path, rejected_dir, f"resolution too low ({w}x{h})")
                return False

            if img.mode == "RGBA":
                rgb = img.convert("RGB")
                rgb.save(image_path)
                log.info(f"Converted RGBA→RGB: {image_path.name}")
            elif img.mode != "RGB":
                _reject(image_path, rejected_dir, f"unsupported mode ({img.mode})")
                return False

        return True

    except Exception as e:
        _reject(image_path, rejected_dir, f"error: {e}")
        return False


def _reject(image_path: Path, rejected_dir: Path, reason: str) -> None:
    rejected_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(image_path), str(rejected_dir / image_path.name))
    log.warning(f"QC rejected {image_path.name}: {reason}")
