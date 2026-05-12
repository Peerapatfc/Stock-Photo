import logging
import urllib.request
from pathlib import Path

import replicate

log = logging.getLogger(__name__)

MODEL = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b"


def upscale(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.info(f"Upscaling {input_path.name} via Real-ESRGAN (Replicate)...")

    with open(input_path, "rb") as f:
        output = replicate.run(
            MODEL,
            input={"image": f, "scale": 4, "face_enhance": False},
        )

    if hasattr(output, "read"):
        img_bytes = output.read()
    else:
        with urllib.request.urlopen(str(output)) as resp:
            img_bytes = resp.read()

    output_path.write_bytes(img_bytes)
    log.info(f"Upscaled → {output_path.name} ({len(img_bytes) // 1024}KB)")
    return output_path
