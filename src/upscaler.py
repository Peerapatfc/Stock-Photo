import logging
import os
import urllib.request
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

MODEL = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b"
TARGET_SIZE = (3072, 2048)  # 2x of the 1536x1024 source
TILE = 512
TILE_PAD = 16

_model = None


def _weights_path() -> str | None:
    return os.environ.get("REALESRGAN_WEIGHTS")


def _build_model(weights: str):
    """realesr-general-x4v3 (SRVGGNetCompact), same architecture as xinntao/Real-ESRGAN, CPU inference."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class SRVGGNetCompact(nn.Module):
        def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4):
            super().__init__()
            self.upscale = upscale
            self.body = nn.ModuleList([nn.Conv2d(num_in_ch, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)])
            for _ in range(num_conv):
                self.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
                self.body.append(nn.PReLU(num_parameters=num_feat))
            self.body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
            self.upsampler = nn.PixelShuffle(upscale)

        def forward(self, x):
            out = x
            for layer in self.body:
                out = layer(out)
            out = self.upsampler(out)
            return out + F.interpolate(x, scale_factor=self.upscale, mode="nearest")

    net = SRVGGNetCompact()
    state = torch.load(weights, map_location="cpu", weights_only=True)
    net.load_state_dict(state["params_ema"] if "params_ema" in state else state["params"], strict=True)
    return net.train(False)


def _upscale_local(weights: str, input_path: Path, output_path: Path) -> None:
    import numpy as np
    import torch

    global _model
    if _model is None:
        _model = _build_model(weights)

    with Image.open(input_path) as im:
        arr = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    x = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    _, _, h, w = x.shape
    scale = 4
    out = torch.zeros(1, 3, h * scale, w * scale)

    with torch.no_grad():
        for y0 in range(0, h, TILE):
            for x0 in range(0, w, TILE):
                y1, x1 = min(y0 + TILE, h), min(x0 + TILE, w)
                py0, px0 = max(y0 - TILE_PAD, 0), max(x0 - TILE_PAD, 0)
                py1, px1 = min(y1 + TILE_PAD, h), min(x1 + TILE_PAD, w)
                tile_out = _model(x[:, :, py0:py1, px0:px1])
                oy0, ox0 = (y0 - py0) * scale, (x0 - px0) * scale
                out[:, :, y0 * scale:y1 * scale, x0 * scale:x1 * scale] = tile_out[
                    :, :, oy0:oy0 + (y1 - y0) * scale, ox0:ox0 + (x1 - x0) * scale
                ]

    res = (out.squeeze(0).clamp_(0, 1).permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
    img = Image.fromarray(res)
    if img.size != TARGET_SIZE:
        img = img.resize(TARGET_SIZE, Image.LANCZOS)  # downscale from 4x, not an upscale
    img.save(output_path, "JPEG", quality=95, subsampling=0)


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

    weights = _weights_path()
    if weights:
        log.info(f"Upscaling {input_path.name} via local Real-ESRGAN general-x4v3 (CPU)...")
        _upscale_local(weights, input_path, output_path)
    else:
        log.info(f"Upscaling {input_path.name} via Real-ESRGAN (Replicate)...")
        _upscale_replicate(input_path, output_path)

    log.info(f"Upscaled → {output_path.name} ({output_path.stat().st_size // 1024}KB)")
    return output_path
