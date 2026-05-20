import logging
import shutil
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

log = logging.getLogger(__name__)


MIN_WIDTH = 1024
MIN_HEIGHT = 1024
MIN_FILE_BYTES = 200 * 1024  # 200KB
MIN_SHARPNESS = 120     # raised from 80; Adobe rejects soft focus below this
MAX_OVEREXPOSED = 0.06  # tightened from 0.12; gpt-image-2 "high" blows highlights
MAX_UNDEREXPOSED = 0.08 # asymmetric: dark niches need slightly more room than bright
MAX_MEAN_SATURATION = 160    # HSV-S mean (0-255); above = oversaturated/filtered look
MAX_HIGH_SAT_FRACTION = 0.30 # fraction of pixels with S > 200; above = neon artifact
MAX_CONTRAST_RATIO = 12.0    # p99/p5 brightness ratio; above = extreme contrast flag


def _sharpness_score(img: Image.Image) -> float:
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    return ImageStat.Stat(edges).var[0]


def _exposure_fractions(img: Image.Image) -> tuple[float, float]:
    hist = img.convert("L").histogram()  # 256 bins
    total = sum(hist)
    overexposed = sum(hist[250:]) / total
    underexposed = sum(hist[:10]) / total
    return overexposed, underexposed


def _saturation_stats(img: Image.Image) -> tuple[float, float]:
    # Downsample for speed; saturation is spatially smooth
    small = img.resize((256, 170), Image.LANCZOS)
    pixels = list(zip(*[list(c.getdata()) for c in small.split()]))
    sat_values = [
        ((max(r, g, b) - min(r, g, b)) / max(r, g, b) * 255) if max(r, g, b) > 0 else 0
        for r, g, b in pixels
    ]
    total = len(sat_values)
    return sum(sat_values) / total, sum(1 for s in sat_values if s > 200) / total


def _contrast_ratio(img: Image.Image) -> float:
    hist = img.convert("L").histogram()
    total = sum(hist)
    cumulative = 0
    p5_val = 5
    for i, count in enumerate(hist):
        cumulative += count
        if cumulative >= total * 0.05:
            p5_val = max(i, 5)  # floor at 5 to avoid division near-zero
            break
    cumulative = 0
    p99_val = 255
    for i in range(255, -1, -1):
        cumulative += hist[i]
        if cumulative >= total * 0.01:
            p99_val = i
            break
    return p99_val / p5_val


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

            mean_sat, high_sat = _saturation_stats(img)
            log.info(f"Saturation — mean: {mean_sat:.1f}, high_frac: {high_sat:.1%} ({image_path.name})")
            if mean_sat > MAX_MEAN_SATURATION:
                _reject(image_path, rejected_dir, f"oversaturated (mean HSV-S={mean_sat:.1f})")
                return False
            if high_sat > MAX_HIGH_SAT_FRACTION:
                _reject(image_path, rejected_dir, f"excessive neon/filtering ({high_sat:.1%} pixels S>200)")
                return False

            contrast = _contrast_ratio(img)
            log.info(f"Contrast ratio (p99/p5): {contrast:.1f} ({image_path.name})")
            if contrast > MAX_CONTRAST_RATIO:
                _reject(image_path, rejected_dir, f"extreme contrast ({contrast:.1f})")
                return False

        return True

    except Exception as e:
        _reject(image_path, rejected_dir, f"error: {e}")
        return False


def check_post_upscale(image_path: Path, rejected_dir: Path) -> bool:
    """QC gate after Real-ESRGAN upscale — catches halos, ringing, and color drift."""
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Normalize to pre-upscale resolution so sharpness scores are comparable
            normalized = img.resize((1536, 1024), Image.LANCZOS)
            score = _sharpness_score(normalized)
            log.info(f"Post-upscale sharpness (normalized): {score:.1f} ({image_path.name})")
            if score < MIN_SHARPNESS:
                _reject(image_path, rejected_dir, f"post-upscale: soft after upscaling (sharpness={score:.1f})")
                return False

            mean_sat, high_sat = _saturation_stats(img)
            log.info(f"Post-upscale saturation — mean: {mean_sat:.1f}, high_frac: {high_sat:.1%}")
            if mean_sat > MAX_MEAN_SATURATION or high_sat > MAX_HIGH_SAT_FRACTION:
                _reject(image_path, rejected_dir, f"post-upscale: oversaturated (mean={mean_sat:.1f}, frac={high_sat:.1%})")
                return False

            over, under = _exposure_fractions(img)
            if over > MAX_OVEREXPOSED or under > MAX_UNDEREXPOSED:
                _reject(image_path, rejected_dir, f"post-upscale: exposure drift (over={over:.1%}, under={under:.1%})")
                return False

        return True

    except Exception as e:
        _reject(image_path, rejected_dir, f"post-upscale error: {e}")
        return False


def _reject(image_path: Path, rejected_dir: Path, reason: str) -> None:
    rejected_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(image_path), str(rejected_dir / image_path.name))
    log.warning(f"QC rejected {image_path.name}: {reason}")
