import json
import random
from datetime import date, timedelta
from pathlib import Path

import yaml
from openai import OpenAI

client = OpenAI()

BLOCKED_TERMS = [
    # Artist names (copyright in prompt = noncompliance)
    "greg rutkowski", "artgerm", "wlop", "alphonse mucha", "makoto shinkai",
    "kentaro miura",
    # Franchise / brand names
    "disney", "pixar", "marvel", "dc comics", "studio ghibli", "nintendo",
    "pokemon", "ghibli", "star wars", "harry potter", "batman", "superman",
    "spider-man", "iron man", "blade runner", "cyberpunk 2077", "minecraft",
    "lego", "ikea", "apple", "samsung", "coca-cola", "pepsi", "nike", "adidas",
    # Identifiable real-world locations (architecture/landmark IP)
    "eiffel tower", "burj khalifa", "empire state building", "colosseum",
    "big ben", "sydney opera house", "taj mahal", "sagrada familia",
    "chrysler building", "flatiron building", "shard", "louvre",
    "times square", "piccadilly circus",
    # Government agencies
    "nasa", "cia", "fbi", "interpol",
    # AI terms forbidden in Adobe Stock title/keywords
    "generative ai", "ai-generated", "ai generated", "artificial intelligence",
    "machine learning", "stable diffusion", "midjourney", "dall-e", "dalle",
]


def load_niches(config_path: Path) -> list[dict]:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["niches"]


def load_usage_log(log_path: Path) -> dict:
    if log_path.exists():
        with open(log_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_usage_log(log_path: Path, log: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def _is_on_cooldown(niche: dict, log: dict, today: date) -> bool:
    cooldown = niche.get("recent_cooldown_days", 3)
    for i in range(1, cooldown + 1):
        d = (today - timedelta(days=i)).isoformat()
        if niche["name"] in log.get(d, []):
            return True
    return False


def _select_niches(niches: list[dict], log: dict, today: date, quota: int) -> list[dict]:
    available = [n for n in niches if not _is_on_cooldown(n, log, today)]
    if not available:
        available = niches  # fallback: all on cooldown

    weights = [n["weight"] for n in available]
    total = sum(weights)
    norm_weights = [w / total for w in weights]

    selected = []
    pool = list(zip(available, norm_weights))

    for _ in range(quota):
        if not pool:
            pool = list(zip(available, norm_weights))
        items, ws = zip(*pool)
        chosen = random.choices(list(items), weights=list(ws), k=1)[0]
        selected.append(chosen)
        pool = [(n, w) for n, w in pool if n["name"] != chosen["name"]]

    return selected


def _sanitize(text: str) -> str:
    lower = text.lower()
    for term in BLOCKED_TERMS:
        if term in lower:
            idx = lower.find(term)
            text = text[:idx] + text[idx + len(term):]
            lower = text.lower()
    return " ".join(text.split())


def sanitize_metadata(title: str, description: str, keywords: list[str]) -> tuple[str, str, list[str]]:
    clean_kw = [kw for kw in keywords if not any(t in kw.lower() for t in BLOCKED_TERMS)]
    return _sanitize(title), _sanitize(description), clean_kw


def _expand_prompt(base_prompt: str, niche_name: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional stock photo prompt writer. "
                    "Expand the base prompt into a detailed, commercially viable image generation prompt. "
                    "Rules: no artist names, no brand names, no real people or celebrities, no watermarks. "
                    "CRITICAL — AVOID OVERSATURATED STOCK SUBJECTS (these get 'similar content' rejection): "
                    "Do NOT use: electronic circuit boards, PCB traces, fiber optic cables, neon glow effects, "
                    "glowing energy particles, data flow visualizations, mainframe computer rooms, CNC machines cutting metal, "
                    "wind turbines on hills, solar panels on rooftops, generic sunsets, hands holding seedlings, "
                    "green leaves on white backgrounds, drone cityscapes at night, aerial highway interchanges, "
                    "any cliché tech/eco/nature imagery that dominates stock photo libraries. "
                    "CRITICAL — AVOID QUALITY-FAIL SUBJECTS: Do not describe motion blur, time-lapse effects, "
                    "long exposure light trails, glowing neon aesthetics, extreme backlighting, or "
                    "heavily stylized color grading — AI renders these with visible artifacts. "
                    "Favor: specific, unusual industrial processes; scientific equipment details; "
                    "natural material textures; precision manufacturing close-ups that are underrepresented. "
                    "CRITICAL IP RULES: Never evoke recognizable fictional universes, film aesthetics, "
                    "or franchise visual styles. No Blade Runner-style neon rain cities, no Star Wars elements, "
                    "no Marvel/DC visual language, no game franchise environments. "
                    "Keep all imagery generic and commercially safe. "
                    "QUALITY RULES: Natural, balanced lighting only — window light, overcast daylight, "
                    "controlled studio softbox. No neon glow, no dramatic backlight, no HDR look. "
                    "Neutral accurate colors, moderate contrast. Output only the prompt text, nothing else."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Niche: {niche_name}\n"
                    f"Base prompt: {base_prompt}\n\n"
                    "Rewrite as a detailed, commercially differentiated version. "
                    "Change at least two of: composition angle, lighting source, subject material, scale, or setting context. "
                    "Be specific about materials (steel grade, glass type, fabric weave) and equipment details. "
                    "Describe natural or controlled studio lighting — never neon, LED color wash, or glow effects. "
                    "The resulting image must look like it was photographed in a real environment, not rendered. "
                    "End with: photorealistic, commercial stock photography, natural lighting, no people, no watermark, 4K"
                ),
            },
        ],
        max_tokens=300,
        temperature=0.9,
    )
    raw = response.choices[0].message.content.strip()
    return _sanitize(raw)


def generate_prompts(
    niches_path: Path,
    log_path: Path,
    quota: int,
    today: date | None = None,
) -> list[tuple[str, str]]:
    if today is None:
        today = date.today()
    niches = load_niches(niches_path)
    log = load_usage_log(log_path)
    selected = _select_niches(niches, log, today, quota)

    results = []
    for niche in selected:
        base = random.choice(niche["base_prompts"])
        prompt = _expand_prompt(base, niche["name"])
        results.append((prompt, niche["name"]))

    return results


def update_usage_log(log_path: Path, used_niches: list[str], today: date | None = None) -> None:
    if today is None:
        today = date.today()
    log = load_usage_log(log_path)
    log[today.isoformat()] = used_niches
    cutoff = (today - timedelta(days=30)).isoformat()
    log = {k: v for k, v in log.items() if k >= cutoff}
    save_usage_log(log_path, log)
