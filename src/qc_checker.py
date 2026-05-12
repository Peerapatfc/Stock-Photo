import logging
import shutil
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

log = logging.getLogger(__name__)


MIN_WIDTH = 1024
MIN_HEIGHT = 1024
MIN_FILE_BYTES = 200 * 1024  # 200KB
MIN_SHARPNESS = 80      # Laplacian edge variance; below = soft/blurry
MAX_OVEREXPOSED = 0.12  # max fraction of pixels above 250 brightness
MAX_UNDEREXPOSED = 0.12 # max fraction of pixels below 10 brightness


def _sharpness_score(img: Image.Image) -> float:
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    return ImageStat.Stat(edges).var[0]


def _exposure_fractions(img: Image.Image) -> tuple[float, float]:
    hist = img.convert("L").histogram()  # 256 bins
    total = sum(hist)
    overexposed = sum(hist[250:]) / total
    underexposed = sum(hist[:10]) / total
    return overexposed, underexposed


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
                img = img.convert("RGB")
                img.save(image_path)
                log.info(f"Converted RGBA→RGB: {image_path.name}")
            elif img.mode != "RGB":
                _reject(image_path, rejected_dir, f"unsupported mode ({img.mode})")
                return False

            score = _sharpness_score(img)
            log.info(f"Sharpness score: {score:.1f} ({image_path.name})")
            if score < MIN_SHARPNESS:
                _reject(image_path, rejected_dir, f"too soft/blurry (sharpness={score:.1f} < {MIN_SHARPNESS})")
                return False

            over, under = _exposure_fractions(img)
            log.info(f"Exposure — overexposed: {over:.1%}, underexposed: {under:.1%} ({image_path.name})")
            if over > MAX_OVEREXPOSED:
                _reject(image_path, rejected_dir, f"overexposed ({over:.1%} pixels > 250)")
                return False
            if under > MAX_UNDEREXPOSED:
                _reject(image_path, rejected_dir, f"underexposed ({under:.1%} pixels < 10)")
                return False

        return True

    except Exception as e:
        _reject(image_path, rejected_dir, f"error: {e}")
        return False


def _reject(image_path: Path, rejected_dir: Path, reason: str) -> None:
    rejected_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(image_path), str(rejected_dir / image_path.name))
    log.warning(f"QC rejected {image_path.name}: {reason}")
