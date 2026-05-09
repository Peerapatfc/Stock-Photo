import base64
import json
import logging
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

client = OpenAI()
log = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))
def generate_image(prompt: str) -> bytes:
    log.info("Generating image via gpt-image-2...")
    response = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        size="1536x1024",
        quality="medium",
        n=1,
    )
    data = response.data[0]
    if data.b64_json:
        return base64.b64decode(data.b64_json)
    with urllib.request.urlopen(data.url) as r:
        return r.read()


def save_generated(img_bytes: bytes, prompt: str, niche: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    slug = re.sub(r"[^\w]", "_", niche.lower())[:20]
    img_path = output_dir / f"{ts}_{slug}.png"
    img_path.write_bytes(img_bytes)

    sidecar = img_path.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "prompt": prompt,
                "niche": niche,
                "model": "gpt-image-2",
                "size": "1536x1024",
                "quality": "medium",
                "generated_at": datetime.now().isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    log.info(f"Saved: {img_path.name} ({len(img_bytes) // 1024}KB)")
    return img_path
