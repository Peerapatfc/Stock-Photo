import json
import logging
import subprocess
from pathlib import Path

from openai import OpenAI

client = OpenAI()
log = logging.getLogger(__name__)


def _generate_metadata(prompt: str, niche: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an Adobe Stock metadata specialist. "
                    "Generate SEO-optimized English metadata for commercial stock photos. "
                    "Output valid JSON only, no markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Niche: {niche}\n"
                    f"Image description: {prompt}\n\n"
                    "Return JSON with:\n"
                    '- "title": max 200 chars, descriptive, commercial English title\n'
                    '- "description": 1-2 sentences describing commercial use cases\n'
                    '- "keywords": array of 30-50 English keywords, most relevant first, no duplicates'
                ),
            },
        ],
        max_tokens=600,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def write(image_path: Path, prompt: str, niche: str, contributor_name: str) -> None:
    meta = _generate_metadata(prompt, niche)
    title = meta.get("title", niche)[:200]
    description = meta.get("description", "")
    keywords = ", ".join(meta.get("keywords", [])[:50])

    success = _run_exiftool_full(image_path, title, description, keywords, prompt, contributor_name)
    if not success:
        log.warning(f"Full IPTC write failed for {image_path.name}, falling back to basic fields")
        _run_exiftool_basic(image_path, title, description, keywords, contributor_name)


def _run_exiftool_full(
    image_path: Path,
    title: str,
    description: str,
    keywords: str,
    prompt: str,
    contributor_name: str,
) -> bool:
    cmd = [
        "exiftool",
        f"-Title={title}",
        f"-Description={description}",
        f"-Keywords={keywords}",
        "-XMP-iptcExt:DigitalSourceType=trainedAlgorithmicMedia",
        "-XMP-plus:ModelStatus=NotAModel",
        f"-IPTC:By-line={contributor_name}",
        f"-XMP-iptcExt:AISystemUsed=OpenAI gpt-image-2",
        "-XMP-iptcExt:AISystemVersionUsed=gpt-image-2-medium",
        f"-XMP-iptcExt:AIPromptInformation={prompt[:1000]}",
        f"-XMP-iptcExt:AIPromptWriterName={contributor_name}",
        "-overwrite_original",
        str(image_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        log.warning("exiftool not found — metadata skipped (install exiftool and add to PATH)")
        return False
    if result.returncode == 0:
        log.info(f"Metadata written (full IPTC 2025.1): {image_path.name}")
        return True
    log.debug(f"exiftool stderr: {result.stderr.strip()}")
    return False


def _run_exiftool_basic(
    image_path: Path,
    title: str,
    description: str,
    keywords: str,
    contributor_name: str,
) -> None:
    cmd = [
        "exiftool",
        f"-Title={title}",
        f"-Description={description}",
        f"-Keywords={keywords}",
        "-XMP-iptcExt:DigitalSourceType=trainedAlgorithmicMedia",
        f"-IPTC:By-line={contributor_name}",
        "-overwrite_original",
        str(image_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        log.warning("exiftool not found — metadata skipped")
        return
    if result.returncode == 0:
        log.info(f"Metadata written (basic fallback): {image_path.name}")
    else:
        log.error(f"exiftool basic fallback failed: {result.stderr.strip()}")
