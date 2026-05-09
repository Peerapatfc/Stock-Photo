# CLAUDE.md — Stock Photo Pipeline

## Project Goal

Daily pipeline: gpt-image-2 → Real-ESRGAN upscale → IPTC metadata → Adobe Stock SFTP upload.
Target: 3 images/day, ~$4.56/month cost, sell on Adobe Stock at 33% royalty.

## Key Constraints

- **No `response_format` param on gpt-image-2** — not supported, omit it. Handle both `b64_json` and URL responses.
- **Niche slugs use `re.sub(r"[^\w]", "_", name)`** — slash in "Technical/Industrial Trades" breaks file paths.
- **exiftool required for metadata** — gracefully skip (log warning) if not found, don't crash pipeline.
- **SFTP skipped when credentials missing** — `ADOBE_STOCK_SFTP_USER/PASS` not set = pipeline continues without upload.
- **Real-ESRGAN via Replicate, not Pillow** — Adobe Stock detects and rejects simple LANCZOS upscaling.
- **All prompts must avoid real faces** — reduces Adobe Stock rejection risk and contributor rating damage.

## Architecture

```
run_daily.py → pipeline.py (error-isolated per image)
  prompt_generator → image_generator → qc_checker → upscaler → metadata_writer → adobe_stock_uploader → report
```

Each image wrapped in try/except — one failure doesn't stop the batch.

## Config Files

- `config/settings.yaml` — `daily_quota`, `contributor_name`, `upscale_model`
- `config/niches.yaml` — 4 niches with weights, cooldown_days, base_prompts, constraints
- `data/niche_usage_log.json` — tracks which niches used per date, committed back to repo by GitHub Actions

## Environment Variables

```
OPENAI_API_KEY       — gpt-image-2 + GPT-4o
REPLICATE_API_TOKEN  — Real-ESRGAN upscaling
ADOBE_STOCK_SFTP_USER — contributor SFTP username
ADOBE_STOCK_SFTP_PASS — contributor SFTP password
```

## Niche Rotation Logic

`prompt_generator.py` filters niches used within `cooldown_days`, then weighted random sample without replacement up to `daily_quota`. Saves selection to `data/niche_usage_log.json`.

## Metadata Standard

IPTC 2025.1 via exiftool ≥ 13.40 (`XMP-iptcExt` namespace). Falls back to basic fields if full write fails.
Required Adobe Stock fields: `Title`, `Description`, `Keywords`, `DigitalSourceType=trainedAlgorithmicMedia`, `By-line`.

## GitHub Actions

- Cron: `0 1 * * *` (08:00 ICT)
- Installs exiftool via `apt-get install -y libimage-exiftool-perl`
- Commits `data/niche_usage_log.json` + `logs/pipeline.log` back to repo after each run
- Uploads `output/*/ready/` as artifact (7-day retention)

## Adobe Stock SFTP

- Host: `sftp.contributor.adobestock.com` port 22
- SFTP unlocks after account is "qualified" (some approved images)
- New accounts: upload via web UI first at contributor.stock.adobe.com

## Known Issues

| Issue | Status |
|-------|--------|
| exiftool not on Windows PATH | Skip gracefully, log warning |
| SFTP creds not set | Skip upload, pipeline continues |
| gpt-image-2 400 on response_format | Fixed — param removed |
| Slash in niche name breaks filename | Fixed — regex slug |
