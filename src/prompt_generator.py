import json
import logging
import random
from datetime import date, timedelta
from pathlib import Path

import yaml
from openai import OpenAI

from . import market_insights

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


def _select_niches(
    niches: list[dict], log: dict, today: date, quota: int, multipliers: dict[str, float] | None = None
) -> list[dict]:
    available = [n for n in niches if not _is_on_cooldown(n, log, today)]
    if not available:
        available = niches  # fallback: all on cooldown

    multipliers = multipliers or {}
    weights = [n["weight"] * multipliers.get(n["name"], 1.0) for n in available]
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


def load_subject_log(path: Path) -> dict:
    """niche name -> {base_prompt: ISO date it was last used}."""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _pick_subject(niche: dict, subject_log: dict, today: date) -> str:
    """Least-recently-used base prompt, so a niche never repeats a subject until all others were used."""
    used = subject_log.get(niche["name"], {})
    oldest = min(used.get(p, "") for p in niche["base_prompts"])
    candidates = [p for p in niche["base_prompts"] if used.get(p, "") == oldest]
    choice = random.choice(candidates)
    used[choice] = today.isoformat()
    # drop prompts that were removed from niches.yaml so the log stays bounded
    subject_log[niche["name"]] = {p: d for p, d in used.items() if p in niche["base_prompts"]}
    return choice


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
        model="gpt-4o-mini",
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
                    "Neutral accurate colors, moderate contrast. "
                    "EXPOSURE RULES (automated QC rejects clipped highlights, crushed blacks and extreme contrast): "
                    "evenly lit mid-tone scenes with open, soft shadows. Use light grey, beige, wood or stone "
                    "backgrounds — never pure white backdrops, fog or glare, and never black velvet, black "
                    "backgrounds, dark rooms, spark showers, UV light or glowing screens. "
                    "Output only the prompt text, nothing else."
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
    subject_log_path: Path | None = None,
) -> list[tuple[str, str]]:
    if today is None:
        today = date.today()
    if subject_log_path is None:
        subject_log_path = log_path.with_name("subject_usage_log.json")
    niches = load_niches(niches_path)
    log = load_usage_log(log_path)
    subject_log = load_subject_log(subject_log_path)
    insights = market_insights.load(log_path.with_name("market_insights.json"))
    multipliers = market_insights.niche_multipliers(insights, today)
    if multipliers:
        logging.getLogger(__name__).info(
            "Market weights: " + ", ".join(f"{n}={m:.2f}" for n, m in sorted(multipliers.items()))
        )
    selected = _select_niches(niches, log, today, quota, multipliers)

    results = []
    for niche in selected:
        base = _pick_subject(niche, subject_log, today)
        prompt = _expand_prompt(base, niche["name"])
        results.append((prompt, niche["name"]))

    save_usage_log(subject_log_path, subject_log)
    return results


def update_usage_log(log_path: Path, used_niches: list[str], today: date | None = None) -> None:
    if today is None:
        today = date.today()
    log = load_usage_log(log_path)
    log[today.isoformat()] = used_niches
    cutoff = (today - timedelta(days=30)).isoformat()
    log = {k: v for k, v in log.items() if k >= cutoff}
    save_usage_log(log_path, log)
