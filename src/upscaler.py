import logging
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

MODEL = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b"
TARGET_SIZE = (3072, 2048)  # 2x of the 1536x1024 source


def _local_binary() -> str | None:
    return os.environ.get("REALESRGAN_BIN") or shutil.which("realesrgan-ncnn-vulkan")


def _upscale_local(binary: str, input_path: Path, output_path: Path) -> None:
    """Run realesrgan-ncnn-vulkan (free). On GPU-less runners device 0 is mesa's llvmpipe (software Vulkan);
    this build rejects `-g -1` ("invalid gpu device")."""
    tmp_png = output_path.with_suffix(".esrgan.png")
    cmd = [binary, "-i", str(input_path), "-o", str(tmp_png), "-n", "realesrgan-x4plus", "-s", "4", "-g", "0"]
    # the binary resolves models/ relative to its own directory
    subprocess.run(cmd, check=True, cwd=Path(binary).parent, timeout=1800)
    try:
        with Image.open(tmp_png) as img:
            img = img.convert("RGB")
            if img.size != TARGET_SIZE:
                img = img.resize(TARGET_SIZE, Image.LANCZOS)  # downscale from 4x, not an upscale
            img.save(output_path, "JPEG", quality=95, subsampling=0)
    finally:
        tmp_png.unlink(missing_ok=True)


def _upscale_replicate(input_path: Path, output_path: Path) -> None:
    import replicate

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


def upscale(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    binary = _local_binary()
    if binary:
        log.info(f"Upscaling {input_path.name} via local Real-ESRGAN ({binary})...")
        _upscale_local(binary, input_path, output_path)
    else:
        log.info(f"Upscaling {input_path.name} via Real-ESRGAN (Replicate)...")
        _upscale_replicate(input_path, output_path)

    log.info(f"Upscaled → {output_path.name} ({output_path.stat().st_size // 1024}KB)")
    return output_path
